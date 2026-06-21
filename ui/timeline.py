# ui/timeline.py
import math
import imgui
from app.state import clamp
import ui.icons as _icons
from ui.icons import ICON_VOLUME_MUTE, ICON_STAR

_BLACK_KEYS = frozenset({1, 3, 6, 8, 10})

_HEADER_ROW_H_BASE = 80
_BTN_PAD_BASE = 8
_BTN_GAP_BASE = 4
_BTN_ROUND = 3.0


def _header_metrics(scale):
    return (
        round(_HEADER_ROW_H_BASE * scale),  # row_h
        round(_BTN_PAD_BASE * scale),        # pad
        round(_BTN_GAP_BASE * scale),        # gap
    )


_HDR_BTN_PAD = 6

def _btn_size_from_icon(icon_text, font=None):
    if font:
        imgui.push_font(font)
    sz = imgui.calc_text_size(icon_text)
    if font:
        imgui.pop_font()
    side = max(sz.x, sz.y)
    return round(side + _HDR_BTN_PAD * 2)


def draw_timeline_canvas(state):
    """Unified piano roll with ghost notes and selectable track headers."""

    # Auto-fit header width on new MIDI load
    if state.midi.path and state.midi.path != getattr(state, '_header_fitted_path', ''):
        max_text_w = 0
        for i, td_fit in enumerate(state.midi.tracks):
            max_text_w = max(max_text_w, imgui.calc_text_size(f"Track {i+1}")[0])
            if td_fit.name:
                max_text_w = max(max_text_w, imgui.calc_text_size(td_fit.name)[0])
        state.track_header_w = int(clamp(max_text_w + 24, 120, 300))
        state._header_fitted_path = state.midi.path
        state._pending_pitch_fit = True

    canvas_pos = imgui.get_cursor_screen_pos()
    avail_w, avail_h = imgui.get_content_region_available()
    state.last_canvas_width = avail_w
    state.last_canvas_height = avail_h

    draw_list = imgui.get_window_draw_list()
    x0, y0 = canvas_pos
    x1, y1 = x0 + avail_w, y0 + avail_h

    sb = 18.0
    view_x1 = x1 - sb
    view_y1 = y1 - sb

    ruler_y0 = y0
    ruler_y1 = y0 + state.ruler_h
    roll_y0 = ruler_y1
    roll_y1 = view_y1

    t = state.theme
    header_x0 = x0
    header_x1 = x0 + state.track_header_w

    draw_list.add_rect_filled(x0, ruler_y0, x1, ruler_y1, imgui.get_color_u32_rgba(*t.track_header_bg))
    draw_list.add_rect_filled(header_x0, roll_y0, header_x1, roll_y1, imgui.get_color_u32_rgba(*t.track_header_bg))

    io = imgui.get_io()
    mousex, mousey = io.mouse_pos
    num_tracks = len(state.midi.tracks)
    any_starred = any(td.starred for td in state.midi.tracks)

    nh = state.note_height
    content_h = 128 * nh
    visible_h = max(1.0, roll_y1 - roll_y0)
    scroll_y_max = max(0.0, content_h - visible_h)

    # === View-menu zoom actions ===
    if state.request_reset_zoom:
        state.note_height = 10
        nh = 10
        state.px_per_beat = 30.0
        state.scroll_x_px = 0.0
        state.scroll_y_px = 0.0
        state.focused_track = None
        content_h = 128 * nh
        scroll_y_max = max(0.0, content_h - visible_h)
        state.request_reset_zoom = False

    do_fit_vert = state.request_fit_vertical or state.request_fit_all or getattr(state, '_pending_pitch_fit', False)
    do_fit_time = state.request_fit_time or state.request_fit_all

    if do_fit_vert:
        gmin, gmax = 127, 0
        for td in state.midi.tracks:
            if td.notes:
                gmin = min(gmin, td.pitch_min)
                gmax = max(gmax, td.pitch_max)
        if gmin <= gmax:
            prange = gmax - gmin + 3
            state.note_height = max(2, min(48, int(visible_h / prange)))
            nh = state.note_height
            content_h = 128 * nh
            scroll_y_max = max(0.0, content_h - visible_h)
            center_pitch = (gmin + gmax) / 2.0
            center_y = (127 - center_pitch) * nh
            state.scroll_y_px = clamp(center_y - visible_h / 2, 0, scroll_y_max)
        state._pending_pitch_fit = False

    if do_fit_time and state.midi.total_beats > 0:
        drawable_w = max(1.0, view_x1 - header_x1)
        state.px_per_beat = clamp(drawable_w / max(1.0, state.midi.total_beats), 10.0, 400.0)
        state.scroll_x_px = 0.0

    state.request_fit_time = False
    state.request_fit_vertical = False
    state.request_fit_all = False

    # === Input ===
    hovered_roll = (header_x1 <= mousex <= view_x1) and (roll_y0 <= mousey <= roll_y1)
    hovered_header = (header_x0 <= mousex <= header_x1) and (roll_y0 <= mousey <= roll_y1)

    focused = state.focused_track
    if focused is not None and (focused < 0 or focused >= num_tracks):
        state.focused_track = None
        focused = None

    # Header click — select track or toggle mute/star
    header_btn_clicked = False
    header_scroll = getattr(state, '_header_scroll_y', 0.0)
    click_row_h, click_btn_pad, click_btn_gap = _header_metrics(state.ui_scale)
    click_btn_sz = _btn_size_from_icon(ICON_VOLUME_MUTE, _icons.font_icon_sm)

    if imgui.is_mouse_clicked(0) and hovered_header:
        click_rel_y = mousey - roll_y0 + header_scroll
        ti_click = int(click_rel_y / click_row_h)
        if 0 <= ti_click < num_tracks:
            td_click = state.midi.tracks[ti_click]
            hy = roll_y0 + ti_click * click_row_h - header_scroll

            btn_y = hy + click_row_h - click_btn_sz - click_btn_pad
            mute_x = header_x0 + click_btn_pad
            star_x = mute_x + click_btn_sz + click_btn_gap

            if mute_x <= mousex <= mute_x + click_btn_sz and btn_y <= mousey <= btn_y + click_btn_sz:
                td_click.muted = not td_click.muted
                header_btn_clicked = True
            elif star_x <= mousex <= star_x + click_btn_sz and btn_y <= mousey <= btn_y + click_btn_sz:
                td_click.starred = not td_click.starred
                header_btn_clicked = True
            else:
                state.focused_track = ti_click if focused != ti_click else None
                focused = state.focused_track
                header_btn_clicked = True

    # Panning (right or middle mouse in roll area)
    if hovered_roll and (imgui.is_mouse_clicked(2) or imgui.is_mouse_clicked(1)):
        state.panning = True
        state.pan_anchor = (mousex, mousey)
        state.pan_scroll_anchor = (state.scroll_x_px, state.scroll_y_px)
    if state.panning and not (imgui.is_mouse_down(2) or imgui.is_mouse_down(1)):
        state.panning = False
    if state.panning:
        dx = mousex - state.pan_anchor[0]
        dy = mousey - state.pan_anchor[1]
        state.scroll_x_px = max(0.0, state.pan_scroll_anchor[0] - dx)
        state.scroll_y_px = clamp(state.pan_scroll_anchor[1] - dy, 0.0, scroll_y_max)
        if state.playing:
            state.tracking_enabled = False

    # Marquee selection (left drag in roll area)
    if hovered_roll and imgui.is_mouse_clicked(0) and not header_btn_clicked:
        state.marquee_active = True
        state.marquee_start = (mousex, mousey)
        state.marquee_end = (mousex, mousey)
        state.selected_notes.clear()
    if state.marquee_active and imgui.is_mouse_down(0):
        state.marquee_end = (mousex, mousey)

    # Mouse wheel
    wheel_y = io.mouse_wheel
    if abs(wheel_y) > 0:
        if hovered_header:
            if not hasattr(state, '_header_scroll_y'):
                state._header_scroll_y = 0.0
            scroll_row_h = _header_metrics(state.ui_scale)[0]
            total_hdr = num_tracks * scroll_row_h
            max_hdr_scroll = max(0.0, total_hdr - visible_h)
            state._header_scroll_y = clamp(
                getattr(state, '_header_scroll_y', 0.0) - wheel_y * 30, 0.0, max_hdr_scroll)
        elif hovered_roll:
            if io.key_ctrl:
                factor = 1.1 if wheel_y > 0 else 1.0 / 1.1
                left_beat = state.scroll_x_px / max(1e-6, state.px_per_beat)
                state.px_per_beat = clamp(state.px_per_beat * factor, 10.0, 400.0)
                state.scroll_x_px = max(0.0, left_beat * state.px_per_beat)
            elif io.key_alt:
                old_nh = nh
                mouse_y_rel = mousey - roll_y0 + state.scroll_y_px
                pitch_at_mouse = 127.0 - mouse_y_rel / max(1, old_nh)

                factor = 1.15 if wheel_y > 0 else 1.0 / 1.15
                state.note_height = max(2, min(48, round(old_nh * factor)))
                nh = state.note_height
                content_h = 128 * nh
                scroll_y_max = max(0.0, content_h - visible_h)

                new_y = (127.0 - pitch_at_mouse) * nh
                state.scroll_y_px = clamp(new_y - (mousey - roll_y0), 0.0, scroll_y_max)
            elif io.key_shift:
                state.scroll_x_px = max(0.0, state.scroll_x_px - wheel_y * 40.0)
                if state.playing:
                    state.tracking_enabled = False
            else:
                state.scroll_y_px = clamp(state.scroll_y_px - wheel_y * 40.0, 0.0, scroll_y_max)

    # Ruler seek
    if imgui.is_mouse_clicked(0):
        mx, my = io.mouse_pos
        if ruler_y0 <= my <= ruler_y1 and header_x1 <= mx <= view_x1:
            beat = (state.scroll_x_px + (mx - header_x1)) / max(1e-6, state.px_per_beat)
            state.playhead_beats = max(0.0, beat)

    state.scroll_y_px = clamp(state.scroll_y_px, 0.0, scroll_y_max)

    # Beat range
    tpq = state.midi.ticks_per_beat
    left_beat = max(0.0, state.scroll_x_px / max(1e-6, state.px_per_beat))
    right_beat = (state.scroll_x_px + avail_w) / max(1e-6, state.px_per_beat)
    vis_start_tick = int(left_beat * tpq)
    vis_end_tick = int(right_beat * tpq)

    # === Draw track headers ===
    if not hasattr(state, '_header_scroll_y'):
        state._header_scroll_y = 0.0
    header_scroll = state._header_scroll_y

    row_h, btn_pad, btn_gap = _header_metrics(state.ui_scale)
    btn_sz = _btn_size_from_icon(ICON_VOLUME_MUTE, _icons.font_icon_sm)

    draw_list.push_clip_rect(header_x0, roll_y0, header_x1, roll_y1)
    if num_tracks == 0:
        msg = "No MIDI loaded."
        msg_sz = imgui.calc_text_size(msg)
        hdr_w = header_x1 - header_x0
        hdr_h = roll_y1 - roll_y0
        draw_list.add_text(
            header_x0 + (hdr_w - msg_sz.x) * 0.5,
            roll_y0 + (hdr_h - msg_sz.y) * 0.5,
            imgui.get_color_u32_rgba(1, 1, 1, 0.9), msg)
    for ti in range(num_tracks):
        td = state.midi.tracks[ti]
        hy = roll_y0 + ti * row_h - header_scroll

        if hy + row_h < roll_y0 or hy > roll_y1:
            continue

        is_selected = (focused == ti)
        is_muted = td.muted

        if is_selected:
            bg_col = imgui.get_color_u32_rgba(0.15, 0.3, 0.5, 0.8)
        elif is_muted:
            bg_col = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 0.5)
        else:
            bg_col = imgui.get_color_u32_rgba(0.08, 0.08, 0.08, 0.8)
        draw_list.add_rect_filled(header_x0, hy, header_x1, hy + row_h, bg_col)

        # "Track N" label
        text_alpha = 0.3 if is_muted else 0.9
        draw_list.add_text(header_x0 + btn_pad, hy + 6,
                           imgui.get_color_u32_rgba(1, 1, 1, text_alpha),
                           f"Track {ti + 1}")

        # Track name underneath
        if td.name:
            name_label = td.name
            if len(name_label) > 18:
                name_label = name_label[:17] + "."
            draw_list.add_text(header_x0 + btn_pad, hy + 26,
                               imgui.get_color_u32_rgba(1, 1, 1, 0.15 if is_muted else 0.55),
                               name_label)

        # Mute button (square, playback-bar style)
        btn_y = hy + row_h - btn_sz - btn_pad
        mute_x = header_x0 + btn_pad
        mute_hov = (mute_x <= mousex <= mute_x + btn_sz
                    and btn_y <= mousey <= btn_y + btn_sz
                    and roll_y0 <= mousey <= roll_y1)
        if is_muted:
            mc = t.destructive_hint
            mute_col = imgui.get_color_u32_rgba(*mc[:3], 1.0 if mute_hov else 0.85)
        else:
            mc = t.toggle_off
            mute_col = imgui.get_color_u32_rgba(*mc[:3], 0.9 if mute_hov else 0.7)
        draw_list.add_rect_filled(mute_x, btn_y, mute_x + btn_sz,
                                  btn_y + btn_sz, mute_col, _BTN_ROUND)
        if _icons.font_icon_sm:
            imgui.push_font(_icons.font_icon_sm)
        icon_sz = imgui.calc_text_size(ICON_VOLUME_MUTE)
        draw_list.add_text(mute_x + (btn_sz - icon_sz.x) * 0.5,
                           btn_y + (btn_sz - icon_sz.y) * 0.5,
                           imgui.get_color_u32_rgba(1, 1, 1, 0.9), ICON_VOLUME_MUTE)

        # Star button (square, playback-bar style)
        star_x = mute_x + btn_sz + btn_gap
        star_hov = (star_x <= mousex <= star_x + btn_sz
                    and btn_y <= mousey <= btn_y + btn_sz
                    and roll_y0 <= mousey <= roll_y1)
        if td.starred:
            sc = t.channel_pcm
            star_col = imgui.get_color_u32_rgba(*sc[:3], 1.0 if star_hov else 0.85)
        else:
            sc = t.toggle_off
            star_col = imgui.get_color_u32_rgba(*sc[:3], 0.9 if star_hov else 0.7)
        draw_list.add_rect_filled(star_x, btn_y, star_x + btn_sz,
                                  btn_y + btn_sz, star_col, _BTN_ROUND)
        icon_sz = imgui.calc_text_size(ICON_STAR)
        draw_list.add_text(star_x + (btn_sz - icon_sz.x) * 0.5,
                           btn_y + (btn_sz - icon_sz.y) * 0.5,
                           imgui.get_color_u32_rgba(1, 1, 1, 0.9), ICON_STAR)
        if _icons.font_icon_sm:
            imgui.pop_font()

        # Bottom separator
        draw_list.add_line(header_x0, hy + row_h, header_x1, hy + row_h,
                           imgui.get_color_u32_rgba(1, 1, 1, 0.08))

    draw_list.pop_clip_rect()
    draw_list.add_line(header_x1, roll_y0, header_x1, roll_y1,
                       imgui.get_color_u32_rgba(1, 1, 1, 0.1))

    # === Piano roll background ===
    first_vis_pitch = max(0, 127 - int(math.ceil((state.scroll_y_px + visible_h) / max(1, nh))))
    last_vis_pitch = min(127, 127 - int(math.floor(state.scroll_y_px / max(1, nh))))

    black_key_col = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.04)
    for pitch in range(first_vis_pitch, last_vis_pitch + 1):
        if pitch % 12 in _BLACK_KEYS:
            py = roll_y0 + (127 - pitch) * nh - state.scroll_y_px
            py_end = py + nh
            if py_end > roll_y0 and py < roll_y1:
                draw_list.add_rect_filled(header_x1, max(roll_y0, py),
                                          view_x1, min(roll_y1, py_end), black_key_col)

    if state.playing and state.active_pitches:
        active_col = imgui.get_color_u32_rgba(*t.accent_secondary[:3], 0.12)
        for pitch in state.active_pitches:
            if first_vis_pitch <= pitch <= last_vis_pitch:
                py = roll_y0 + (127 - pitch) * nh - state.scroll_y_px
                py_end = py + nh
                if py_end > roll_y0 and py < roll_y1:
                    draw_list.add_rect_filled(header_x1, max(roll_y0, py),
                                              view_x1, min(roll_y1, py_end), active_col)

    # Which tracks to show (star filter)
    visible_tracks = []
    for ti, td in enumerate(state.midi.tracks):
        if any_starred and not td.starred:
            continue
        visible_tracks.append(ti)

    # Note colors
    note_color = imgui.get_color_u32_rgba(0.27, 0.58, 0.98, 0.95)
    border_col = imgui.get_color_u32_rgba(0.05, 0.1, 0.18, 1.0)
    ghost_color = imgui.get_color_u32_rgba(0.27, 0.58, 0.98, 0.15)
    ghost_border = imgui.get_color_u32_rgba(0.05, 0.1, 0.18, 0.25)
    playing_note_col = imgui.get_color_u32_rgba(*t.channel_fm[:3], 0.95)
    playing_border_col = imgui.get_color_u32_rgba(*(c * 0.4 for c in t.channel_fm[:3]), 1.0)
    sel_color = imgui.get_color_u32_rgba(0.98, 0.78, 0.28, 0.95)
    sel_border = imgui.get_color_u32_rgba(0.95, 0.85, 0.45, 1.0)
    muted_color = imgui.get_color_u32_rgba(0.27, 0.58, 0.98, 0.08)
    muted_border = imgui.get_color_u32_rgba(0.05, 0.1, 0.18, 0.15)

    playhead_b = state.playhead_beats if state.playing else None

    # Two-pass: ghost notes behind, active notes on top
    for pass_idx in (0, 1):
        for ti in visible_tracks:
            td = state.midi.tracks[ti]
            is_active = (focused is None or focused == ti)

            if pass_idx == 0 and is_active:
                continue
            if pass_idx == 1 and not is_active:
                continue

            is_muted = td.muted

            for ni, n in enumerate(td.notes):
                if n.end_tick < vis_start_tick or n.start_tick > vis_end_tick:
                    continue

                start_b = n.start_tick / float(tpq or 1)
                end_b = n.end_tick / float(tpq or 1)
                xs = header_x1 + start_b * state.px_per_beat - state.scroll_x_px
                xe = header_x1 + end_b * state.px_per_beat - state.scroll_x_px
                if xe < header_x1 or xs > view_x1:
                    continue

                yn = roll_y0 + (127 - n.pitch) * nh - state.scroll_y_px
                yn2 = yn + nh - 1
                if yn2 < roll_y0 or yn > roll_y1:
                    continue

                x1c = max(header_x1, xs)
                x2c = min(view_x1, xe)
                y1c = max(roll_y0, yn)
                y2c = min(roll_y1, yn2)

                is_playing_now = playhead_b is not None and start_b <= playhead_b < end_b
                sel = (ti, ni) in state.selected_notes

                if not is_active:
                    fill = ghost_color
                    edge = ghost_border
                elif is_muted:
                    fill = muted_color
                    edge = muted_border
                elif is_playing_now:
                    fill = playing_note_col
                    edge = playing_border_col
                elif sel:
                    fill = sel_color
                    edge = sel_border
                else:
                    fill = note_color
                    edge = border_col

                draw_list.add_rect_filled(x1c, y1c, x2c, y2c, fill)
                draw_list.add_rect(x1c, y1c, x2c, y2c, edge)

    # === Vertical grid ===
    header_x = header_x1
    col_bar_grid = imgui.get_color_u32_rgba(1, 1, 1, 0.18)
    col_beat_grid = imgui.get_color_u32_rgba(1, 1, 1, 0.12)
    col_8th = imgui.get_color_u32_rgba(1, 1, 1, 0.07)
    col_16th = imgui.get_color_u32_rgba(1, 1, 1, 0.045)
    col_tick_ruler = imgui.get_color_u32_rgba(1, 1, 1, 0.18)

    def _vline(bp, col):
        X = header_x + bp * state.px_per_beat - state.scroll_x_px
        if header_x <= X <= view_x1:
            draw_list.add_line(X, roll_y0, X, roll_y1, col)

    def _tick_ruler(bp, th, col):
        X = header_x + bp * state.px_per_beat - state.scroll_x_px
        if header_x <= X <= view_x1:
            draw_list.add_line(X, ruler_y1 - th, X, ruler_y1, col)

    show_beats = state.px_per_beat >= 15.0
    show_8th = state.px_per_beat >= 50.0
    show_16th = state.px_per_beat >= 90.0

    if show_16th:
        step = 0.25
        i = math.ceil(left_beat / step)
        while i * step <= right_beat:
            _vline(i * step, col_16th)
            i += 1
    elif show_8th:
        step = 0.5
        i = math.ceil(left_beat / step)
        while i * step <= right_beat:
            _vline(i * step, col_8th)
            i += 1

    for seg in state.midi.ts_segments:
        seg_left = max(left_beat, seg['start_beats'])
        seg_right = min(right_beat, seg['end_beats'])
        if seg_left >= seg_right:
            continue
        bar_len = seg['bar_len']
        beat_len = seg['beat_len']
        num = seg['num']
        k0 = max(0, int(math.floor((seg_left - seg['start_beats']) / max(1e-9, bar_len))))
        k1 = int(math.floor((seg_right - seg['start_beats']) / max(1e-9, bar_len)))
        for k in range(k0, k1 + 1):
            mpos = seg['start_beats'] + k * bar_len
            _vline(mpos, col_bar_grid)
            if show_beats:
                for j in range(1, num):
                    bpos = mpos + j * beat_len
                    if seg['start_beats'] <= bpos <= seg['end_beats'] and left_beat <= bpos <= right_beat:
                        _vline(bpos, col_beat_grid)

    # === Ruler ===
    draw_list.add_rect_filled(x0, ruler_y0, x1, ruler_y1, imgui.get_color_u32_rgba(*t.track_header_bg))
    for seg in state.midi.ts_segments:
        seg_left = max(left_beat, seg['start_beats'])
        seg_right = min(right_beat, seg['end_beats'])
        if seg_left >= seg_right:
            continue
        bar_len = seg['bar_len']
        beat_len = seg['beat_len']
        num = seg['num']
        k0 = max(0, int(math.floor((seg_left - seg['start_beats']) / max(1e-9, bar_len))))
        k1 = int(math.floor((seg_right - seg['start_beats']) / max(1e-9, bar_len)))
        for k in range(k0, k1 + 1):
            mpos = seg['start_beats'] + k * bar_len
            _tick_ruler(mpos, 14, col_tick_ruler)
            meas_num = seg['measure_start_index'] + k + 1
            X = header_x + mpos * state.px_per_beat - state.scroll_x_px
            if header_x <= X <= view_x1:
                draw_list.add_text(X + 4, ruler_y0 + 4,
                                   imgui.get_color_u32_rgba(1, 1, 1, 0.95), str(meas_num))
            if show_beats:
                for j in range(1, num):
                    bpos = mpos + j * beat_len
                    if seg['start_beats'] <= bpos <= seg['end_beats'] and left_beat <= bpos <= right_beat:
                        _tick_ruler(bpos, 8, col_tick_ruler)

    draw_list.add_line(x0, ruler_y1, x1, ruler_y1, imgui.get_color_u32_rgba(1, 1, 1, 0.15))

    # === Marquee finalization ===
    if state.marquee_active and not imgui.is_mouse_down(0):
        sx0, sy0 = state.marquee_start
        sx1_, sy1_ = state.marquee_end
        if sx1_ < sx0: sx0, sx1_ = sx1_, sx0
        if sy1_ < sy0: sy0, sy1_ = sy1_, sy0
        sx0 = max(sx0, header_x1)
        sx1_ = min(sx1_, view_x1)
        sy0 = max(sy0, roll_y0)
        sy1_ = min(sy1_, roll_y1)
        if (sx1_ - sx0) > 2 and (sy1_ - sy0) > 2:
            for ti in visible_tracks:
                td = state.midi.tracks[ti]
                for ni, n in enumerate(td.notes):
                    if n.end_tick < vis_start_tick or n.start_tick > vis_end_tick:
                        continue
                    start_b = n.start_tick / float(tpq or 1)
                    end_b = n.end_tick / float(tpq or 1)
                    xs = header_x1 + start_b * state.px_per_beat - state.scroll_x_px
                    xe = header_x1 + end_b * state.px_per_beat - state.scroll_x_px
                    yn = roll_y0 + (127 - n.pitch) * nh - state.scroll_y_px
                    yn2 = yn + nh - 1
                    if xe < sx0 or xs > sx1_:
                        continue
                    if yn2 < sy0 or yn > sy1_:
                        continue
                    state.selected_notes.add((ti, ni))

        state.marquee_active = False

        if state.selected_notes and not state.playing:
            min_b = min(
                (state.midi.tracks[ti].notes[ni].start_tick / tpq)
                for (ti, ni) in state.selected_notes
            )
            state.playhead_beats = max(0.0, float(min_b))

    # Marquee overlay
    if state.marquee_active:
        sx0, sy0 = state.marquee_start
        sx1_, sy1_ = state.marquee_end
        vx0 = max(min(sx0, sx1_), header_x1)
        vx1_ = min(max(sx0, sx1_), view_x1)
        vy0 = max(min(sy0, sy1_), roll_y0)
        vy1_ = min(max(sy0, sy1_), roll_y1)
        if vx1_ > vx0 and vy1_ > vy0:
            draw_list.add_rect_filled(vx0, vy0, vx1_, vy1_,
                                      imgui.get_color_u32_rgba(0.6, 0.7, 1.0, 0.20))
            draw_list.add_rect(vx0, vy0, vx1_, vy1_,
                               imgui.get_color_u32_rgba(0.6, 0.7, 1.0, 0.85))

    # === Playhead ===
    Xp = header_x1 + state.playhead_beats * state.px_per_beat - state.scroll_x_px
    if header_x1 <= Xp <= view_x1:
        col_play = imgui.get_color_u32_rgba(1.0, 0.4, 0.2, 0.95)
        draw_list.add_line(Xp, roll_y0, Xp, roll_y1, col_play, 2.0)
        draw_list.add_line(Xp, ruler_y0, Xp, ruler_y1, col_play, 2.0)

    # === Auto-follow playhead ===
    if state.playing and state.tracking_enabled:
        view_w_track = max(1.0, view_x1 - header_x1)
        target = state.playhead_beats * state.px_per_beat - view_w_track * 0.3
        state.scroll_x_px = max(0.0, target)

    # === Scrollbars ===
    content_w_time = max(0.0, state.midi.total_beats * state.px_per_beat)
    visible_w = max(1.0, view_x1 - header_x1)
    scroll_x_max = max(0.0, content_w_time - visible_w)
    state.scroll_x_px = clamp(state.scroll_x_px, 0.0, scroll_x_max)

    # Horizontal (custom drawn, matching vertical style)
    hx0_sb = header_x1
    hy0_sb = view_y1 + 2
    hw_sb = max(10.0, view_x1 - header_x1 - 4)
    hh_sb = sb - 6

    draw_list.add_rect_filled(hx0_sb, hy0_sb, hx0_sb + hw_sb, hy0_sb + hh_sb,
                               imgui.get_color_u32_rgba(1, 1, 1, 0.06))

    if scroll_x_max > 0:
        thumb_w_sb = max(18.0, hw_sb * (visible_w / max(content_w_time, 1.0)))
        thumb_x_sb = hx0_sb + (hw_sb - thumb_w_sb) * (state.scroll_x_px / scroll_x_max)
    else:
        thumb_w_sb = hw_sb
        thumb_x_sb = hx0_sb

    imgui.set_cursor_screen_position((hx0_sb, hy0_sb))
    imgui.invisible_button("##hsb", hw_sb, hh_sb)
    if imgui.is_item_active():
        if not state.hsb_dragging:
            state.hsb_dragging = True
            state.hsb_anchor_mouse_x = io.mouse_pos[0]
            state.hsb_anchor_scroll_x = state.scroll_x_px
        denom = max(1.0, hw_sb - thumb_w_sb)
        factor_sb = scroll_x_max / denom if scroll_x_max > 0 else 0.0
        dx = io.mouse_pos[0] - state.hsb_anchor_mouse_x
        state.scroll_x_px = clamp(state.hsb_anchor_scroll_x + dx * factor_sb, 0.0, scroll_x_max)
    else:
        state.hsb_dragging = False

    draw_list.add_rect_filled(thumb_x_sb + 1, hy0_sb + 1,
                               thumb_x_sb + thumb_w_sb - 1, hy0_sb + hh_sb - 1,
                               imgui.get_color_u32_rgba(1, 1, 1, 0.22))
    draw_list.add_rect(thumb_x_sb + 1, hy0_sb + 1,
                        thumb_x_sb + thumb_w_sb - 1, hy0_sb + hh_sb - 1,
                        imgui.get_color_u32_rgba(1, 1, 1, 0.35))

    # Vertical (custom drawn)
    vx0_sb = view_x1 + 2
    vy0_sb = roll_y0
    vw_sb = sb - 6
    vh_sb = max(10.0, roll_y1 - roll_y0 - 4)

    draw_list.add_rect_filled(vx0_sb, vy0_sb, vx0_sb + vw_sb, vy0_sb + vh_sb,
                               imgui.get_color_u32_rgba(1, 1, 1, 0.06))

    if scroll_y_max > 0:
        thumb_h_sb = max(18.0, vh_sb * (visible_h / max(content_h, 1.0)))
        thumb_y_sb = vy0_sb + (vh_sb - thumb_h_sb) * (state.scroll_y_px / scroll_y_max)
    else:
        thumb_h_sb = vh_sb
        thumb_y_sb = vy0_sb

    imgui.set_cursor_screen_position((vx0_sb, vy0_sb))
    imgui.invisible_button("##vsb", vw_sb, vh_sb)
    if imgui.is_item_active():
        if not state.vsb_dragging:
            state.vsb_dragging = True
            state.vsb_anchor_mouse_y = io.mouse_pos[1]
            state.vsb_anchor_scroll_y = state.scroll_y_px
        denom = max(1.0, vh_sb - thumb_h_sb)
        factor_sb = scroll_y_max / denom if scroll_y_max > 0 else 0.0
        dy = io.mouse_pos[1] - state.vsb_anchor_mouse_y
        state.scroll_y_px = clamp(state.vsb_anchor_scroll_y + dy * factor_sb, 0.0, scroll_y_max)
    else:
        state.vsb_dragging = False

    draw_list.add_rect_filled(vx0_sb + 1, thumb_y_sb + 1,
                               vx0_sb + vw_sb - 1, thumb_y_sb + thumb_h_sb - 1,
                               imgui.get_color_u32_rgba(1, 1, 1, 0.22))
    draw_list.add_rect(vx0_sb + 1, thumb_y_sb + 1,
                        vx0_sb + vw_sb - 1, thumb_y_sb + thumb_h_sb - 1,
                        imgui.get_color_u32_rgba(1, 1, 1, 0.35))

    # === Corner note-height drag handle ===
    corner_x = view_x1
    corner_y = view_y1
    corner_w = sb
    corner_h = sb
    imgui.set_cursor_screen_position((corner_x, corner_y))
    imgui.invisible_button("##nh_drag", corner_w, corner_h)
    nh_hov = imgui.is_item_hovered()
    nh_active = imgui.is_item_active()
    if nh_active:
        if not getattr(state, '_nh_dragging', False):
            state._nh_dragging = True
            state._nh_anchor_y = io.mouse_pos[1]
            state._nh_anchor_val = state.note_height
        dy = state._nh_anchor_y - io.mouse_pos[1]
        state.note_height = max(2, min(48, round(state._nh_anchor_val + dy * 0.15)))
    else:
        state._nh_dragging = False

    bg = imgui.get_color_u32_rgba(1, 1, 1, 0.12 if nh_hov or nh_active else 0.06)
    draw_list.add_rect_filled(corner_x, corner_y, corner_x + corner_w, corner_y + corner_h, bg)
    line_col = imgui.get_color_u32_rgba(1, 1, 1, 0.5 if nh_hov or nh_active else 0.3)
    cx = corner_x + corner_w * 0.5
    cy = corner_y + corner_h * 0.5
    lw = corner_w * 0.4
    for off in (-2, 0, 2):
        draw_list.add_line(cx - lw, cy + off, cx + lw, cy + off, line_col, 1.0)

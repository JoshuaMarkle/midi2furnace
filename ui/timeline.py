# ui/timeline.py
import math
import imgui
from app.state import clamp, center_track_pitch_scroll
from ui.icons import ICON_VOLUME_MUTE, ICON_STAR, ICON_BACK

_BLACK_KEYS = frozenset({1, 3, 6, 8, 10})  # C#, D#, F#, G#, A#
_INSTRUMENTS = ["Square", "Triangle", "Sine", "Sawtooth", "Noise", "Pulse 25%", "Pulse 12.5%", "FM"]

def draw_timeline_canvas(state):
    """Main piano roll canvas: grid, notes, marquee, scrollbars, ruler."""
    if state.midi.path and state.midi.path != getattr(state, '_header_fitted_path', ''):
        max_text_w = 0
        for i, td_fit in enumerate(state.midi.tracks):
            max_text_w = max(max_text_w, imgui.calc_text_size(f"Track {i+1}")[0])
            if td_fit.name:
                max_text_w = max(max_text_w, imgui.calc_text_size(td_fit.name)[0])
        state.track_header_w = int(clamp(max_text_w + 24, 120, 300))
        state._header_fitted_path = state.midi.path

    canvas_pos = imgui.get_cursor_screen_pos()
    avail_w, avail_h = imgui.get_content_region_available()

    # Cache for view actions
    state.last_canvas_width = avail_w
    state.last_canvas_height = avail_h

    draw_list = imgui.get_window_draw_list()
    x0, y0 = canvas_pos
    x1, y1 = x0 + avail_w, y0 + avail_h

    # Reserve space for custom scrollbars
    sb = 18.0
    view_x1 = x1 - sb
    view_y1 = y1 - sb

    # Areas
    ruler_y0 = y0
    ruler_y1 = y0 + state.ruler_h
    track_area_y0 = ruler_y1
    track_area_y1 = view_y1

    t = state.theme

    header_x0 = x0
    header_x1 = x0 + state.track_header_w
    draw_list.add_rect_filled(x0, ruler_y0, x1, ruler_y1, imgui.get_color_u32_rgba(*t.track_header_bg))
    draw_list.add_rect_filled(header_x0, track_area_y0, header_x1, track_area_y1, imgui.get_color_u32_rgba(*t.track_header_bg))

    # ---- Apply View-menu zoom actions now that we know canvas sizes ----
    do_fit_time = state.request_fit_time or state.request_fit_all
    do_fit_vert = state.request_fit_vertical or state.request_fit_all

    if state.request_reset_zoom:
        from app.state import zoom_reset
        zoom_reset(state)
        state.request_reset_zoom = False

    if do_fit_time and state.midi.total_beats > 0:
        drawable_w = max(1.0, (view_x1 - header_x1))
        beats = max(1.0, state.midi.total_beats)
        state.px_per_beat = clamp(drawable_w / beats, 10.0, 400.0)
        state.scroll_x_px = 0.0

    if do_fit_vert:
        for td in state.midi.tracks:
            if not td.notes:
                continue
            prange = td.pitch_max - td.pitch_min + 1
            if prange > 0:
                available = max(8, state.track_height - 8)
                td.note_height = max(2, min(48, int(available / prange)))
            center_track_pitch_scroll(state, td)

    # clear requests
    state.request_fit_time = False
    state.request_fit_vertical = False
    state.request_fit_all = False

    # Interaction helpers
    io = imgui.get_io()
    mousex, mousey = io.mouse_pos
    hovered = (header_x0 <= mousex <= view_x1) and (track_area_y0 <= mousey <= track_area_y1)
    note_hovered = (header_x1 <= mousex <= view_x1) and (track_area_y0 <= mousey <= track_area_y1)

    # Resolve focus state
    focused = state.focused_track
    num_tracks_total = len(state.midi.tracks)
    if focused is not None and (focused < 0 or focused >= num_tracks_total):
        state.focused_track = None
        focused = None

    # Header click detection
    header_btn_clicked = False
    if imgui.is_mouse_clicked(0) and header_x0 <= mousex <= header_x1 and track_area_y0 <= mousey <= track_area_y1:
        if focused is not None:
            # Focus mode: back button, "...", and mute/inst buttons
            ti_click = focused
            row_bottom_click = track_area_y1

            # Back button (top-right)
            back_w, back_h = 32, 28
            back_x = header_x1 - back_w - 4
            back_y = track_area_y0 + 4
            if back_x <= mousex <= back_x + back_w and back_y <= mousey <= back_y + back_h:
                state.focused_track = None
                focused = None
                header_btn_clicked = True

            # "..." at bottom
            if not header_btn_clicked:
                dots_y = row_bottom_click - 38
                if header_x0 <= mousex <= header_x1 and dots_y <= mousey <= dots_y + 28:
                    state.focused_track = None
                    focused = None
                    header_btn_clicked = True

            # Mute/star/inst buttons (above "...")
            if not header_btn_clicked:
                btn_h_ck, btn_margin_ck = 28, 4
                btn_y_ck = row_bottom_click - btn_h_ck - btn_margin_ck - 42
                if btn_y_ck <= mousey <= btn_y_ck + btn_h_ck:
                    mute_w_ck = 32
                    mute_x_ck = header_x0 + 4
                    star_w_ck = 32
                    star_x_ck = mute_x_ck + mute_w_ck + 4
                    inst_x_ck = star_x_ck + star_w_ck + 4
                    if mute_x_ck <= mousex <= mute_x_ck + mute_w_ck:
                        state.midi.tracks[ti_click].muted = not state.midi.tracks[ti_click].muted
                        header_btn_clicked = True
                    elif star_x_ck <= mousex <= star_x_ck + star_w_ck:
                        state.midi.tracks[ti_click].starred = not state.midi.tracks[ti_click].starred
                        header_btn_clicked = True
                    elif inst_x_ck <= mousex <= header_x1 - 4:
                        state._open_inst_popup = ti_click
                        header_btn_clicked = True
        else:
            # Normal mode
            click_y = mousey - track_area_y0 + state.scroll_y_px
            ti_click = int(click_y / max(1, state.track_height))
            if 0 <= ti_click < num_tracks_total:
                row_bottom_click = track_area_y0 + (ti_click + 1) * state.track_height - state.scroll_y_px
                btn_h_ck, btn_margin_ck = 28, 4
                btn_y_ck = row_bottom_click - btn_h_ck - btn_margin_ck
                if btn_y_ck <= mousey <= btn_y_ck + btn_h_ck:
                    mute_w_ck = 32
                    mute_x_ck = header_x0 + 4
                    star_w_ck = 32
                    star_x_ck = mute_x_ck + mute_w_ck + 4
                    inst_x_ck = star_x_ck + star_w_ck + 4
                    if mute_x_ck <= mousex <= mute_x_ck + mute_w_ck:
                        state.midi.tracks[ti_click].muted = not state.midi.tracks[ti_click].muted
                        header_btn_clicked = True
                    elif star_x_ck <= mousex <= star_x_ck + star_w_ck:
                        state.midi.tracks[ti_click].starred = not state.midi.tracks[ti_click].starred
                        header_btn_clicked = True
                    elif inst_x_ck <= mousex <= header_x1 - 4:
                        state._open_inst_popup = ti_click
                        header_btn_clicked = True
                else:
                    state.focused_track = ti_click
                    focused = ti_click
                    state.scroll_y_px = 0.0
                    header_btn_clicked = True

    # Start/stop panning (right or middle)
    if hovered and (imgui.is_mouse_clicked(2) or imgui.is_mouse_clicked(1)):
        state.panning = True
        state.pan_anchor = (mousex, mousey)
        state.pan_scroll_anchor = (state.scroll_x_px, state.scroll_y_px)
    if state.panning and not (imgui.is_mouse_down(2) or imgui.is_mouse_down(1)):
        state.panning = False

    if state.panning:
        dx = mousex - state.pan_anchor[0]
        dy = mousey - state.pan_anchor[1]
        state.scroll_x_px = max(0.0, state.pan_scroll_anchor[0] - dx)
        if focused is None:
            state.scroll_y_px = max(0.0, state.pan_scroll_anchor[1] - dy)
        if state.playing:
            state.tracking_enabled = False

    # Selection marquee (left drag)
    if note_hovered and imgui.is_mouse_clicked(0) and not header_btn_clicked:
        state.marquee_active = True
        state.marquee_start = (mousex, mousey)
        state.marquee_end = (mousex, mousey)
        state.selected_notes.clear()
    if state.marquee_active and imgui.is_mouse_down(0):
        state.marquee_end = (mousex, mousey)

    # Mouse wheel zoom/scroll (FL Studio-style)
    wheel_y = io.mouse_wheel
    if hovered and abs(wheel_y) > 0.0:
        if io.key_ctrl:
            factor = 1.1 if wheel_y > 0 else 1 / 1.1
            left_beat = state.scroll_x_px / max(1e-6, state.px_per_beat)
            state.px_per_beat = clamp(state.px_per_beat * factor, 10.0, 400.0)
            state.scroll_x_px = max(0.0, left_beat * state.px_per_beat)
        elif io.key_shift:
            state.scroll_x_px = max(0.0, state.scroll_x_px - wheel_y * 40.0)
            if state.playing:
                state.tracking_enabled = False
        elif focused is None:
            state.scroll_y_px = max(0.0, state.scroll_y_px - wheel_y * 40.0)

    # Click on ruler to seek
    if imgui.is_mouse_clicked(0):
        mx, my = io.mouse_pos
        if ruler_y0 <= my <= ruler_y1 and header_x1 <= mx <= view_x1:
            beat = (state.scroll_x_px + (mx - header_x1)) / max(1e-6, state.px_per_beat)
            state.playhead_beats = max(0.0, beat)

    # Visible beat range
    total_beats = state.midi.total_beats if state.midi.tracks else 128
    left_beat = max(0.0, state.scroll_x_px / max(1e-6, state.px_per_beat))
    right_beat = (state.scroll_x_px + avail_w) / max(1e-6, state.px_per_beat)

    # Visible track rows
    num_tracks = len(state.midi.tracks)
    if num_tracks <= 0:
        first_visible_row, last_visible_row = 0, -1
    elif focused is not None:
        first_visible_row = focused
        last_visible_row = focused
    else:
        first_visible_row = int(max(0, (state.scroll_y_px // state.track_height)))
        last_visible_row  = int(min(num_tracks - 1, math.floor((state.scroll_y_px + (track_area_y1 - track_area_y0)) / state.track_height)))

    # Focus mode: compute note height for full-height focused track
    if focused is not None and 0 <= focused < num_tracks:
        td_focus = state.midi.tracks[focused]
        focus_h = track_area_y1 - track_area_y0
        if td_focus.notes and td_focus.pitch_max >= td_focus.pitch_min:
            prange = td_focus.pitch_max - td_focus.pitch_min + 1
            td_focus.note_height = max(2, min(48, int((focus_h - 8) / prange)))
        center_pitch = (td_focus.pitch_min + td_focus.pitch_max) * 0.5
        td_focus.pitch_scroll_px = focus_h * 0.5 - 4 - (127.0 - center_pitch) * td_focus.note_height

    # Precompute tick window
    tpq = state.midi.ticks_per_beat
    vis_start_tick  = int(left_beat * tpq)
    vis_end_tick    = int(right_beat * tpq)

    # Draw rows + notes
    note_color = imgui.get_color_u32_rgba(0.27, 0.58, 0.98, 0.95)
    border_col = imgui.get_color_u32_rgba(0.05, 0.1, 0.18, 1.0)
    playing_note_col = imgui.get_color_u32_rgba(*t.channel_fm[:3], 0.95)
    playing_border_col = imgui.get_color_u32_rgba(*(c * 0.4 for c in t.channel_fm[:3]), 1.0)
    playhead_b = state.playhead_beats if state.playing else None

    any_starred = any(td.starred for td in state.midi.tracks)

    if last_visible_row >= first_visible_row:
        for ti in range(first_visible_row, last_visible_row + 1):
            td = state.midi.tracks[ti]

            if focused is not None:
                row_top = track_area_y0
                row_bottom = track_area_y1
            else:
                row_top    = track_area_y0 + (ti * state.track_height) - state.scroll_y_px
                row_bottom = row_top + state.track_height

            muted = td.muted
            silenced = muted or (any_starred and not td.starred)
            dim = 0.3 if silenced else 1.0
            nh = td.note_height

            # Row stripes
            if ti % 2 == 0:
                draw_list.add_rect_filled(header_x1, row_top, view_x1, row_bottom, imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.02 * dim))
            else:
                draw_list.add_rect_filled(header_x1, row_top, view_x1, row_bottom, imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 0.05 * dim))

            # Header background (solid black when muted)
            if muted:
                draw_list.add_rect_filled(header_x0, row_top, header_x1, row_bottom, imgui.get_color_u32_rgba(0, 0, 0, 1.0))

            # Header text
            draw_list.add_text(header_x0 + 8, row_top + 6, imgui.get_color_u32_rgba(1, 1, 1, 0.3 if muted else 0.9), f"Track {ti+1}")
            if td.name:
                draw_list.add_text(header_x0 + 8, row_top + 28, imgui.get_color_u32_rgba(1, 1, 1, 0.15 if muted else 0.6), td.name)

            # Focus mode elements
            focus_bottom_pad = 0
            if focused is not None:
                focus_bottom_pad = 42
                # Back button at top-right
                back_w, back_h = 32, 28
                back_x = header_x1 - back_w - 4
                back_y_pos = row_top + 4
                back_hov = (back_x <= mousex <= back_x + back_w
                            and back_y_pos <= mousey <= back_y_pos + back_h
                            and track_area_y0 <= mousey <= track_area_y1)
                back_col = imgui.get_color_u32_rgba(*t.toggle_off[:3], 0.9 if back_hov else 0.7)
                draw_list.add_rect_filled(back_x, back_y_pos, back_x + back_w, back_y_pos + back_h, back_col)
                draw_list.add_text(back_x + 8, back_y_pos + 6, imgui.get_color_u32_rgba(1, 1, 1, 0.9), ICON_BACK)
                # "..." at bottom
                dots_cx = header_x0 + (header_x1 - header_x0) * 0.5
                dots_y_pos = row_bottom - 38
                dots_hov = (header_x0 <= mousex <= header_x1
                            and dots_y_pos <= mousey <= dots_y_pos + 28
                            and track_area_y0 <= mousey <= track_area_y1)
                draw_list.add_text(dots_cx - 6, dots_y_pos + 6,
                                   imgui.get_color_u32_rgba(1, 1, 1, 0.9 if dots_hov else 0.5), "...")

            # Mute + Star + Instrument buttons
            btn_h_draw, btn_margin_draw = 28, 4
            btn_y_draw = row_bottom - btn_h_draw - btn_margin_draw - focus_bottom_pad
            mute_w_draw = 32
            mute_x_draw = header_x0 + 4
            mute_hov = (mute_x_draw <= mousex <= mute_x_draw + mute_w_draw
                        and btn_y_draw <= mousey <= btn_y_draw + btn_h_draw
                        and track_area_y0 <= mousey <= track_area_y1)
            if muted:
                mc = t.destructive_hint
                mute_col = imgui.get_color_u32_rgba(*mc[:3], 1.0 if mute_hov else 0.85)
            else:
                mc = t.toggle_off
                mute_col = imgui.get_color_u32_rgba(*mc[:3], 0.9 if mute_hov else 0.7)
            draw_list.add_rect_filled(mute_x_draw, btn_y_draw, mute_x_draw + mute_w_draw, btn_y_draw + btn_h_draw, mute_col)
            draw_list.add_text(mute_x_draw + 8, btn_y_draw + 6, imgui.get_color_u32_rgba(1, 1, 1, 0.9), ICON_VOLUME_MUTE)

            star_w_draw = 32
            star_x_draw = mute_x_draw + mute_w_draw + 4
            star_hov = (star_x_draw <= mousex <= star_x_draw + star_w_draw
                        and btn_y_draw <= mousey <= btn_y_draw + btn_h_draw
                        and track_area_y0 <= mousey <= track_area_y1)
            if td.starred:
                star_col = imgui.get_color_u32_rgba(0.9, 0.75, 0.1, 1.0 if star_hov else 0.85)
            else:
                star_col = imgui.get_color_u32_rgba(*t.toggle_off[:3], 0.9 if star_hov else 0.7)
            draw_list.add_rect_filled(star_x_draw, btn_y_draw, star_x_draw + star_w_draw, btn_y_draw + btn_h_draw, star_col)
            draw_list.add_text(star_x_draw + 8, btn_y_draw + 6, imgui.get_color_u32_rgba(1, 1, 1, 0.9), ICON_STAR)

            inst_x_draw = star_x_draw + star_w_draw + 4
            inst_w_draw = max(10, int(header_x1 - inst_x_draw - 4))
            inst_hov = (inst_x_draw <= mousex <= inst_x_draw + inst_w_draw
                        and btn_y_draw <= mousey <= btn_y_draw + btn_h_draw
                        and track_area_y0 <= mousey <= track_area_y1)
            inst_col = imgui.get_color_u32_rgba(*t.toggle_off[:3], 0.9 if inst_hov else 0.7)
            draw_list.add_rect_filled(inst_x_draw, btn_y_draw, inst_x_draw + inst_w_draw, btn_y_draw + btn_h_draw, inst_col)
            draw_list.add_text(inst_x_draw + 4, btn_y_draw + 6, imgui.get_color_u32_rgba(1, 1, 1, 0.9), td.instrument)

            # Separator
            draw_list.add_line(header_x1, row_top, header_x1, row_bottom, imgui.get_color_u32_rgba(1,1,1,0.1))

            # Note area and piano-key background coloring
            note_area_y0 = row_top + 4 + td.pitch_scroll_px
            clip_y0 = row_top + 1
            clip_y1 = row_bottom - 1
            if nh > 0:
                black_key_col = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.04 * dim)
                first_pitch = max(0, 127 - int(math.floor((clip_y1 - note_area_y0) / nh)))
                last_pitch = min(127, 127 - int(math.floor((clip_y0 - note_area_y0) / nh)))
                for pitch in range(first_pitch, last_pitch + 1):
                    if pitch % 12 in _BLACK_KEYS:
                        ry0 = note_area_y0 + (127 - pitch) * nh
                        ry1 = ry0 + nh
                        ry0c = max(clip_y0, ry0)
                        ry1c = min(clip_y1, ry1)
                        if ry1c > ry0c:
                            draw_list.add_rect_filled(header_x1, ry0c, view_x1, ry1c, black_key_col)

                if state.playing and state.active_pitches and not silenced:
                    active_row_col = imgui.get_color_u32_rgba(*t.accent_secondary[:3], 0.12)
                    for pitch in range(first_pitch, last_pitch + 1):
                        if pitch in state.active_pitches:
                            ry0 = note_area_y0 + (127 - pitch) * nh
                            ry1 = ry0 + nh
                            ry0c = max(clip_y0, ry0)
                            ry1c = min(clip_y1, ry1)
                            if ry1c > ry0c:
                                draw_list.add_rect_filled(header_x1, ry0c, view_x1, ry1c, active_row_col)

            # Draw notes in visible time
            for ni, n in enumerate(td.notes):
                if n.end_tick < vis_start_tick or n.start_tick > vis_end_tick:
                    continue

                start_b = n.start_tick / float(tpq or 1)
                end_b   = n.end_tick / float(tpq or 1)
                x_start = header_x1 + (start_b * state.px_per_beat) - state.scroll_x_px
                x_end   = header_x1 + (end_b   * state.px_per_beat) - state.scroll_x_px
                if x_end < header_x1 or x_start > view_x1:
                    continue

                y_note = note_area_y0 + ((127 - n.pitch) * nh)
                y2     = y_note + nh - 1
                if y2 < clip_y0 or y_note > clip_y1:
                    continue

                y1c = max(clip_y0, y_note)
                y2c = min(clip_y1, y2)
                x1c = max(header_x1, x_start)
                x2c = min(view_x1, x_end)

                is_playing_now = playhead_b is not None and start_b <= playhead_b < end_b
                sel = (ti, ni) in state.selected_notes
                if silenced:
                    fill_col = imgui.get_color_u32_rgba(0.27, 0.58, 0.98, 0.15)
                    edge_col = imgui.get_color_u32_rgba(0.05, 0.1, 0.18, 0.3)
                elif is_playing_now:
                    fill_col = playing_note_col
                    edge_col = playing_border_col
                elif sel:
                    fill_col = imgui.get_color_u32_rgba(0.98, 0.78, 0.28, 0.95)
                    edge_col = imgui.get_color_u32_rgba(0.95, 0.85, 0.45, 1.0)
                else:
                    fill_col = note_color
                    edge_col = border_col
                draw_list.add_rect_filled(x1c, y1c, x2c, y2c, fill_col)
                draw_list.add_rect(x1c, y1c, x2c, y2c, edge_col)

            # Row bottom line
            draw_list.add_line(x0, row_bottom, view_x1, row_bottom, imgui.get_color_u32_rgba(1,1,1,0.08))

    # === Vertical grid overlay and ruler ===
    header_x = header_x1
    col_bar_grid  = imgui.get_color_u32_rgba(1, 1, 1, 0.18)
    col_beat_grid = imgui.get_color_u32_rgba(1, 1, 1, 0.12)
    col_8th  = imgui.get_color_u32_rgba(1, 1, 1, 0.07)
    col_16th = imgui.get_color_u32_rgba(1, 1, 1, 0.045)
    col_tick_ruler = imgui.get_color_u32_rgba(1, 1, 1, 0.18)

    def _vline_grid(beats_pos: float, col: int):
        X = header_x + (beats_pos * state.px_per_beat) - state.scroll_x_px
        if header_x <= X <= view_x1:
            draw_list.add_line(X, track_area_y0, X, track_area_y1, col)

    def _tick_on_ruler(beats_pos: float, tick_h: float, col: int):
        X = header_x + (beats_pos * state.px_per_beat) - state.scroll_x_px
        if header_x <= X <= view_x1:
            draw_list.add_line(X, ruler_y1 - tick_h, X, ruler_y1, col)

    show_beats = state.px_per_beat >= 15.0
    show_8th = state.px_per_beat >= 50.0
    show_16th = state.px_per_beat >= 90.0

    if show_16th:
        step = 0.25
        i = math.ceil(left_beat / step)
        while True:
            pos = i * step
            if pos > right_beat: break
            _vline_grid(pos, col_16th)
            i += 1
    elif show_8th:
        step = 0.5
        i = math.ceil(left_beat / step)
        while True:
            pos = i * step
            if pos > right_beat: break
            _vline_grid(pos, col_8th)
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
            _vline_grid(mpos, col_bar_grid)
            if show_beats:
                for j in range(1, num):
                    bpos = mpos + j * beat_len
                    if seg['start_beats'] <= bpos <= seg['end_beats'] and left_beat <= bpos <= right_beat:
                        _vline_grid(bpos, col_beat_grid)

    # Ruler on top
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
            _tick_on_ruler(mpos, 14, col_tick_ruler)
            meas_num = seg['measure_start_index'] + k + 1
            X = header_x + (mpos * state.px_per_beat) - state.scroll_x_px
            if header_x <= X <= view_x1:
                draw_list.add_text(X + 4, ruler_y0 + 4, imgui.get_color_u32_rgba(1, 1, 1, 0.95), str(meas_num))
            if show_beats:
                for j in range(1, num):
                    bpos = mpos + j * beat_len
                    if seg['start_beats'] <= bpos <= seg['end_beats'] and left_beat <= bpos <= right_beat:
                        _tick_on_ruler(bpos, 8, col_tick_ruler)

    # Ruler bottom border
    draw_list.add_line(x0, ruler_y1, x1, ruler_y1, imgui.get_color_u32_rgba(1, 1, 1, 0.15))

    # Finalize marquee selection when mouse released
    if state.marquee_active and not imgui.is_mouse_down(0):
        sx0, sy0 = state.marquee_start
        sx1_, sy1_ = state.marquee_end
        if sx1_ < sx0: sx0, sx1_ = sx1_, sx0
        if sy1_ < sy0: sy0, sy1_ = sy1_, sy0
        sx0 = max(sx0, header_x1); sx1_ = min(sx1_, view_x1)
        sy0 = max(sy0, track_area_y0); sy1_ = min(sy1_, track_area_y1)
        if (sx1_ - sx0) > 2 and (sy1_ - sy0) > 2:
            if last_visible_row >= first_visible_row:
                for ti in range(first_visible_row, last_visible_row + 1):
                    td = state.midi.tracks[ti]
                    if focused is not None:
                        row_top = track_area_y0
                    else:
                        row_top = track_area_y0 + (ti * state.track_height) - state.scroll_y_px
                    note_area_y0 = row_top + 4 + td.pitch_scroll_px
                    t_nh = td.note_height
                    for ni, n in enumerate(td.notes):
                        if n.end_tick < vis_start_tick or n.start_tick > vis_end_tick:
                            continue
                        start_b = n.start_tick / float(tpq or 1)
                        end_b   = n.end_tick   / float(tpq or 1)
                        x_start = header_x1 + (start_b * state.px_per_beat) - state.scroll_x_px
                        x_end   = header_x1 + (end_b   * state.px_per_beat) - state.scroll_x_px
                        y_note  = note_area_y0 + ((127 - n.pitch) * t_nh)
                        y2      = y_note + t_nh - 1
                        if x_end < sx0 or x_start > sx1_:
                            continue
                        if y2 < sy0 or y_note > sy1_:
                            continue
                        state.selected_notes.add((ti, ni))
        state.marquee_active = False

        # >>> Snap playhead to selection start only when not playing <<<
        if state.selected_notes and not getattr(state, "playing", False):
            tpq = state.midi.ticks_per_beat or 480
            min_b = min(
                (state.midi.tracks[ti].notes[ni].start_tick / tpq)
                for (ti, ni) in state.selected_notes
            )
            state.playhead_beats = max(0.0, float(min_b))


    # Marquee overlay while dragging
    if state.marquee_active:
        sx0, sy0 = state.marquee_start
        sx1_, sy1_ = state.marquee_end
        vx0 = max(min(sx0, sx1_), header_x1)
        vx1 = min(max(sx0, sx1_), view_x1)
        vy0 = max(min(sy0, sy1_), track_area_y0)
        vy1 = min(max(sy0, sy1_), track_area_y1)
        if vx1 > vx0 and vy1 > vy0:
            col_fill = imgui.get_color_u32_rgba(0.6, 0.7, 1.0, 0.20)
            col_edge = imgui.get_color_u32_rgba(0.6, 0.7, 1.0, 0.85)
            draw_list.add_rect_filled(vx0, vy0, vx1, vy1, col_fill)
            draw_list.add_rect(vx0, vy0, vx1, vy1, col_edge)

    # Instrument popup
    if getattr(state, '_open_inst_popup', None) is not None:
        imgui.open_popup("##inst_popup")
        state._inst_popup_track = state._open_inst_popup
        state._open_inst_popup = None
    if imgui.begin_popup("##inst_popup"):
        ti_popup = getattr(state, '_inst_popup_track', 0)
        if 0 <= ti_popup < len(state.midi.tracks):
            for inst in _INSTRUMENTS:
                selected = (state.midi.tracks[ti_popup].instrument == inst)
                if imgui.selectable(inst, selected)[0]:
                    state.midi.tracks[ti_popup].instrument = inst
        imgui.end_popup()

    # Auto-follow playhead during playback
    if state.playing and state.tracking_enabled:
        view_w_track = max(1.0, view_x1 - header_x1)
        target = state.playhead_beats * state.px_per_beat - view_w_track * 0.3
        state.scroll_x_px = max(0.0, target)

    # Dynamic track height: fill available space (normal mode only)
    if focused is None and state.track_height_auto and state.midi.tracks:
        available = max(240.0, track_area_y1 - track_area_y0)
        num_t = max(1, len(state.midi.tracks))
        state.track_height = max(240, int(available / num_t))
        for td in state.midi.tracks:
            if td.notes and td.pitch_max >= td.pitch_min:
                prange = td.pitch_max - td.pitch_min + 1
                td.note_height = max(2, min(48, int((state.track_height - 8) / prange)))
            center_track_pitch_scroll(state, td)

    # Custom scrollbars
    content_w_time = max(0.0, state.midi.total_beats * state.px_per_beat)
    visible_w_time = max(1.0, view_x1 - header_x1)
    scroll_x_max = max(0.0, content_w_time - visible_w_time)
    state.scroll_x_px = clamp(state.scroll_x_px, 0.0, scroll_x_max)

    if focused is not None:
        content_h = 0.0
        visible_h = max(1.0, track_area_y1 - track_area_y0)
        scroll_y_max = 0.0
        state.scroll_y_px = 0.0
    else:
        content_h = max(0.0, len(state.midi.tracks) * float(state.track_height))
        visible_h = max(1.0, track_area_y1 - track_area_y0)
        scroll_y_max = max(0.0, content_h - visible_h)
        state.scroll_y_px = clamp(state.scroll_y_px, 0.0, scroll_y_max)

    # Horizontal scrollbar (bottom)
    imgui.set_cursor_screen_position((header_x1, view_y1 + 2))
    imgui.push_item_width(max(10.0, view_x1 - header_x1 - 4))
    changed, new_sx = imgui.slider_float("##hsb", state.scroll_x_px, 0.0, max(1.0, scroll_x_max))
    if changed:
        state.scroll_x_px = new_sx
    imgui.pop_item_width()

    # Vertical scrollbar (right) — custom (compatible across pyimgui versions)
    vx0, vy0 = view_x1 + 2, track_area_y0
    vw, vh = (sb - 6), max(10.0, track_area_y1 - track_area_y0 - 4)

    # Track
    col_track = imgui.get_color_u32_rgba(1, 1, 1, 0.06)
    draw_list.add_rect_filled(vx0, vy0, vx0 + vw, vy0 + vh, col_track)


    # --- Playhead (draw last so it's on top) ---
    Xp = header_x1 + (state.playhead_beats * state.px_per_beat) - state.scroll_x_px
    if header_x1 <= Xp <= view_x1:
        col_play = imgui.get_color_u32_rgba(1.0, 0.4, 0.2, 0.95)
        draw_list.add_line(Xp, track_area_y0, Xp, track_area_y1, col_play, 2.0)
        draw_list.add_line(Xp, ruler_y0, Xp, ruler_y1, col_play, 2.0)


    # Thumb size & position
    if scroll_y_max > 0.0:
        thumb_h = max(18.0, vh * (visible_h / max(content_h, 1.0)))
        thumb_y = vy0 + (vh - thumb_h) * (state.scroll_y_px / scroll_y_max)
    else:
        thumb_h = vh
        thumb_y = vy0

    # Interaction area (invisible button)
    imgui.set_cursor_screen_position((vx0, vy0))
    imgui.invisible_button("##vsb", vw, vh)
    if focused is None and imgui.is_item_active():
        if not state.vsb_dragging:
            state.vsb_dragging = True
            state.vsb_anchor_mouse_y = io.mouse_pos[1]
            state.vsb_anchor_scroll_y = state.scroll_y_px
        # Map mouse delta to scroll space
        denom = max(1.0, vh - thumb_h)
        factor = scroll_y_max / denom if scroll_y_max > 0.0 else 0.0
        dy = io.mouse_pos[1] - state.vsb_anchor_mouse_y
        state.scroll_y_px = clamp(state.vsb_anchor_scroll_y + dy * factor, 0.0, scroll_y_max)
    else:
        state.vsb_dragging = False

    # Draw thumb
    if focused is None:
        col_thumb = imgui.get_color_u32_rgba(1, 1, 1, 0.22)
        col_thumb_border = imgui.get_color_u32_rgba(1, 1, 1, 0.35)
        draw_list.add_rect_filled(vx0 + 1, thumb_y + 1, vx0 + vw - 1, thumb_y + thumb_h - 1, col_thumb)
        draw_list.add_rect(vx0 + 1, thumb_y + 1, vx0 + vw - 1, thumb_y + thumb_h - 1, col_thumb_border)

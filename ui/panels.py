import os
import imgui
from app.state import compute_track_pitch_bounds
from tracker.export import copy_selection_to_clipboard, NOTE_NAMES
from ui.icons import (
    ICON_PLAY, ICON_STOP, ICON_CIRCLE_PLAY,
    ICON_CROSSHAIRS, ICON_VOLUME_UP, ICON_VOLUME_MUTE, ICON_COPY,
)

_INSTRUMENTS = ["Square", "Triangle", "Sine"]


def _brighten(c, factor=1.2):
    return tuple(min(1.0, v * factor) for v in c[:3]) + (c[3],)


def _darken(c, factor=0.7):
    return tuple(v * factor for v in c[:3]) + (c[3],)


def _toggle_colors(base):
    return (base, _brighten(base), _darken(base))


def _square_icon_button(label, colors=None, enabled=True, size_from=None):
    visible = label.split("##")[0]
    text_size = imgui.calc_text_size(visible)
    ref = imgui.calc_text_size(size_from) if size_from else text_size
    side = max(ref.x, ref.y)
    base = 8.0
    pad_x = (side - text_size.x) * 0.5 + base
    pad_y = (side - text_size.y) * 0.5 + base
    imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (pad_x, pad_y))
    if colors:
        imgui.push_style_color(imgui.COLOR_BUTTON, *colors[0])
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *colors[1])
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *colors[2])
    if not enabled:
        imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)
    clicked = imgui.button(label)
    if not enabled:
        clicked = False
        imgui.pop_style_var()
    if colors:
        imgui.pop_style_color(3)
    imgui.pop_style_var()
    return clicked


def draw_playback_bar(state):
    from audio.player import start_playback, stop_playback

    t = state.theme
    on_colors = _toggle_colors(t.toggle_on)
    off_colors = _toggle_colors(t.toggle_off)
    idle_colors = _toggle_colors(t.toggle)
    mute_colors = _toggle_colors(t.destructive_hint)
    has_track = bool(state.midi.tracks)

    # Compute vertical offset to center sliders with the taller buttons
    btn_text_sz = imgui.calc_text_size(ICON_PLAY)
    btn_side = max(btn_text_sz.x, btn_text_sz.y)
    btn_total_h = btn_side + 8.0 * 2
    slider_h = imgui.get_frame_height()
    slider_offset_y = (btn_total_h - slider_h) * 0.5

    imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 4.0)

    # Copy to Furnace button
    if _square_icon_button(ICON_COPY, colors=on_colors if has_track else off_colors, enabled=has_track):
        ok, msg = copy_selection_to_clipboard(state, state.tracker_cfg)
        if not ok:
            state.pending_export_popup = msg or "Export failed."

    imgui.same_line(spacing=12.0)

    if state.playing:
        if _square_icon_button(ICON_STOP, colors=on_colors, enabled=has_track):
            stop_playback(state, restore_cursor=False)
    else:
        if _square_icon_button(ICON_PLAY, colors=idle_colors if has_track else off_colors, enabled=has_track):
            start_playback(state)

    imgui.same_line()
    if _square_icon_button(ICON_CIRCLE_PLAY, colors=idle_colors if has_track else off_colors, enabled=has_track):
        if state.playing:
            stop_playback(state, restore_cursor=False)
        state.playhead_beats = 0.0
        start_playback(state)

    imgui.same_line()
    tracking_cols = on_colors if state.tracking_enabled else off_colors
    if _square_icon_button(ICON_CROSSHAIRS, colors=tracking_cols, enabled=has_track):
        state.tracking_enabled = not state.tracking_enabled

    # Playhead position slider — vertically centered
    if not has_track:
        imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)

    imgui.same_line(spacing=12.0)
    save_y = imgui.get_cursor_pos_y()
    imgui.set_cursor_pos_y(save_y + slider_offset_y)
    total_beats = max(1.0, state.midi.total_beats)
    imgui.push_item_width(max(60.0, imgui.get_content_region_available()[0] - 380.0))
    changed, new_b = imgui.slider_float(
        "##playhead", state.playhead_beats, 0.0, total_beats,
        f"{state.playhead_beats:.1f} / {total_beats:.1f}",
    )
    if has_track and changed:
        state.playhead_beats = max(0.0, new_b)
        if state.playing:
            stop_playback(state, restore_cursor=False)
            state.playhead_beats = max(0.0, new_b)
            start_playback(state)
    imgui.pop_item_width()
    imgui.set_cursor_pos_y(save_y)

    if not has_track:
        imgui.pop_style_var()

    # Mute button — reset Y so it aligns with the other icon buttons
    imgui.same_line(spacing=12.0)
    imgui.set_cursor_pos_y(save_y)
    mute_icon = ICON_VOLUME_MUTE if state.master_muted else ICON_VOLUME_UP
    if state.master_muted:
        mute_btn_colors = mute_colors
    else:
        mute_btn_colors = idle_colors if has_track else off_colors
    if _square_icon_button(mute_icon + "##master_mute", colors=mute_btn_colors, enabled=has_track, size_from=ICON_PLAY):
        state.master_muted = not state.master_muted

    # Volume slider — vertically centered, disabled when muted
    muted_or_no_track = state.master_muted or not has_track
    if muted_or_no_track:
        imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)

    imgui.same_line()
    save_y = imgui.get_cursor_pos_y()
    imgui.set_cursor_pos_y(save_y + slider_offset_y)
    imgui.push_item_width(300.0)
    changed, g = imgui.slider_float("##vol", state.master_gain, 0.0, 1.0)
    if has_track and not state.master_muted and changed:
        state.master_gain = g
    imgui.pop_item_width()
    imgui.set_cursor_pos_y(save_y)

    if muted_or_no_track:
        imgui.pop_style_var()

    imgui.pop_style_var()


def _table_row(label, value):
    imgui.table_next_row()
    imgui.table_next_column()
    imgui.text_colored(label, 0.6, 0.6, 0.6, 1.0)
    imgui.table_next_column()
    imgui.text(value)


def _note_name(pitch):
    name = NOTE_NAMES[pitch % 12]
    octave = pitch // 12 - 1
    return f"{name}{octave}"


def draw_midi_info(state):
    focused = state.focused_track
    num_tracks = len(state.midi.tracks)
    if focused is not None and (focused < 0 or focused >= num_tracks):
        focused = None

    if focused is not None and state.midi.path:
        _draw_track_info(state, focused)
    elif state.midi.path:
        _draw_file_info(state)
    else:
        text = "No MIDI loaded."
        text_size = imgui.calc_text_size(text)
        avail = imgui.get_content_region_available()
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + (avail[0] - text_size[0]) * 0.5)
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + (avail[1] - text_size[1]) * 0.5)
        imgui.text(text)


def _draw_file_info(state):
    imgui.text(os.path.basename(state.midi.path))
    imgui.spacing()

    TABLE_FLAGS = getattr(imgui, "TABLE_BORDERS_INNER_H", 0) | getattr(imgui, "TABLE_SIZING_STRETCH_SAME", 0)
    if imgui.begin_table("##midi_info_table", 2, TABLE_FLAGS):
        imgui.table_setup_column("Label")
        imgui.table_setup_column("Value")

        _table_row("Tracks", str(len(state.midi.tracks)))
        _table_row("TPQ", str(state.midi.ticks_per_beat))
        _table_row("Length", f"{state.midi.total_beats:.1f} beats")
        bpm = getattr(state.midi, "tempo_bpm", 120.0)
        _table_row("Tempo", f"{bpm:.1f} BPM")
        has_notes, gmin, gmax = compute_track_pitch_bounds(state)
        if has_notes:
            _table_row("Pitch", f"{gmin}..{gmax} ({gmax-gmin+1} semitones)")
        if state.midi.ts_segments:
            seg = state.midi.ts_segments[0]
            _table_row("Time sig", f"{seg['num']}/{seg['den']}")

        imgui.end_table()


def _draw_track_info(state, ti):
    td = state.midi.tracks[ti]
    title = td.name if td.name else f"Track {ti + 1}"
    imgui.text(title)
    imgui.spacing()

    TABLE_FLAGS = getattr(imgui, "TABLE_BORDERS_INNER_H", 0) | getattr(imgui, "TABLE_SIZING_STRETCH_SAME", 0)
    if imgui.begin_table("##track_info_table", 2, TABLE_FLAGS):
        imgui.table_setup_column("Label")
        imgui.table_setup_column("Value")

        _table_row("Track", str(ti + 1))
        _table_row("Notes", str(len(td.notes)))
        if td.notes:
            _table_row("Pitch range", f"{_note_name(td.pitch_min)} - {_note_name(td.pitch_max)}")
            tpq = state.midi.ticks_per_beat or 480
            start_b = td.notes[0].start_tick / tpq
            end_b = td.notes[-1].end_tick / tpq
            _table_row("Span", f"{start_b:.1f} - {end_b:.1f} beats")

        imgui.end_table()

    imgui.separator()
    imgui.spacing()
    imgui.text("Instrument")

    current_idx = _INSTRUMENTS.index(td.instrument) if td.instrument in _INSTRUMENTS else 0
    changed, new_idx = imgui.combo("##inst_combo", current_idx, _INSTRUMENTS)
    if changed:
        td.instrument = _INSTRUMENTS[new_idx]

    imgui.separator()
    imgui.spacing()
    imgui.text("Volume")
    changed, vol = imgui.slider_float("##track_vol", td.volume, 0.0, 1.0, "%.2f")
    if changed:
        td.volume = vol

    imgui.separator()
    imgui.spacing()
    imgui.text("Export overrides")

    changed, ov_inst = imgui.checkbox("Override Instrument", td.override_instrument)
    if changed:
        td.override_instrument = ov_inst

    _btn = getattr(imgui, "small_button", imgui.button)

    imgui.same_line()
    _dimmed = False
    if not td.override_instrument:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _dimmed = True
        except Exception:
            pass

    if _btn(" - ##ti"):
        if td.override_instrument:
            try:
                v = int(td.override_instrument_hex or "0", 16)
            except Exception:
                v = 0
            td.override_instrument_hex = f"{max(0, v - 1):02X}"

    imgui.same_line()

    if _btn(" + ##ti"):
        if td.override_instrument:
            try:
                v = int(td.override_instrument_hex or "0", 16)
            except Exception:
                v = 0
            td.override_instrument_hex = f"{min(255, v + 1):02X}"

    if _dimmed:
        imgui.pop_style_var()

    readonly_flag = getattr(imgui, "INPUT_TEXT_READ_ONLY", 0)
    inst_flags = imgui.INPUT_TEXT_CHARS_UPPERCASE | (0 if td.override_instrument else readonly_flag)

    _pushed = False
    if not td.override_instrument:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, inst = imgui.input_text("Instrument (hex)##trk", td.override_instrument_hex, 4, inst_flags)
    if td.override_instrument and changed:
        td.override_instrument_hex = inst.strip().upper()

    if _pushed:
        imgui.pop_style_var()

    changed, ov_vel = imgui.checkbox("Override Velocity", td.override_velocity)
    if changed:
        td.override_velocity = ov_vel

    vmax_flags = imgui.INPUT_TEXT_CHARS_UPPERCASE | (0 if td.override_velocity else readonly_flag)

    _pushed = False
    if not td.override_velocity:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, vmax = imgui.input_text("Velocity max (hex)##trk", td.override_velocity_max_hex, 4, vmax_flags)
    if td.override_velocity and changed:
        td.override_velocity_max_hex = vmax.strip().upper()

    if _pushed:
        imgui.pop_style_var()

    changed, ov_spill = imgui.checkbox("Override Spillover", td.override_spillover)
    if changed:
        td.override_spillover = ov_spill

    _pushed = False
    if not td.override_spillover:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, sc = imgui.slider_int("Spillover##trk", td.override_spillover_count, 1, 64)
    if td.override_spillover and changed:
        td.override_spillover_count = sc

    if _pushed:
        imgui.pop_style_var()


def draw_tips_window(state):
    if not state.show_tips:
        return
    try:
        imgui.set_next_window_focus()
    except Exception:
        pass
    expanded, opened = imgui.begin("Tips", True)
    if not opened:
        state.show_tips = False
        imgui.end()
        return

    imgui.text("Mouse:")
    imgui.bullet_text("Scroll: vertical pan")
    imgui.bullet_text("Shift + Scroll: horizontal pan")
    imgui.bullet_text("Ctrl + Scroll: horizontal zoom")
    imgui.bullet_text("Middle or Right-drag: pan")
    imgui.bullet_text("Left-drag in roll: Marquee select")
    imgui.bullet_text("Click ruler: move playhead")

    imgui.separator()
    imgui.text("Keyboard:")
    imgui.bullet_text("Arrow Keys: Pan (time / rows)")
    imgui.bullet_text("= / - : Horizontal zoom")
    imgui.bullet_text("Shift + (= / -): Vertical track zoom")
    imgui.bullet_text("PageUp / PageDown: Note height zoom")
    imgui.bullet_text("Space: Play / Pause")
    imgui.bullet_text("Esc: Clear selection")
    imgui.bullet_text("Ctrl+C: Copy selection to Furnace")
    imgui.bullet_text("?: Toggle this window")

    imgui.end()

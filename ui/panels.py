import os
import imgui
from app.state import center_track_pitch_scroll, compute_track_pitch_bounds
from tracker.export import copy_selection_to_clipboard
from ui.icons import (
    ICON_PLAY, ICON_STOP, ICON_CIRCLE_PLAY,
    ICON_CROSSHAIRS, ICON_VOLUME_UP, ICON_COPY,
)


def _brighten(c, factor=1.2):
    return tuple(min(1.0, v * factor) for v in c[:3]) + (c[3],)


def _darken(c, factor=0.7):
    return tuple(v * factor for v in c[:3]) + (c[3],)


def _toggle_colors(base):
    return (base, _brighten(base), _darken(base))


def _square_icon_button(label, colors=None, enabled=True):
    text_size = imgui.calc_text_size(label)
    side = max(text_size.x, text_size.y)
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
    has_track = bool(state.midi.tracks)

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

    imgui.pop_style_var()

    # Volume icon + slider — dimmed when no track
    if not has_track:
        imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)

    imgui.same_line(spacing=12.0)
    imgui.text(ICON_VOLUME_UP)
    imgui.same_line()
    imgui.push_item_width(300.0)
    changed, g = imgui.slider_float("##vol", state.master_gain, 0.0, 1.0)
    if has_track and changed:
        state.master_gain = g
    imgui.pop_item_width()

    if not has_track:
        imgui.pop_style_var()


def _table_row(label, value):
    imgui.table_next_row()
    imgui.table_next_column()
    imgui.text_colored(label, 0.6, 0.6, 0.6, 1.0)
    imgui.table_next_column()
    imgui.text(value)


def draw_midi_info(state):
    if state.midi.path:
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
    else:
        text = "No MIDI loaded."
        text_size = imgui.calc_text_size(text)
        avail = imgui.get_content_region_available()
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + (avail[0] - text_size[0]) * 0.5)
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + (avail[1] - text_size[1]) * 0.5)
        imgui.text(text)


def draw_tips_window(state):
    if not state.show_tips:
        return
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

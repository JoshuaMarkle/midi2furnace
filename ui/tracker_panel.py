# ui/tracker_panel.py
import imgui
from tracker.types import FurnaceConfig
from tracker.export import copy_selection_to_clipboard, build_furnace_clipboard_text
from ui.icons import ICON_COPY, ICON_EYE, ICON_CHECK

def draw_tracker_settings_content(state):
    cfg: FurnaceConfig = state.tracker_cfg
    t = state.theme

    imgui.text_colored("- Export settings -", 1.0, 1.0, 1.0, 1.0)
    imgui.spacing()
    imgui.separator()

    changed, lpq = imgui.slider_int("Lines per 1/4 note", cfg.lines_per_quarter, 1, 32)
    if changed: cfg.lines_per_quarter = lpq

    changed, tr = imgui.slider_int("Transpose (octaves)", cfg.transpose_octaves, -6, 6)
    if changed: cfg.transpose_octaves = tr

    # Default Instrument / Velocity
    imgui.separator()

    changed, definst = imgui.checkbox("Default Instrument", cfg.define_instrument)
    if changed:
        cfg.define_instrument = definst

    imgui.same_line()
    _btn = getattr(imgui, "small_button", imgui.button)

    _dimmed = False
    if not cfg.define_instrument:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _dimmed = True
        except Exception:
            pass

    if _btn(" - "):
        if cfg.define_instrument:
            try:
                v = int(cfg.instrument_hex or "0", 16)
            except Exception:
                v = 0
            v = max(0, min(255, v - 1))
            cfg.instrument_hex = f"{v:02X}"

    imgui.same_line()

    if _btn(" + "):
        if cfg.define_instrument:
            try:
                v = int(cfg.instrument_hex or "0", 16)
            except Exception:
                v = 0
            v = max(0, min(255, v + 1))
            cfg.instrument_hex = f"{v:02X}"

    if _dimmed:
        imgui.pop_style_var()

    readonly_flag = getattr(imgui, "INPUT_TEXT_READ_ONLY", 0)
    inst_flags = imgui.INPUT_TEXT_CHARS_UPPERCASE | (0 if cfg.define_instrument else readonly_flag)

    _pushed = False
    if not cfg.define_instrument:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, inst = imgui.input_text("Instrument (hex)", cfg.instrument_hex, 4, inst_flags)
    if cfg.define_instrument and changed:
        cfg.instrument_hex = inst.strip().upper()

    if _pushed:
        imgui.pop_style_var()

    changed, v_on = imgui.checkbox("Default Velocity", cfg.velocity_enabled)
    if changed:
        cfg.velocity_enabled = v_on

    readonly_flag = getattr(imgui, "INPUT_TEXT_READ_ONLY", 0)
    vmax_flags = imgui.INPUT_TEXT_CHARS_UPPERCASE | (0 if cfg.velocity_enabled else readonly_flag)

    _pushed = False
    if not cfg.velocity_enabled:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, vmax = imgui.input_text("Velocity max (hex)", cfg.velocity_max_hex, 4, vmax_flags)
    if cfg.velocity_enabled and changed:
        cfg.velocity_max_hex = vmax.strip().upper()

    if _pushed:
        imgui.pop_style_var()

    # Note-off mode
    imgui.separator()
    imgui.text("Note-off")
    off_off  = (cfg.note_off_mode == "OFF")
    off_rel  = (cfg.note_off_mode == "REL")

    _off_dimmed = cfg.suppress_note_off
    if _off_dimmed:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.4)
        except Exception:
            _off_dimmed = False
    if imgui.radio_button("REL", off_rel) and not cfg.suppress_note_off:
        cfg.note_off_mode = "REL"
    imgui.same_line()
    if imgui.radio_button("OFF", off_off) and not cfg.suppress_note_off:
        cfg.note_off_mode = "OFF"
    if _off_dimmed:
        imgui.pop_style_var()

    changed, suppress = imgui.checkbox("No note-off (pluck)", cfg.suppress_note_off)
    if changed:
        cfg.suppress_note_off = suppress

    # Polyphony
    imgui.separator()
    imgui.text("Polyphony")
    p1 = (cfg.polyphony_mode == "per_track")
    p2 = (cfg.polyphony_mode == "spillover")
    if imgui.radio_button("Channel per track", p1):
        cfg.polyphony_mode = "per_track"
    if imgui.radio_button("Spillover", p2):
        cfg.polyphony_mode = "spillover"

    spill_disabled = (cfg.polyphony_mode != "spillover")

    _pushed = False
    if spill_disabled:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, auto = imgui.checkbox("Auto spillover", cfg.auto_spillover)
    if not spill_disabled and changed:
        cfg.auto_spillover = auto

    if _pushed:
        imgui.pop_style_var()

    slider_disabled = spill_disabled or cfg.auto_spillover

    _pushed = False
    if slider_disabled:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.5)
            _pushed = True
        except Exception:
            pass

    changed, c = imgui.slider_int("Spillover count", cfg.spillover_count, 1, 64)
    if not slider_disabled and changed:
        cfg.spillover_count = c

    if _pushed:
        imgui.pop_style_var()

    # Export range
    imgui.separator()
    changed, range_on = imgui.checkbox("Limit export range", cfg.export_range_enabled)
    if changed:
        cfg.export_range_enabled = range_on
        if range_on and cfg.export_range_end_beat <= cfg.export_range_start_beat:
            total_b = state.midi.total_beats if state.midi else 0.0
            cfg.export_range_end_beat = max(1.0, total_b)

    _range_dimmed = not cfg.export_range_enabled
    if _range_dimmed:
        try:
            style = imgui.get_style()
            imgui.push_style_var(imgui.STYLE_ALPHA, style.alpha * 0.4)
        except Exception:
            _range_dimmed = False

    total_b = max(1.0, state.midi.total_beats if state.midi else 1.0)
    changed, v = imgui.slider_float("Range start (beat)", cfg.export_range_start_beat, 0.0, total_b, "%.2f")
    if cfg.export_range_enabled and changed:
        cfg.export_range_start_beat = min(v, cfg.export_range_end_beat - 0.25)

    changed, v = imgui.slider_float("Range end (beat)", cfg.export_range_end_beat, 0.0, total_b, "%.2f")
    if cfg.export_range_enabled and changed:
        cfg.export_range_end_beat = max(v, cfg.export_range_start_beat + 0.25)

    if _range_dimmed:
        imgui.pop_style_var()

    imgui.separator()

    # Modal for warnings/errors (e.g., spillover with multi-track selection)
    if getattr(state, "pending_export_popup", None):
        try:
            imgui.open_popup("Export Warning")
        except Exception:
            pass
    try:
        opened = imgui.begin_popup_modal("Export Warning")[0]
    except Exception:
        opened = False
    if opened:
        imgui.text_wrapped(state.pending_export_popup)
        if imgui.button("OK"):
            imgui.close_current_popup()
            state.pending_export_popup = None
        imgui.end_popup()


def draw_furnace_preview(state):
    """Furnace clipboard preview, rendered in mono font."""
    from tracker.export import build_furnace_clipboard_text
    from ui.icons import font_mono

    cfg = state.tracker_cfg
    ok, text_or_err = build_furnace_clipboard_text(state, cfg)

    HSCROLL = getattr(imgui, "WINDOW_HORIZONTAL_SCROLLING_BAR", 0)
    avail_w, avail_h = imgui.get_content_region_available()
    imgui.begin_child("##furnace_preview", 0.0, max(100.0, float(avail_h)), True, HSCROLL)

    if font_mono is not None:
        imgui.push_font(font_mono)

    if ok:
        try:
            imgui.text_unformatted(text_or_err)
        except Exception:
            for line in text_or_err.splitlines():
                imgui.text_unformatted(line)
    else:
        imgui.text_colored("Cannot preview export:", 1.0, 0.5, 0.5, 1.0)
        imgui.separator()
        imgui.text_wrapped(text_or_err)

    if font_mono is not None:
        imgui.pop_font()

    imgui.end_child()

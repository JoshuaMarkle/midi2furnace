import math
from app.state import clamp, zoom_time_center

def handle_navigation_keys(io, state):
    """Arrows pan; +/- horizontal zoom; Shift+/- note height; PgUp/PgDn note height."""
    try:
        if getattr(io, "want_text_input", False):
            return
    except Exception:
        pass

    import pygame as _pg
    keys = _pg.key.get_pressed()
    mods = _pg.key.get_mods()

    dt = float(getattr(io, "delta_time", 1/60.0) or 1/60.0)

    view_w = max(1.0, state.last_canvas_width - state.track_header_w - 18.0)
    pan_speed_x = max(60.0, view_w * 0.5)
    pan_speed_y = max(60.0, state.note_height * 20.0)

    dx = pan_speed_x * dt
    dy = pan_speed_y * dt

    if keys[_pg.K_LEFT]:
        state.scroll_x_px = max(0.0, state.scroll_x_px - dx)
    if keys[_pg.K_RIGHT]:
        state.scroll_x_px = state.scroll_x_px + dx
    if keys[_pg.K_UP]:
        state.scroll_y_px = max(0.0, state.scroll_y_px - dy)
    if keys[_pg.K_DOWN]:
        state.scroll_y_px = state.scroll_y_px + dy

    hz_rate = 10.0
    nh_rate = 5.0
    hz_in = hz_rate ** dt
    hz_out = (1.0 / hz_rate) ** dt
    nh_in = nh_rate ** dt
    nh_out = (1.0 / nh_rate) ** dt

    K_KP_PLUS = getattr(_pg, "K_KP_PLUS", None)
    K_KP_MINUS = getattr(_pg, "K_KP_MINUS", None)
    K_PLUS = getattr(_pg, "K_PLUS", None)
    shift_down = bool(mods & (_pg.KMOD_LSHIFT | _pg.KMOD_RSHIFT))

    plus_pressed = keys[_pg.K_EQUALS] or (K_PLUS is not None and keys[K_PLUS]) or (K_KP_PLUS is not None and keys[K_KP_PLUS])
    minus_pressed = keys[_pg.K_MINUS] or (K_KP_MINUS is not None and keys[K_KP_MINUS])

    if shift_down:
        if not hasattr(state, "_note_h_float"):
            state._note_h_float = float(state.note_height)
        if plus_pressed:
            state._note_h_float *= nh_in
        if minus_pressed:
            state._note_h_float *= nh_out
        state._note_h_float = float(clamp(state._note_h_float, 2.0, 48.0))
        new_nh = int(round(state._note_h_float))
        if new_nh != state.note_height and (plus_pressed or minus_pressed):
            state.note_height = new_nh
    else:
        if plus_pressed:
            zoom_time_center(state, hz_in)
        if minus_pressed:
            zoom_time_center(state, hz_out)

    # Note height via PageUp/PageDown
    if not hasattr(state, "_note_h_float"):
        state._note_h_float = float(state.note_height)
    note_step_per_sec = 8.0
    changed_nh = False
    if keys[_pg.K_PAGEUP]:
        state._note_h_float += note_step_per_sec * dt
        changed_nh = True
    elif keys[_pg.K_PAGEDOWN]:
        state._note_h_float -= note_step_per_sec * dt
        changed_nh = True

    state._note_h_float = float(clamp(state._note_h_float, 2.0, 48.0))
    new_int = int(round(state._note_h_float))
    if changed_nh and new_int != state.note_height:
        state.note_height = new_int

import imgui
from app.state import clamp
from ui.panels import draw_playback_bar, draw_midi_info
from ui.tracker_panel import draw_tracker_settings_content, draw_furnace_preview
from ui.timeline import draw_timeline_canvas
from ui.tracker_view import draw_tracker_view

_NO_DECOR = (
    imgui.WINDOW_NO_MOVE
    | imgui.WINDOW_NO_RESIZE
    | imgui.WINDOW_NO_COLLAPSE
    | imgui.WINDOW_NO_TITLE_BAR
)

_NO_DECOR_TITLED = (
    imgui.WINDOW_NO_MOVE
    | imgui.WINDOW_NO_RESIZE
    | imgui.WINDOW_NO_COLLAPSE
)

_SPLITTER_W = 4.0
_SPLITTER_H = 4.0


def draw_dim_overlay(state):
    if not (state.show_settings or state.show_tips):
        return
    w, h = state.window_size
    imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, 0, 0, 0, 0.4)
    imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(w, h)
    try:
        imgui.set_next_window_focus()
    except Exception:
        pass
    imgui.begin(
        "##dim_overlay",
        flags=_NO_DECOR | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_NAV,
    )
    imgui.invisible_button("##dim_click", w, h)
    if imgui.is_item_clicked():
        state.show_settings = False
        state.show_tips = False
    imgui.end()
    imgui.pop_style_var()
    imgui.pop_style_color()


def draw_tiled_layout(state):
    w, h = state.window_size
    menu_h = imgui.get_frame_height_with_spacing()
    io = imgui.get_io()

    # --- Top toolbar: playback controls (full width) ---
    toolbar_h = imgui.get_frame_height() + 24
    imgui.set_next_window_position(0, menu_h)
    imgui.set_next_window_size(w, toolbar_h)
    imgui.begin("##toolbar", flags=_NO_DECOR | imgui.WINDOW_NO_SCROLLBAR)
    draw_playback_bar(state)
    imgui.end()

    body_y = menu_h + toolbar_h
    body_h = h - body_y
    if body_h < 1:
        return

    left_w = w * state.split_x
    right_x = left_w + _SPLITTER_W
    right_w = max(1.0, w - right_x)

    show_top = state.show_playback
    show_bot = state.show_tracker_settings

    if show_top and show_bot:
        top_h = body_h * state.split_y
        bot_y = body_y + top_h + _SPLITTER_H
        bot_h = max(1.0, body_h - top_h - _SPLITTER_H)
    elif show_top:
        top_h = body_h
        bot_y = body_y + body_h
        bot_h = 0
    elif show_bot:
        top_h = 0
        bot_y = body_y
        bot_h = body_h
    else:
        top_h = 0
        bot_y = body_y
        bot_h = 0

    # --- Left: Piano Roll / Preview tabs ---
    imgui.set_next_window_position(0, body_y)
    imgui.set_next_window_size(left_w, body_h)
    imgui.begin(
        "##left_panel",
        flags=_NO_DECOR
        | imgui.WINDOW_NO_SCROLLBAR
        | imgui.WINDOW_NO_SCROLL_WITH_MOUSE,
    )
    imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (4, 2))
    if imgui.begin_tab_bar("##left_tabs"):
        if imgui.begin_tab_item("Piano Roll")[0]:
            draw_timeline_canvas(state)
            imgui.end_tab_item()
        if imgui.begin_tab_item("Tracker")[0]:
            draw_tracker_view(state)
            imgui.end_tab_item()
        if imgui.begin_tab_item("Preview")[0]:
            draw_furnace_preview(state)
            imgui.end_tab_item()
        imgui.end_tab_bar()
    imgui.pop_style_var()
    imgui.end()

    # --- Vertical splitter ---
    _draw_v_splitter(state, io, left_w, body_y, body_h, w)

    # --- Top-right: MIDI Info ---
    if show_top and top_h > 0:
        imgui.set_next_window_position(right_x, body_y)
        imgui.set_next_window_size(right_w, top_h)
        imgui.begin("##midi_info", flags=_NO_DECOR)
        draw_midi_info(state)
        imgui.end()

    # --- Horizontal splitter on right side ---
    if show_top and show_bot:
        _draw_h_splitter(state, io, right_x, right_w, body_y + top_h, body_y, body_h)

    # --- Bottom-right: Furnace Export ---
    if show_bot and bot_h > 0:
        imgui.set_next_window_position(right_x, bot_y)
        imgui.set_next_window_size(right_w, bot_h)
        imgui.begin("##furnace_export", flags=_NO_DECOR)
        draw_tracker_settings_content(state)
        imgui.end()


def _draw_v_splitter(state, io, left_w, body_y, body_h, total_w):
    sx = left_w
    grab_w = 8.0
    imgui.set_next_window_position(sx - (grab_w - _SPLITTER_W) * 0.5, body_y)
    imgui.set_next_window_size(grab_w, body_h)
    imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
    imgui.begin("##vsplit", flags=_NO_DECOR | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_BACKGROUND)
    imgui.invisible_button("##vdrag", grab_w, body_h)
    hovered = imgui.is_item_hovered()
    active = imgui.is_item_active()
    if hovered or active:
        try:
            imgui.set_mouse_cursor(imgui.MOUSE_CURSOR_RESIZE_EW)
        except Exception:
            pass
    if active:
        state.split_x = clamp(io.mouse_pos[0] / max(1.0, total_w), 0.2, 0.85)
    dl = imgui.get_window_draw_list()
    if hovered or active:
        col = imgui.get_color_u32_rgba(0.059, 0.529, 0.980, 0.7)
    else:
        col = imgui.get_color_u32_rgba(1, 1, 1, 0.08)
    cx = sx + _SPLITTER_W * 0.5
    dl.add_line(cx, body_y, cx, body_y + body_h, col, _SPLITTER_W)
    imgui.end()
    imgui.pop_style_var()


def _draw_h_splitter(state, io, right_x, right_w, splitter_y, body_y, body_h):
    grab_h = 8.0
    imgui.set_next_window_position(right_x, splitter_y - (grab_h - _SPLITTER_H) * 0.5)
    imgui.set_next_window_size(right_w, grab_h)
    imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
    imgui.begin("##hsplit", flags=_NO_DECOR | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_BACKGROUND)
    imgui.invisible_button("##hdrag", right_w, grab_h)
    hovered = imgui.is_item_hovered()
    active = imgui.is_item_active()
    if hovered or active:
        try:
            imgui.set_mouse_cursor(imgui.MOUSE_CURSOR_RESIZE_NS)
        except Exception:
            pass
    if active:
        state.split_y = clamp((io.mouse_pos[1] - body_y) / max(1.0, body_h), 0.1, 0.9)
    dl = imgui.get_window_draw_list()
    if hovered or active:
        col = imgui.get_color_u32_rgba(0.059, 0.529, 0.980, 0.7)
    else:
        col = imgui.get_color_u32_rgba(1, 1, 1, 0.08)
    cy = splitter_y + _SPLITTER_H * 0.5
    dl.add_line(right_x, cy, right_x + right_w, cy, col, _SPLITTER_H)
    imgui.end()
    imgui.pop_style_var()

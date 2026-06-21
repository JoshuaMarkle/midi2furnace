"""Floating settings window with General and Colors tabs."""
import imgui


_IMGUI_COLOR_GROUPS = [
    ("Text", [
        ("Text", "COLOR_TEXT"),
        ("Text Disabled", "COLOR_TEXT_DISABLED"),
    ]),
    ("Backgrounds", [
        ("Window", "COLOR_WINDOW_BACKGROUND"),
        ("Child", "COLOR_CHILD_BACKGROUND"),
        ("Popup", "COLOR_POPUP_BACKGROUND"),
        ("Menu Bar", "COLOR_MENUBAR_BACKGROUND"),
    ]),
    ("Borders", [
        ("Border", "COLOR_BORDER"),
        ("Border Shadow", "COLOR_BORDER_SHADOW"),
    ]),
    ("Frames", [
        ("Frame Background", "COLOR_FRAME_BACKGROUND"),
        ("Frame Bg Hovered", "COLOR_FRAME_BACKGROUND_HOVERED"),
        ("Frame Bg Active", "COLOR_FRAME_BACKGROUND_ACTIVE"),
    ]),
    ("Title Bar", [
        ("Title Background", "COLOR_TITLE_BACKGROUND"),
        ("Title Bg Active", "COLOR_TITLE_BACKGROUND_ACTIVE"),
        ("Title Bg Collapsed", "COLOR_TITLE_BACKGROUND_COLLAPSED"),
    ]),
    ("Buttons", [
        ("Button", "COLOR_BUTTON"),
        ("Button Hovered", "COLOR_BUTTON_HOVERED"),
        ("Button Active", "COLOR_BUTTON_ACTIVE"),
    ]),
    ("Headers", [
        ("Header", "COLOR_HEADER"),
        ("Header Hovered", "COLOR_HEADER_HOVERED"),
        ("Header Active", "COLOR_HEADER_ACTIVE"),
    ]),
    ("Scrollbar", [
        ("Scrollbar Bg", "COLOR_SCROLLBAR_BACKGROUND"),
        ("Scrollbar Grab", "COLOR_SCROLLBAR_GRAB"),
        ("Grab Hovered", "COLOR_SCROLLBAR_GRAB_HOVERED"),
        ("Grab Active", "COLOR_SCROLLBAR_GRAB_ACTIVE"),
    ]),
    ("Tabs", [
        ("Tab", "COLOR_TAB"),
        ("Tab Hovered", "COLOR_TAB_HOVERED"),
        ("Tab Active", "COLOR_TAB_ACTIVE"),
    ]),
    ("Slider / Check", [
        ("Check Mark", "COLOR_CHECK_MARK"),
        ("Slider Grab", "COLOR_SLIDER_GRAB"),
        ("Slider Active", "COLOR_SLIDER_GRAB_ACTIVE"),
    ]),
    ("Separator", [
        ("Separator", "COLOR_SEPARATOR"),
        ("Separator Hovered", "COLOR_SEPARATOR_HOVERED"),
        ("Separator Active", "COLOR_SEPARATOR_ACTIVE"),
    ]),
    ("Resize Grip", [
        ("Grip", "COLOR_RESIZE_GRIP"),
        ("Grip Hovered", "COLOR_RESIZE_GRIP_HOVERED"),
        ("Grip Active", "COLOR_RESIZE_GRIP_ACTIVE"),
    ]),
]

_APP_COLOR_FIELDS = [
    ("Accent", [
        ("Primary", "accent_primary"),
        ("Secondary", "accent_secondary"),
    ]),
    ("Piano Roll", [
        ("Background", "piano_roll_bg"),
        ("Track Header", "track_header_bg"),
        ("Ruler", "ruler_bg"),
        ("Selection", "selection"),
        ("GL Clear", "clear_color"),
    ]),
    ("Channels", [
        ("FM", "channel_fm"),
        ("Pulse", "channel_pulse"),
        ("Noise", "channel_noise"),
        ("PCM", "channel_pcm"),
        ("Wave", "channel_wave"),
        ("OP", "channel_op"),
    ]),
]


_FIRST_USE = getattr(imgui, "FIRST_USE_EVER", 4)


def draw_settings_window(state):
    if not state.show_settings:
        return

    w, h = state.window_size
    win_w, win_h = 520, 500
    imgui.set_next_window_size(win_w, win_h, _FIRST_USE)
    imgui.set_next_window_position(
        (w - win_w) * 0.5, (h - win_h) * 0.5, _FIRST_USE
    )

    try:
        imgui.set_next_window_focus()
    except Exception:
        pass
    expanded, opened = imgui.begin("Settings", True)
    if not opened:
        state.show_settings = False
        imgui.end()
        return

    if imgui.begin_tab_bar("##SettingsTabs"):
        if imgui.begin_tab_item("General").selected:
            _draw_general_tab(state)
            imgui.end_tab_item()

        if imgui.begin_tab_item("Colors").selected:
            _draw_colors_tab(state)
            imgui.end_tab_item()

        imgui.end_tab_bar()

    imgui.end()


def _draw_general_tab(state):
    imgui.spacing()
    imgui.text("UI Scale")
    changed, val = imgui.slider_float("##ui_scale", state.ui_scale, 1.0, 3.0, "%.2f")
    if changed:
        state.ui_scale = val
        state.request_font_rebuild = True

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    imgui.text("Layout")
    changed, val = imgui.slider_int("Track Header Width", state.track_header_w, 80, 300)
    if changed:
        state.track_header_w = val

    changed, val = imgui.slider_int("Ruler Height", state.ruler_h, 16, 60)
    if changed:
        state.ruler_h = val


def _draw_colors_tab(state):
    theme = state.theme
    style = imgui.get_style()

    imgui.begin_child("##ColorScroll", 0, 0, True)

    if imgui.tree_node("ImGui Style", imgui.TREE_NODE_DEFAULT_OPEN):
        for group_name, entries in _IMGUI_COLOR_GROUPS:
            if imgui.tree_node(group_name):
                for label, attr_name in entries:
                    idx = getattr(imgui, attr_name, None)
                    if idx is None or idx not in theme.imgui_colors:
                        continue
                    r, g, b, a = theme.imgui_colors[idx]
                    changed, color = imgui.color_edit4(
                        label, r, g, b, a
                    )
                    if changed:
                        theme.imgui_colors[idx] = color
                        try:
                            style.colors[idx] = color
                        except Exception:
                            pass
                imgui.tree_pop()
        imgui.tree_pop()

    if imgui.tree_node("App Colors", imgui.TREE_NODE_DEFAULT_OPEN):
        for group_name, entries in _APP_COLOR_FIELDS:
            if imgui.tree_node(group_name):
                for label, field_name in entries:
                    cur = getattr(theme, field_name)
                    r, g, b, a = cur
                    changed, color = imgui.color_edit4(
                        label, r, g, b, a
                    )
                    if changed:
                        setattr(theme, field_name, color)
                imgui.tree_pop()
        imgui.tree_pop()

    imgui.end_child()

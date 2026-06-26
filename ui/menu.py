import imgui


def draw_menu_bar(state, *, on_open, ini_path: str = "", on_copy=None, on_export_file=None):
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File", True):
            if imgui.menu_item("Open file", "Ctrl+O", False, True)[0]:
                on_open()
            if on_copy and imgui.menu_item("Copy to Furnace", "Ctrl+C", False, True)[0]:
                on_copy()
            if on_export_file and imgui.menu_item("Export selection", "Ctrl+S", False, True)[0]:
                on_export_file()
            imgui.separator()
            if imgui.menu_item("Quit", "Ctrl+Q", False, True)[0]:
                state.should_quit = True
            imgui.end_menu()

        if imgui.begin_menu("View", True):
            if imgui.menu_item("Zoom to Fit (Time)", None, False, True)[0]:
                state.request_fit_time = True
            if imgui.menu_item("Zoom to Fit (Vertical)", None, False, True)[0]:
                state.request_fit_vertical = True
            if imgui.menu_item("Zoom to Fit (All)", None, False, True)[0]:
                state.request_fit_all = True
            imgui.separator()
            if imgui.menu_item("Reset Zoom", None, False, True)[0]:
                state.request_reset_zoom = True
            imgui.end_menu()

        if imgui.begin_menu("Windows", True):
            clicked, val = imgui.menu_item("MIDI Info", None, state.show_playback, True)
            if clicked:
                state.show_playback = not state.show_playback
            clicked, val = imgui.menu_item("Furnace Export", None, state.show_tracker_settings, True)
            if clicked:
                state.show_tracker_settings = not state.show_tracker_settings
            clicked, val = imgui.menu_item("Settings", None, state.show_settings, True)
            if clicked:
                state.show_settings = not state.show_settings
            imgui.separator()
            clicked, val = imgui.menu_item("Tips", "?", state.show_tips, True)
            if clicked:
                state.show_tips = not state.show_tips
            imgui.end_menu()

        imgui.end_main_menu_bar()

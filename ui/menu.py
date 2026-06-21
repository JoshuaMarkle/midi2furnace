import imgui
from ui.icons import (
    ICON_FOLDER_OPEN, ICON_FILE_EXPORT, ICON_TIMES,
    ICON_COPY, ICON_SEARCH_PLUS, ICON_COMPRESS, ICON_UNDO,
    ICON_MUSIC, ICON_SLIDERS, ICON_QUESTION_CIRCLE, ICON_COG,
)


def draw_menu_bar(state, *, on_open, ini_path: str = "", on_copy=None, on_export_file=None):
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File", True):
            if imgui.menu_item(ICON_FOLDER_OPEN + " Open file", "Ctrl+O", False, True)[0]:
                on_open()
            if on_export_file and imgui.menu_item(ICON_FILE_EXPORT + " Export selection", None, False, True)[0]:
                on_export_file()
            imgui.separator()
            if imgui.menu_item(ICON_TIMES + " Quit", "Ctrl+Q", False, True)[0]:
                state.should_quit = True
            imgui.end_menu()

        if imgui.begin_menu("Edit", True):
            if on_copy and imgui.menu_item(ICON_COPY + " Copy selection to Furnace", "Ctrl+C", False, True)[0]:
                on_copy()
            imgui.separator()
            if imgui.menu_item(ICON_COG + " Settings", None, False, True)[0]:
                state.show_settings = not state.show_settings
            imgui.end_menu()

        if imgui.begin_menu("View", True):
            if imgui.menu_item(ICON_SEARCH_PLUS + " Zoom to Fit (Time)", None, False, True)[0]:
                state.request_fit_time = True
            if imgui.menu_item(ICON_SEARCH_PLUS + " Zoom to Fit (Vertical)", None, False, True)[0]:
                state.request_fit_vertical = True
            if imgui.menu_item(ICON_COMPRESS + " Zoom to Fit (All)", None, False, True)[0]:
                state.request_fit_all = True
            imgui.separator()
            if imgui.menu_item(ICON_UNDO + " Reset Zoom", None, False, True)[0]:
                state.request_reset_zoom = True
            imgui.end_menu()

        if imgui.begin_menu("Windows", True):
            clicked, val = imgui.menu_item(ICON_MUSIC + " MIDI Info", None, state.show_playback, True)
            if clicked:
                state.show_playback = not state.show_playback
            clicked, val = imgui.menu_item(ICON_SLIDERS + " Furnace Export", None, state.show_tracker_settings, True)
            if clicked:
                state.show_tracker_settings = not state.show_tracker_settings
            imgui.separator()
            clicked, val = imgui.menu_item(ICON_QUESTION_CIRCLE + " Tips", "?", state.show_tips, True)
            if clicked:
                state.show_tips = not state.show_tips
            imgui.end_menu()

        imgui.end_main_menu_bar()

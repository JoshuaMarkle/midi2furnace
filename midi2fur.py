#!/bin/python

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import sys
import math
import warnings
warnings.filterwarnings("ignore", message=".*avx2.*", category=RuntimeWarning)
import pygame
from pygame.locals import DOUBLEBUF, OPENGL, RESIZABLE, VIDEORESIZE, QUIT, MOUSEWHEEL
import OpenGL.GL as gl

import imgui
from imgui.integrations.pygame import PygameRenderer

from typing import List, Tuple, Optional


from input.shortcuts import handle_shortcuts, handle_global_keys
from input.nav import handle_navigation_keys
from ui.menu import draw_menu_bar
from ui.layout import draw_tiled_layout, draw_dim_overlay
from ui.panels import draw_tips_window
from ui.settings import draw_settings_window
from ui.icons import load_fonts
from ui.theme import load_default_theme
from audio.player import update_playback
from input.play_keys import handle_play_keys
from tracker.export import copy_selection_to_clipboard, export_selection_to_file

from version import __version__


# Persist ImGui layout here
UI_INI_PATH = "imgui.ini"
UI_SCALE = 1.5

# ---- bring in our split modules ----
from app.state import (
    AppState, clamp, beats_to_x, tick_to_beats,
    compute_track_pitch_bounds, center_track_pitch_scroll,
    zoom_to_fit_time, zoom_to_fit_vertical, zoom_reset, zoom_time_center,
)
from app.midi_doc import MidiDoc, Note, TrackData


# ---- file dialogs (zenity -> tkinter fallback) ----
def _zenity_path():
    import shutil
    return shutil.which("zenity")

def ask_open_midi() -> Optional[str]:
    zenity = _zenity_path()
    if zenity:
        try:
            import subprocess
            result = subprocess.run(
                [zenity, "--file-selection",
                 "--title=Open MIDI file",
                 "--file-filter=MIDI files | *.mid *.midi",
                 "--file-filter=All files | *"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception:
            pass
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Open MIDI file",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")],
        )
        root.destroy()
        return path if path else None
    except Exception:
        return None


def _ask_save_path() -> Optional[str]:
    zenity = _zenity_path()
    if zenity:
        try:
            import subprocess
            result = subprocess.run(
                [zenity, "--file-selection", "--save", "--confirm-overwrite",
                 "--title=Export Furnace Pattern Data",
                 "--file-filter=Text files | *.txt",
                 "--file-filter=All files | *"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception:
            pass
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.asksaveasfilename(
            title="Export Furnace Pattern Data",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        root.destroy()
        return path if path else None
    except Exception:
        return None


def do_export_file(state: AppState):
    path = _ask_save_path()
    if not path:
        return
    ok, msg = export_selection_to_file(state, state.tracker_cfg, path)
    print(f"[Export] {msg}")


def do_open_file(state: AppState):
    path = ask_open_midi()
    if not path:
        return
    try:
        state.midi.load(path)
        state.request_fit_all = True
        state.track_height_auto = True
    except Exception as e:
        print(f"Failed to open MIDI: {e}")


# ----------------- App -----------------
def main():
    # --- Pygame / GL init ---
    pygame.init()
    size = (1920, 1080)
    flags = DOUBLEBUF | OPENGL | RESIZABLE

    def try_make_gl(size, flags):
        # Attempt 0: default (no attributes)
        try:
            pygame.display.set_mode(size, flags)
            return True, "default"
        except Exception as e0:
            print(f"[GL] default failed: {e0}")

        # Attempt 1: very compatible GL 2.1 (compat profile), no extra buffers
        try:
            try:
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_COMPATIBILITY)
            except Exception:
                pass
            for attr, val in [
                (pygame.GL_CONTEXT_MAJOR_VERSION, 2),
                (pygame.GL_CONTEXT_MINOR_VERSION, 1),
                (pygame.GL_DOUBLEBUFFER, 1),
                (pygame.GL_DEPTH_SIZE, 0),
                (pygame.GL_STENCIL_SIZE, 0),
                (pygame.GL_MULTISAMPLEBUFFERS, 0),
                (pygame.GL_MULTISAMPLESAMPLES, 0),
            ]:
                try: pygame.display.gl_set_attribute(attr, val)
                except Exception: pass
            pygame.display.set_mode(size, flags)
            return True, "GL 2.1 compat"
        except Exception as e1:
            print(f"[GL] GL 2.1 compat failed: {e1}")

        # Attempt 2: GL 3.2 core (some drivers prefer core profiles)
        try:
            try:
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            except Exception:
                pass
            for attr, val in [
                (pygame.GL_CONTEXT_MAJOR_VERSION, 3),
                (pygame.GL_CONTEXT_MINOR_VERSION, 2),
                (pygame.GL_DOUBLEBUFFER, 1),
                (pygame.GL_DEPTH_SIZE, 0),
                (pygame.GL_STENCIL_SIZE, 0),
                (pygame.GL_MULTISAMPLEBUFFERS, 0),
                (pygame.GL_MULTISAMPLESAMPLES, 0),
            ]:
                try: pygame.display.gl_set_attribute(attr, val)
                except Exception: pass
            pygame.display.set_mode(size, flags)
            return True, "GL 3.2 core"
        except Exception as e2:
            print(f"[GL] GL 3.2 core failed: {e2}")

        return False, "no GL context"

    ok, mode = try_make_gl(size, flags)
    if not ok:
        print("\n[Error] Could not create an OpenGL context. On Linux, install Mesa GL/GLX and run under X11/XWayland.\n"
            "Try: sudo apt install mesa-utils libgl1 libglu1-mesa libglx-mesa0\n"
            "If using Wayland, run: SDL_VIDEODRIVER=x11 ./midi2furnace\n")
        sys.exit(1)

    pygame.display.set_caption("MIDI Piano Roll (pyimgui)")
    gl.glViewport(0, 0, *pygame.display.get_surface().get_size())



    # --- ImGui init ---
    imgui.create_context()
    io = imgui.get_io()

    load_fonts(io, UI_SCALE)

    io.config_flags |= imgui.CONFIG_NAV_ENABLE_KEYBOARD
    # Only allow moving windows from the title bar (not the content area)
    try:
        io.config_windows_move_from_title_bar_only = True
    except AttributeError:
        try:
            io.ConfigWindowsMoveFromTitleBarOnly = True
        except Exception:
            pass

    # Tell ImGui where to persist layout and load it
    try:
        io.ini_filename = UI_INI_PATH
    except AttributeError:
        try:
            io.ini_file_name = UI_INI_PATH
        except AttributeError:
            try:
                io.IniFilename = UI_INI_PATH
            except Exception:
                pass
    try:
        imgui.load_ini_settings_from_disk(UI_INI_PATH)
    except Exception as _e:
        # Non-fatal: we'll still run and save on exit
        print(f"[Layout] Load warning: {_e}")

    try:
        renderer = PygameRenderer(pygame.display.get_surface())
    except TypeError:
        renderer = PygameRenderer()

    clock = pygame.time.Clock()
    state = AppState()
    state.window_size = size
    state.ui_scale = UI_SCALE

    # Load and apply Furnace-style theme
    state.theme = load_default_theme()
    state.theme.apply()

    try:
        while not state.should_quit:
            for event in pygame.event.get():
                if event.type == QUIT:
                    state.should_quit = True
                elif event.type == VIDEORESIZE:
                    size = event.size
                    pygame.display.set_mode(size, flags)
                    gl.glViewport(0, 0, *size)
                    state.window_size = size
                elif event.type == MOUSEWHEEL:
                    io.mouse_wheel = event.y
                renderer.process_event(event)

            renderer.process_inputs()
            io.display_size = state.window_size

            imgui.new_frame()

            # UI
            draw_menu_bar(
                state,
                on_open=lambda: do_open_file(state),
                ini_path=UI_INI_PATH,
                on_copy=lambda: copy_selection_to_clipboard(state, state.tracker_cfg),
                on_export_file=lambda: do_export_file(state),
            )
            draw_tiled_layout(state)
            draw_dim_overlay(state)
            draw_tips_window(state)
            draw_settings_window(state)

            # Update play transport and keys
            update_playback(state)
            handle_navigation_keys(io, state)
            handle_play_keys(io, state)  # SPACE to toggle play
            handle_global_keys(io, state)
            handle_shortcuts(io, state, on_open=lambda: do_open_file(state),
                 on_copy=lambda: copy_selection_to_clipboard(state, state.tracker_cfg),
                 on_export=lambda: do_export_file(state))

            if state.show_demo:
                imgui.show_demo_window()

            # Render
            gl.glClearColor(*state.theme.clear_color)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            imgui.render()
            renderer.render(imgui.get_draw_data())
            pygame.display.flip()
            clock.tick(120)

            # Rebuild fonts when UI scale changes
            if state.request_font_rebuild:
                state.request_font_rebuild = False
                load_fonts(io, state.ui_scale)
                try:
                    renderer.refresh_font_texture()
                except Exception:
                    pass
    finally:
        try:
            renderer.shutdown()
            try:
                imgui.save_ini_settings_to_disk(UI_INI_PATH)
            except Exception as _e:
                print(f"[Layout] Save warning: {_e}")
        except Exception:
            pass
        pygame.quit()
        try:
            if imgui.get_current_context() is not None:
                imgui.destroy_context()
        except Exception:
            pass


def _check_deps():
    missing = []
    for mod in ("pygame", "OpenGL", "OpenGL.GL", "imgui", "imgui.integrations.pygame", "mido"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"[Error] Missing packages: {', '.join(missing)}")
        print("Install with: pip install", " ".join(m.split(".")[0].lower() for m in missing))
        sys.exit(1)


if __name__ == "__main__":
    _check_deps()
    main()

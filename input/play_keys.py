# input/play_keys.py
import imgui


def _key_pressed(name):
    KeyEnum = getattr(imgui, "Key", None)
    if KeyEnum is not None and hasattr(KeyEnum, name):
        try:
            if imgui.is_key_pressed(getattr(KeyEnum, name), repeat=False):
                return True
        except Exception:
            pass
    legacy = getattr(imgui, f"KEY_{name.upper()}", None)
    if legacy is not None:
        try:
            if imgui.is_key_pressed(legacy, repeat=False):
                return True
        except Exception:
            pass
    return False


def handle_play_keys(io, state):
    try:
        if getattr(io, "want_text_input", False):
            return
    except Exception:
        pass

    from audio.player import start_playback, stop_playback

    if _key_pressed("Space"):
        if getattr(state, "playing", False):
            stop_playback(state, restore_cursor=False)
        else:
            start_playback(state)

    if _key_pressed("Enter") or _key_pressed("Return"):
        if getattr(state, "playing", False):
            stop_playback(state, restore_cursor=False)
        else:
            state.playhead_beats = 0.0
            start_playback(state)

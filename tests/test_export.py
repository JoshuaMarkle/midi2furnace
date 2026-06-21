"""Tests for tracker/export.py — clipboard copy and file export."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tracker.export import (
    build_furnace_clipboard_text,
    copy_selection_to_clipboard,
    export_selection_to_file,
    _midi_to_name_oct,
    _vol_hex,
    _note_on_cell,
    _off_cell,
    _blank_cell,
)
from tracker.types import FurnaceConfig
from app.midi_doc import MidiDoc, Note, TrackData


# ---------- minimal state stub ----------

class _State:
    def __init__(self):
        self.midi = MidiDoc()
        self.selected_notes = set()


def _make_state(*notes):
    """notes: list of (pitch, vel, start_tick, end_tick)"""
    state = _State()
    td = TrackData("test")
    for pitch, vel, st, et in notes:
        td.notes.append(Note(st, et, pitch, vel, 0))
    td.pitch_min = min(n.pitch for n in td.notes) if td.notes else 127
    td.pitch_max = max(n.pitch for n in td.notes) if td.notes else 0
    state.midi.tracks = [td]
    state.midi.ticks_per_beat = 480
    state.midi.total_ticks = max((n.end_tick for n in td.notes), default=0)
    return state


# ---------- unit tests ----------

def test_midi_to_name_oct_middle_c():
    L, acc, oct = _midi_to_name_oct(60, 0)
    assert L == "C" and acc == "-" and oct == 4


def test_midi_to_name_oct_transpose():
    L, acc, oct = _midi_to_name_oct(60, 1)
    assert oct == 5


def test_midi_to_name_oct_sharp():
    L, acc, oct = _midi_to_name_oct(61, 0)  # C#4
    assert L == "C" and acc == "#" and oct == 4


def test_vol_hex_disabled():
    cfg = FurnaceConfig(velocity_enabled=False)
    assert _vol_hex(100, cfg) == ".."


def test_vol_hex_max():
    cfg = FurnaceConfig(velocity_enabled=True, velocity_max_hex="FF")
    assert _vol_hex(127, cfg) == "FF"


def test_vol_hex_zero():
    cfg = FurnaceConfig(velocity_enabled=True, velocity_max_hex="FF")
    assert _vol_hex(0, cfg) == "00"


def test_note_on_cell_length():
    cfg = FurnaceConfig()
    cell = _note_on_cell(60, 100, cfg)
    assert len(cell) == 11


def test_note_on_cell_with_instrument():
    cfg = FurnaceConfig(define_instrument=True, instrument_hex="01")
    cell = _note_on_cell(60, 100, cfg)
    assert "01" in cell


def test_note_on_cell_no_instrument():
    cfg = FurnaceConfig(define_instrument=False)
    cell = _note_on_cell(60, 100, cfg)
    assert cell[3:5] == ".."


def test_off_cell():
    cfg = FurnaceConfig(note_off_mode="REL")
    cell = _off_cell(cfg)
    assert cell.startswith("REL") and len(cell) == 11


def test_blank_cell_length():
    assert len(_blank_cell()) == 11


# ---------- build_furnace_clipboard_text ----------

def test_empty_state_returns_header():
    state = _State()
    state.midi.tracks = []
    state.midi.ticks_per_beat = 480
    cfg = FurnaceConfig()
    ok, text = build_furnace_clipboard_text(state, cfg)
    assert ok
    assert text.startswith("org.tildearrow.furnace - Pattern Data")


def test_single_note_output():
    # C4, vel 100, beats 0-1 at 480tpq -> lines 0-4 (lpq=4)
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig(lines_per_quarter=4)
    ok, text = build_furnace_clipboard_text(state, cfg)
    assert ok
    lines = text.split("\n")
    # header + "0" + pattern rows
    assert len(lines) >= 3
    # First pattern row must contain a note-on
    first_row = lines[2]
    assert "C-4" in first_row


def test_note_off_appears():
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig(lines_per_quarter=4, note_off_mode="REL")
    ok, text = build_furnace_clipboard_text(state, cfg)
    assert ok
    assert "REL" in text


def test_two_tracks_two_channels():
    state = _State()
    td1 = TrackData("t1")
    td1.notes = [Note(0, 480, 60, 100, 0)]
    td2 = TrackData("t2")
    td2.notes = [Note(0, 480, 64, 100, 0)]
    state.midi.tracks = [td1, td2]
    state.midi.ticks_per_beat = 480
    cfg = FurnaceConfig(polyphony_mode="per_track")
    ok, text = build_furnace_clipboard_text(state, cfg)
    assert ok
    first_row = text.split("\n")[2]
    # two cells separated by |
    assert first_row.count("|") == 2


def test_spillover_single_track():
    state = _make_state((60, 100, 0, 480), (64, 100, 0, 480))
    cfg = FurnaceConfig(polyphony_mode="spillover", spillover_count=2, lines_per_quarter=4)
    ok, text = build_furnace_clipboard_text(state, cfg)
    assert ok


def test_spillover_multi_track_error():
    state = _State()
    td1 = TrackData("t1")
    td1.notes = [Note(0, 480, 60, 100, 0)]
    td2 = TrackData("t2")
    td2.notes = [Note(0, 480, 64, 100, 0)]
    state.midi.tracks = [td1, td2]
    state.midi.ticks_per_beat = 480
    cfg = FurnaceConfig(polyphony_mode="spillover")
    ok, msg = build_furnace_clipboard_text(state, cfg)
    assert not ok
    assert "single track" in msg.lower() or "spillover" in msg.lower()


# ---------- file export ----------

def test_export_to_file_creates_file():
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig()
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        path = f.name
    try:
        ok, msg = export_selection_to_file(state, cfg, path)
        assert ok, msg
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert content.startswith("org.tildearrow.furnace")
    finally:
        os.unlink(path)


def test_export_to_file_content_matches_build():
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig()
    _, expected = build_furnace_clipboard_text(state, cfg)
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        path = f.name
    try:
        ok, _ = export_selection_to_file(state, cfg, path)
        assert ok
        with open(path) as f:
            content = f.read()
        assert content == expected
    finally:
        os.unlink(path)


def test_export_to_bad_path_returns_error():
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig()
    ok, msg = export_selection_to_file(state, cfg, "/nonexistent_dir/out.txt")
    assert not ok
    assert "Failed" in msg


# ---------- clipboard ----------

def test_clipboard_copy_succeeds():
    """xclip must be installed for this to pass."""
    state = _make_state((60, 100, 0, 480))
    cfg = FurnaceConfig()
    ok, msg = copy_selection_to_clipboard(state, cfg)
    assert ok, f"Clipboard copy failed: {msg}"
    assert msg == "Copied"

    import subprocess
    result = subprocess.run(
        ["xclip", "-selection", "clipboard", "-o"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("org.tildearrow.furnace")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

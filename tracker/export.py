# tracker/export.py
import math
from typing import List, Tuple, Dict, Set
from tracker.types import FurnaceConfig

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def _midi_to_name_oct(note: int, transpose_octaves: int) -> Tuple[str, str, int]:
    n = max(0, min(127, int(note) + 12 * transpose_octaves))
    name = NOTE_NAMES[n % 12]
    letter = name[0]
    accidental = '#' if (len(name) >= 2 and name[1] == '#') else '-'
    octave = n // 12 - 1
    return letter, accidental, octave

def _resolve_track_settings(cfg: FurnaceConfig, td=None):
    """Return (define_instrument, instrument_hex, velocity_enabled, velocity_max_hex)
    using per-track overrides if available, otherwise defaults from cfg."""
    define_inst = cfg.define_instrument
    inst_hex = cfg.instrument_hex
    vel_enabled = cfg.velocity_enabled
    vel_max_hex = cfg.velocity_max_hex
    if td is not None:
        if td.override_instrument:
            define_inst = True
            inst_hex = td.override_instrument_hex
        if td.override_velocity:
            vel_enabled = True
            vel_max_hex = td.override_velocity_max_hex
    return define_inst, inst_hex, vel_enabled, vel_max_hex

def _vol_hex(vel: int, vel_enabled: bool, vel_max_hex: str) -> str:
    if not vel_enabled:
        return ".."
    vmax = int(vel_max_hex or "FF", 16) & 0xFF
    v = max(0, min(127, int(vel)))
    out = round(v / 127.0 * vmax)
    return f"{out:02X}"

def _note_on_cell(note: int, vel: int, cfg: FurnaceConfig, td=None) -> str:
    L, acc, octv = _midi_to_name_oct(note, cfg.transpose_octaves)
    define_inst, inst_hex, vel_enabled, vel_max_hex = _resolve_track_settings(cfg, td)
    if define_inst:
        inst = (inst_hex or "00").upper().strip()
        if len(inst) != 2:
            try:
                inst = f"{int(inst or '0', 16) & 0xFF:02X}"
            except Exception:
                inst = "00"
    else:
        inst = ".."
    vol = _vol_hex(vel, vel_enabled, vel_max_hex)
    return f"{L}{acc}{octv}{inst}{vol}...."

def _off_cell(cfg: FurnaceConfig) -> str:
    tag = cfg.note_off_mode if cfg.note_off_mode in ("OFF", "REL") else "OFF"
    return f"{tag}{'.'*8}"

def _blank_cell() -> str:
    return "..........."

def _quantize_beats_to_line(beat: float, lpq: int) -> int:
    return int(round(beat * lpq))


def get_visible_tracks(state):
    """Track indices to display/export based on focused/starred state."""
    if not state.midi.tracks:
        return []
    focused = state.focused_track
    num = len(state.midi.tracks)
    if focused is not None and 0 <= focused < num:
        return [focused]
    any_starred = any(td.starred for td in state.midi.tracks)
    if any_starred:
        return [i for i, td in enumerate(state.midi.tracks) if td.starred]
    return list(range(num))


def _max_concurrency(events):
    """Given list of (start_line, end_line, ...) events, return peak active overlap."""
    pts = []
    for e in events:
        pts.append((e[0], +1))
        pts.append((e[1], -1))
    pts.sort()
    cur = peak = 0
    for _, d in pts:
        cur += d
        peak = max(peak, cur)
    return peak


def build_track_grids(state, cfg: FurnaceConfig):
    """Build per-track spillover grids for visible tracks.

    Returns:
        groups: list of (track_idx, track_name, grid, num_channels)
            grid[row][ch] = None | ("NOTE", pitch, vel) | ("OFF",)
        total_lines: int
    """
    cfg.sanitize()
    track_indices = get_visible_tracks(state)
    if not track_indices or not state.midi.tracks:
        return [], 0

    tpq = state.midi.ticks_per_beat or 480
    lpq = max(1, cfg.lines_per_quarter)
    total_lines = max(1, int(math.ceil(state.midi.total_beats * lpq)))

    is_spillover = cfg.polyphony_mode == "spillover"

    groups = []
    for ti in track_indices:
        td = state.midi.tracks[ti]
        name = td.name if td.name else f"Track {ti + 1}"

        events = []
        for n in td.notes:
            sb = n.start_tick / tpq
            eb = n.end_tick / tpq
            sl = _quantize_beats_to_line(sb, lpq)
            el = _quantize_beats_to_line(eb, lpq)
            if el <= sl:
                el = sl + 1
            events.append((sl, el, n.pitch, n.velocity))

        events.sort(key=lambda e: (e[0], e[2]))

        suppress_off = cfg.suppress_note_off

        if not is_spillover:
            chans = 1
        elif td.override_spillover:
            chans = max(1, td.override_spillover_count)
        elif cfg.auto_spillover:
            if suppress_off:
                concurrency_events = [(sl, sl + 1, p, v) for sl, el, p, v in events]
            else:
                concurrency_events = events
            chans = max(1, _max_concurrency(concurrency_events))
        else:
            chans = max(1, cfg.spillover_count)

        grid: List[List] = [[None] * chans for _ in range(total_lines)]
        chan_ends = [-10**9] * chans
        off_events: Dict[int, List[int]] = {}

        for sl, el, pitch, vel in events:
            if sl < 0 or sl >= total_lines:
                continue

            free = None
            for j in range(chans):
                if chan_ends[j] <= sl:
                    free = j
                    break

            if free is None:
                j = min(range(chans), key=lambda k: chan_ends[k])
                chan_ends[j] = sl
                free = j

            grid[sl][free] = ("NOTE", pitch, vel)
            if suppress_off:
                chan_ends[free] = sl + 1
            else:
                off_line = max(0, min(el, total_lines - 1))
                off_events.setdefault(off_line, []).append(free)
                chan_ends[free] = el

        for line, chs in off_events.items():
            for ch in chs:
                if 0 <= line < total_lines and grid[line][ch] is None:
                    grid[line][ch] = ("OFF",)

        groups.append((ti, name, grid, chans))

    return groups, total_lines


def build_furnace_clipboard_text(state, cfg: FurnaceConfig) -> Tuple[bool, str]:
    """Return (ok, text_or_error). On success, ok=True and text is the clipboard payload."""
    groups, total_lines = build_track_grids(state, cfg)
    header = "org.tildearrow.furnace - Pattern Data (232)\n0\n"

    if not groups:
        return True, header

    # Find content range (trim empty leading/trailing rows)
    min_row = total_lines
    max_row = -1
    for _, _, grid, num_ch in groups:
        for row in range(total_lines):
            for ch in range(num_ch):
                if grid[row][ch] is not None:
                    min_row = min(min_row, row)
                    max_row = max(max_row, row)
                    break

    if max_row < 0:
        return True, header

    if cfg.export_range_enabled and cfg.export_range_end_beat > cfg.export_range_start_beat:
        lpq = max(1, cfg.lines_per_quarter)
        range_start_line = max(0, int(round(cfg.export_range_start_beat * lpq)))
        range_end_line = max(0, int(round(cfg.export_range_end_beat * lpq)) - 1)
        min_row = max(min_row, range_start_line)
        max_row = min(max_row, range_end_line)

    if max_row < min_row:
        return True, header

    out_lines = []
    for row in range(min_row, max_row + 1):
        cells = []
        for ti, _, grid, num_ch in groups:
            td = state.midi.tracks[ti]
            for ch in range(num_ch):
                cell = grid[row][ch]
                if cell is None:
                    cells.append(_blank_cell())
                elif cell[0] == "NOTE":
                    cells.append(_note_on_cell(cell[1], cell[2], cfg, td))
                elif cell[0] == "OFF":
                    cells.append(_off_cell(cfg))
        out_lines.append("".join(c + "|" for c in cells))

    return True, header + "\n".join(out_lines)


def copy_selection_to_clipboard(state, cfg: FurnaceConfig) -> Tuple[bool, str]:
    """(ok, message). On success, message='Copied'. On error, message explains why."""
    ok, text_or_error = build_furnace_clipboard_text(state, cfg)
    if not ok:
        return False, text_or_error

    text = text_or_error
    try:
        import subprocess
        proc = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            timeout=5,
        )
        if proc.returncode == 0:
            return True, "Copied"
    except Exception:
        pass
    try:
        import pyperclip
        pyperclip.copy(text)
        return True, "Copied"
    except Exception:
        pass
    try:
        import tkinter as tk
        r = tk.Tk(); r.withdraw()
        r.clipboard_clear(); r.clipboard_append(text); r.update(); r.destroy()
        return True, "Copied"
    except Exception:
        pass
    return False, "Failed to access any clipboard backend"


def export_selection_to_file(state, cfg: FurnaceConfig, path: str) -> Tuple[bool, str]:
    """(ok, message). Writes the same payload copy_selection_to_clipboard would copy, to a file."""
    ok, text_or_error = build_furnace_clipboard_text(state, cfg)
    if not ok:
        return False, text_or_error

    text = text_or_error
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return True, f"Exported to {path}"
    except Exception as e:
        return False, f"Failed to write file: {e!r}"

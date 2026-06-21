import math
import imgui
from ui.icons import font_mono
from tracker.export import NOTE_NAMES

_COL_DIVIDER = None
_COL_ROW_NUM = None
_COL_NOTE = None
_COL_NOTE_OFF = None
_COL_INST = None
_COL_VOL = None
_COL_EMPTY = None
_COL_ROW_HIGHLIGHT = None
_COL_ROW_ALT = None
_COL_HEADER_BG = None
_COL_HEADER_TEXT = None
_COL_PLAYHEAD = None


def _init_colors():
    global _COL_DIVIDER, _COL_ROW_NUM, _COL_NOTE, _COL_NOTE_OFF
    global _COL_INST, _COL_VOL, _COL_EMPTY, _COL_ROW_HIGHLIGHT, _COL_ROW_ALT
    global _COL_HEADER_BG, _COL_HEADER_TEXT, _COL_PLAYHEAD
    _COL_DIVIDER = imgui.get_color_u32_rgba(1, 1, 1, 0.15)
    _COL_ROW_NUM = imgui.get_color_u32_rgba(1, 1, 1, 0.5)
    _COL_NOTE = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 1.0)
    _COL_NOTE_OFF = imgui.get_color_u32_rgba(1.0, 0.3, 0.3, 1.0)
    _COL_INST = imgui.get_color_u32_rgba(0.4, 0.4, 1.0, 1.0)
    _COL_VOL = imgui.get_color_u32_rgba(0.0, 0.8, 0.0, 1.0)
    _COL_EMPTY = imgui.get_color_u32_rgba(1, 1, 1, 0.15)
    _COL_ROW_HIGHLIGHT = imgui.get_color_u32_rgba(1, 1, 1, 0.06)
    _COL_ROW_ALT = imgui.get_color_u32_rgba(1, 1, 1, 0.025)
    _COL_HEADER_BG = imgui.get_color_u32_rgba(0.04, 0.04, 0.04, 1.0)
    _COL_HEADER_TEXT = imgui.get_color_u32_rgba(1, 1, 1, 0.9)
    _COL_PLAYHEAD = imgui.get_color_u32_rgba(1.0, 0.4, 0.2, 0.35)


def _midi_note_str(pitch, transpose_octaves=0):
    n = max(0, min(127, pitch + 12 * transpose_octaves))
    name = NOTE_NAMES[n % 12]
    letter = name[0]
    acc = "#" if len(name) > 1 and name[1] == "#" else "-"
    octave = n // 12 - 1
    return f"{letter}{acc}{octave}"


def _build_tracker_grid(state):
    cfg = state.tracker_cfg
    tpq = state.midi.ticks_per_beat or 480
    lpq = max(1, cfg.lines_per_quarter)

    if not state.midi.tracks:
        return [], 0, 0, []

    total_lines = max(1, int(math.ceil(state.midi.total_beats * lpq)))
    num_tracks = len(state.midi.tracks)

    grid = [[None] * num_tracks for _ in range(total_lines)]

    for ti, td in enumerate(state.midi.tracks):
        events = []
        for n in td.notes:
            sb = n.start_tick / tpq
            eb = n.end_tick / tpq
            sl = int(round(sb * lpq))
            el = int(round(eb * lpq))
            if el <= sl:
                el = sl + 1
            events.append((sl, el, n.pitch, n.velocity))

        events.sort(key=lambda e: (e[0], e[2]))

        off_lines = {}
        for sl, el, pitch, vel in events:
            if 0 <= sl < total_lines:
                grid[sl][ti] = ("NOTE", pitch, vel)
            off_line = min(el, total_lines - 1)
            if off_line > sl:
                off_lines[off_line] = True

        for line in off_lines:
            if 0 <= line < total_lines and grid[line][ti] is None:
                grid[line][ti] = ("OFF",)

    track_names = []
    for i, td in enumerate(state.midi.tracks):
        name = td.name if td.name else f"Channel {i + 1}"
        if len(name) > 12:
            name = name[:11] + "."
        track_names.append(name)

    return grid, total_lines, num_tracks, track_names


def draw_tracker_view(state):
    _init_colors()

    if font_mono is not None:
        imgui.push_font(font_mono)

    cfg = state.tracker_cfg
    lpq = max(1, cfg.lines_per_quarter)

    avail_w, avail_h = imgui.get_content_region_available()
    canvas_pos = imgui.get_cursor_screen_pos()
    x0, y0 = canvas_pos

    char_w = imgui.calc_text_size("W")[0]
    row_h = imgui.get_text_line_height_with_spacing() + 1

    row_num_chars = 4
    row_num_w = char_w * row_num_chars + 8

    cell_chars = 11
    cell_w = char_w * cell_chars + 2
    divider_w = 1

    grid, total_lines, num_tracks, track_names = _build_tracker_grid(state)

    if num_tracks == 0:
        imgui.text("No MIDI data loaded.")
        if font_mono is not None:
            imgui.pop_font()
        return

    header_h = row_h + 4
    content_w = row_num_w + num_tracks * (cell_w + divider_w)

    dl = imgui.get_window_draw_list()

    # Header
    dl.add_rect_filled(x0, y0, x0 + max(avail_w, content_w), y0 + header_h, _COL_HEADER_BG)
    dl.add_text(x0 + 4, y0 + 2, _COL_HEADER_TEXT, "++")

    for ci in range(num_tracks):
        cx = x0 + row_num_w + ci * (cell_w + divider_w)
        ci_muted = state.midi.tracks[ci].muted if ci < len(state.midi.tracks) else False
        text_col = imgui.get_color_u32_rgba(1, 1, 1, 0.3 if ci_muted else 0.9)
        dl.add_text(cx + 2, y0 + 2, text_col, track_names[ci])
        dl.add_line(cx, y0, cx, y0 + header_h, _COL_DIVIDER)

    dl.add_line(x0, y0 + header_h, x0 + max(avail_w, content_w), y0 + header_h, _COL_DIVIDER)

    # Body area (no scrolling)
    body_y = y0 + header_h
    body_h = max(100.0, avail_h - header_h)
    visible_rows = max(1, int(body_h / row_h))

    # Determine center line
    playhead_line = -1
    if state.playing or state.playhead_beats > 0:
        playhead_line = int(state.playhead_beats * lpq)

    if state.playing and state.tracking_enabled:
        state.tracker_view_line = playhead_line

    # Handle mouse wheel scrolling when hovered
    imgui.set_cursor_screen_position((x0, body_y))
    imgui.invisible_button("##tracker_body", max(avail_w, content_w), body_h)
    if imgui.is_item_hovered():
        io = imgui.get_io()
        scroll_delta = int(io.mouse_wheel)
        if scroll_delta != 0:
            state.tracker_view_line -= scroll_delta * 4

    state.tracker_view_line = max(0, min(total_lines - 1, state.tracker_view_line))

    # Compute which rows to draw: center_line is at the middle of the view
    center_slot = visible_rows // 2
    first_row = state.tracker_view_line - center_slot

    _muted_flags = [state.midi.tracks[ci].muted if ci < len(state.midi.tracks) else False for ci in range(num_tracks)]
    _COL_NOTE_DIM = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.25)
    _COL_NOTE_OFF_DIM = imgui.get_color_u32_rgba(1.0, 0.3, 0.3, 0.25)
    _COL_INST_DIM = imgui.get_color_u32_rgba(0.4, 0.4, 1.0, 0.25)
    _COL_VOL_DIM = imgui.get_color_u32_rgba(0.0, 0.8, 0.0, 0.25)
    _COL_EMPTY_DIM = imgui.get_color_u32_rgba(1, 1, 1, 0.05)

    ts_num = state.midi.time_sig_num if hasattr(state.midi, 'time_sig_num') else 4
    highlight_interval = lpq * ts_num

    for slot in range(visible_rows):
        row = first_row + slot
        ry = body_y + slot * row_h

        if ry + row_h < body_y or ry > body_y + body_h:
            continue

        if row < 0 or row >= total_lines:
            continue

        # Row background
        if row == playhead_line:
            dl.add_rect_filled(x0, ry, x0 + max(avail_w, content_w), ry + row_h, _COL_PLAYHEAD)
        elif row % highlight_interval == 0:
            dl.add_rect_filled(x0, ry, x0 + max(avail_w, content_w), ry + row_h, _COL_ROW_HIGHLIGHT)
        elif row % lpq == 0:
            dl.add_rect_filled(x0, ry, x0 + max(avail_w, content_w), ry + row_h, _COL_ROW_ALT)

        # Row number
        row_str = f"{row:02X}"
        dl.add_text(x0 + 4, ry, _COL_ROW_NUM, row_str)

        # Cells
        for ci in range(num_tracks):
            cell_x = x0 + row_num_w + ci * (cell_w + divider_w)
            dl.add_line(cell_x, ry, cell_x, ry + row_h, _COL_DIVIDER)

            ci_muted = _muted_flags[ci]
            col_empty = _COL_EMPTY_DIM if ci_muted else _COL_EMPTY
            col_note = _COL_NOTE_DIM if ci_muted else _COL_NOTE
            col_off = _COL_NOTE_OFF_DIM if ci_muted else _COL_NOTE_OFF
            col_inst = _COL_INST_DIM if ci_muted else _COL_INST
            col_vol = _COL_VOL_DIM if ci_muted else _COL_VOL

            cell = grid[row][ci]
            tx = cell_x + 1

            if cell is None:
                dl.add_text(tx, ry, col_empty, "...........")
            elif cell[0] == "NOTE":
                _, pitch, vel = cell
                note_str = _midi_note_str(pitch, cfg.transpose_octaves)
                dl.add_text(tx, ry, col_note, note_str)

                inst_x = tx + char_w * 3
                if cfg.define_instrument:
                    dl.add_text(inst_x, ry, col_inst, cfg.instrument_hex.upper())
                else:
                    dl.add_text(inst_x, ry, col_empty, "..")

                vol_x = inst_x + char_w * 2
                if cfg.velocity_enabled:
                    vmax = int(cfg.velocity_max_hex or "FF", 16) & 0xFF
                    v = round(max(0, min(127, vel)) / 127.0 * vmax)
                    dl.add_text(vol_x, ry, col_vol, f"{v:02X}")
                else:
                    dl.add_text(vol_x, ry, col_empty, "..")

                eff_x = vol_x + char_w * 2
                dl.add_text(eff_x, ry, col_empty, "....")

            elif cell[0] == "OFF":
                tag = cfg.note_off_mode if cfg.note_off_mode in ("OFF", "REL") else "OFF"
                dl.add_text(tx, ry, col_off, tag)
                dl.add_text(tx + char_w * 3, ry, col_empty, "........")

    # Right edge divider
    last_div_x = x0 + row_num_w + num_tracks * (cell_w + divider_w)
    dl.add_line(last_div_x, body_y, last_div_x, body_y + body_h, _COL_DIVIDER)

    if font_mono is not None:
        imgui.pop_font()

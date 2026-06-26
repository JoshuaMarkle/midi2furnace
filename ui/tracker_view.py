import math
import imgui
from ui.icons import font_mono
from tracker.export import NOTE_NAMES, build_track_grids, _resolve_track_settings

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
    _COL_PLAYHEAD = imgui.get_color_u32_rgba(1, 1, 1, 0.10)


def _midi_note_str(pitch, transpose_octaves=0):
    n = max(0, min(127, pitch + 12 * transpose_octaves))
    name = NOTE_NAMES[n % 12]
    letter = name[0]
    acc = "#" if len(name) > 1 and name[1] == "#" else "-"
    octave = n // 12 - 1
    return f"{letter}{acc}{max(0, min(9, octave))}"


def draw_tracker_view(state):
    _init_colors()

    if font_mono is not None:
        imgui.push_font(font_mono)

    cfg = state.tracker_cfg
    lpq = max(1, cfg.lines_per_quarter)

    avail_w, avail_h = imgui.get_content_region_available()
    canvas_pos = imgui.get_cursor_screen_pos()
    x0, y0 = canvas_pos

    char_w = imgui.calc_text_size("0")[0]
    dot_w = imgui.calc_text_size("·")[0]
    dot_pad = (char_w - dot_w) * 0.5
    row_h = imgui.get_text_line_height_with_spacing() + 1

    groups, total_lines = build_track_grids(state, cfg)

    row_num_digits = max(4, len(str(max(1, total_lines - 1))))
    row_num_w = round(char_w * row_num_digits) + 8
    cell_w = round(char_w * 9) + 2
    divider_w = 1

    if not groups:
        msg = "No MIDI loaded."
        msg_sz = imgui.calc_text_size(msg)
        cx = imgui.get_cursor_pos_x() + (avail_w - msg_sz.x) * 0.5
        cy = imgui.get_cursor_pos_y() + (avail_h - msg_sz.y) * 0.5
        imgui.set_cursor_pos((cx, cy))
        imgui.text_colored(msg, 1, 1, 1, 0.4)
        if font_mono is not None:
            imgui.pop_font()
        return

    total_channels = sum(num_ch for _, _, _, num_ch in groups)
    content_w = row_num_w + total_channels * (cell_w + divider_w)
    full_w = max(avail_w, content_w)

    dl = imgui.get_window_draw_list()

    # --- Track name header row ---
    track_hdr_h = row_h + 2
    dl.add_rect_filled(x0, y0, x0 + full_w, y0 + track_hdr_h, _COL_HEADER_BG)

    _COL_TRACK_DIV = imgui.get_color_u32_rgba(1, 1, 1, 0.25)
    ch_offset = 0
    for ti, name, grid, num_ch in groups:
        gx = x0 + row_num_w + ch_offset * (cell_w + divider_w)
        gw = num_ch * (cell_w + divider_w)

        label = f"Track {ti + 1}"
        label_sz = imgui.calc_text_size(label)
        lx = gx + (gw - label_sz.x) * 0.5
        dl.add_text(max(gx + 2, lx), y0 + 1, _COL_HEADER_TEXT, label)

        dl.add_line(gx, y0, gx, y0 + track_hdr_h, _COL_TRACK_DIV)
        ch_offset += num_ch

    last_x = x0 + row_num_w + total_channels * (cell_w + divider_w)
    dl.add_line(last_x, y0, last_x, y0 + track_hdr_h, _COL_TRACK_DIV)
    dl.add_line(x0, y0 + track_hdr_h, x0 + full_w, y0 + track_hdr_h, _COL_DIVIDER)

    # --- Channel number header row ---
    chan_y = y0 + track_hdr_h
    chan_hdr_h = row_h + 2
    dl.add_rect_filled(x0, chan_y, x0 + full_w, chan_y + chan_hdr_h, _COL_HEADER_BG)
    dl.add_text(x0 + 4, chan_y + 1, _COL_HEADER_TEXT, "++")

    ch_offset = 0
    _COL_CHAN_TEXT = imgui.get_color_u32_rgba(1, 1, 1, 0.6)
    for ti, name, grid, num_ch in groups:
        for ch in range(num_ch):
            cx = x0 + row_num_w + (ch_offset + ch) * (cell_w + divider_w)
            dl.add_text(cx + 2, chan_y + 1, _COL_CHAN_TEXT, f"Ch {ch + 1}")
            dl.add_line(cx, chan_y, cx, chan_y + chan_hdr_h, _COL_DIVIDER)
        ch_offset += num_ch

    dl.add_line(last_x, chan_y, last_x, chan_y + chan_hdr_h, _COL_DIVIDER)
    dl.add_line(x0, chan_y + chan_hdr_h, x0 + full_w, chan_y + chan_hdr_h, _COL_DIVIDER)

    # --- Body ---
    header_h = track_hdr_h + chan_hdr_h
    body_y = y0 + header_h
    body_h = max(100.0, avail_h - header_h)
    visible_rows = max(1, int(body_h / row_h))

    playhead_line = -1
    if state.playing or state.playhead_beats > 0:
        playhead_line = int(state.playhead_beats * lpq)

    if state.playing and state.tracking_enabled:
        state.tracker_view_line = playhead_line

    imgui.set_cursor_screen_position((x0, body_y))
    imgui.invisible_button("##tracker_body", full_w, body_h)
    if imgui.is_item_hovered():
        io = imgui.get_io()
        scroll_delta = int(io.mouse_wheel)
        if scroll_delta != 0:
            state.tracker_view_line -= scroll_delta * 4

    state.tracker_view_line = max(0, min(total_lines - 1, state.tracker_view_line))

    center_slot = visible_rows // 2
    first_row = state.tracker_view_line - center_slot

    # Build flat channel list for row rendering
    flat_channels = []
    for ti, name, grid, num_ch in groups:
        td = state.midi.tracks[ti] if ti < len(state.midi.tracks) else None
        muted = td.muted if td else False
        for ch in range(num_ch):
            flat_channels.append((grid, ch, muted, td))

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

        if row == playhead_line:
            dl.add_rect_filled(x0, ry, x0 + full_w, ry + row_h, _COL_PLAYHEAD)
        elif row % highlight_interval == 0:
            dl.add_rect_filled(x0, ry, x0 + full_w, ry + row_h, _COL_ROW_HIGHLIGHT)
        elif row % lpq == 0:
            dl.add_rect_filled(x0, ry, x0 + full_w, ry + row_h, _COL_ROW_ALT)

        dl.add_text(x0 + 4, ry, _COL_ROW_NUM, f"{row:0{row_num_digits}d}")

        for ci, (grid, ch, muted, td) in enumerate(flat_channels):
            cell_x = x0 + row_num_w + ci * (cell_w + divider_w)
            dl.add_line(cell_x, ry, cell_x, ry + row_h, _COL_DIVIDER)

            col_empty = _COL_EMPTY_DIM if muted else _COL_EMPTY
            col_note = _COL_NOTE_DIM if muted else _COL_NOTE
            col_off = _COL_NOTE_OFF_DIM if muted else _COL_NOTE_OFF
            col_inst = _COL_INST_DIM if muted else _COL_INST
            col_vol = _COL_VOL_DIM if muted else _COL_VOL

            cell = grid[row][ch]
            tx = cell_x + 1

            def _dots(x, y, n, col):
                for k in range(n):
                    dl.add_text(round(x + k * char_w + dot_pad), y, col, "·")

            if cell is None:
                _dots(tx, ry, 9, col_empty)
            elif cell[0] == "NOTE":
                _, pitch, vel = cell
                note_str = _midi_note_str(pitch, cfg.transpose_octaves)
                define_inst, inst_hex, vel_enabled, vel_max_hex = _resolve_track_settings(cfg, td)

                x1 = tx
                x2 = round(tx + char_w * 3)
                x3 = round(tx + char_w * 5)
                x4 = round(tx + char_w * 7)

                dl.add_text(x1, ry, col_note, note_str)
                if define_inst:
                    dl.add_text(x2, ry, col_inst, inst_hex.upper())
                else:
                    _dots(x2, ry, 2, col_empty)
                if vel_enabled:
                    vmax = int(vel_max_hex or "FF", 16) & 0xFF
                    v = round(max(0, min(127, vel)) / 127.0 * vmax)
                    dl.add_text(x3, ry, col_vol, f"{v:02X}")
                else:
                    _dots(x3, ry, 2, col_empty)
                _dots(x4, ry, 2, col_empty)

            elif cell[0] == "OFF":
                tag = cfg.note_off_mode if cfg.note_off_mode in ("OFF", "REL") else "OFF"
                dl.add_text(tx, ry, col_off, tag)
                _dots(round(tx + char_w * 3), ry, 6, col_empty)

    dl.add_line(last_x, body_y, last_x, body_y + body_h, _COL_DIVIDER)

    if font_mono is not None:
        imgui.pop_font()

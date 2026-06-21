import os
import imgui

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
FONT_SANS = os.path.join(FONTS_DIR, "IBMPlexSans.ttf")
FONT_MONO = os.path.join(FONTS_DIR, "IBMPlexMono.ttf")
FONT_FA_SOLID = os.path.join(FONTS_DIR, "fa-solid-900.otf")

ICON_RANGE_MIN = 0xF000
ICON_RANGE_MAX = 0xF900

# Playback
ICON_PLAY = ""
ICON_PAUSE = ""
ICON_STOP = ""
ICON_STEP_BACKWARD = ""
ICON_STEP_FORWARD = ""
ICON_VOLUME_UP = ""
ICON_VOLUME_MUTE = ""
ICON_CIRCLE_PLAY = ""

# File / Edit
ICON_FOLDER_OPEN = ""
ICON_COPY = ""
ICON_FILE_EXPORT = ""
ICON_TIMES = ""

# View / Window
ICON_SEARCH_PLUS = ""
ICON_SEARCH_MINUS = ""
ICON_EXPAND = ""
ICON_COMPRESS = ""
ICON_UNDO = ""
ICON_MUSIC = ""
ICON_SLIDERS = ""
ICON_QUESTION_CIRCLE = ""
ICON_COG = ""
ICON_EYE = ""

# Misc
ICON_CHECK = ""
ICON_PLUS = ""
ICON_MINUS = ""
ICON_BACK = ""
ICON_STAR = ""
ICON_INSTRUMENT = ""
ICON_INFO_CIRCLE = ""
ICON_CROSSHAIRS = ""


font_mono = None
font_icon_sm = None
_keep_alive = []

def load_fonts(io, scale=1.0):
    global font_mono, font_icon_sm
    _keep_alive.clear()

    io.fonts.clear()
    io.fonts.add_font_from_file_ttf(FONT_SANS, 16 * scale)

    glyph_ranges = imgui.core.GlyphRanges([ICON_RANGE_MIN, ICON_RANGE_MAX, 0])
    font_config = imgui.core.FontConfig(merge_mode=True)
    _keep_alive.extend([glyph_ranges, font_config])

    io.fonts.add_font_from_file_ttf(
        FONT_FA_SOLID,
        16 * scale,
        font_config=font_config,
        glyph_ranges=glyph_ranges,
    )

    font_mono = io.fonts.add_font_from_file_ttf(FONT_MONO, 14 * scale)

    glyph_ranges_sm = imgui.core.GlyphRanges([ICON_RANGE_MIN, ICON_RANGE_MAX, 0])
    _keep_alive.append(glyph_ranges_sm)
    font_icon_sm = io.fonts.add_font_from_file_ttf(
        FONT_FA_SOLID, 11 * scale, glyph_ranges=glyph_ranges_sm,
    )

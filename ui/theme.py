"""Theme system with hardcoded Furnace default colors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

import imgui

Color = Tuple[float, float, float, float]


def _hex(h: str) -> Color:
    """Convert '#RRGGBB' or '#RRGGBBAA' hex string to (r, g, b, a) floats."""
    h = h.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
    return (r, g, b, a)


_IMGUI_COLOR_PAIRS = [
    ("COLOR_TEXT",                       "#FFFFFF"),
    ("COLOR_TEXT_DISABLED",              "#808080"),
    ("COLOR_WINDOW_BACKGROUND",          "#000000DC"),
    ("COLOR_CHILD_BACKGROUND",           "#000000DC"),
    ("COLOR_POPUP_BACKGROUND",           "#141414F0"),
    ("COLOR_BORDER",                     "#6E6E8080"),
    ("COLOR_BORDER_SHADOW",              "#00000000"),
    ("COLOR_FRAME_BACKGROUND",           "#15283E"),
    ("COLOR_FRAME_BACKGROUND_HOVERED",   "#2A507D"),
    ("COLOR_FRAME_BACKGROUND_ACTIVE",    "#4296FA"),
    ("COLOR_TITLE_BACKGROUND",           "#0A0A0A"),
    ("COLOR_TITLE_BACKGROUND_ACTIVE",    "#163757"),
    ("COLOR_TITLE_BACKGROUND_COLLAPSED", "#00000082"),
    ("COLOR_MENUBAR_BACKGROUND",         "#242424"),
    ("COLOR_SCROLLBAR_BACKGROUND",       "#05050554"),
    ("COLOR_SCROLLBAR_GRAB",             "#4F4F4F"),
    ("COLOR_SCROLLBAR_GRAB_HOVERED",     "#696969"),
    ("COLOR_SCROLLBAR_GRAB_ACTIVE",      "#828282"),
    ("COLOR_CHECK_MARK",                 "#0F87FA"),
    ("COLOR_SLIDER_GRAB",                "#0F87FA"),
    ("COLOR_SLIDER_GRAB_ACTIVE",         "#0F87FA"),
    ("COLOR_BUTTON",                     "#163757"),
    ("COLOR_BUTTON_HOVERED",             "#13497D"),
    ("COLOR_BUTTON_ACTIVE",              "#0F87FA"),
    ("COLOR_HEADER",                     "#15283E"),
    ("COLOR_HEADER_HOVERED",             "#2A507D"),
    ("COLOR_HEADER_ACTIVE",              "#4296FA"),
    ("COLOR_SEPARATOR",                  "#6E6E8080"),
    ("COLOR_SEPARATOR_HOVERED",          "#1A66BFC7"),
    ("COLOR_SEPARATOR_ACTIVE",           "#1A66BF"),
    ("COLOR_RESIZE_GRIP",                "#15283E"),
    ("COLOR_RESIZE_GRIP_HOVERED",        "#2A507D"),
    ("COLOR_RESIZE_GRIP_ACTIVE",         "#4296FA"),
    ("COLOR_TAB",                        "#163757"),
    ("COLOR_TAB_HOVERED",                "#2A507D"),
    ("COLOR_TAB_ACTIVE",                 "#4078BB"),
    ("COLOR_TAB_UNFOCUSED",              "#163757"),
    ("COLOR_TAB_UNFOCUSED_ACTIVE",       "#13497D"),
    ("COLOR_PLOT_LINES",                 "#9C9C9C"),
    ("COLOR_PLOT_LINES_HOVERED",         "#FF6E59"),
    ("COLOR_PLOT_HISTOGRAM",             "#00E6FF"),
    ("COLOR_PLOT_HISTOGRAM_HOVERED",     "#00E6FF"),
    ("COLOR_TEXT_SELECTED_BACKGROUND",   "#2A507D"),
    ("COLOR_MODAL_WINDOW_DIM_BACKGROUND","#2A507D"),
]


def _default_imgui_colors() -> Dict[int, Color]:
    """Furnace default theme colors mapped to ImGui style indices."""
    out = {}
    for attr, hex_val in _IMGUI_COLOR_PAIRS:
        idx = getattr(imgui, attr, None)
        if idx is not None:
            out[idx] = _hex(hex_val)
    return out


@dataclass
class Theme:
    imgui_colors: Dict[int, Color] = field(default_factory=_default_imgui_colors)

    accent_primary:  Color = _hex("#0F87FA")
    accent_secondary: Color = _hex("#4296FA")
    piano_roll_bg:   Color = _hex("#000000")
    track_header_bg: Color = _hex("#0A0A0A")
    ruler_bg:        Color = _hex("#242424")
    selection:       Color = _hex("#262633")
    clear_color:     Color = _hex("#1A1A1A")

    toggle:        Color = _hex("#1A3859")
    toggle_on:     Color = _hex("#339933")
    toggle_off:    Color = _hex("#333333")
    destructive_hint: Color = _hex("#FF3333")


    channel_fm:    Color = _hex("#33CCFF")
    channel_pulse: Color = _hex("#66FF33")
    channel_noise: Color = _hex("#CCCCCC")
    channel_pcm:   Color = _hex("#FFE633")
    channel_wave:  Color = _hex("#FF8033")
    channel_op:    Color = _hex("#3366FF")

    def apply(self):
        try:
            style = imgui.get_style()
            for idx, rgba in self.imgui_colors.items():
                style.colors[idx] = rgba
        except Exception:
            pass


def load_default_theme() -> Theme:
    return Theme()

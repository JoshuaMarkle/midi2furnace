"""Verify all third-party packages required by midi2furnace are importable."""
import importlib
import pytest

REQUIRED = [
    "pygame",
    "OpenGL",
    "OpenGL.GL",
    "imgui",
    "imgui.integrations.pygame",
    "mido",
]


@pytest.mark.parametrize("module", REQUIRED)
def test_package_importable(module):
    importlib.import_module(module)

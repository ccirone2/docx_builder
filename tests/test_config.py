"""Tests for engine.config — validate configuration constants."""
from __future__ import annotations

import re

from engine.config import (
    HEADER_COLOR,
    HEADER_FONT_COLOR,
    IS_PYODIDE,
    OPTIONAL_BG_COLOR,
    REQUIRED_INDICATOR_COLOR,
    SHEET_CONTROL,
)


def test_is_pyodide_false_in_test_env() -> None:
    """IS_PYODIDE should be False when running in a standard test environment."""
    assert IS_PYODIDE is False


def test_color_constants_hex_format() -> None:
    """All color constants must be valid 6-digit hex strings."""
    hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    for name, value in [
        ("HEADER_COLOR", HEADER_COLOR),
        ("HEADER_FONT_COLOR", HEADER_FONT_COLOR),
        ("OPTIONAL_BG_COLOR", OPTIONAL_BG_COLOR),
        ("REQUIRED_INDICATOR_COLOR", REQUIRED_INDICATOR_COLOR),
    ]:
        assert hex_pattern.match(value), f"{name} = {value!r} is not valid hex"


def test_sheet_name_constants_non_empty() -> None:
    """SHEET_CONTROL must be a non-empty string."""
    assert isinstance(SHEET_CONTROL, str)
    assert len(SHEET_CONTROL) > 0

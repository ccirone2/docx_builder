"""mock_book.py — In-memory xlwings Book/Sheet/Cell mock.

Implements the exact xlwings API surface used by excel_writer.py and
runner.py so the full pipeline can run locally without Excel or Pyodide.

API surface verified against:
  - excel_writer.py: sheet iteration, .add(), .range(), cell formatting
  - runner.py: A1 notation indexing, .value reads/writes
"""

from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# A1 notation helper
# ---------------------------------------------------------------------------

_A1_RE = re.compile(r"^([A-Z]+)(\d+)$", re.IGNORECASE)


def _a1_to_rowcol(address: str) -> tuple[int, int]:
    """Convert an A1-style cell address to 1-based (row, col).

    Args:
        address: Cell reference like "B3" or "D20".

    Returns:
        Tuple of (row, col) with 1-based indexing.

    Raises:
        ValueError: If address doesn't match A1 pattern.
    """
    m = _A1_RE.match(address.strip())
    if not m:
        raise ValueError(f"Invalid A1 address: {address!r}")
    col_str, row_str = m.group(1).upper(), m.group(2)
    col = 0
    for ch in col_str:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(row_str), col


# ---------------------------------------------------------------------------
# MockCell + formatting proxies
# ---------------------------------------------------------------------------


class _MockFont:
    """Proxy for cell.font.bold and cell.font.color."""

    def __init__(self, cell: MockCell) -> None:
        self._cell = cell

    @property
    def bold(self) -> bool | None:
        return self._cell._bold

    @bold.setter
    def bold(self, value: bool | None) -> None:
        self._cell._bold = value

    @property
    def color(self) -> str:
        return self._cell._font_color

    @color.setter
    def color(self, value: str) -> None:
        self._cell._font_color = value


class _MockNote:
    """Proxy for cell.note.text."""

    def __init__(self, cell: MockCell) -> None:
        self._cell = cell

    @property
    def text(self) -> str:
        return self._cell._note_text

    @text.setter
    def text(self, value: str) -> None:
        self._cell._note_text = value


class MockCell:
    """In-memory cell with value and formatting storage."""

    def __init__(self, row: int, col: int) -> None:
        self.row: int = row
        self.col: int = col
        self.value: Any = None
        # Formatting fields
        self._bold: bool | None = None
        self._color: str = ""
        self._font_color: str = ""
        self._number_format: str = ""
        self._row_height: int | None = None
        self._note_text: str = ""

    @property
    def font(self) -> _MockFont:
        return _MockFont(self)

    @property
    def note(self) -> _MockNote:
        return _MockNote(self)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value

    @property
    def number_format(self) -> str:
        return self._number_format

    @number_format.setter
    def number_format(self, value: str) -> None:
        self._number_format = value

    @property
    def row_height(self) -> int | None:
        return self._row_height

    @row_height.setter
    def row_height(self, value: int | None) -> None:
        self._row_height = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize cell to a dict (only non-default values)."""
        d: dict[str, Any] = {"row": self.row, "col": self.col}
        if self.value is not None:
            d["value"] = self.value
        if self._bold is not None:
            d["bold"] = self._bold
        if self._color:
            d["color"] = self._color
        if self._font_color:
            d["font_color"] = self._font_color
        if self._number_format:
            d["number_format"] = self._number_format
        if self._row_height is not None:
            d["row_height"] = self._row_height
        if self._note_text:
            d["note_text"] = self._note_text
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MockCell:
        """Deserialize a cell from a dict."""
        cell = cls(d["row"], d["col"])
        cell.value = d.get("value")
        cell._bold = d.get("bold")
        cell._color = d.get("color", "")
        cell._font_color = d.get("font_color", "")
        cell._number_format = d.get("number_format", "")
        cell._row_height = d.get("row_height")
        cell._note_text = d.get("note_text", "")
        return cell


# ---------------------------------------------------------------------------
# MockSheet
# ---------------------------------------------------------------------------


class MockSheet:
    """In-memory sheet with cell storage and xlwings-compatible access."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self._cells: dict[tuple[int, int], MockCell] = {}

    def range(self, address: tuple[int, int] | str) -> MockCell:
        """Return (or create) a cell at the given position.

        Args:
            address: Either a (row, col) tuple or an A1-style string like "B3:F3".
                     For range strings, returns the top-left cell.
        """
        if isinstance(address, str):
            # Handle range strings like "A1:F1" — return top-left cell
            top_left = address.split(":")[0]
            row, col = _a1_to_rowcol(top_left)
        else:
            row, col = address
        if (row, col) not in self._cells:
            self._cells[(row, col)] = MockCell(row, col)
        return self._cells[(row, col)]

    def __getitem__(self, key: str) -> MockCell:
        """A1 notation access: sheet["B3"]."""
        row, col = _a1_to_rowcol(key)
        if (row, col) not in self._cells:
            self._cells[(row, col)] = MockCell(row, col)
        return self._cells[(row, col)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize sheet to a dict."""
        cells = [c.to_dict() for c in self._cells.values() if c.value is not None]
        return {"name": self.name, "cells": cells}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MockSheet:
        """Deserialize a sheet from a dict."""
        sheet = cls(d["name"])
        for cd in d.get("cells", []):
            cell = MockCell.from_dict(cd)
            sheet._cells[(cell.row, cell.col)] = cell
        return sheet


# ---------------------------------------------------------------------------
# MockBook
# ---------------------------------------------------------------------------


class _MockSheetCollection:
    """List-like sheet collection with add/access by name."""

    def __init__(self) -> None:
        self._sheets: list[MockSheet] = []

    def add(self, name: str) -> MockSheet:
        """Add a new sheet. Returns the created sheet."""
        sheet = MockSheet(name)
        self._sheets.append(sheet)
        return sheet

    def __getitem__(self, key: str | int) -> MockSheet:
        if isinstance(key, int):
            return self._sheets[key]
        for s in self._sheets:
            if s.name == key:
                return s
        raise KeyError(f"Sheet not found: {key!r}")

    def __iter__(self):
        return iter(self._sheets)

    def __len__(self) -> int:
        return len(self._sheets)

    def __contains__(self, name: str) -> bool:
        return any(s.name == name for s in self._sheets)


class MockBook:
    """In-memory xlwings Book mock with JSON serialization."""

    def __init__(self) -> None:
        self.sheets = _MockSheetCollection()

    def to_dict(self) -> dict[str, Any]:
        """Serialize entire workbook to a dict."""
        return {"sheets": [s.to_dict() for s in self.sheets]}

    def to_json(self, indent: int = 2) -> str:
        """Serialize entire workbook to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MockBook:
        """Deserialize a workbook from a dict."""
        book = cls()
        for sd in d.get("sheets", []):
            sheet = MockSheet.from_dict(sd)
            book.sheets._sheets.append(sheet)
        return book

    @classmethod
    def from_json(cls, text: str) -> MockBook:
        """Deserialize a workbook from a JSON string."""
        return cls.from_dict(json.loads(text))

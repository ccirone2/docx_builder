"""Tests for dev.mock_book — in-memory xlwings mock."""
from __future__ import annotations

import json

import pytest

from dev.mock_book import MockBook, MockCell, MockSheet, _a1_to_rowcol


# ---------------------------------------------------------------------------
# A1 notation parsing
# ---------------------------------------------------------------------------


class TestA1Parsing:
    def test_a1(self):
        assert _a1_to_rowcol("A1") == (1, 1)

    def test_b3(self):
        assert _a1_to_rowcol("B3") == (3, 2)

    def test_d20(self):
        assert _a1_to_rowcol("D20") == (20, 4)

    def test_f1(self):
        assert _a1_to_rowcol("F1") == (1, 6)

    def test_aa1(self):
        assert _a1_to_rowcol("AA1") == (1, 27)

    def test_case_insensitive(self):
        assert _a1_to_rowcol("b3") == (3, 2)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _a1_to_rowcol("123")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _a1_to_rowcol("")


# ---------------------------------------------------------------------------
# MockCell
# ---------------------------------------------------------------------------


class TestMockCell:
    def test_read_write_value(self):
        cell = MockCell(1, 1)
        assert cell.value is None
        cell.value = "hello"
        assert cell.value == "hello"

    def test_font_bold(self):
        cell = MockCell(1, 1)
        cell.font.bold = True
        assert cell.font.bold is True
        assert cell._bold is True

    def test_font_color(self):
        cell = MockCell(1, 1)
        cell.font.color = "#FFFFFF"
        assert cell.font.color == "#FFFFFF"

    def test_bg_color(self):
        cell = MockCell(1, 1)
        cell.color = "#1F4E79"
        assert cell.color == "#1F4E79"

    def test_number_format(self):
        cell = MockCell(1, 1)
        cell.number_format = "$#,##0.00"
        assert cell.number_format == "$#,##0.00"

    def test_row_height(self):
        cell = MockCell(1, 1)
        cell.row_height = 60
        assert cell.row_height == 60

    def test_note_text(self):
        cell = MockCell(1, 1)
        cell.note.text = "Some note"
        assert cell.note.text == "Some note"

    def test_to_dict_minimal(self):
        cell = MockCell(3, 2)
        d = cell.to_dict()
        assert d == {"row": 3, "col": 2}

    def test_to_dict_with_values(self):
        cell = MockCell(1, 1)
        cell.value = "test"
        cell._bold = True
        d = cell.to_dict()
        assert d["value"] == "test"
        assert d["bold"] is True

    def test_roundtrip(self):
        cell = MockCell(5, 3)
        cell.value = 42
        cell._bold = True
        cell._color = "#123456"
        restored = MockCell.from_dict(cell.to_dict())
        assert restored.row == 5
        assert restored.col == 3
        assert restored.value == 42
        assert restored._bold is True
        assert restored._color == "#123456"


# ---------------------------------------------------------------------------
# MockSheet
# ---------------------------------------------------------------------------


class TestMockSheet:
    def test_name(self):
        sheet = MockSheet("Control")
        assert sheet.name == "Control"

    def test_range_tuple(self):
        sheet = MockSheet("Test")
        cell = sheet.range((3, 2))
        cell.value = "hello"
        assert sheet.range((3, 2)).value == "hello"

    def test_getitem_a1(self):
        sheet = MockSheet("Test")
        sheet["B3"].value = "world"
        assert sheet["B3"].value == "world"

    def test_range_and_getitem_same_cell(self):
        sheet = MockSheet("Test")
        sheet["B3"].value = "via a1"
        assert sheet.range((3, 2)).value == "via a1"

    def test_range_string(self):
        sheet = MockSheet("Test")
        cell = sheet.range("A1:F1")
        cell.value = "merged"
        assert sheet["A1"].value == "merged"

    def test_missing_cell_returns_none_value(self):
        sheet = MockSheet("Test")
        assert sheet.range((99, 99)).value is None

    def test_to_dict(self):
        sheet = MockSheet("Data")
        sheet["A1"].value = "label"
        sheet["B1"].value = "value"
        d = sheet.to_dict()
        assert d["name"] == "Data"
        assert len(d["cells"]) == 2

    def test_roundtrip(self):
        sheet = MockSheet("Data")
        sheet["A1"].value = "hello"
        sheet["B2"].value = 123
        restored = MockSheet.from_dict(sheet.to_dict())
        assert restored.name == "Data"
        assert restored["A1"].value == "hello"
        assert restored["B2"].value == 123


# ---------------------------------------------------------------------------
# MockBook
# ---------------------------------------------------------------------------


class TestMockBook:
    def test_add_sheet(self):
        book = MockBook()
        book.sheets.add("Control")
        assert len(book.sheets) == 1
        assert book.sheets["Control"].name == "Control"

    def test_access_by_name(self):
        book = MockBook()
        book.sheets.add("Sheet1")
        book.sheets.add("Sheet2")
        assert book.sheets["Sheet2"].name == "Sheet2"

    def test_missing_sheet_raises(self):
        book = MockBook()
        with pytest.raises(KeyError):
            book.sheets["Nonexistent"]

    def test_iterate_sheets(self):
        book = MockBook()
        book.sheets.add("A")
        book.sheets.add("B")
        names = [s.name for s in book.sheets]
        assert names == ["A", "B"]

    def test_sheet_names_in_check(self):
        book = MockBook()
        book.sheets.add("Control")
        sheet_names = [s.name for s in book.sheets]
        assert "Control" in sheet_names
        assert "Missing" not in sheet_names

    def test_json_roundtrip(self):
        book = MockBook()
        book.sheets.add("Control")
        book.sheets["Control"]["B3"].value = "rfq_electric_utility"
        book.sheets.add("Data")
        book.sheets["Data"].range((2, 1)).value = "Company"
        book.sheets["Data"].range((2, 2)).value = "Acme Corp"

        json_str = book.to_json()
        parsed = json.loads(json_str)
        assert len(parsed["sheets"]) == 2

        restored = MockBook.from_json(json_str)
        assert len(restored.sheets) == 2
        assert restored.sheets["Control"]["B3"].value == "rfq_electric_utility"
        assert restored.sheets["Data"].range((2, 2)).value == "Acme Corp"

    def test_to_dict_skips_empty_cells(self):
        book = MockBook()
        book.sheets.add("Test")
        book.sheets["Test"]["A1"].value = "keep"
        book.sheets["Test"]["B1"]  # access but don't set value
        d = book.to_dict()
        assert len(d["sheets"][0]["cells"]) == 1

    def test_delete_sheet(self):
        book = MockBook()
        book.sheets.add("Keep")
        book.sheets.add("Remove")
        book.sheets.add("Also Keep")
        assert len(book.sheets) == 3
        book.sheets["Remove"].delete()
        assert len(book.sheets) == 2
        names = [s.name for s in book.sheets]
        assert "Remove" not in names
        assert "Keep" in names
        assert "Also Keep" in names

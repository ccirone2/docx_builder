"""
excel_writer.py — xlwings adapter layer for writing sheet plans to Excel.

Runtime-only code that writes CellInstruction data structures to actual
Excel sheets via the xlwings API. Not unit tested — formatting is
environment-dependent.

Split from excel_builder.py for module size. See also:
  - excel_plan.py — Pure logic planning + dataclasses
  - excel_control.py — Control sheet layout planning
"""

from __future__ import annotations

from typing import Any

from engine.config import IS_PYODIDE
from engine.excel_plan import CellInstruction, SheetPlan


def build_sheets(book: Any, plan: SheetPlan) -> None:
    """Create sheets and write all cell instructions to an xlwings Book.

    Each cell write is individually guarded so that one failure does
    not prevent the remaining cells from being written.

    Args:
        book: An xlwings Book object.
        plan: The SheetPlan to execute.
    """
    for sheet_name in plan.sheets:
        if sheet_name not in [s.name for s in book.sheets]:
            if len(book.sheets) > 0:
                book.sheets.add(sheet_name, after=book.sheets[-1])
            else:
                book.sheets.add(sheet_name)

    for instr in plan.instructions:
        try:
            sheet = book.sheets[instr.sheet]
            apply_cell(sheet, instr)
        except Exception:
            pass


def apply_cell(sheet: Any, instr: CellInstruction) -> None:
    """Write a single cell to an xlwings Sheet with formatting.

    In xlwings Lite the Office.js bridge batches all operations and
    syncs them when Python returns.  If any single queued operation
    is invalid the **entire** batch is rolled back — including value
    writes.  Python ``try/except`` cannot catch these because the
    error is raised asynchronously in JavaScript, not in Python.

    In Pyodide mode we therefore write **values only** and skip all
    formatting to avoid poisoning the batch.  Formatting operations
    are applied only when running in desktop xlwings.

    Args:
        sheet: An xlwings Sheet object.
        instr: The CellInstruction to apply.
    """
    cell = sheet.range((instr.row, instr.col))
    cell.value = instr.value

    # In Pyodide / xlwings Lite, skip ALL formatting to prevent
    # invalid Office.js operations from rolling back value writes.
    if IS_PYODIDE:
        return

    # --- Desktop xlwings formatting (best-effort) ---
    try:
        if instr.bold:
            cell.font.bold = True
    except Exception:
        pass

    try:
        if instr.bg_color:
            cell.color = instr.bg_color
    except Exception:
        pass

    try:
        if instr.font_color:
            cell.font.color = instr.font_color
    except Exception:
        pass

    try:
        if instr.number_format:
            cell.number_format = instr.number_format
    except Exception:
        pass

    try:
        if instr.note:
            cell.note.text = instr.note
    except Exception:
        pass

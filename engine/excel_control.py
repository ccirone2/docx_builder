"""
excel_control.py — Control sheet layout planning.

Computes the cell instructions for the Control sheet (title banner,
document-type selector, button labels, configuration area, data staging).

Split from excel_builder.py for module size. See also:
  - excel_plan.py — Data entry sheet planning + dataclasses
  - excel_writer.py — xlwings adapter layer
"""

from __future__ import annotations

from engine.config import (
    HEADER_COLOR,
    HEADER_FONT_COLOR,
    OPTIONAL_BG_COLOR,
)
from engine.excel_plan import CellInstruction

# --- Default GitHub base URL ---
_DEFAULT_GITHUB_BASE = "https://raw.githubusercontent.com/ccirone2/docx_builder/main"


def plan_control_sheet(github_base: str = "") -> list[CellInstruction]:
    """Compute cell instructions for the Control sheet layout.

    Creates the full Control sheet with title, document-type selector,
    status area, configuration section, and data staging area. This
    is the "easy button" — call once to scaffold the entire UI.

    Args:
        github_base: GitHub raw content URL for the config area.
            Defaults to the project's public repo URL.

    Returns:
        List of CellInstruction for the Control sheet.
    """
    sheet = "Control"
    url = github_base or _DEFAULT_GITHUB_BASE
    instrs: list[CellInstruction] = []

    # --- Title banner (Row 1, A1:F1) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=1,
            col=1,
            value="DOCUMENT GENERATOR",
            bold=True,
            bg_color=HEADER_COLOR,
            font_color=HEADER_FONT_COLOR,
            is_header=True,
        )
    )

    # --- Row 3: Document Type selector + status ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=3,
            col=1,
            value="Document Type:",
            bold=True,
        )
    )
    # B3: dropdown cell (populated later by initialize_sheets)
    instrs.append(CellInstruction(sheet=sheet, row=3, col=2, value=""))

    # --- Button label rows (A column, next to xlwings button widgets) ---
    button_labels = [
        (5, "Initialize Sheets"),
        (7, "Generate Document"),
        (9, "Validate Data"),
        (11, "Export Data (YAML)"),
        (13, "Import Data (YAML)"),
        (15, "Generate LLM Prompt"),
        (17, "Load Custom Schema"),
        (19, "Load Custom Template"),
    ]
    for row, label in button_labels:
        instrs.append(
            CellInstruction(
                sheet=sheet,
                row=row,
                col=1,
                value=label,
                bold=True,
            )
        )

    # --- Configuration section (Row 10+) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=10,
            col=3,
            value="CONFIGURATION",
            bold=True,
            bg_color=OPTIONAL_BG_COLOR,
        )
    )
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=12,
            col=3,
            value="GitHub Repo URL:",
        )
    )
    instrs.append(CellInstruction(sheet=sheet, row=12, col=4, value=url))

    # --- Redact toggle (Row 16) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=16,
            col=3,
            value="Redact on Export:",
        )
    )
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=16,
            col=4,
            value="TRUE",
        )
    )

    # --- Data staging section (Row 18+) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=18,
            col=3,
            value="DATA STAGING AREA",
            bold=True,
            bg_color=OPTIONAL_BG_COLOR,
        )
    )

    return instrs

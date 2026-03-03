"""Tests for engine/excel_plan.py and engine/excel_control.py — pure logic layer."""
from __future__ import annotations

from engine.config import SHEET_DATA_ENTRY
from engine.excel_control import plan_control_sheet
from engine.excel_plan import (
    CellInstruction,
    plan_data_entry,
    plan_sheets,
    plan_table_layout,
)
from engine.schema_loader import Schema


# ---------------------------------------------------------------------------
# plan_sheets — overall structure
# ---------------------------------------------------------------------------


def test_plan_sheets_has_data_entry_sheet(rfq_schema: Schema) -> None:
    """plan_sheets always creates a 'Data Entry' sheet."""
    plan = plan_sheets(rfq_schema)
    assert SHEET_DATA_ENTRY in plan.sheets


def test_plan_sheets_has_table_sheets(rfq_schema: Schema) -> None:
    """Table fields get their own sheets."""
    plan = plan_sheets(rfq_schema)
    assert "Work Items - Line Items" in plan.sheets
    assert "Required Documents" in plan.sheets


def test_plan_sheets_all_instructions_col_one(rfq_schema: Schema) -> None:
    """All instructions are in column 1 (single-column layout)."""
    plan = plan_sheets(rfq_schema)
    assert all(i.col == 1 for i in plan.instructions)


def test_plan_sheets_no_field_locations(rfq_schema: Schema) -> None:
    """SheetPlan no longer has field_locations attribute."""
    plan = plan_sheets(rfq_schema)
    assert not hasattr(plan, "field_locations")


# ---------------------------------------------------------------------------
# plan_data_entry — SCN layout for non-table fields
# ---------------------------------------------------------------------------


def test_data_entry_has_section_headers(rfq_schema: Schema) -> None:
    """Each group produces a [Group Name] section header."""
    instrs, _ = plan_data_entry(rfq_schema)
    sections = [i for i in instrs if i.is_header and str(i.value).startswith("[")]
    # RFQ schema has 9 groups (6 core + 3 optional)
    assert len(sections) >= 6


def test_data_entry_section_headers_styled(rfq_schema: Schema) -> None:
    """Section headers are bold with no background/font color."""
    instrs, _ = plan_data_entry(rfq_schema)
    sections = [i for i in instrs if i.is_header and str(i.value).startswith("[")]
    for s in sections:
        assert s.bold
        assert s.bg_color == ""
        assert s.font_color == ""


def test_data_entry_has_key_declarations(rfq_schema: Schema) -> None:
    """Fields produce key: declaration rows that are bold."""
    instrs, _ = plan_data_entry(rfq_schema)
    keys = [i for i in instrs if str(i.value).endswith(":")]
    assert len(keys) > 0
    assert all(k.bold for k in keys)


def test_data_entry_no_comment_labels(rfq_schema: Schema) -> None:
    """No ;; comment labels before keys (only table headers use ;;)."""
    instrs, _ = plan_data_entry(rfq_schema)
    comments = [i for i in instrs if str(i.value).startswith(";;")]
    assert len(comments) == 0


def test_data_entry_no_required_indicators(rfq_schema: Schema) -> None:
    """No required field indicators (* suffix) in data entry."""
    instrs, _ = plan_data_entry(rfq_schema)
    starred = [i for i in instrs if str(i.value).endswith(" *")]
    assert len(starred) == 0


def test_data_entry_has_value_cells_with_field_key(rfq_schema: Schema) -> None:
    """Value cells carry field_key for identification."""
    instrs, _ = plan_data_entry(rfq_schema)
    keyed = [i for i in instrs if i.field_key]
    assert len(keyed) > 0
    # Value cells are not headers and not bold
    assert all(not i.is_header for i in keyed)


def test_data_entry_issuer_name_present(rfq_schema: Schema) -> None:
    """issuer_name field produces key declaration and value cell."""
    instrs, _ = plan_data_entry(rfq_schema)
    key_rows = [i for i in instrs if i.value == "issuer_name:"]
    assert len(key_rows) == 1
    value_cells = [i for i in instrs if i.field_key == "issuer_name"]
    assert len(value_cells) == 1


def test_data_entry_compound_field_dot_notation(rfq_schema: Schema) -> None:
    """Compound fields use dot notation: parent_key.sub_key:"""
    instrs, _ = plan_data_entry(rfq_schema)
    dot_keys = [i for i in instrs if "." in str(i.value) and str(i.value).endswith(":")]
    assert len(dot_keys) > 0
    # safety_requirements.general should be present
    safety_keys = [i for i in dot_keys if "safety_requirements" in str(i.value)]
    assert len(safety_keys) >= 1


def test_data_entry_no_compound_label_header(rfq_schema: Schema) -> None:
    """Compound fields have no separate label header — just key: rows."""
    instrs, _ = plan_data_entry(rfq_schema)
    compound_labels = [
        i for i in instrs
        if i.is_header and str(i.value).startswith(";;")
    ]
    assert len(compound_labels) == 0


def test_data_entry_all_on_data_entry_sheet(rfq_schema: Schema) -> None:
    """All data entry instructions target the Data Entry sheet."""
    instrs, _ = plan_data_entry(rfq_schema)
    assert all(i.sheet == SHEET_DATA_ENTRY for i in instrs)


# ---------------------------------------------------------------------------
# plan_table_layout — SCN dict-list layout
# ---------------------------------------------------------------------------


def test_table_layout_has_header_comment(rfq_schema: Schema) -> None:
    """Table sheets start with a ;; comment describing columns."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    instrs = plan_table_layout(work_items, "Work Items")
    header = instrs[0]
    assert header.is_header
    assert str(header.value).startswith(";;")
    assert "Item #" in str(header.value)


def test_table_layout_dict_list_entries(rfq_schema: Schema) -> None:
    """Table rows use +field_key notation."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    instrs = plan_table_layout(work_items, "Work Items")
    plus_entries = [i for i in instrs if str(i.value).startswith("+")]
    # work_items has no default_rows, so 1 empty template row
    assert len(plus_entries) == 1
    assert plus_entries[0].value == "+work_items"


def test_table_layout_column_keys(rfq_schema: Schema) -> None:
    """Each table row has key: declarations for all columns."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    instrs = plan_table_layout(work_items, "Work Items")
    key_rows = [i for i in instrs if str(i.value).endswith(":") and not str(i.value).startswith(";;")]
    # 6 columns in work_items template row
    assert len(key_rows) == 6


def test_table_layout_default_rows(rfq_schema: Schema) -> None:
    """required_documents table has default rows with values."""
    req_docs = rfq_schema.get_field("required_documents")
    assert req_docs is not None
    instrs = plan_table_layout(req_docs, "Required Docs")
    plus_entries = [i for i in instrs if str(i.value).startswith("+")]
    # 6 default rows in the schema
    assert len(plus_entries) == 6


def test_table_layout_all_col_one(rfq_schema: Schema) -> None:
    """All table instructions are in column 1."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    instrs = plan_table_layout(work_items, "Work Items")
    assert all(i.col == 1 for i in instrs)


# ---------------------------------------------------------------------------
# plan_control_sheet tests
# ---------------------------------------------------------------------------


def test_plan_control_sheet_returns_instructions() -> None:
    """plan_control_sheet returns a non-empty list of CellInstruction."""
    instrs = plan_control_sheet()
    assert len(instrs) > 0
    assert all(isinstance(i, CellInstruction) for i in instrs)


def test_plan_control_sheet_all_on_control_sheet() -> None:
    """Every instruction targets the 'Control' sheet."""
    instrs = plan_control_sheet()
    assert all(i.sheet == "Control" for i in instrs)


def test_plan_control_sheet_has_title_banner() -> None:
    """First instruction is the DOCUMENT GENERATOR title banner."""
    instrs = plan_control_sheet()
    title = [i for i in instrs if i.value == "DOCUMENT GENERATOR"]
    assert len(title) == 1
    assert title[0].row == 1
    assert title[0].is_header


def test_plan_control_sheet_has_button_labels() -> None:
    """All expected button labels are present."""
    instrs = plan_control_sheet()
    values = {str(i.value) for i in instrs}
    expected_labels = [
        "Initialize Sheets",
        "Generate Document",
        "Validate Data",
        "Export Data",
        "Import Data",
        "Generate LLM Prompt",
        "Load Custom Schema",
        "Load Custom Template",
    ]
    for label in expected_labels:
        assert label in values, f"Missing button label: {label}"


def test_plan_control_sheet_has_document_type_selector() -> None:
    """Row 3 has Document Type label and empty dropdown cell."""
    instrs = plan_control_sheet()
    doc_type = [i for i in instrs if i.value == "Document Type:"]
    assert len(doc_type) == 1
    assert doc_type[0].row == 3
    assert doc_type[0].col == 1


def test_plan_control_sheet_has_config_section() -> None:
    """Configuration section has GitHub URL and Redact toggle."""
    instrs = plan_control_sheet()
    config_header = [i for i in instrs if i.value == "CONFIGURATION"]
    assert len(config_header) == 1

    gh_label = [i for i in instrs if i.value == "GitHub Repo URL:"]
    assert len(gh_label) == 1

    redact_label = [i for i in instrs if i.value == "Redact on Export:"]
    assert len(redact_label) == 1


def test_plan_control_sheet_custom_github_url() -> None:
    """Custom github_base URL appears in the config area."""
    custom = "https://raw.githubusercontent.com/myorg/myrepo/main"
    instrs = plan_control_sheet(github_base=custom)
    url_cells = [i for i in instrs if i.value == custom]
    assert len(url_cells) == 1


def test_plan_control_sheet_has_data_staging() -> None:
    """DATA STAGING AREA section header exists."""
    instrs = plan_control_sheet()
    staging = [i for i in instrs if i.value == "DATA STAGING AREA"]
    assert len(staging) == 1


def test_field_key_on_value_cells(rfq_schema: Schema) -> None:
    """Value cells (not headers) carry field_key for data-entry fields."""
    plan = plan_sheets(rfq_schema)
    keyed = [i for i in plan.instructions if i.field_key]
    assert len(keyed) > 0
    # None of the keyed instructions should be headers
    assert all(not i.is_header for i in keyed)

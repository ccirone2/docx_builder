"""Tests for engine/excel_builder.py — pure logic layer."""
from __future__ import annotations

from engine.excel_builder import (
    CellInstruction,
    plan_control_sheet,
    plan_group_layout,
    plan_sheets,
    plan_table_layout,
    _table_sheet_name,
)
from engine.schema_loader import Schema


def test_plan_sheets_creates_correct_sheet_names(rfq_schema: Schema) -> None:
    """Sheet plan produces expected sheet names for RFQ schema."""
    plan = plan_sheets(rfq_schema)
    assert len(plan.sheets) > 0
    # Should have data sheets for groups and table sheets
    assert any("Data" in s for s in plan.sheets)
    assert any("Table" in s for s in plan.sheets)
    # Specific expected sheets
    assert "Data - Issuing Organization" in plan.sheets
    assert "Data - RFQ Details" in plan.sheets
    assert "Table - Work Items / Line Items" in plan.sheets
    assert "Table - Required Documents" in plan.sheets


def test_plan_group_layout_required_fields(rfq_schema: Schema) -> None:
    """Required fields produce red indicator instructions."""
    group = rfq_schema.core_groups[0]  # Issuing Organization
    non_table = [f for f in group.fields if not f.is_table]
    instrs = plan_group_layout(group.name, non_table, "Test Sheet")

    # Find required indicators (col 6, value "*")
    indicators = [i for i in instrs if i.col == 6 and i.value == "*"]
    assert len(indicators) > 0
    for ind in indicators:
        assert ind.font_color != ""  # Has color


def test_plan_group_layout_choice_dropdown(rfq_schema: Schema) -> None:
    """Choice field (work_category) gets dropdown_choices in its instruction."""
    # Project Information group has work_category
    project_group = rfq_schema.core_groups[2]
    non_table = [f for f in project_group.fields if not f.is_table]
    instrs = plan_group_layout(project_group.name, non_table, "Test Sheet")

    # Find instruction with dropdown_choices
    dropdowns = [i for i in instrs if i.dropdown_choices is not None]
    assert len(dropdowns) > 0
    # work_category should have the choices
    category_dropdown = [
        i for i in dropdowns if "Distribution Line Construction" in (i.dropdown_choices or [])
    ]
    assert len(category_dropdown) == 1


def test_plan_group_layout_compound(rfq_schema: Schema) -> None:
    """Compound field (safety_requirements) creates sub-header + indented sub-fields."""
    # Additional Provisions group has safety_requirements compound
    provisions_group = rfq_schema.optional_groups[2]
    non_table = [f for f in provisions_group.fields if not f.is_table]
    instrs = plan_group_layout(provisions_group.name, non_table, "Test Sheet")

    # Should have a sub-header for "Additional Safety Requirements"
    sub_headers = [i for i in instrs if i.is_header and "Safety" in str(i.value)]
    assert len(sub_headers) >= 1

    # Should have indented sub-field rows (col 2 for label)
    indented = [i for i in instrs if i.col == 2 and not i.is_header and "  " in str(i.value)]
    assert len(indented) >= 3  # general, hot_work, lockout_tagout, etc.


def test_plan_group_layout_conditional(rfq_schema: Schema) -> None:
    """Conditional field (bonding_amount) has a note about the condition."""
    # Terms & Conditions group
    terms_group = rfq_schema.core_groups[5]
    non_table = [f for f in terms_group.fields if not f.is_table]
    instrs = plan_group_layout(terms_group.name, non_table, "Test Sheet")

    # bonding_amount should have a note instruction
    notes = [i for i in instrs if i.note and "bonding_required" in i.note]
    assert len(notes) == 1


def test_plan_table_layout_work_items(rfq_schema: Schema) -> None:
    """work_items table has correct headers and 0 default rows."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    tp = plan_table_layout(work_items, "Table - Work Items")

    # Should have 6 header columns
    assert len(tp.headers) == 6
    header_labels = [h.value for h in tp.headers]
    assert "Item #" in header_labels
    assert "Description" in header_labels
    assert "Unit Price ($)" in header_labels

    # work_items has no default_rows
    assert len(tp.default_rows) == 0


def test_plan_table_layout_required_docs(rfq_schema: Schema) -> None:
    """required_documents table has 6 default rows."""
    req_docs = rfq_schema.get_field("required_documents")
    assert req_docs is not None
    tp = plan_table_layout(req_docs, "Table - Required Docs")

    # 6 default rows in the schema
    assert len(tp.default_rows) == 6


def test_plan_table_layout_column_formats(rfq_schema: Schema) -> None:
    """Currency columns in work_items get currency number format."""
    work_items = rfq_schema.get_field("work_items")
    assert work_items is not None
    tp = plan_table_layout(work_items, "Table - Work Items")

    # Check that unit_price column width hint is for currency (15)
    # Column 5 = unit_price (currency type)
    assert tp.column_widths[4] == 15  # 0-indexed, 5th column


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
    assert title[0].merge_cols >= 4


def test_plan_control_sheet_has_button_labels() -> None:
    """All expected button labels are present."""
    instrs = plan_control_sheet()
    values = {str(i.value) for i in instrs}
    expected_labels = [
        "Initialize Sheets",
        "Generate Document",
        "Validate Data",
        "Export Data (YAML)",
        "Import Data (YAML)",
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

    redact_value = [i for i in instrs if i.value == "TRUE" and i.dropdown_choices]
    assert len(redact_value) == 1
    assert redact_value[0].dropdown_choices == ["TRUE", "FALSE"]


def test_plan_control_sheet_custom_github_url() -> None:
    """Custom github_base URL appears in the config area."""
    custom = "https://raw.githubusercontent.com/myorg/myrepo/main"
    instrs = plan_control_sheet(github_base=custom)
    url_cells = [i for i in instrs if i.value == custom]
    assert len(url_cells) == 1


def test_plan_control_sheet_has_yaml_staging() -> None:
    """YAML STAGING AREA section header exists."""
    instrs = plan_control_sheet()
    staging = [i for i in instrs if i.value == "YAML STAGING AREA"]
    assert len(staging) == 1

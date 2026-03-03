"""Tests for dev.local_runner — local pipeline orchestration."""
from __future__ import annotations

from dev.local_runner import (
    export_yaml,
    fill_data,
    generate,
    init_workbook,
    read_data,
    validate,
)
from dev.mock_book import MockBook
from engine.config import SHEET_DATA_ENTRY
from engine.schema_loader import Schema

# ---------------------------------------------------------------------------
# init_workbook
# ---------------------------------------------------------------------------


class TestInitWorkbook:
    def test_creates_control_sheet(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema, schema_name="RFQ - Electric Utility")
        sheet_names = [s.name for s in book.sheets]
        assert "Control" in sheet_names

    def test_writes_schema_name(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema, schema_name="RFQ - Electric Utility")
        assert book.sheets["Control"]["B3"].value == "RFQ - Electric Utility"

    def test_creates_data_entry_sheet(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema)
        sheet_names = [s.name for s in book.sheets]
        assert SHEET_DATA_ENTRY in sheet_names

    def test_creates_table_sheets(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema)
        sheet_names = [s.name for s in book.sheets]
        assert "Work Items - Line Items" in sheet_names
        assert "Required Documents" in sheet_names

    def test_no_sheet1_after_init(self, rfq_schema: Schema):
        book = MockBook()
        book.sheets.add("Sheet1")  # Simulate Excel's default
        init_workbook(book, rfq_schema)
        sheet_names = [s.name for s in book.sheets]
        assert "Sheet1" not in sheet_names

    def test_data_entry_has_scn_sections(self, rfq_schema: Schema):
        """Data Entry sheet has [Group Name] section headers."""
        book = MockBook()
        init_workbook(book, rfq_schema)
        sheet = book.sheets[SHEET_DATA_ENTRY]
        # Read column A to find section headers
        values = []
        for r in range(1, 100):
            v = sheet.range((r, 1)).value
            if v is not None:
                values.append(str(v))
        sections = [v for v in values if v.startswith("[") and v.endswith("]")]
        assert len(sections) >= 6  # At least 6 groups

    def test_data_entry_has_key_declarations(self, rfq_schema: Schema):
        """Data Entry sheet has field_key: declarations."""
        book = MockBook()
        init_workbook(book, rfq_schema)
        sheet = book.sheets[SHEET_DATA_ENTRY]
        values = []
        for r in range(1, 200):
            v = sheet.range((r, 1)).value
            if v is not None:
                values.append(str(v))
        keys = [v for v in values if v.endswith(":") and not v.startswith(";;")]
        assert "issuer_name:" in keys
        assert "rfq_number:" in keys


# ---------------------------------------------------------------------------
# fill_data + read_data round-trip
# ---------------------------------------------------------------------------


class TestFillReadRoundtrip:
    def test_simple_fields_roundtrip(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema)

        data_in = {
            "issuer_name": "Ozark Electric Cooperative",
            "rfq_number": "RFQ-2026-042",
            "rfq_title": "Distribution Line Reconstruction",
        }
        fill_data(book, rfq_schema, data_in)
        data_out = read_data(book, rfq_schema)

        assert data_out["issuer_name"] == "Ozark Electric Cooperative"
        assert data_out["rfq_number"] == "RFQ-2026-042"
        assert data_out["rfq_title"] == "Distribution Line Reconstruction"

    def test_table_fields_roundtrip(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema)

        data_in = {
            "work_items": [
                {
                    "item_number": "1",
                    "description": "Set steel poles",
                    "quantity": 45,
                    "unit": "EA",
                    "unit_price": 4200,
                    "extended_price": 189000,
                },
            ],
        }
        fill_data(book, rfq_schema, data_in)
        data_out = read_data(book, rfq_schema)

        assert len(data_out["work_items"]) == 1
        assert data_out["work_items"][0]["description"] == "Set steel poles"

    def test_compound_fields_roundtrip(self, rfq_schema: Schema):
        book = MockBook()
        init_workbook(book, rfq_schema)

        data_in = {
            "safety_requirements": {
                "general": "OSHA 10-hr required",
                "ppe": "FR clothing, hard hat",
            },
        }
        fill_data(book, rfq_schema, data_in)
        data_out = read_data(book, rfq_schema)

        assert data_out["safety_requirements"]["general"] == "OSHA 10-hr required"
        assert data_out["safety_requirements"]["ppe"] == "FR clothing, hard hat"

    def test_unfilled_fields_are_none(self, rfq_schema: Schema):
        """Fields not filled in should read back as None."""
        book = MockBook()
        init_workbook(book, rfq_schema)
        data_out = read_data(book, rfq_schema)
        assert data_out["issuer_name"] is None

    def test_full_sample_data_roundtrip(self, rfq_schema: Schema, sample_data: dict):
        book = MockBook()
        init_workbook(book, rfq_schema)

        fill_data(book, rfq_schema, sample_data)
        data_out = read_data(book, rfq_schema)

        assert data_out["issuer_name"] == sample_data["issuer_name"]
        assert data_out["rfq_number"] == sample_data["rfq_number"]
        assert data_out["payment_terms"] == sample_data["payment_terms"]


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_data_passes(self, rfq_schema: Schema, sample_data: dict):
        result = validate(rfq_schema, sample_data)
        assert result.valid, f"Validation errors: {result.errors}"

    def test_missing_required_field(self, rfq_schema: Schema):
        result = validate(rfq_schema, {})
        assert not result.valid
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_produces_document(self, rfq_schema: Schema, sample_data: dict):
        doc = generate(rfq_schema, sample_data)
        assert doc is not None
        # Document should have content (paragraphs)
        assert len(doc.paragraphs) > 0

    def test_save_to_file(self, rfq_schema: Schema, sample_data: dict, tmp_path):
        out = tmp_path / "test.docx"
        doc = generate(rfq_schema, sample_data, output_path=out)
        assert out.exists()
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# export_yaml
# ---------------------------------------------------------------------------


class TestExportYaml:
    def test_produces_yaml(self, rfq_schema: Schema, sample_data: dict):
        yaml_str = export_yaml(rfq_schema, sample_data)
        assert isinstance(yaml_str, str)
        assert "schema_id" in yaml_str
        assert "rfq_electric_utility" in yaml_str

    def test_redacted_export(self, rfq_schema: Schema, sample_data: dict):
        yaml_str = export_yaml(rfq_schema, sample_data, redact=True)
        assert isinstance(yaml_str, str)
        assert "redacted: true" in yaml_str

"""Tests for engine/validation_ux.py."""
from __future__ import annotations

from engine.schema_loader import Schema, validate_data
from engine.validation_ux import build_report, format_for_sheet


def test_valid_data_report(rfq_schema: Schema, sample_data: dict) -> None:
    """Valid data produces a report with no errors."""
    result = validate_data(rfq_schema, sample_data)
    report = build_report(rfq_schema, result)
    assert report.valid is True
    assert report.error_count == 0


def test_invalid_data_report(rfq_schema: Schema) -> None:
    """Empty data produces a report with multiple errors."""
    result = validate_data(rfq_schema, {})
    report = build_report(rfq_schema, result)
    assert report.valid is False
    assert report.error_count > 0
    assert "error" in report.summary.lower()


def test_report_rows_have_error_status(rfq_schema: Schema) -> None:
    """Error rows have status='ERROR'."""
    result = validate_data(rfq_schema, {})
    report = build_report(rfq_schema, result)
    error_rows = [r for r in report.rows if r.status == "ERROR"]
    assert len(error_rows) > 0
    for row in error_rows:
        assert row.status_color == "#C00000"


def test_ok_rows_for_valid_data(rfq_schema: Schema, sample_data: dict) -> None:
    """Valid data has OK rows for required fields."""
    result = validate_data(rfq_schema, sample_data)
    report = build_report(rfq_schema, result)
    ok_rows = [r for r in report.rows if r.status == "OK"]
    assert len(ok_rows) > 0
    for row in ok_rows:
        assert row.status_color == "#00B050"


def test_format_for_sheet_structure(rfq_schema: Schema, sample_data: dict) -> None:
    """format_for_sheet returns header + summary + data rows."""
    result = validate_data(rfq_schema, sample_data)
    report = build_report(rfq_schema, result)
    sheet_rows = format_for_sheet(report)

    assert len(sheet_rows) >= 2  # Header + summary at minimum
    assert sheet_rows[0] == ["Status", "Field", "Message"]
    assert sheet_rows[1][0] == "SUMMARY"


def test_warning_detection(rfq_schema: Schema, sample_data: dict) -> None:
    """Invalid choice value produces a warning row."""
    data = {**sample_data, "work_category": "Invalid"}
    result = validate_data(rfq_schema, data)
    report = build_report(rfq_schema, result)
    warning_rows = [r for r in report.rows if r.status == "WARNING"]
    assert len(warning_rows) >= 1
    assert report.warning_count >= 1

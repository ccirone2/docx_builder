"""Tests for workbook/runner.py — validation reporting helpers."""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field

from workbook.runner import _format_validation_line, _report_validation


# Minimal stand-in for ValidationResult so we don't import schema_loader twice
@dataclass
class _FakeValidation:
    valid: bool = True
    errors: list[str] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# _format_validation_line
# ---------------------------------------------------------------------------


class TestFormatValidationLine:
    def test_missing_required_field(self):
        msg = "Missing required field: Project Title (project_title)"
        assert _format_validation_line(msg) == "  - Project Title: missing"

    def test_missing_required_sub_field(self):
        msg = "Missing required sub-field: Address → City (address.city)"
        assert _format_validation_line(msg) == "  - Address → City: missing"

    def test_date_format_error(self):
        msg = "RFQ Issue Date: Expected date format YYYY-MM-DD, got '03/01/2026'"
        result = _format_validation_line(msg)
        assert result.startswith("  - RFQ Issue Date: ")
        assert "YYYY-MM-DD" in result

    def test_invalid_choice_warning(self):
        msg = "Work Category: 'Invalid' not in expected choices"
        result = _format_validation_line(msg)
        assert result == "  - Work Category: 'Invalid' not in expected choices"

    def test_number_format_error(self):
        msg = "Quantity: Expected a number, got 'abc'"
        result = _format_validation_line(msg)
        assert result.startswith("  - Quantity: ")

    def test_long_detail_truncated(self):
        detail = "x" * 100
        msg = f"Field: {detail}"
        result = _format_validation_line(msg)
        assert len(result) < len(msg)
        assert result.endswith("...")

    def test_fallback_no_colon(self):
        msg = "Something went wrong"
        result = _format_validation_line(msg)
        assert result == "  - Something went wrong"


# ---------------------------------------------------------------------------
# _report_validation
# ---------------------------------------------------------------------------


class TestReportValidation:
    def test_errors_printed(self, capsys):
        validation = _FakeValidation(
            valid=False,
            errors=[
                "Missing required field: Project Title (project_title)",
                "Missing required field: Utility Name (issuer_name)",
            ],
        )
        _report_validation(None, validation)
        captured = capsys.readouterr().out
        assert "Validation failed: 2 errors" in captured
        assert "Project Title: missing" in captured
        assert "Utility Name: missing" in captured

    def test_warnings_printed(self, capsys):
        validation = _FakeValidation(
            valid=True,
            warnings=["Work Category: 'Invalid' not in expected choices"],
        )
        _report_validation(None, validation)
        captured = capsys.readouterr().out
        assert "Validation warnings: 1" in captured
        assert "Work Category" in captured

    def test_no_output_when_valid_no_warnings(self, capsys):
        validation = _FakeValidation(valid=True)
        _report_validation(None, validation)
        captured = capsys.readouterr().out
        assert captured == ""

    def test_errors_and_warnings_together(self, capsys):
        validation = _FakeValidation(
            valid=False,
            errors=["Missing required field: Title (title)"],
            warnings=["Category: 'Bad' not in expected choices"],
        )
        _report_validation(None, validation)
        captured = capsys.readouterr().out
        assert "Validation failed: 1 errors" in captured
        assert "Title: missing" in captured
        assert "Validation warnings: 1" in captured
        assert "Category" in captured

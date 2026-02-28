"""
validation_ux.py — Validation result formatting for display in Excel.

Converts ValidationResult into structured data for a Validation sheet,
including color-coded status indicators and actionable error messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.schema_loader import Schema, ValidationResult

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ValidationRow:
    """Single row for the validation results display."""

    status: str  # "OK", "ERROR", "WARNING"
    field: str
    message: str

    @property
    def status_color(self) -> str:
        """Return a hex color code for the status indicator."""
        if self.status == "OK":
            return "#00B050"  # Green
        if self.status == "ERROR":
            return "#C00000"  # Red
        return "#ED7D31"  # Orange (warning)


@dataclass
class ValidationReport:
    """Full validation report for display."""

    valid: bool
    summary: str
    rows: list[ValidationRow]
    error_count: int
    warning_count: int


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_report(
    schema: Schema,
    result: ValidationResult,
) -> ValidationReport:
    """Convert a ValidationResult into a displayable report.

    Args:
        schema: The schema that was validated against.
        result: The ValidationResult from validate_data().

    Returns:
        A ValidationReport with rows for each issue and OK fields.
    """
    rows: list[ValidationRow] = []

    # Collect error field keys
    error_fields: set[str] = set()
    for error in result.errors:
        field_key = _extract_field_key(error)
        error_fields.add(field_key)
        rows.append(ValidationRow(status="ERROR", field=field_key, message=error))

    # Collect warning field keys
    warning_fields: set[str] = set()
    for warning in result.warnings:
        field_key = _extract_field_key(warning)
        warning_fields.add(field_key)
        rows.append(ValidationRow(status="WARNING", field=field_key, message=warning))

    # Add OK rows for required fields that passed
    for field in schema.get_required_fields():
        if field.key not in error_fields and field.key not in warning_fields:
            rows.append(
                ValidationRow(
                    status="OK",
                    field=field.key,
                    message=f"{field.label}: OK",
                )
            )

    # Build summary
    error_count = len(result.errors)
    warning_count = len(result.warnings)

    if result.valid:
        summary = "All required fields are valid."
        if warning_count > 0:
            summary += f" {warning_count} warning(s) noted."
    else:
        summary = f"{error_count} error(s) found."
        if warning_count > 0:
            summary += f" {warning_count} warning(s) noted."

    return ValidationReport(
        valid=result.valid,
        summary=summary,
        rows=rows,
        error_count=error_count,
        warning_count=warning_count,
    )


def _extract_field_key(message: str) -> str:
    """Extract the field key from an error/warning message.

    Messages follow the pattern:
        "Missing required field: Field Label (field_key)"
        "Field Label: validation message"
        "Missing required sub-field: Parent → Child (parent.child)"

    Args:
        message: Error or warning message.

    Returns:
        Extracted field key, or the message itself as fallback.
    """
    # Try "... (field_key)" pattern
    if "(" in message and message.endswith(")"):
        start = message.rfind("(")
        return message[start + 1 : -1]

    # Try "Field Label: message" pattern
    if ":" in message:
        parts = message.split(":", 1)
        key = parts[0].strip()
        if " " not in key:
            return key

    return message


# ---------------------------------------------------------------------------
# Format for sheet display
# ---------------------------------------------------------------------------


def format_for_sheet(report: ValidationReport) -> list[list[Any]]:
    """Convert report into rows suitable for writing to a sheet.

    Args:
        report: The ValidationReport.

    Returns:
        List of [status, field, message] rows (header + data).
    """
    rows: list[list[Any]] = []

    # Header row
    rows.append(["Status", "Field", "Message"])

    # Summary row
    rows.append(["SUMMARY", "", report.summary])

    # Detail rows — errors first, then warnings, then OK
    for status in ("ERROR", "WARNING", "OK"):
        for row in report.rows:
            if row.status == status:
                rows.append([row.status, row.field, row.message])

    return rows

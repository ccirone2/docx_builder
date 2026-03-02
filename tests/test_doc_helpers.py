"""Tests for doc_generator internal helper functions."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from engine.doc_generator import (
    _format_date,
    _format_value_for_doc,
    _should_include_section,
)
from engine.schema_loader import FieldDef

# ---------------------------------------------------------------------------
# _format_date
# ---------------------------------------------------------------------------


def test_format_date_iso_string() -> None:
    """ISO date string is formatted as 'Month DD, YYYY'."""
    assert _format_date("2026-01-15") == "January 15, 2026"


def test_format_date_date_object() -> None:
    """A date object is formatted as 'Month DD, YYYY'."""
    assert _format_date(date(2026, 1, 15)) == "January 15, 2026"


def test_format_date_datetime_object() -> None:
    """A datetime object is formatted as 'Month DD, YYYY'."""
    assert _format_date(datetime(2026, 1, 15, 10, 30)) == "January 15, 2026"


def test_format_date_invalid_string() -> None:
    """A non-date string is returned unchanged (passthrough)."""
    assert _format_date("not-a-date") == "not-a-date"


# ---------------------------------------------------------------------------
# _format_value_for_doc
# ---------------------------------------------------------------------------


def test_format_value_boolean_true() -> None:
    """Boolean True is displayed as 'Yes'."""
    assert _format_value_for_doc("boolean", True) == "Yes"


def test_format_value_boolean_false() -> None:
    """Boolean False is displayed as 'No'."""
    assert _format_value_for_doc("boolean", False) == "No"


def test_format_value_currency() -> None:
    """Currency float is formatted as '$X,XXX.XX'."""
    assert _format_value_for_doc("currency", 1234.5) == "$1,234.50"


def test_format_value_none() -> None:
    """None value returns an empty string regardless of field type."""
    assert _format_value_for_doc("text", None) == ""


def test_format_value_date_delegates() -> None:
    """Date type delegates to _format_date for formatting."""
    assert _format_value_for_doc("date", "2026-03-01") == "March 01, 2026"


# ---------------------------------------------------------------------------
# _should_include_section
# ---------------------------------------------------------------------------


def _make_field(conditional_on: dict[str, Any] | None = None) -> FieldDef:
    """Create a minimal FieldDef for testing _should_include_section.

    Args:
        conditional_on: Optional conditional dict.

    Returns:
        A FieldDef with the given conditional_on.
    """
    return FieldDef(
        key="test_field",
        label="Test Field",
        type="text",
        conditional_on=conditional_on,
    )


def test_should_include_no_condition() -> None:
    """A field with no conditional_on is always included."""
    field = _make_field(conditional_on=None)
    assert _should_include_section(field, {}) is True


def test_should_include_condition_met() -> None:
    """A field is included when its condition is satisfied."""
    field = _make_field(conditional_on={"field": "x", "value": "y"})
    assert _should_include_section(field, {"x": "y"}) is True


def test_should_include_condition_not_met() -> None:
    """A field is excluded when its condition is not satisfied."""
    field = _make_field(conditional_on={"field": "x", "value": "y"})
    assert _should_include_section(field, {"x": "z"}) is False

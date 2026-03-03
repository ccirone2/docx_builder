"""Edge-case tests across multiple engine modules."""
from __future__ import annotations

import time
from typing import Any

import pytest

from engine.data_exchange import (
    _deserialize_value,
    export_snapshot,
    import_snapshot,
)
from engine.github_loader import (
    _cache,
    _cache_timestamps,
    clear_cache,
    get_local_template_source,
    is_cache_fresh,
    load_template_builder,
    register_local_schema,
)
from engine.schema_loader import (
    FieldDef,
    Schema,
    discover_schemas,
    validate_data,
)

# ---------------------------------------------------------------------------
# schema_loader edge cases
# ---------------------------------------------------------------------------


def test_validate_invalid_date_format(rfq_schema: Schema) -> None:
    """A date in MM/DD/YYYY format triggers a date-format error."""
    data: dict[str, Any] = {"rfq_issue_date": "03/01/2026"}
    result = validate_data(rfq_schema, data)
    date_errors = [e for e in result.errors if "date" in e.lower() or "YYYY-MM-DD" in e]
    assert len(date_errors) > 0


def test_validate_invalid_number(rfq_schema: Schema) -> None:
    """A non-numeric string in a number field triggers an error."""
    data: dict[str, Any] = {"estimated_duration": "ninety days"}
    validate_data(rfq_schema, data)
    # estimated_duration is type 'text', so find a real number field.
    # Use work_items' quantity indirectly — instead, directly validate
    # against a standalone schema. The schema does not expose a bare
    # 'number' field at top level, so validate via _validate_single_field.
    from engine.schema_loader import _validate_single_field

    errors: list[str] = []
    warnings: list[str] = []
    number_field = FieldDef(key="qty", label="Quantity", type="number", required=True)
    _validate_single_field(number_field, "not-a-number", errors, warnings)
    assert any("number" in e.lower() for e in errors)


def test_all_fields_deep_includes_sub_fields(rfq_schema: Schema) -> None:
    """all_fields_deep is larger than all_fields because it expands compound sub-fields."""
    assert len(rfq_schema.all_fields_deep) > len(rfq_schema.all_fields)


def test_discover_schemas_finds_rfq() -> None:
    """discover_schemas locates rfq_electric_utility in the schemas directory."""
    result = discover_schemas("schemas/")
    assert "rfq_electric_utility" in result


# ---------------------------------------------------------------------------
# data_exchange edge cases
# ---------------------------------------------------------------------------


def test_deserialize_boolean_yes() -> None:
    """String 'yes' deserializes to True for a boolean field."""
    field = FieldDef(key="flag", label="Flag", type="boolean")
    assert _deserialize_value(field, "yes") is True


def test_deserialize_boolean_no() -> None:
    """String 'no' deserializes to False for a boolean field."""
    field = FieldDef(key="flag", label="Flag", type="boolean")
    assert _deserialize_value(field, "no") is False


def test_deserialize_currency_string() -> None:
    """A formatted currency string is parsed to a float."""
    field = FieldDef(key="amount", label="Amount", type="currency")
    assert _deserialize_value(field, "$1,234.56") == pytest.approx(1234.56)


def test_import_invalid_scn(rfq_schema: Schema) -> None:
    """Importing empty/malformed SCN returns empty data with no crash."""
    data, warnings = import_snapshot(rfq_schema, "")
    assert data == {}


def test_export_import_none_values(rfq_schema: Schema) -> None:
    """None values survive an export/import round-trip as None."""
    sparse_data: dict[str, Any] = {
        "rfq_number": "RFQ-001",
        "rfq_title": None,
    }
    scn_text = export_snapshot(rfq_schema, sparse_data, redact=False)
    imported, _warnings = import_snapshot(rfq_schema, scn_text)
    # rfq_title was None so it should remain None (or absent) after import
    assert imported.get("rfq_title") is None


# ---------------------------------------------------------------------------
# github_loader edge cases
# ---------------------------------------------------------------------------


def test_clear_cache_empties_dicts() -> None:
    """clear_cache removes all entries from _cache and _cache_timestamps."""
    _cache["http://test-url"] = "some data"
    _cache_timestamps["http://test-url"] = time.time()
    clear_cache()
    assert len(_cache) == 0
    assert len(_cache_timestamps) == 0


def test_is_cache_fresh_missing_url() -> None:
    """is_cache_fresh returns False for a URL that was never cached."""
    assert is_cache_fresh("http://nonexistent") is False


def test_load_template_builder_missing_function() -> None:
    """load_template_builder returns None when source lacks build_document."""
    result = load_template_builder("x = 1")
    assert result is None


def test_register_local_with_template() -> None:
    """register_local_schema stores template_source and makes it retrievable."""
    yaml_text = """
schema:
  id: test_tpl_schema
  name: "Template Test"
  version: "0.1"
  template: ""
core_fields:
  - group: "Basics"
    fields:
      - key: title
        label: "Title"
        type: text
        required: true
"""
    template_code = "def build_document(data): pass"
    entry = register_local_schema(yaml_text, template_source=template_code)
    assert entry is not None
    assert entry.id == "test_tpl_schema"
    retrieved = get_local_template_source("test_tpl_schema")
    assert retrieved == template_code

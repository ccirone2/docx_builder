"""Tests for engine/schema_loader.py."""
from __future__ import annotations

from pathlib import Path

from engine.schema_loader import (
    Schema,
    load_schema,
    load_schema_from_text,
    validate_data,
)


def test_load_schema(rfq_schema: Schema) -> None:
    """Schema loads with expected field counts."""
    assert len(rfq_schema.all_fields) == 36
    assert len(rfq_schema.get_required_fields()) == 24
    assert len(rfq_schema.core_groups) == 6
    assert len(rfq_schema.optional_groups) == 3
    assert len(rfq_schema.get_table_fields()) == 3
    assert len(rfq_schema.get_compound_fields()) == 1


def test_load_schema_from_text(rfq_schema: Schema) -> None:
    """Loading from text produces same results as from file."""
    yaml_text = Path("schemas/rfq_electric_utility.yaml").read_text()
    schema = load_schema_from_text(yaml_text)
    assert schema.id == rfq_schema.id
    assert len(schema.all_fields) == len(rfq_schema.all_fields)
    assert len(schema.get_required_fields()) == len(rfq_schema.get_required_fields())


def test_compound_field_structure(rfq_schema: Schema) -> None:
    """safety_requirements is compound with 7 sub-fields."""
    field = rfq_schema.get_field("safety_requirements")
    assert field is not None
    assert field.is_compound
    assert field.sub_fields is not None
    assert len(field.sub_fields) == 7
    sub_keys = [sf.key for sf in field.sub_fields]
    assert "general" in sub_keys
    assert "lockout_tagout" in sub_keys
    assert "ppe" in sub_keys


def test_get_field_dotted(rfq_schema: Schema) -> None:
    """Dotted notation finds compound sub-fields."""
    field = rfq_schema.get_field("safety_requirements.general")
    assert field is not None
    assert field.key == "general"
    assert field.type == "multiline"


def test_get_field_flat(rfq_schema: Schema) -> None:
    """Flat child key finds inside compound fields."""
    field = rfq_schema.get_field("general")
    assert field is not None
    assert field.key == "general"


def test_redact_flags(rfq_schema: Schema) -> None:
    """issuer_name has redact=True, rfq_number has redact=False."""
    issuer = rfq_schema.get_field("issuer_name")
    assert issuer is not None
    assert issuer.redact is True

    rfq_num = rfq_schema.get_field("rfq_number")
    assert rfq_num is not None
    assert rfq_num.redact is False


def test_conditional_fields(rfq_schema: Schema) -> None:
    """bonding_amount has conditional_on pointing to bonding_required."""
    field = rfq_schema.get_field("bonding_amount")
    assert field is not None
    assert field.conditional_on is not None
    assert field.conditional_on["field"] == "bonding_required"
    assert field.conditional_on["value"] is True


def test_validate_valid_data(rfq_schema: Schema, sample_data: dict) -> None:
    """sample_data passes validation."""
    result = validate_data(rfq_schema, sample_data)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_missing_required(rfq_schema: Schema) -> None:
    """Empty dict fails validation with errors for required fields."""
    result = validate_data(rfq_schema, {})
    assert result.valid is False
    assert len(result.errors) >= 20  # At least 20 required fields


def test_validate_invalid_choice(rfq_schema: Schema, sample_data: dict) -> None:
    """Bad work_category produces a warning."""
    data = {**sample_data, "work_category": "Invalid Category"}
    result = validate_data(rfq_schema, data)
    assert any("work_category" in w or "Invalid Category" in w for w in result.warnings)

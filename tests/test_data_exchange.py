"""Tests for engine/data_exchange.py and engine/llm_helpers.py."""
from __future__ import annotations

from engine.data_exchange import (
    export_snapshot,
    import_snapshot,
)
from engine.llm_helpers import (
    generate_llm_prompt,
    generate_schema_reference,
)
from engine.schema_loader import Schema


def test_export_unredacted(rfq_schema: Schema, sample_data: dict) -> None:
    """issuer_name appears in unredacted export."""
    output = export_snapshot(rfq_schema, sample_data, redact=False)
    assert "Ozark Electric Cooperative" in output


def test_export_redacted_pii(rfq_schema: Schema, sample_data: dict) -> None:
    """issuer_name becomes [REDACTED] in redacted export."""
    output = export_snapshot(rfq_schema, sample_data, redact=True)
    assert "Ozark Electric Cooperative" not in output
    assert "[REDACTED]" in output


def test_export_redacted_prices(rfq_schema: Schema, sample_data: dict) -> None:
    """unit_price becomes 0 in redacted export."""
    output = export_snapshot(rfq_schema, sample_data, redact=True)
    # The actual price values (4200, 28000) should not appear
    assert "4200" not in output
    assert "28000" not in output


def test_export_redacted_flexible(rfq_schema: Schema, sample_data: dict) -> None:
    """Flexible field values become [REDACTED] in redacted export."""
    output = export_snapshot(rfq_schema, sample_data, redact=True)
    # The flexible value "Random testing required" should not appear
    assert "Random testing required" not in output


def test_export_produces_scn_structure(rfq_schema: Schema, sample_data: dict) -> None:
    """Export produces SCN with [sections] and key: lines."""
    output = export_snapshot(rfq_schema, sample_data, redact=False)
    assert "[_meta]" in output
    assert "schema_id:" in output
    assert "rfq_electric_utility" in output


def test_import_round_trip(rfq_schema: Schema, sample_data: dict) -> None:
    """Export then import: non-None values match."""
    scn_text = export_snapshot(rfq_schema, sample_data, redact=False)
    imported, warnings = import_snapshot(rfq_schema, scn_text)

    # Check key fields survived
    assert imported.get("rfq_number") == "RFQ-2026-042"
    assert imported.get("rfq_title") == "Distribution Line Reconstruction - Hwy 65 Corridor"
    assert imported.get("project_location") == "Taney County, MO"
    assert imported.get("issuer_name") == "Ozark Electric Cooperative"


def test_import_redacted_is_none(rfq_schema: Schema, sample_data: dict) -> None:
    """Importing [REDACTED] values results in None."""
    scn_text = export_snapshot(rfq_schema, sample_data, redact=True)
    imported, _ = import_snapshot(rfq_schema, scn_text)
    assert imported.get("issuer_name") is None
    assert imported.get("issuer_contact_email") is None


def test_compound_round_trip(rfq_schema: Schema, sample_data: dict) -> None:
    """Compound field round-trips: dict in, dict out with correct sub-fields."""
    scn_text = export_snapshot(rfq_schema, sample_data, redact=False)
    imported, _ = import_snapshot(rfq_schema, scn_text)

    safety = imported.get("safety_requirements")
    assert isinstance(safety, dict)
    assert "general" in safety
    assert "lockout_tagout" in safety
    assert "OSHA" in safety["general"]


def test_llm_prompt_markers(rfq_schema: Schema, sample_data: dict) -> None:
    """LLM prompt contains START SCN and END SCN markers."""
    prompt = generate_llm_prompt(rfq_schema, sample_data)
    assert "START SCN" in prompt
    assert "END SCN" in prompt


def test_llm_prompt_redaction_rule(rfq_schema: Schema, sample_data: dict) -> None:
    """LLM prompt contains rule #11 about [REDACTED]."""
    prompt = generate_llm_prompt(rfq_schema, sample_data, redact=True)
    assert "[REDACTED]" in prompt
    # Rule 11 mentions REDACTED
    assert "REDACTED" in prompt


def test_llm_prompt_redacts_pii(rfq_schema: Schema, sample_data: dict) -> None:
    """LLM prompt with redact=True shows [REDACTED] for issuer_name, real rfq_number."""
    prompt = generate_llm_prompt(rfq_schema, sample_data, redact=True)
    # issuer_name should be redacted
    assert "Ozark Electric Cooperative" not in prompt
    # rfq_number should show real value (not marked redact in schema)
    assert "RFQ-2026-042" in prompt


def test_schema_reference_compound(rfq_schema: Schema) -> None:
    """Schema reference shows compound sub-fields with dot notation."""
    ref = generate_schema_reference(rfq_schema)
    assert ".general" in ref
    assert ".lockout_tagout" in ref

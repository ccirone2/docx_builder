"""End-to-end integration tests spanning multiple engine modules."""
from __future__ import annotations

import io
from typing import Any

from engine.data_exchange import export_snapshot, import_snapshot
from engine.doc_generator import generate_document
from engine.schema_loader import Schema, validate_data
from engine.validation_ux import build_report


def test_full_pipeline_validate_and_generate(
    rfq_schema: Schema, sample_data: dict[str, Any]
) -> None:
    """Validate data, generate a Document, and save it to a BytesIO buffer."""
    result = validate_data(rfq_schema, sample_data)
    assert result.valid is True

    doc = generate_document(rfq_schema, sample_data)
    assert doc is not None

    buf = io.BytesIO()
    doc.save(buf)
    assert buf.tell() > 0


def test_export_import_round_trip(
    rfq_schema: Schema, sample_data: dict[str, Any]
) -> None:
    """Exported SCN can be re-imported with key fields surviving intact."""
    scn_text = export_snapshot(rfq_schema, sample_data, redact=False)
    imported, warnings = import_snapshot(rfq_schema, scn_text)

    assert imported.get("issuer_name") == "Ozark Electric Cooperative"
    assert imported.get("rfq_title") == "Distribution Line Reconstruction - Hwy 65 Corridor"
    assert imported.get("rfq_number") == "RFQ-2026-042"


def test_redacted_export_import(
    rfq_schema: Schema, sample_data: dict[str, Any]
) -> None:
    """Redacted export replaces sensitive fields; import converts them to None."""
    scn_text = export_snapshot(rfq_schema, sample_data, redact=True)
    imported, _warnings = import_snapshot(rfq_schema, scn_text)

    # issuer_contact_email is marked redact=True in the schema
    assert imported.get("issuer_contact_email") is None
    # Non-redacted fields survive
    assert imported.get("rfq_number") == "RFQ-2026-042"


def test_validation_report_pipeline(rfq_schema: Schema) -> None:
    """Empty data produces a report with ERROR rows."""
    result = validate_data(rfq_schema, {})
    assert result.valid is False

    report = build_report(rfq_schema, result)
    assert report.error_count > 0
    error_rows = [r for r in report.rows if r.status == "ERROR"]
    assert len(error_rows) > 0

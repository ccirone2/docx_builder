"""Tests for engine/file_bridge.py."""
from __future__ import annotations

import os
import tempfile

from docx import Document

from engine.file_bridge import generate_and_download, save_docx_local
from engine.schema_loader import Schema


def test_save_docx_local() -> None:
    """save_docx_local saves to temp file, file exists and is non-empty."""
    doc = Document()
    doc.add_paragraph("Test content")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result_bytes = save_docx_local(doc, tmp_path)
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
        assert len(result_bytes) > 0
    finally:
        os.unlink(tmp_path)


def test_generate_and_download_valid(rfq_schema: Schema, sample_data: dict) -> None:
    """With valid data, generate_and_download returns ValidationResult.valid=True."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = generate_and_download(rfq_schema, sample_data, filename=tmp_path)
        assert result.valid is True
        assert len(result.errors) == 0
        # File should have been created
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_generate_and_download_invalid(rfq_schema: Schema) -> None:
    """With missing required fields, returns errors without generating."""
    result = generate_and_download(rfq_schema, {}, filename="should_not_exist.docx")
    assert result.valid is False
    assert len(result.errors) > 0
    # File should NOT have been created
    assert not os.path.exists("should_not_exist.docx")

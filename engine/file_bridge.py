"""
file_bridge.py — Bridge between Pyodide (in-browser Python) and browser file APIs.

Provides functions to trigger file downloads from in-memory Python objects,
since we have no filesystem access in the xlwings Lite / Pyodide environment.

Usage:
    from docx import Document
    doc = Document()
    doc.add_paragraph("Hello!")
    trigger_docx_download(doc, "output.docx")
"""

from __future__ import annotations

import base64
import io
import sys
from typing import Any


def is_pyodide() -> bool:
    """Check if we're running inside Pyodide (WebAssembly)."""
    return sys.platform == "emscripten"


def trigger_docx_download(doc, filename: str = "document.docx"):
    """
    Save a python-docx Document and trigger a browser download.

    Works in Pyodide by converting to a Blob and creating a temporary
    download link. Falls back to regular file save outside Pyodide.
    """
    # Serialize document to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    byte_data = buffer.getvalue()

    if is_pyodide():
        _browser_download(
            byte_data,
            filename,
            mime_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
    else:
        # Fallback: save to local filesystem (for development/testing)
        with open(filename, "wb") as f:
            f.write(byte_data)
        print(f"Saved to {filename}")


def trigger_bytes_download(data: bytes, filename: str, mime_type: str = "application/octet-stream"):
    """
    Generic download trigger for any byte data.
    """
    if is_pyodide():
        _browser_download(data, filename, mime_type)
    else:
        with open(filename, "wb") as f:
            f.write(data)
        print(f"Saved to {filename}")


def _browser_download(data: bytes, filename: str, mime_type: str):
    """
    Trigger a file download in the browser using Pyodide's JS bridge.

    This creates a Blob from the byte data, generates a temporary object URL,
    creates an invisible <a> element, clicks it to trigger the download,
    and cleans up.
    """
    try:
        from js import URL, Blob, Uint8Array
        from js import document as js_doc
        from pyodide.ffi import to_js

        # Convert Python bytes → JS Uint8Array → Blob
        js_array = Uint8Array.new(to_js(data))
        options = to_js({"type": mime_type}, dict_converter=lambda x: x)
        blob = Blob.new([js_array], options)

        # Create object URL and trigger download
        url = URL.createObjectURL(blob)
        a = js_doc.createElement("a")
        a.href = url
        a.download = filename
        js_doc.body.appendChild(a)
        a.click()

        # Cleanup
        js_doc.body.removeChild(a)
        URL.revokeObjectURL(url)

        print(f"Download triggered: {filename}")

    except ImportError:
        # If JS bridge isn't available, fall back to base64 approach
        print("Warning: JS bridge not available. Using base64 fallback.")
        b64 = base64.b64encode(data).decode("ascii")
        print(f"Base64 data ({len(data)} bytes) for {filename}:")
        print(f"data:{mime_type};base64,{b64[:100]}...")


def save_docx_local(doc: Any, filename: str) -> bytes:
    """Save a python-docx Document to a local file and return bytes.

    For development/testing use outside of Pyodide.

    Args:
        doc: A python-docx Document object.
        filename: Path to save the file.

    Returns:
        The document as bytes.
    """
    buffer = io.BytesIO()
    doc.save(buffer)
    byte_data = buffer.getvalue()

    with open(filename, "wb") as f:
        f.write(byte_data)

    return byte_data


def bytes_to_base64_data_uri(data: bytes, mime_type: str) -> str:
    """Convert bytes to a base64 data URI.

    Useful as an alternative download method or for embedding in HTML.

    Args:
        data: Raw bytes.
        mime_type: MIME type string.

    Returns:
        Data URI string.
    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def generate_and_download(
    schema: Any,
    data: dict,
    filename: str | None = None,
) -> Any:
    """High-level function: validate, generate document, trigger download.

    Chains the full pipeline: validate data against schema, generate the
    Word document, and either trigger a browser download (Pyodide) or
    save locally (development).

    Args:
        schema: A Schema object.
        data: Field data dict.
        filename: Optional output filename. Defaults to "{schema.id}.docx".

    Returns:
        A ValidationResult object. If valid, the document was generated
        and download was triggered. Check result.valid and result.errors.
    """
    from engine.doc_generator import generate_document
    from engine.schema_loader import validate_data

    # Step 1: Validate
    result = validate_data(schema, data)
    if not result.valid:
        return result

    # Step 2: Generate document
    doc = generate_document(schema, data)

    # Step 3: Serialize to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    byte_data = buffer.getvalue()

    # Step 4: Download or save
    if filename is None:
        filename = f"{schema.id}.docx"

    if is_pyodide():
        _browser_download(
            byte_data,
            filename,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        with open(filename, "wb") as f:
            f.write(byte_data)

    return result

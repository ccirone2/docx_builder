# Architecture Decision Records

## ADR-001: xlwings Lite over Classic xlwings
**Date:** 2026-02-28
**Context:** Need Excel-based data entry with Python processing.
**Decision:** Use xlwings Lite (Pyodide) instead of classic xlwings.
**Consequences:** No local Python install needed, but no filesystem
access. All file I/O must go through browser download or clipboard.

## ADR-002: YAML for Schema Definitions
**Date:** 2026-02-28
**Context:** Need a human-readable, LLM-friendly format for field definitions.
**Decision:** YAML with a structured schema format.
**Consequences:** Matches LLM prompt format, easy to edit, but requires
PyYAML (available in Pyodide).

## ADR-003: Compound Field Type
**Date:** 2026-02-28
**Context:** safety_requirements needs structured sub-fields, not a single text blob.
**Decision:** Add `compound` type with recursive sub_fields on FieldDef.
**Consequences:** Every function that handles fields must now check
is_compound. Adds complexity but enables clean nested data structures.

## ADR-004: GitHub-Centric Distribution
**Date:** 2026-02-28
**Context:** Need schemas and templates to update independently of the workbook.
**Decision:** Public GitHub repo as source of truth. Workbook fetches at runtime.
**Consequences:** Users always get latest schemas. Requires CORS-friendly
host (GitHub raw URLs work). Offline needs cache/fallback.

## ADR-005: Per-Field Redaction
**Date:** 2026-02-28
**Context:** Users want LLM help filling in RFQ data but can't share PII.
**Decision:** `redact: true` property on fields and table columns.
**Consequences:** LLM prompts show field structure without sensitive values.
Import recognizes [REDACTED] and converts to None (no data overwrite).

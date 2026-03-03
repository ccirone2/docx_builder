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

## ADR-006: Two-Layer Excel Builder
**Date:** 2026-02-28
**Context:** Need to unit test Excel sheet generation without xlwings.
**Decision:** Separate pure logic layer (CellInstruction dataclasses) from
xlwings adapter layer (build_sheets/apply_cell).
**Consequences:** Logic layer is fully testable. Adapter layer is thin
and only runs in xlwings Lite runtime.

## ADR-007: Programmatic Document Generation (v1)
**Date:** 2026-02-28
**Context:** Need to generate Word documents from schema data.
**Decision:** Use python-docx programmatically rather than template files.
**Consequences:** More code but full control over output. No template
.docx files to manage. Future v2 can use docxtpl for hosted templates.

## ADR-008: TTL Cache with Stale Fallback
**Date:** 2026-02-28
**Context:** Need to balance freshness with performance and offline support.
**Decision:** 5-minute TTL on cached GitHub fetches, stale cache returned
on network failure, plus bundled schemas as last resort.
**Consequences:** Users get fresh schemas within 5 minutes. Network failures
degrade gracefully to cached or bundled content.

## ADR-009: Repo Config in Loader Constants, Not Cell D12
**Date:** 2026-03-02
**Context:** Both loader.py and runner.py read a custom GitHub URL from
Control!D12 on every function call. This created two sources of truth
(loader constants vs. cell value), added fragile cell-reading code, and
meant the runner re-checked the cell even when the loader had already
resolved the URL. Users who changed D12 mid-session could get into
inconsistent states.
**Decision:** Remove all D12 reading. Repo and branch are configured
exclusively via `GITHUB_REPO` and `GITHUB_BRANCH` constants at the top
of loader.py. The loader propagates its `GITHUB_BASE` to the runner on
every call. Users click **Reload Scripts** after changing the constants.
**Consequences:** Single source of truth for repo config. Simpler code
(deleted `_get_github_base`, `_resolve_base`, `_invalidate_runner`).
Changing repos requires editing loader.py rather than a cell, but this
matches the intended use case (fork contributors, not casual users).

## ADR-011: Flat Sheet Names (No Type Prefixes)
**Date:** 2026-03-02
**Context:** Sheet names were prefixed with "Data - ", "Optional - ", or
"Table - " (e.g., "Data - Project Overview", "Table - Line Items"). These
prefixes consumed 8–9 of the 31-character Excel limit, truncated long group
names aggressively, and made it harder to look up sheets by label in
`_read_table_data()` because the prefix had to be reconstructed at read time.
**Decision:** Remove all type prefixes from `_group_sheet_name()` and
`_table_sheet_name()` in `engine/excel_plan.py`. Sheet names are now the
sanitized, truncated group or field label only. `_read_table_data()` in
`workbook/runner.py` updated to match (`field.label[:31]` instead of
`f"Table - {field.label}"`).
**Consequences:** Sheet names are shorter, more readable, and consistent
with what users see in the data. Lookup is simpler. Any external code or
saved workbooks that relied on the "Data - " / "Table - " prefix convention
will need to be updated.

## ADR-012: Row Height Not Set Programmatically
**Date:** 2026-03-02
**Context:** `_field_row_instructions()` in `engine/excel_plan.py` set
`row_height=60` on rows containing multiline fields, and `apply_cell()` in
`engine/excel_writer.py` applied it via `sheet[row].height = value`. In
xlwings Lite (Office.js), row height APIs are unreliable and can raise
exceptions. The fixed height also prevented Excel's auto-fit from working
after users typed long values.
**Decision:** Remove the `row_height=60` assignment from
`_field_row_instructions()`. `apply_cell()` no longer reads or applies
`CellInstruction.row_height`. The field is retained on `CellInstruction`
(defaulting to `None`) for backwards compatibility but is ignored.
**Consequences:** Rows size themselves according to Excel's default or
auto-fit behavior. No risk of Office.js row-height exceptions. Any future
intentional row-height control must be re-added deliberately and tested
against xlwings Lite.

## ADR-013: Single-Column Notation (SCN) for Data Entry
**Date:** 2026-03-03
**Context:** The multi-column Excel layout (label in col 1, value in col 2,
required indicator in col 6) was fragile — reading required coordinate-based
`field_locations` tracking, and any layout change broke readers. The format
was also not human-readable outside Excel.
**Decision:** Replace multi-column layout with SCN (Single-Column Notation)
in column A. All non-table fields on one "Data Entry" sheet using SCN
constructs: `[Section]`, `;; Label`, `key:`, value. Tables use `+name`
dict-list notation on separate sheets. Reading uses `scn.parse_entry()`,
writing scans for `key:` rows. No coordinate tracking needed.
**Consequences:** Simpler read/write code (no `field_locations` dict).
Workbook data is human-readable as plain text. SCN parser is reusable for
issue #15 (data exchange format). Trade-off: single-column layout is less
visually polished than label/value columns, but SCN comments (`;;`) provide
field labels for guidance.

## ADR-010: Local Development Harness with MockBook
**Date:** 2026-03-02
**Context:** Need Claude Code to run the engine pipeline locally and verify
workbook initialization without Pyodide or browser Excel. The engine has a
clean two-layer design (pure logic vs. xlwings adapter), but workbook/runner.py
can't be imported locally because it uses pyodide.http for fetching.
**Decision:** Create dev/ package with MockBook (in-memory xlwings mock),
local_runner.py (direct engine imports), and harness.py (CLI). Desktop
xlwings is an optional backend for real Excel control.
**Consequences:** Fast feedback loop with zero external deps (mock mode).
Real Excel testing available when xlwings is installed. Sample data shared
between test fixtures and harness via dev/sample_data.py.

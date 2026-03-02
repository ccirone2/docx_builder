# Development Log

## 2026-02-28 — Initial Architecture & Schema System

Designed and implemented the core schema system for the RFQ document
generator. Key decisions:

- Chose xlwings Lite (Pyodide/WebAssembly) over classic xlwings for
  zero-install deployment
- YAML as the schema definition format
- Three-tier field model: core, optional, flexible
- Added compound field type for nested structures (e.g., safety_requirements)
- Added per-field redaction for LLM data exchange safety
- GitHub as single source of truth, workbook as thin shell

**Files created:**
- engine/schema_loader.py (Schema, FieldDef, validation)
- engine/data_exchange.py (YAML import/export, LLM prompts, redaction)
- engine/github_loader.py (GitHub fetch, local override, resolution)
- schemas/rfq_electric_utility.yaml (36 fields, 9 groups)
- schemas/registry.yaml (master index)
- ARCHITECTURE.md (full system design)

**Decisions:** See docs/DECISIONS.md #1-#5

## 2026-02-28 — Full Build (Phases A-H)

Executed the complete bootstrap build across all phases. Built out the
entire engine, workbook integration, and documentation in one session.

### Phase A — Project Setup
- pyproject.toml with all dependencies
- Full test suite (27 initial tests)
- README, LICENSE, .gitignore
- CI workflow with lint + schema validation + tests
- Contributing guide, schema authoring guide, user guide

### Phase B — GitHub Loader Completion
- TTL-based cache (5-minute expiry)
- Stale cache fallback on network failure
- Bundled schema support for offline use
- Tests for TTL and bundled fallback

### Phase C — Excel Builder
- Pure logic layer: plan_sheets, plan_group_layout, plan_table_layout
- CellInstruction, SheetPlan, TablePlan dataclasses
- xlwings adapter layer (apply_cell, build_sheets)
- Handles compound fields, tables, dropdowns, conditionals
- 8 tests

### Phase D — Document Builder
- generate_document() produces professional Word .docx
- Title block, numbered sections, formatted tables
- Compound field sub-sections, conditional sections
- Custom styles: navy headers, Calibri, consistent formatting
- 10 tests

### Phase E — Browser Download Bridge
- generate_and_download() pipeline: validate -> generate -> download
- save_docx_local() for development
- 3 tests

### Phase F — Workbook Bootstrap
- 6 @script functions for xlwings Lite
- initialize_sheets, generate_document, validate_data
- export_data_yaml, import_data_yaml, generate_llm_prompt
- Workbook setup guide in workbook/README.md

### Phase G — Local Customization & Validation UX
- validation_ux.py: color-coded validation reports
- Custom schema loading via staging cell
- Custom template loading
- 6 tests

### Phase H — Finalization
- 56 tests, all passing
- Lint clean across all engine modules
- All docs updated

**Files created:**
- engine/excel_builder.py
- engine/doc_generator.py
- engine/validation_ux.py
- workbook/scripts.py, workbook/README.md
- tests/ (7 test files, 56 tests total)
- pyproject.toml, README.md, LICENSE, .gitignore
- docs/CONTRIBUTING.md, docs/SCHEMA_AUTHORING.md, docs/USER_GUIDE.md

## 2026-02-28 — Easy Workbook Init (PR #4)

Major refactor of the workbook bootstrap system. Replaced the
monolithic scripts.py with a two-layer loader/runner architecture.

### Loader/Runner Architecture
- **loader.py**: Stable ~120-line bootstrap pasted into xlwings Lite.
  Defines `@xw.script` entry points that delegate to the runner.
  Never needs updating unless new buttons are added.
- **runner.py**: ~500-line business logic module fetched from GitHub
  at runtime. All updates take effect automatically.
- **init_workbook()**: One-click setup — creates Control sheet with
  labels, formatting, config cells, and builds data entry sheets.
  No manual sheet creation required.

### xlwings Lite Compatibility Fixes
- Removed `from __future__ import annotations` (breaks Pyodide)
- Removed all merge operations (Office.js incompatibility)
- Removed autofit/column_width code (not supported in Lite)
- Wrapped formatting in try/except for graceful degradation
- Used values-only mode for cell writes

### Logging & Status
- Added `engine/log.py` with timestamped DEBUG/INFO/WARN/ERROR
- All status output via print() to xlwings task pane
- Improved error reporting with exception type and step progress

### Other Changes
- Custom GitHub URL read from Control!D12
- 404 handling in loader and github_loader
- BRANCH variable for non-main branch support
- scripts.py preserved as self-contained alternative
- excel_builder.py expanded with control sheet planning (+8 tests)

**Files created:** workbook/loader.py, workbook/runner.py, engine/log.py
**Files modified:** engine/excel_builder.py, engine/data_exchange.py,
  engine/doc_generator.py, engine/file_bridge.py, engine/github_loader.py,
  engine/schema_loader.py, workbook/scripts.py, workbook/README.md,
  tests/test_excel_builder.py

**Test count:** 64 tests across 7 test files (up from 56)

## 2026-03-02 — Documentation Audit

Verified all documentation against current codebase and PRs. Fixed:

- **ARCHITECTURE.md**: Updated repo structure (added loader.py,
  runner.py, log.py, validation_ux.py; removed references to
  nonexistent templates/ directory, DocGen.xlsx, and
  TEMPLATE_AUTHORING.md). Updated build phases table (phases 2–8
  marked complete). Replaced bootstrap script section with
  loader/runner architecture description.
- **PLAN.md**: Updated test count from 56 to 64.
- **README.md**: Updated user quickstart to reference loader.py
  and init_workbook() instead of manual Control sheet creation.
- **CLAUDE.md**: Added engine/log.py and all missing modules to
  architecture quick reference. Updated print() convention to
  reference engine.log helpers.
- **BOOTSTRAP_PROMPT.md**: Added historical context note.
- **DEVLOG.md**: Added entries for PR #4 changes and this audit.

## 2026-03-02 — Workbook Script Cleanup

Removed stale code, simplified repo configuration, and improved
runtime feedback in the workbook scripts.

### scripts.py Removed
- Deleted `workbook/scripts.py` (593 lines). This was a self-contained
  alternative to the loader/runner architecture, but was never kept in
  sync and duplicated all logic. The loader/runner pair is the sole
  supported approach going forward.
- Removed all references to scripts.py from ARCHITECTURE.md and
  workbook/README.md.

### D12 Cell Override Removed
- Removed `_get_github_base()` from runner.py and `_resolve_base()` /
  `_invalidate_runner()` from loader.py. These read a custom GitHub
  URL from Control!D12 at every function call.
- Repo and branch are now configured exclusively via `GITHUB_REPO`
  and `GITHUB_BRANCH` constants in loader.py. Users click
  **Reload Scripts** after changing them.
- Removed the D12 config row from the Control sheet layout built
  by `_build_control_sheet()`.
- Updated ARCHITECTURE.md (Mechanism C, Configuration section) and
  workbook/README.md to match.

### Triggered Status Messages
- Added `_set_status(book, "<function_name> triggered")` as the first
  line of all 9 public runner functions, before the try block. This
  gives immediate feedback in the xlwings output pane when a button
  is clicked.

**Files deleted:** workbook/scripts.py
**Files modified:** workbook/runner.py, workbook/loader.py,
  workbook/README.md, ARCHITECTURE.md, docs/DECISIONS.md

## 2026-03-02 — Stale Code Cleanup (Plan 1)

Removed dead code, unused constants, and an obsolete module across four
engine files. All changes verified with 96 passing tests and clean lint.

### engine/schema_loader.py
- Removed dead `return ValidationResult(...)` at end of
  `_validate_single_field()`. The function mutates `errors`/`warnings`
  lists in place; callers never use the return value. Changed return
  type annotation to `-> None`.
- Added one-line Google-style docstrings to 5 properties/methods that
  were missing them: `is_table`, `is_compound`, `all_groups`,
  `get_table_fields`, `get_compound_fields`.

### engine/config.py
- Removed 9 unused constants with zero references in the codebase:
  `SCHEMA_SOURCE`, `DEFAULT_DATE_FORMAT`, `PLACEHOLDER_OPEN`,
  `PLACEHOLDER_CLOSE`, `DEFAULT_FONT`, `DEFAULT_FONT_SIZE_PT`,
  `TEMPLATE_STRATEGY`, `STRICT_VALIDATION`, `LOG_LEVEL`.
- Removed associated section header comments for now-empty sections.

### engine/file_bridge.py
- Removed `bytes_to_base64_data_uri()` function (zero callers).

### engine/template_registry.py
- Deleted entire 68-line file. Not imported anywhere, no tests,
  superseded by programmatic generation (ADR-007).

**Files deleted:** engine/template_registry.py
**Files modified:** engine/schema_loader.py, engine/config.py,
  engine/file_bridge.py

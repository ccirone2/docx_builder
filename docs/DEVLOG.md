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

## 2026-03-02 — Code Quality Review (Plans 2-4)

Completed documentation reconciliation, test coverage expansion, and
code refactoring — the remaining 3 plans from the comprehensive code
quality review.

### Plan 2: Documentation Reconciliation
- ARCHITECTURE.md: added missing modules (config.py, github_loader.py,
  validation_ux.py) to system diagram; removed template_registry.py
  from file tree; annotated templates/ as future-phase
- CLAUDE.md: removed template_registry.py from Architecture Quick Reference
- schemas/rfq_electric_utility.yaml: set template to "" with ADR-007 comment
- schemas/registry.yaml: set template_file to "" with ADR-007 comment

### Plan 3: Test Coverage Expansion (32 new tests)
- tests/test_config.py (3 tests): IS_PYODIDE, color hex format, sheet names
- tests/test_doc_helpers.py (12 tests): _format_date, _format_value_for_doc,
  _should_include_section
- tests/test_edge_cases.py (13 tests): schema validation edge cases,
  data_exchange deserialization, github_loader error paths
- tests/test_integration.py (4 tests): full pipeline, export/import
  round-trip, redacted round-trip, validation report pipeline

### Plan 4: Code Refactoring
- workbook/runner.py: extracted `_prepare_schema()` helper to eliminate
  5-step boilerplate duplicated across 5 public functions
- engine/github_loader.py: removed dead code (BUNDLED_REGISTRY,
  fetch_engine, ENGINE_MODULE_NAMES, TEMPLATES_DIR, CLI block);
  fixed docstring
- engine/data_exchange.py: removed 161-line CLI block

**Files modified:** ARCHITECTURE.md, CLAUDE.md, schemas/registry.yaml,
  schemas/rfq_electric_utility.yaml, workbook/runner.py,
  engine/github_loader.py, engine/data_exchange.py
**Files created:** tests/test_config.py, tests/test_doc_helpers.py,
  tests/test_edge_cases.py, tests/test_integration.py
**Test count:** 96 tests (was 64), all passing, lint clean

## 2026-03-02 — Module Splits and Performance (Plan 5)

Four refactoring tasks to reduce module size, eliminate duplication, and
improve field-lookup performance in the workbook runner.

### Task A: Consolidated is_pyodide()
- Removed the `is_pyodide()` function from `engine/file_bridge.py`.
  The function duplicated the detection logic already in `engine/config.py`.
- `file_bridge.py` now imports `IS_PYODIDE` (a module-level constant)
  from `engine/config.py` and uses it directly: `if IS_PYODIDE:`.
- Removed the now-unused `import sys` from `file_bridge.py`.
- All 3 call sites inside `file_bridge.py` updated from `if is_pyodide():`
  to `if IS_PYODIDE:`.

### Task B: Split data_exchange.py → data_exchange.py + llm_helpers.py
- `engine/data_exchange.py` reduced from 621 to 312 lines. Retains YAML
  formatting, redaction, export (`export_data_yaml`), and import
  (`import_data_yaml`). LLM logic removed.
- `engine/llm_helpers.py` (NEW, ~260 lines): houses `generate_llm_prompt()`
  and `generate_schema_reference()`.
- `tests/test_data_exchange.py` updated: LLM functions now imported from
  `engine.llm_helpers` instead of `engine.data_exchange`.

### Task C: 3-way split of excel_builder.py
- `engine/excel_builder.py` (589 lines) deleted entirely.
- `engine/excel_plan.py` (NEW, ~340 lines): dataclasses `CellInstruction`,
  `SheetPlan`, `TablePlan`, and planning functions `plan_sheets()`,
  `plan_group_layout()`, `plan_table_layout()`. Added `field_key: str = ""`
  field to `CellInstruction` and `field_locations: dict[str, tuple[str, int, int]]`
  to `SheetPlan` for O(1) field address lookups.
- `engine/excel_control.py` (NEW, ~130 lines): `plan_control_sheet()`
  function for generating the Control sheet layout.
- `engine/excel_writer.py` (NEW, ~95 lines): xlwings adapter functions
  `build_sheets()` and `apply_cell()`.
- `tests/test_excel_builder.py` updated to import from the three new modules.
  3 new tests added to cover `field_locations` population.

### Task D: Updated runner.py
- `_MODULE_DEPS` dependency graph updated: replaced `excel_builder` with
  `excel_plan`, `excel_control`, `excel_writer`; added `llm_helpers`; added
  `config` as a dependency of `file_bridge`.
- Added module-level `_field_index: dict[str, tuple[str, int, int]]` cache.
- `_read_field_value()` now does O(1) lookup via `_field_index` with a full
  scan fallback for safety.
- `init_workbook()` and `initialize_sheets()` populate `_field_index` after
  calling `build_sheets()`.
- `generate_llm_prompt()` now loads `llm_helpers` module instead of
  `data_exchange`.

**Files deleted:** engine/excel_builder.py
**Files created:** engine/llm_helpers.py, engine/excel_plan.py,
  engine/excel_control.py, engine/excel_writer.py
**Files modified:** engine/data_exchange.py, engine/file_bridge.py,
  workbook/runner.py, tests/test_data_exchange.py, tests/test_excel_builder.py,
  ARCHITECTURE.md, CLAUDE.md, docs/PLAN.md

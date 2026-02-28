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

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

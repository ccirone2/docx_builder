# CLAUDE.md

## Project
Template-driven document generator for electric utility RFQs.
Excel (xlwings Lite) → Python (Pyodide) → Word .docx output.

## Architecture
Read ARCHITECTURE.md for the full system design.

## Key Files
- engine/schema_loader.py — Schema parsing, validation, compound fields
- engine/data_exchange.py — YAML import/export, LLM prompts, redaction
- engine/github_loader.py — Fetch schemas/templates from GitHub + local
- schemas/registry.yaml — Master index of available schemas
- schemas/rfq_electric_utility.yaml — RFQ schema definition

## Current State
Phase 1 (schema system) and Phase 1b (data exchange) are complete.
Next: Phase 2 (GitHub loader integration) or Phase 3 (Excel builder).

## Conventions
- Python 3.11+, type hints everywhere
- All engine code must be Pyodide-compatible (pure Python)
- Schemas are YAML, templates are Python modules
- Tests run with: PYTHONPATH=. python -m pytest tests/

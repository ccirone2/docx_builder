# CLAUDE.md

## Project Overview
Template-driven document generator for electric utility RFQs.
Excel (xlwings Lite/Pyodide) → Python → Word .docx output.
Public open-source repo. See ARCHITECTURE.md for full design.

## Session Start Checklist
Before doing ANY work, always:
1. Read `docs/PLAN.md` for current phase and task status
2. Read the last 3 entries in `docs/DEVLOG.md` for recent context
3. Check open GitHub issues with `gh issue list --limit 10`
4. Confirm which task/issue you're working on before writing code

## Session End Checklist
Before ending ANY session, always:
1. Append a dated entry to `docs/DEVLOG.md` summarizing what was done
2. Update task status in `docs/PLAN.md` (mark completed, note blockers)
3. If architecture decisions were made, append to `docs/DECISIONS.md`
4. Ensure all new/modified files have updated docstrings
5. Run `PYTHONPATH=. python -m pytest tests/ -v` if tests exist
6. Commit with conventional commit messages (see below)

## Key Commands
- Test: `PYTHONPATH=. python -m pytest tests/ -v`
- Lint: `ruff check engine/ --fix`
- Format: `ruff format engine/`
- Type check: `pyright engine/`
- Run schema loader: `PYTHONPATH=. python engine/schema_loader.py`
- Run data exchange: `PYTHONPATH=. python engine/data_exchange.py`

## Code Conventions
- Python 3.11+, type hints on all function signatures
- All engine code must be Pyodide-compatible (pure Python, no C extensions)
- Use dataclasses, not raw dicts, for structured data
- Docstrings on all public functions (Google style)
- Keep modules under 400 lines; split if larger
- No `print()` in library code — use return values; `print()` only in CLI blocks

## Git Conventions
- Branch naming: `feature/xxx`, `fix/xxx`, `docs/xxx`
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Always reference GitHub issue: `feat: add excel builder (#12)`
- Never commit directly to `main` — always use branches + PRs
- Squash merge PRs to keep history clean

## Architecture Quick Reference
- `engine/schema_loader.py` — YAML → Schema objects, validation, compound fields
- `engine/data_exchange.py` — YAML import/export, LLM prompts, redaction
- `engine/github_loader.py` — Fetch schemas/templates from GitHub + local
- `engine/config.py` — Pyodide-aware settings
- `engine/file_bridge.py` — Pyodide → browser download via JS bridge
- `schemas/registry.yaml` — Master index of document types
- `schemas/rfq_electric_utility.yaml` — RFQ schema (36 fields, 9 groups)

## Current Build Phase
See `docs/PLAN.md` for the active phase and task breakdown.

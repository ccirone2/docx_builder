# Development Infrastructure Guide
## Claude Code Setup for Quality, Plan-Driven Development

This guide describes the full set of files, hooks, agents, skills, and
commands to add to the `docgen` repo for a disciplined, self-documenting
development workflow using Claude Code.

---

## Philosophy

Every development cycle should follow this loop:

```
┌─ READ current state (plans, logs, issues) ──────────┐
│                                                       │
│  ┌─ PLAN what to do (create/update GH issue) ──┐    │
│  │                                               │    │
│  │  ┌─ IMPLEMENT (code, test, commit) ──────┐  │    │
│  │  │                                        │  │    │
│  │  │  ┌─ DOCUMENT (update logs, plans) ─┐  │  │    │
│  │  │  │                                  │  │  │    │
│  │  │  └──────────────────────────────────┘  │  │    │
│  │  └────────────────────────────────────────┘  │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**Key principles:**
- The LLM always reads existing plans/logs before starting work
- Every code change has a corresponding GitHub issue
- Every session ends by updating documentation and logs
- The next session (or a different LLM) can pick up cleanly from files alone

---

## File Structure

```
docgen/
├── CLAUDE.md                           # ← Primary context for Claude Code
├── .claude/
│   ├── settings.json                   # Hooks, permissions, env
│   ├── commands/                       # Slash commands
│   │   ├── plan.md                     # /plan — create implementation plan
│   │   ├── implement.md                # /implement — build from plan
│   │   ├── review.md                   # /review — code review
│   │   ├── log.md                      # /log — update dev log
│   │   ├── wrapup.md                   # /wrapup — end-of-session routine
│   │   └── issue.md                    # /issue — create GitHub issue
│   ├── agents/                         # Subagents
│   │   ├── planner.md                  # Planning & architecture
│   │   ├── reviewer.md                 # Code review (read-only)
│   │   ├── documenter.md              # Docs & logs updater
│   │   └── schema-author.md           # Schema/template specialist
│   └── skills/                         # Auto-loaded skills
│       ├── python-conventions/SKILL.md # Python style for this project
│       └── schema-system/SKILL.md      # Schema authoring patterns
├── docs/
│   ├── DEVLOG.md                       # Development log (append-only)
│   ├── DECISIONS.md                    # Architecture decision records
│   ├── PLAN.md                         # Current phase plan + status
│   └── ...
└── .github/
    └── ISSUE_TEMPLATE/
        ├── feature.md
        ├── bug.md
        └── schema-request.md
```

---

## 1. CLAUDE.md (Project Root)

This is the most important file. Claude Code reads it automatically at session start.

```markdown
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
```

---

## 2. Hooks (`.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo '📋 Current plan:' && head -50 docs/PLAN.md 2>/dev/null || echo 'No plan yet.' && echo '' && echo '📝 Recent dev log:' && tail -30 docs/DEVLOG.md 2>/dev/null || echo 'No log yet.' && echo '' && echo '🔀 Git status:' && git status --short && echo '' && echo '📌 Open issues:' && gh issue list --limit 5 2>/dev/null || echo 'gh CLI not configured'",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash(git commit*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: Use conventional commit format (feat:/fix:/docs:/refactor:/test:) and reference the GH issue number.'",
            "timeout": 3
          }
        ]
      },
      {
        "matcher": "Edit:*.py|Write:*.py",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: Ensure type hints, docstrings, and Pyodide compatibility.'",
            "timeout": 2
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit:*.py|Write:*.py",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$CLAUDE_PROJECT_DIR\" && ruff check --quiet $(echo $CLAUDE_TOOL_INPUT | jq -r '.file_path // empty') 2>/dev/null || true",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Glob",
      "Grep",
      "Bash(python*)",
      "Bash(ruff*)",
      "Bash(pyright*)",
      "Bash(pytest*)",
      "Bash(git*)",
      "Bash(gh issue*)",
      "Bash(gh pr*)",
      "Bash(cat*)",
      "Bash(head*)",
      "Bash(tail*)",
      "Bash(wc*)",
      "Bash(ls*)",
      "Bash(find*)",
      "Bash(echo*)",
      "Bash(mkdir*)",
      "Bash(cp*)",
      "Bash(mv*)"
    ],
    "deny": [
      "Bash(rm -rf /)*",
      "Bash(sudo*)"
    ]
  }
}
```

### What the hooks do:

| Hook | Event | Purpose |
|------|-------|---------|
| **Session context** | `SessionStart` | Injects current plan, recent log, git status, and open issues into context automatically |
| **Commit reminder** | `PreToolUse` (git commit) | Reminds about conventional commit format and issue references |
| **Code quality hint** | `PreToolUse` (Edit/Write .py) | Reminds about type hints, docstrings, Pyodide compatibility |
| **Auto-lint** | `PostToolUse` (Edit/Write .py) | Runs ruff on edited Python files automatically |

---

## 3. Slash Commands (`.claude/commands/`)

### `/plan` — Create or update implementation plan

```markdown
<!-- .claude/commands/plan.md -->
# Create Implementation Plan

Read the current state of the project:
1. Read `ARCHITECTURE.md` for the full system design
2. Read `docs/PLAN.md` for the current phase and status
3. Read `docs/DEVLOG.md` for recent context and decisions
4. Check open GitHub issues with `gh issue list`

Then, for the topic: $ARGUMENTS

1. Break it into discrete tasks (max 1-2 hours each)
2. Identify dependencies between tasks
3. For each task, note: what files are affected, what tests are needed
4. Create or update `docs/PLAN.md` with the new plan
5. Create GitHub issues for each task using `gh issue create`
6. Label issues appropriately (enhancement, bug, documentation, etc.)
7. Log this planning session in `docs/DEVLOG.md`
```

### `/implement` — Build from plan

```markdown
<!-- .claude/commands/implement.md -->
# Implement Next Task

1. Read `docs/PLAN.md` and find the next uncompleted task
2. Read the corresponding GitHub issue for full context
3. Create a feature branch: `git checkout -b feature/ISSUE-NUMBER-short-description`
4. Implement the task, following conventions in CLAUDE.md
5. Write or update tests for the changed code
6. Run tests: `PYTHONPATH=. python -m pytest tests/ -v`
7. Run lint: `ruff check engine/ --fix && ruff format engine/`
8. Update the task status in `docs/PLAN.md` to ✅
9. Commit with conventional format referencing the issue
10. Update `docs/DEVLOG.md` with what was done

If $ARGUMENTS is provided, implement that specific task/issue instead.
```

### `/review` — Code review

```markdown
<!-- .claude/commands/review.md -->
# Code Review

Review the recent changes for quality and correctness.

1. Run `git diff main --stat` to see what changed
2. For each modified file, check:
   - Type hints on all function signatures
   - Docstrings on all public functions
   - No raw `print()` in library code (only in `if __name__` blocks)
   - Pyodide compatibility (no filesystem, no C extensions, no threading)
   - Error handling (don't silently swallow exceptions)
   - YAML/data round-trip safety (can export → import without data loss)
3. Run tests: `PYTHONPATH=. python -m pytest tests/ -v`
4. Check for any TODO/FIXME/HACK comments that should be issues
5. Provide a summary of findings

Focus area: $ARGUMENTS
```

### `/wrapup` — End-of-session routine

```markdown
<!-- .claude/commands/wrapup.md -->
# End-of-Session Wrapup

Perform all end-of-session housekeeping:

1. Run tests and report results: `PYTHONPATH=. python -m pytest tests/ -v`
2. Run lint: `ruff check engine/`
3. Append a dated entry to `docs/DEVLOG.md` with:
   - Date and session summary
   - What was accomplished (files changed, features added)
   - Decisions made and rationale
   - Blockers or open questions
   - Next steps
4. Update `docs/PLAN.md`:
   - Mark completed tasks
   - Note any new tasks discovered
   - Update the "Current Status" section
5. If architecture decisions were made, append to `docs/DECISIONS.md`
6. Verify all changes are committed
7. Print a final status summary
```

### `/log` — Quick dev log entry

```markdown
<!-- .claude/commands/log.md -->
# Add Development Log Entry

Append an entry to `docs/DEVLOG.md` with today's date.

Content to log: $ARGUMENTS

Format:
```
## YYYY-MM-DD — [Brief Title]

[Content]

**Files changed:** [list]
**Related issues:** [list]
```
```

### `/issue` — Create GitHub issue

```markdown
<!-- .claude/commands/issue.md -->
# Create GitHub Issue

Create a well-structured GitHub issue for: $ARGUMENTS

1. Determine the issue type (feature, bug, task, documentation)
2. Write a clear title (imperative mood, e.g., "Add Excel builder module")
3. Write a detailed body including:
   - **Context:** Why this is needed
   - **Scope:** What files/modules are affected
   - **Acceptance criteria:** How to verify it's done
   - **Dependencies:** What must be done first
4. Add appropriate labels
5. Create the issue: `gh issue create --title "..." --body "..." --label "..."`
6. Log the issue creation in `docs/DEVLOG.md`
```

---

## 4. Subagents (`.claude/agents/`)

### Planner Agent

```markdown
<!-- .claude/agents/planner.md -->
---
name: planner
description: >
  Creates implementation plans, breaks work into tasks, identifies
  dependencies, and structures GitHub issues. Use for any planning,
  scoping, or architecture discussion.
tools: Read, Glob, Grep, Bash(gh issue*), Bash(git log*), Bash(cat*), Bash(head*), Bash(tail*)
model: sonnet
---

You are a senior software architect and project planner.

## Your Role
- Break complex features into discrete, testable tasks
- Identify dependencies and optimal implementation order
- Write clear GitHub issues with acceptance criteria
- Update docs/PLAN.md with structured plans
- Consider Pyodide constraints in all technical decisions

## Planning Format
For each task:
1. **Title** — clear imperative description
2. **Files** — which modules are created/modified
3. **Dependencies** — what must exist first
4. **Tests** — what should be tested
5. **Estimate** — rough size (small/medium/large)
6. **Issue** — corresponding GitHub issue number

## Rules
- Never create tasks larger than ~2 hours of work
- Always check docs/PLAN.md and docs/DEVLOG.md for context
- Always create GitHub issues for planned tasks
- Reference architecture from ARCHITECTURE.md
```

### Reviewer Agent

```markdown
<!-- .claude/agents/reviewer.md -->
---
name: reviewer
description: >
  Reviews code for quality, correctness, and adherence to project
  conventions. Read-only — does not modify files. Use for code
  review, architecture review, or pre-commit checks.
tools: Read, Glob, Grep, Bash(python*), Bash(ruff*), Bash(pytest*)
model: sonnet
---

You are a meticulous code reviewer for a Python project that
must run in Pyodide (browser-based WebAssembly).

## Review Checklist
- [ ] Type hints on all function signatures
- [ ] Google-style docstrings on public functions
- [ ] No raw print() in library code
- [ ] Pyodide compatibility (no filesystem, no C extensions, no threading)
- [ ] Data round-trip safety (export → import without loss)
- [ ] Error handling (explicit, not swallowed)
- [ ] Schema field types validated correctly
- [ ] Compound fields handled in all code paths
- [ ] Redaction applied consistently
- [ ] Tests cover the new/changed code

## Output Format
For each finding:
- **File:Line** — description of issue
- **Severity** — error / warning / suggestion
- **Fix** — recommended change

End with a summary: PASS / PASS WITH WARNINGS / NEEDS CHANGES
```

### Documenter Agent

```markdown
<!-- .claude/agents/documenter.md -->
---
name: documenter
description: >
  Updates project documentation, dev logs, decision records, and
  plans. Use at the end of sessions or after significant changes
  to keep all documentation current.
tools: Read, Write, Edit, Glob, Grep, Bash(git diff*), Bash(git log*)
model: sonnet
---

You are a technical writer responsible for keeping this project's
documentation current and useful for the next developer (human or AI)
who picks up the work.

## Your Files
- `docs/DEVLOG.md` — Append-only development log
- `docs/PLAN.md` — Current phase plan with task status
- `docs/DECISIONS.md` — Architecture decision records
- `ARCHITECTURE.md` — System design (update when architecture changes)
- `CLAUDE.md` — Session context (update when conventions change)

## Rules
- DEVLOG.md is append-only — never delete or modify past entries
- PLAN.md should always reflect current reality
- DECISIONS.md uses ADR format (Context, Decision, Consequences)
- Write for someone with no prior context on the project
- Be specific: mention file names, function names, field names
- Date all entries
```

### Schema Author Agent

```markdown
<!-- .claude/agents/schema-author.md -->
---
name: schema-author
description: >
  Specialist in writing and validating YAML schema definitions and
  document templates for the docgen system. Use when creating new
  schemas, modifying existing ones, or authoring document templates.
tools: Read, Write, Edit, Glob, Grep, Bash(python*)
model: sonnet
---

You are an expert in the docgen schema system. You know:

## Schema Structure
- Three-tier fields: core (required), optional, flexible
- Field types: text, multiline, date, number, currency, choice, boolean, table, compound
- Compound fields have sub_fields with full FieldDef properties
- Tables have columns with key, label, type, and optional redact
- Conditional fields use conditional_on: {field, value}
- Redaction via redact: true on fields and table columns

## Your Tasks
- Write new schema YAML files following the established format
- Validate schemas by running: PYTHONPATH=. python engine/schema_loader.py path/to/schema.yaml
- Test data exchange round-trips with realistic sample data
- Add entries to schemas/registry.yaml
- Write matching document template Python modules

## Rules
- Every schema must have: id, name, version, template, description
- Required fields need sensible placeholders
- Group fields logically (issuer info, project info, scope, etc.)
- Add redact: true on PII fields (names, emails, phones, addresses)
- Include default_rows for table fields where applicable
- Test with: PYTHONPATH=. python -c "from engine.schema_loader import load_schema; s = load_schema('path'); print(f'{s.name}: {len(s.all_fields)} fields')"
```

---

## 5. Skills (`.claude/skills/`)

### Python Conventions

```markdown
<!-- .claude/skills/python-conventions/SKILL.md -->
---
name: python-conventions
description: >
  Python coding conventions for the docgen project. Apply when writing
  or editing any Python file in the engine/ directory.
---

# Python Conventions for docgen

## Type Hints
- All function signatures must have type hints
- Use `X | None` not `Optional[X]`
- Use `list[str]` not `List[str]` (Python 3.11+)
- Import `from __future__ import annotations` in all modules

## Docstrings (Google Style)
```python
def my_function(schema: Schema, data: dict[str, Any]) -> str:
    """Brief one-line summary.

    Longer description if needed.

    Args:
        schema: The active schema definition.
        data: Field key-value pairs from Excel.

    Returns:
        YAML string ready for clipboard.

    Raises:
        ValueError: If schema is invalid.
    """
```

## Module Structure
1. Module docstring
2. `from __future__ import annotations`
3. Standard library imports
4. Third-party imports
5. Local imports
6. Constants
7. Data classes
8. Private helpers
9. Public API functions
10. `if __name__ == "__main__":` CLI test block

## Pyodide Constraints
- No filesystem access (no open(), no Path.exists() in runtime code)
- No C extensions (use pure Python packages only)
- No threading/multiprocessing
- HTTP via `requests` (works in Pyodide)
- Use `io.BytesIO` for in-memory file operations
```

### Schema System

```markdown
<!-- .claude/skills/schema-system/SKILL.md -->
---
name: schema-system
description: >
  Schema system architecture and patterns for the docgen project.
  Apply when working with schema_loader.py, data_exchange.py, YAML
  schema files, or any code that touches field definitions.
---

# Schema System Patterns

## Field Type Handling
Every function that processes fields must handle ALL types:
- text, multiline, date, number, currency, choice, boolean
- table (list of dicts, with columns)
- compound (dict of sub-field values, with sub_fields)

## Compound Field Pattern
```python
if field.is_compound and isinstance(value, dict):
    for sf in (field.sub_fields or []):
        sv = value.get(sf.key)
        # process sub-field value
elif field.is_table and isinstance(value, list):
    for row in value:
        # process table row
else:
    # process scalar value
```

## Redaction Pattern
Always check three levels:
1. Field-level: `field.redact`
2. Table column-level: `col.get("redact", False)`
3. Compound sub-field-level: `sf.redact`

## Round-Trip Safety
Any data transformation must survive: export → import without loss.
Test with: export → import → re-export → compare.

## Schema Resolution Order
1. Local override (registered via file picker or paste)
2. Session cache
3. GitHub raw URL
4. Bundled fallback
```

---

## 6. Documentation Files (`docs/`)

### `docs/PLAN.md` — Living plan document

```markdown
# Development Plan

## Current Phase: Phase 2 — GitHub Loader Integration

### Status: 🟡 In Progress

### Tasks

| # | Task | Issue | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Implement github_loader.py | #3 | ✅ Done | Core fetch + local registration |
| 2 | Add load_schema_from_text() | #3 | ✅ Done | For string-based schema loading |
| 3 | Create registry.yaml | #4 | ✅ Done | Master schema index |
| 4 | Add session caching | #5 | 🔲 Todo | In-memory cache for fetched files |
| 5 | Add bundled fallback | #6 | 🔲 Todo | Offline support |

### Next Phase: Phase 3 — Excel Builder
- Auto-generate data entry sheets from schema
- Format cells, dropdowns, conditional visibility
- See ARCHITECTURE.md Phase 3 for details

### Backlog
- [ ] Phase 4: Document builder (python-docx templates)
- [ ] Phase 5: Browser download bridge
- [ ] Phase 6: Workbook bootstrap
- [ ] Phase 7: Local customization UX
```

### `docs/DEVLOG.md` — Append-only development log

```markdown
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
```

### `docs/DECISIONS.md` — Architecture Decision Records

```markdown
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
```

---

## 7. GitHub Issue Templates (`.github/ISSUE_TEMPLATE/`)

### Feature Request

```markdown
<!-- .github/ISSUE_TEMPLATE/feature.md -->
---
name: Feature Request
about: Propose a new feature or enhancement
labels: enhancement
---

## Summary
<!-- One sentence describing the feature -->

## Context
<!-- Why is this needed? What problem does it solve? -->

## Scope
<!-- Which files/modules are affected? -->

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
- [ ] Documentation updated

## Dependencies
<!-- What must be done first? Reference other issues. -->
```

### Schema Request

```markdown
<!-- .github/ISSUE_TEMPLATE/schema-request.md -->
---
name: Schema Request
about: Request a new document schema
labels: schema, enhancement
---

## Document Type
<!-- What type of document? e.g., Change Order, Bid Tabulation -->

## Industry
<!-- What industry is this for? -->

## Fields Needed
<!-- List the key fields this document requires -->

## Sample Document
<!-- Attach or link to a sample of this document type -->

## Notes
<!-- Any special requirements, conditional logic, etc. -->
```

---

## 8. GitHub Actions (`.github/workflows/`)

### Schema Validation CI

```yaml
# .github/workflows/validate.yml
name: Validate Schemas & Engine

on:
  push:
    branches: [main]
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pyyaml ruff pyright

      - name: Lint
        run: ruff check engine/

      - name: Type check
        run: pyright engine/
        continue-on-error: true

      - name: Load all schemas
        run: |
          PYTHONPATH=. python -c "
          from engine.schema_loader import load_schema
          from pathlib import Path
          for p in sorted(Path('schemas').glob('*.yaml')):
              if p.name == 'registry.yaml': continue
              s = load_schema(p)
              print(f'✅ {s.id}: {s.name} ({len(s.all_fields)} fields)')
          "

      - name: Validate registry
        run: |
          PYTHONPATH=. python -c "
          import yaml
          with open('schemas/registry.yaml') as f:
              reg = yaml.safe_load(f)
          for entry in reg['schemas']:
              assert 'id' in entry, f'Missing id in registry entry'
              assert 'schema_file' in entry, f'Missing schema_file for {entry[\"id\"]}'
              print(f'✅ {entry[\"id\"]}: {entry[\"name\"]}')
          "

      - name: Run tests
        run: PYTHONPATH=. python -m pytest tests/ -v
        if: hashFiles('tests/') != ''
```

---

## Installation Checklist

When setting up the repo for the first time:

1. Copy all files from this guide into the repo structure
2. `pip install ruff pyright pyyaml` (dev dependencies)
3. `gh auth login` (for GitHub CLI integration)
4. Start Claude Code: `claude`
5. Verify hooks load: you should see plan, log, and git status on startup
6. Test a command: type `/plan Phase 3 — Excel Builder`
7. Verify agents: type `/agents` to see the list

The system is self-reinforcing — every session starts by reading the current
state and ends by updating it, so the project is always ready for the next cycle.

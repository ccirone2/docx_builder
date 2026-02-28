# FULL BUILD PROMPT — docx_builder
# ==================================
# Current state: Engine modules exist but no tests, no templates,
# no pyproject.toml, no README. Phases 3-7+ not started.
#
# Usage:
#   cd docx_builder
#   claude
#   [paste this prompt]
#
# This prompt completes all remaining setup AND builds phases 2b–7.


You are completing the build of **docx_builder** — an open-source, template-driven document generator for the electric utility industry. Excel (xlwings Lite / Pyodide) handles data entry, Python generates Word .docx files. Everything runs in-browser via WebAssembly — zero Python install.

## What already exists in the repo

**Infrastructure (do NOT modify):**
- `CLAUDE.md`, `ARCHITECTURE.md`, `docs/DEV_INFRASTRUCTURE.md`
- `.claude/` — settings.json, 6 commands, 4 agents, 2 skills

**Engine (exists, may need minor fixes):**
- `engine/schema_loader.py` — YAML parser, validator, compound fields, `load_schema_from_text()`
- `engine/data_exchange.py` — YAML import/export, LLM prompts, redaction
- `engine/github_loader.py` — GitHub fetch, local registration, resolution chain
- `engine/config.py` — Configuration constants
- `engine/file_bridge.py` — Pyodide → browser download bridge
- `engine/template_registry.py` — Schema ↔ template mapping (stub)

**Schemas (exist):**
- `schemas/rfq_electric_utility.yaml` — 36-field RFQ schema (9 groups, 1 compound)
- `schemas/registry.yaml` — Master index

**What does NOT exist yet:**
- `tests/` — no tests at all
- `templates/` — no document templates
- `engine/excel_builder.py` — not created
- `engine/doc_generator.py` — not created
- `pyproject.toml` — no project config
- `README.md`, `LICENSE`, `.gitignore`
- `docs/PLAN.md`, `docs/DEVLOG.md`, `docs/DECISIONS.md`, `docs/CONTRIBUTING.md`, `docs/SCHEMA_AUTHORING.md`
- `.github/` — no issue templates or CI workflow
- `python-docx`, `pytest`, `ruff` not installed

---

## PHASE A: PROJECT SETUP (do this first)

### A1: Read existing files

Before creating anything, read these completely:
```bash
cat ARCHITECTURE.md
cat CLAUDE.md
cat docs/DEV_INFRASTRUCTURE.md
find . -type f ! -path './.git/*' ! -path './.claude/*' | sort
git log --oneline -10
git remote -v
```

### A2: Create pyproject.toml

```toml
[project]
name = "docx_builder"
version = "0.1.0"
description = "Template-driven document generator for electric utility RFQs"
requires-python = ">=3.11"
dependencies = [
    "pyyaml",
    "python-docx",
    "docxtpl",
    "jinja2",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "pyright",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

### A3: Install dependencies

```bash
pip install pyyaml python-docx docxtpl jinja2 pytest ruff --break-system-packages
```

### A4: Create root files

**README.md** — Project overview: what it does, key features (schema-driven, LLM-friendly data exchange with redaction, zero-install via xlwings Lite, open source), quickstart for users, quickstart for contributors (`pip install -e ".[dev]"`, `pytest tests/ -v`), links to ARCHITECTURE.md and docs/.

**LICENSE** — MIT, copyright the repo owner.

**.gitignore** — `__pycache__/`, `*.pyc`, `.env`, `.venv/`, `*.egg-info/`, `dist/`, `build/`, `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/`, `*.xlsx~`, `output/`, `.ruff_cache/`, `*.docx` (in output/ only)

### A5: Create documentation files

**docs/PLAN.md** — Phases 1-2 partially complete, Phase A (this session) in progress, Phases 3-7 planned.

**docs/DEVLOG.md** — First entry dated today noting current state.

**docs/DECISIONS.md** — ADR-001 through ADR-005:
1. xlwings Lite over Classic xlwings
2. YAML for schema definitions
3. Compound field type
4. GitHub-centric distribution
5. Per-field redaction for LLM safety

**docs/CONTRIBUTING.md** — Fork workflow, PR checklist, schema contribution steps.

**docs/SCHEMA_AUTHORING.md** — Field types reference, compound fields, tables, conditional fields, redaction, testing.

**docs/USER_GUIDE.md** — Placeholder with section headers.

### A6: Create GitHub infrastructure

**.github/ISSUE_TEMPLATE/feature.md** — Summary, context, scope, acceptance criteria, dependencies.

**.github/ISSUE_TEMPLATE/bug.md** — Standard bug template.

**.github/ISSUE_TEMPLATE/schema-request.md** — Document type, industry, fields, sample.

**.github/workflows/validate.yml** — CI on push/PR: Python 3.11, install deps, `ruff check engine/`, load all schemas, validate registry, `pytest tests/ -v`.

### A7: Create test suite for existing engine

Before building new modules, lock down what exists with tests.

**tests/conftest.py** — Shared fixtures:
- `rfq_schema` — loads `schemas/rfq_electric_utility.yaml`
- `sample_data` — realistic dict with all 24 required fields filled, plus work_items (2 rows with pricing), required_documents, safety_requirements (compound with 3 sub-fields populated), and flexible fields

**tests/test_schema_loader.py:**
- `test_load_schema` — 36 fields, 24 required, 6 core groups, 3 optional, 3 tables, 1 compound
- `test_load_schema_from_text` — same results from string
- `test_compound_field_structure` — safety_requirements is compound with 7 sub-fields
- `test_get_field_dotted` — `get_field("safety_requirements.general")` works
- `test_get_field_flat` — `get_field("general")` finds inside compound
- `test_redact_flags` — issuer_name redact=True, rfq_number redact=False
- `test_conditional_fields` — bonding_amount has conditional_on
- `test_validate_valid_data` — sample_data passes validation
- `test_validate_missing_required` — empty dict fails with 24 errors
- `test_validate_invalid_choice` — bad work_category warns

**tests/test_data_exchange.py:**
- `test_export_unredacted` — issuer_name appears in output
- `test_export_redacted_pii` — issuer_name becomes `[REDACTED]`
- `test_export_redacted_prices` — unit_price becomes 0
- `test_export_redacted_flexible` — flexible values become `[REDACTED]`
- `test_import_round_trip` — export → import, non-None values match
- `test_import_redacted_is_none` — `[REDACTED]` → None
- `test_compound_round_trip` — dict in → dict out with correct sub-fields
- `test_llm_prompt_markers` — contains "START YAML" and "END YAML"
- `test_llm_prompt_redaction_rule` — contains rule #11 about `[REDACTED]`
- `test_llm_prompt_redacts_pii` — issuer_name `[REDACTED]`, rfq_number shows real value
- `test_schema_reference_compound` — shows `.general` and `.lockout_tagout`

**tests/test_github_loader.py:**
- `test_register_local` — returns RegistryEntry with source="local"
- `test_local_retrieval` — register then get_local_schema_yaml works
- `test_local_overrides` — local wins over GitHub on same ID
- `test_resolve_local` — resolve_schema_yaml returns local content
- `test_invalid_yaml` — returns None
- `test_missing_id` — returns None

Run tests and fix any issues in the existing engine modules until ALL pass:
```bash
pytest tests/ -v
ruff check engine/ --fix
ruff format engine/
```

**Do not proceed to Phase B until all tests are green.**

### A8: Commit Phase A

```bash
git checkout -b feature/complete-setup-and-build
git add -A
git commit -m "chore: complete project setup — tests, docs, CI, pyproject.toml

- pyproject.toml with dependencies and dev tools
- Full test suite for schema_loader, data_exchange, github_loader
- CI workflow (lint + schema validation + tests)
- Documentation: PLAN, DEVLOG, DECISIONS, CONTRIBUTING, SCHEMA_AUTHORING
- README, LICENSE, .gitignore
- GitHub issue templates"
```

---

## PHASE B: COMPLETE GITHUB LOADER (Phase 2b)

### B1: Add caching improvements to github_loader.py

The current github_loader.py has basic caching. Add:
- `_cache_timestamps: dict[str, float]` — track when each URL was cached
- `CACHE_TTL = 300` — 5-minute TTL for cached items
- `fetch_text()` checks if cached item is stale before returning it
- `is_cache_fresh(url)` helper

### B2: Add bundled fallback to github_loader.py

For offline support:
- `_bundled_schemas: dict[str, str]` — embedded schema YAML for offline use
- `register_bundled_schema(schema_id, yaml_text)` — preload at init time
- Update `resolve_schema_yaml()` resolution chain: local → cache → GitHub → bundled
- Add `BUNDLED_REGISTRY` constant with minimal registry data

### B3: Test the additions

**tests/test_github_loader.py** — add:
- `test_bundled_fallback` — register bundled, resolve when GitHub unavailable
- `test_cache_ttl` — verify stale cache is refreshed (mock time)

```bash
pytest tests/test_github_loader.py -v
```

### B4: Commit Phase B

```bash
git add -A
git commit -m "feat: complete GitHub loader — TTL caching, bundled fallback (#phase-2b)"
```

---

## PHASE C: EXCEL BUILDER (Phase 3)

### C1: Create engine/excel_builder.py

This module builds Excel data entry sheets from a schema definition. Since it runs in xlwings Lite, it uses the xlwings API (`xw.Book`, `xw.Sheet`, `xw.Range`).

**However**, for testability, design it in two layers:
1. **Pure logic layer** (testable without Excel): functions that compute sheet layouts, cell positions, dropdown lists, formatting instructions — returning data structures
2. **xlwings layer** (thin adapter): functions that take those data structures and write to actual Excel sheets

**Pure logic functions:**

`plan_sheets(schema) → SheetPlan` — Determines which sheets to create:
- One sheet per core field group (e.g., "Data - Issuing Organization")
- One sheet per optional field group that has fields
- One sheet per table field (e.g., "Table - Work Items")
- Compound fields get a sub-section within their group's sheet, not a separate sheet

`plan_group_layout(group, start_row=2) → list[CellInstruction]` — For each field in a group:
- Label in column A, value in column B (merged B:E for wide fields)
- Multiline fields get a taller row height
- Compound fields: parent label as a sub-header row, then each sub-field indented in rows below
- Choice fields get a data validation dropdown
- Boolean fields get a data validation (TRUE/FALSE)
- Date fields get date format
- Currency fields get currency format
- Required fields get a red indicator marker in column F
- Conditional fields get a note about their condition

`plan_table_layout(field) → TablePlan` — For table-type fields:
- Header row with column labels
- Default rows pre-populated if `default_rows` exists
- Auto-width column sizing hints
- Currency/number formatting per column type

**Data classes:**

```python
@dataclass
class CellInstruction:
    sheet: str
    row: int
    col: int  # 1-based
    value: Any
    bold: bool = False
    bg_color: str = ""
    font_color: str = ""
    number_format: str = ""
    merge_cols: int = 1
    row_height: int | None = None
    dropdown_choices: list[str] | None = None
    is_header: bool = False
    note: str = ""

@dataclass
class SheetPlan:
    sheets: list[str]  # sheet names to create
    instructions: list[CellInstruction]

@dataclass
class TablePlan:
    sheet: str
    headers: list[CellInstruction]
    default_rows: list[list[CellInstruction]]
    column_widths: list[int]
```

**xlwings adapter functions (for runtime only, not unit tested):**

`build_sheets(book: xw.Book, plan: SheetPlan)` — Creates sheets, writes cells, applies formatting.

`apply_cell(sheet: xw.Sheet, instr: CellInstruction)` — Writes one cell with formatting, merges, dropdowns.

### C2: Test the pure logic layer

**tests/test_excel_builder.py:**
- `test_plan_sheets_creates_correct_sheet_names` — verify expected sheet names for RFQ schema
- `test_plan_group_layout_required_fields` — required fields have red indicator instructions
- `test_plan_group_layout_choice_dropdown` — work_category gets dropdown_choices
- `test_plan_group_layout_compound` — safety_requirements creates sub-header + indented sub-field rows
- `test_plan_group_layout_conditional` — bonding_amount has a note about condition
- `test_plan_table_layout_work_items` — correct headers, 0 default rows (work_items has no defaults)
- `test_plan_table_layout_required_docs` — 6 default rows
- `test_plan_table_layout_column_formats` — unit_price column gets currency format

```bash
pytest tests/test_excel_builder.py -v
```

### C3: Commit Phase C

```bash
git add -A
git commit -m "feat: add Excel builder — schema-driven sheet generation (#phase-3)

- Pure logic layer: plan_sheets, plan_group_layout, plan_table_layout
- Data classes: CellInstruction, SheetPlan, TablePlan
- xlwings adapter layer for runtime
- Compound fields as sub-sections, tables as dedicated sheets
- Full test coverage for layout planning"
```

---

## PHASE D: DOCUMENT BUILDER (Phase 4)

### D1: Create engine/doc_generator.py

Generates a professional Word .docx from validated schema data using `python-docx`.

**Main function:**
`generate_document(schema, data, template_id=None) → Document`

**Document structure for RFQ:**

```
[Logo placeholder area]

REQUEST FOR QUOTATION
[rfq_title]

RFQ Number: [rfq_number]          Issue Date: [rfq_issue_date]
                                   Due Date: [rfq_due_date] [rfq_due_time]

ISSUED BY:
[issuer_name]
[issuer_address]
Contact: [issuer_contact_name], [issuer_contact_title]
Email: [issuer_contact_email] | Phone: [issuer_contact_phone]

─────────────────────────────────────────

1. PROJECT DESCRIPTION
[project_description]

Location: [project_location]
Category: [work_category]
Duration: [estimated_duration]
Start Date: [estimated_start_date]

2. SCOPE OF WORK
[scope_summary]

2.1 Work Items
┌──────┬────────────────────┬─────┬──────┬───────────┬────────────┐
│ Item │ Description        │ Qty │ Unit │ Unit Price│ Ext. Price │
├──────┼────────────────────┼─────┼──────┼───────────┼────────────┤
│ ...  │ ...                │ ... │ ...  │ ...       │ ...        │
└──────┴────────────────────┴─────┴──────┴───────────┴────────────┘

2.2 Technical Specifications
[specifications]

3. SUBMISSION REQUIREMENTS
Method: [submission_method]
Address: [submission_address]

3.1 Required Documents
[table]

4. TERMS & CONDITIONS
Payment: [payment_terms]
Insurance: [insurance_requirements]
Prevailing Wage: [Yes/No]
Bond Required: [Yes/No] ([bonding_amount])

5. PRE-BID CONFERENCE (if applicable)
...

6. EVALUATION CRITERIA (if applicable)
[table]

7. ADDITIONAL PROVISIONS (if applicable)
Safety Requirements:
  General: [...]
  Hot Work: [...]
  LOTO: [...]
  ...
Environmental: [...]
Liquidated Damages: [...]
Retainage: [...]
```

**Implementation details:**

- `_setup_styles(doc)` — Define custom styles: Title, Heading1, Heading2, BodyText, TableHeader, TableCell
- `_add_header(doc, data)` — Title block with RFQ number, dates, issuer info
- `_add_section(doc, heading, content)` — Numbered section with heading and body
- `_add_table(doc, field, rows)` — Formatted table from table-type field data
- `_add_compound_section(doc, field, data)` — Renders compound sub-fields as labeled paragraphs
- `_format_value(field, value)` — Format dates, currency, booleans for display
- `_should_include_section(field, data)` — Check conditional fields

**Font/formatting:**
- Title: 16pt, bold, navy (#1F4E79)
- Heading 1: 13pt, bold, navy
- Heading 2: 11pt, bold, dark gray
- Body: 10.5pt, Calibri
- Table headers: bold, white on navy background
- Table cells: 10pt
- Page margins: 1 inch all sides
- Section numbers: auto-incrementing

### D2: Test the document builder

**tests/test_doc_generator.py:**
- `test_generate_returns_document` — returns a `docx.Document` object
- `test_document_contains_rfq_title` — rfq_title appears in the doc text
- `test_document_contains_issuer` — issuer_name appears
- `test_document_contains_work_items_table` — doc has at least one table with work item headers
- `test_document_contains_required_docs_table` — table with "Document Name" header exists
- `test_conditional_section_included` — when bonding_required=True, bonding_amount appears
- `test_conditional_section_excluded` — when prebid_conference=False, prebid section absent
- `test_compound_section_rendered` — safety sub-fields appear as labeled content
- `test_optional_sections_only_when_data` — evaluation criteria only appears if data provided
- `test_document_saveable` — doc.save(BytesIO()) doesn't raise

```bash
pytest tests/test_doc_generator.py -v
```

### D3: Commit Phase D

```bash
git add -A
git commit -m "feat: add document builder — python-docx RFQ generation (#phase-4)

- generate_document() produces formatted Word doc from schema data
- Professional layout: title block, numbered sections, formatted tables
- Compound fields rendered as labeled sub-sections
- Conditional sections included/excluded based on data
- Custom styles: navy headers, formatted tables, consistent typography
- Full test coverage"
```

---

## PHASE E: BROWSER DOWNLOAD BRIDGE (Phase 5)

### E1: Update engine/file_bridge.py

The file exists but verify it has:
- `trigger_docx_download(doc, filename)` — full Pyodide JS bridge implementation
- `save_docx_local(doc, filename)` — fallback for local development
- `download_bytes(byte_data, filename, mime_type)` — generic version
- `generate_and_download(schema, data, filename=None)` — **NEW** high-level function that chains: validate → generate_document → trigger download (or save local). Returns the validation result so callers can check for errors.

### E2: Test

**tests/test_file_bridge.py:**
- `test_save_docx_local` — saves to temp file, file exists and is non-empty
- `test_generate_and_download_valid` — with valid data, returns ValidationResult.valid=True and produces bytes
- `test_generate_and_download_invalid` — with missing required fields, returns errors

```bash
pytest tests/test_file_bridge.py -v
```

### E3: Commit Phase E

```bash
git add -A
git commit -m "feat: update file bridge — high-level generate_and_download (#phase-5)"
```

---

## PHASE F: WORKBOOK BOOTSTRAP (Phase 6)

### F1: Create workbook/scripts.py

This is the xlwings Lite script that gets pasted into the add-in. It's the thin shell that bootstraps everything from GitHub.

```python
"""
docx_builder — xlwings Lite bootstrap script.
Paste this into the xlwings Lite add-in code editor.
"""
import xlwings as xw
from xlwings import script
import requests
import yaml
import io

# --- Configuration ---
GITHUB_BASE = "https://raw.githubusercontent.com/OWNER/docx_builder/main"
_cache = {}
_engine = {}

# --- Fetch helpers ---
def _fetch(path):
    url = f"{GITHUB_BASE}/{path}"
    if url not in _cache:
        _cache[url] = requests.get(url).text
    return _cache[url]

def _load_module(name):
    if name not in _engine:
        source = _fetch(f"engine/{name}.py")
        ns = {"__name__": f"engine.{name}"}
        exec(source, ns)
        _engine[name] = ns
    return _engine[name]

# --- Scripts ---
@script(button="[btn_init]Control!B5")
def initialize_sheets(book: xw.Book):
    """Fetch registry, populate dropdown, build data entry sheets."""
    # ... implementation using _fetch and _load_module

@script(button="[btn_generate]Control!B7")
def generate_document(book: xw.Book):
    """Read data, validate, build .docx, trigger download."""
    # ... implementation

@script(button="[btn_validate]Control!B9")
def validate_data(book: xw.Book):
    """Run validation only, show results in status area."""
    # ... implementation

@script(button="[btn_export]Control!B11")
def export_data_yaml(book: xw.Book):
    """Export data to YAML, copy to clipboard."""
    # ... implementation

@script(button="[btn_import]Control!B13")
def import_data_yaml(book: xw.Book):
    """Import YAML data from a staging cell."""
    # ... implementation

@script(button="[btn_llm]Control!B15")
def generate_llm_prompt(book: xw.Book):
    """Generate LLM fill-in prompt, copy to clipboard."""
    # ... implementation
```

Flesh out each script function fully. They should:
- Read schema selection from Control sheet
- Fetch schema from GitHub via `_fetch`
- Use `_load_module` to get engine functions
- Read/write data from/to the appropriate sheets
- Show status messages on the Control sheet
- Handle errors gracefully with user-visible messages

### F2: Create workbook/README.md

Instructions for setting up the workbook:
1. Install xlwings Lite from Office add-in store
2. Open a blank workbook
3. Create a "Control" sheet with the layout from ARCHITECTURE.md
4. Paste scripts.py into the xlwings Lite code editor
5. Set requirements: python-docx, docxtpl, pyyaml
6. Click Initialize

### F3: Update xlwings_lite/requirements.txt

Verify it contains: `python-docx`, `docxtpl`, `pyyaml` (one per line).

### F4: Commit Phase F

```bash
git add -A
git commit -m "feat: add workbook bootstrap — xlwings Lite scripts (#phase-6)

- Full xlwings Lite bootstrap script with 6 @script functions
- Initialize, Generate, Validate, Export, Import, LLM Prompt
- Fetches engine and schemas from GitHub at runtime
- Session caching for performance
- Workbook setup instructions"
```

---

## PHASE G: LOCAL CUSTOMIZATION & VALIDATION UX (Phase 7-8)

### G1: Add custom schema loading to workbook/scripts.py

Add two more scripts:

```python
@script(button="[btn_load_schema]Control!B17")
def load_custom_schema(book: xw.Book):
    """Read YAML from a staging cell and register as local schema."""
    # Read from a designated cell (e.g., Control!D20)
    # Call register_local_schema()
    # Refresh the schema dropdown
    # Show confirmation

@script(button="[btn_load_template]Control!B19")
def load_custom_template(book: xw.Book):
    """Read Python template source from staging cell."""
    # Similar pattern
```

### G2: Add validation display to workbook/scripts.py

Enhance `validate_data` script to:
- Run validation against schema
- Write errors to a "Validation" sheet (create if needed)
- Color-code: red for errors, yellow for warnings
- Show summary count on Control sheet
- Optionally highlight invalid cells on data sheets (if feasible in xlwings Lite)

### G3: Create engine/validation_display.py

Helper that formats validation results for Excel display:
- `format_errors_for_sheet(result) → list[list[str]]` — rows of [severity, field, message]
- `get_cell_highlights(result, schema) → dict[str, str]` — maps "sheet!cell" → color for invalid fields

### G4: Test

**tests/test_validation_display.py:**
- `test_format_errors` — errors produce rows with "ERROR" severity
- `test_format_warnings` — warnings produce rows with "WARNING" severity
- `test_empty_result` — valid result produces no rows

```bash
pytest tests/ -v
```

### G5: Commit Phase G

```bash
git add -A
git commit -m "feat: add local customization and validation UX (#phase-7-8)

- Custom schema/template loading via staging cells
- Validation display: error/warning sheet, color coding
- validation_display.py helper for formatting results
- Test coverage for validation display"
```

---

## PHASE H: FINALIZE AND SHIP

### H1: Run full test suite

```bash
pytest tests/ -v --tb=short
ruff check engine/ --fix
ruff format engine/
```

Fix anything broken. All tests must pass.

### H2: Update template_registry.py

Replace the stub with a real implementation that maps schema IDs to template builders in `engine/doc_generator.py`.

### H3: Create GitHub issues for future work

```bash
gh issue create --title "Phase 9: Contribution tooling — schema/template validation CLI" --body "CLI tool to validate schemas and templates before PR submission. Includes: schema lint, template dry-run, registry consistency check." --label enhancement
gh issue create --title "Phase 10: Template system v2 — docxtpl hosted templates" --body "Support file-based .docx templates via docxtpl, fetched from GitHub. Allows non-programmers to design templates in Word." --label enhancement
gh issue create --title "Add more schemas: Change Order, Bid Tabulation, Safety Plan" --body "Expand schema library beyond RFQ." --label enhancement,schema
gh issue create --title "Add workbook distribution — pre-built .xlsx with embedded scripts" --body "Create a downloadable workbook with Control sheet pre-configured." --label enhancement
```

### H4: Final documentation updates

**docs/DEVLOG.md** — Append a comprehensive dated entry covering everything built in this session: all phases completed, files created, decisions made.

**docs/PLAN.md** — Update to reflect:
- Phases 1-8: ✅ Complete
- Phase 9-10: 🔲 Planned (with issue links)
- Known limitations and future work

**docs/DECISIONS.md** — Append any new ADRs from this session (e.g., two-layer Excel builder design, programmatic template approach).

**ARCHITECTURE.md** — Update the build phases table to reflect completed phases.

### H5: Final commit and PR

```bash
git add -A
git commit -m "feat: complete build — all phases through production-ready

Phases completed:
- A: Project setup (tests, docs, CI, pyproject.toml)
- B: GitHub loader caching and offline fallback
- C: Excel builder (schema-driven sheet generation)
- D: Document builder (python-docx RFQ generation)
- E: Browser download bridge (generate-and-download pipeline)
- F: Workbook bootstrap (xlwings Lite scripts)
- G: Local customization and validation UX
- H: Finalization, documentation, future issues

All tests passing. Lint clean."

git push origin feature/complete-setup-and-build
gh pr create --title "feat: complete engine build — phases A through H" --body "Full build from project setup through production-ready workbook. See docs/DEVLOG.md for complete session summary."
```

### H6: Print final status

```bash
echo "=== FINAL STATUS ==="
echo ""
echo "Tests:"
pytest tests/ -v --tb=line 2>&1 | tail -20
echo ""
echo "Lint:"
ruff check engine/
echo ""
echo "Files:"
find . -type f ! -path './.git/*' ! -path '*__pycache__*' | wc -l
echo ""
echo "Issues:"
gh issue list
echo ""
echo "Done."
```

---

## CRITICAL RULES (apply to every step)

1. **Read ARCHITECTURE.md and CLAUDE.md before starting** — they define all conventions
2. **Do NOT modify** `.claude/`, `CLAUDE.md`, `ARCHITECTURE.md`, or `docs/DEV_INFRASTRUCTURE.md`
3. **Every Python module**: `from __future__ import annotations` at top
4. **Every public function**: type hints + Google-style docstrings
5. **Type hints**: `X | None` not `Optional[X]`, `list[str]` not `List[str]`
6. **Pyodide-compatible**: no filesystem in runtime paths, no C extensions, no threading
7. **Tests must pass before each commit** — never commit red
8. **Conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
9. **Feature branch**: all work on `feature/complete-setup-and-build`, never direct to main
10. **Update docs at the end**: DEVLOG, PLAN, DECISIONS reflect reality
11. **Check `git remote -v`** and use the actual repo URL in github_loader.py DEFAULT_GITHUB_BASE

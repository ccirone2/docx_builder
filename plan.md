# Refactoring Plan: Module Splits & Performance

## Overview

Four refactoring tasks to improve module cohesion and read performance.
Execution in two phases: Phase 1 (3 parallel tasks), Phase 2 (1 sequential task).

---

## Phase 1 — Parallel Tasks (no file conflicts)

### Task A: Consolidate `is_pyodide` duplication

**Problem:** `is_pyodide()` function in file_bridge.py duplicates `IS_PYODIDE` constant in config.py.

**Changes:**

1. **engine/file_bridge.py** — Remove `is_pyodide()` function (lines 24-26), add `from engine.config import IS_PYODIDE`, replace 3 call sites:
   - Line 41: `if is_pyodide():` → `if IS_PYODIDE:`
   - Line 58: `if is_pyodide():` → `if IS_PYODIDE:`
   - Line 168: `if is_pyodide():` → `if IS_PYODIDE:`

2. **No test changes needed** — test_config.py already tests `IS_PYODIDE`, and no tests import `is_pyodide()` from file_bridge.

**Risk:** None. Both implementations are identical (`sys.platform == "emscripten"`).

---

### Task B: Split `data_exchange.py` (621 lines) → `data_exchange.py` + `llm_helpers.py`

**Boundary:** Data round-trip (export/import) stays; LLM prompt generation moves out.

**data_exchange.py keeps (~315 lines):**
- YAML formatting: `_YAMLDumper`, `_str_representer`, `_none_representer`, `_to_yaml`
- Redaction: `REDACTED_TEXT`, `REDACTED_NUMBER`, `REDACTED_TABLE_TEXT`, `_redact_value`, `_redact_table_row`, `_redact_compound`
- Export: `export_snapshot` (PUBLIC), `_export_field_value`, `_group_key`, `_serialize_value`
- Import: `import_snapshot` (PUBLIC), `_deserialize_value`

Make these **importable by llm_helpers.py** (promote from `_private` to public or keep private and re-export):
- `_to_yaml` → keep private, used only internally... actually used by LLM prompt. Rename to `to_yaml` or have llm_helpers import the private name.
- `_redact_value`, `_redact_table_row`, `_redact_compound` — used by LLM render helpers.
- `_serialize_value` — used by `_format_existing_value` in LLM helpers.
- `REDACTED_TEXT`, `REDACTED_TABLE_TEXT` — constants, already module-level.

**Decision:** Keep the underscore-prefix names (they're internal to the engine package, not user-facing) and import them directly in llm_helpers.py. This is a sibling-module import within the same package.

**llm_helpers.py gets (~310 lines):**
```python
"""LLM prompt generation helpers for schema-driven data fill-in."""

from engine.schema_loader import FieldDef, FieldGroup, Schema
from engine.data_exchange import (
    _to_yaml,
    _redact_value,
    _redact_table_row,
    _redact_compound,
    _serialize_value,
    REDACTED_TEXT,
    REDACTED_TABLE_TEXT,
)
```
- `generate_llm_prompt` (PUBLIC)
- `_render_field_for_llm`
- `_render_table_for_llm`
- `_render_compound_for_llm`
- `_format_existing_value`
- `generate_schema_reference` (PUBLIC)

**Files to update:**

1. **engine/data_exchange.py** — Remove lines 314-621 (LLM functions). Keep everything else.
2. **engine/llm_helpers.py** — NEW file. Move LLM functions + imports from data_exchange.
3. **tests/test_data_exchange.py** — Change imports of `generate_llm_prompt` and `generate_schema_reference` to come from `engine.llm_helpers`.
4. **tests/test_edge_cases.py** — No change needed (only imports `_deserialize_value`, `export_snapshot`, `import_snapshot`).
5. **tests/test_integration.py** — No change needed (only imports `export_snapshot`, `import_snapshot`).

**Runner.py impact (deferred to Phase 2):**
- Add `"llm_helpers": ["schema_loader", "data_exchange"]` to `_MODULE_DEPS`
- In `generate_llm_prompt()` function (runner.py line 484): change `exchange = _load_module("data_exchange")` / `exchange["generate_llm_prompt"]` → `llm = _load_module("llm_helpers")` / `llm["generate_llm_prompt"]`

---

### Task C: 3-way split `excel_builder.py` (589 lines) + add `field_key`/`field_locations`

Combines the excel split with the field→location index (Task 4) since both touch the same file.

**excel_plan.py (~340 lines) — Pure planning logic:**
- Imports: `dataclass`, `Any`, config constants (`HEADER_COLOR`, etc.), `FieldDef`, `Schema`
- Dataclasses: `CellInstruction` (with new `field_key: str = ""`), `SheetPlan` (with new `field_locations`), `TablePlan`
- Sheet name helpers: `_truncate_sheet_name`, `_group_sheet_name`, `_table_sheet_name`, `_MAX_SHEET_NAME`
- Planning functions: `plan_sheets`, `plan_group_layout`, `_field_row_instructions`, `plan_table_layout`
- `plan_sheets()` populates `SheetPlan.field_locations` by scanning instructions for those with `field_key` set

**excel_control.py (~130 lines) — Control sheet layout:**
- Imports: `CellInstruction` from excel_plan, config constants
- `DEFAULT_GITHUB_BASE` constant
- `plan_control_sheet()` function (lines 170-282)

**excel_writer.py (~95 lines) — xlwings adapter:**
- Imports: `CellInstruction`, `SheetPlan` from excel_plan, `IS_PYODIDE` from config
- `build_sheets()` function
- `apply_cell()` function

**New fields on dataclasses:**

```python
@dataclass
class CellInstruction:
    # ... existing fields ...
    field_key: str = ""  # FieldDef.key for data-entry value cells

@dataclass
class SheetPlan:
    sheets: list[str]
    instructions: list[CellInstruction]
    field_locations: dict[str, tuple[str, int, int]] = field(default_factory=dict)
    # Maps field_key → (sheet_name, row, value_col) for O(1) reads
```

**Populating field_key in `_field_row_instructions()`:**

The value cell instruction (the one at `value_col`, currently line 399-410) gets `field_key=field.key`.

**Populating field_locations in `plan_sheets()`:**

After collecting all instructions, build the index:
```python
locations = {}
for instr in instructions:
    if instr.field_key:
        locations[instr.field_key] = (instr.sheet, instr.row, instr.col)
return SheetPlan(sheets=sheets, instructions=instructions, field_locations=locations)
```

**Files to update:**

1. **engine/excel_plan.py** — NEW. Dataclasses + planning functions from excel_builder.py.
2. **engine/excel_control.py** — NEW. `plan_control_sheet()` from excel_builder.py.
3. **engine/excel_writer.py** — NEW. `build_sheets()` + `apply_cell()` from excel_builder.py.
4. **engine/excel_builder.py** — DELETE (replaced by the 3 new files).
5. **tests/test_excel_builder.py** — Update imports: `from engine.excel_plan import ...`, add `from engine.excel_control import plan_control_sheet`. Add test for `field_locations` population.

**Runner.py impact (deferred to Phase 2):**
- Update `_MODULE_DEPS`:
  - Remove `"excel_builder"` key
  - Add `"excel_plan": ["config", "schema_loader"]`
  - Add `"excel_control": ["config", "excel_plan"]`
  - Add `"excel_writer": ["config", "excel_plan"]`
- Update all `_load_module("excel_builder")` calls to load appropriate new module
- Use `plan.field_locations` in `_read_field_value()` for O(1) lookups

---

## Phase 2 — Sequential Task (depends on all Phase 1 tasks)

### Task D: Update `workbook/runner.py` for all module splits + field index

All three Phase 1 tasks require coordinated runner.py changes. Doing them together avoids merge conflicts.

**Changes to `_MODULE_DEPS` (lines 32-42):**
```python
_MODULE_DEPS: dict[str, list[str]] = {
    "log": [],
    "config": [],
    "schema_loader": ["log"],
    "excel_plan": ["config", "schema_loader"],
    "excel_control": ["config", "excel_plan"],
    "excel_writer": ["config", "excel_plan"],
    "data_exchange": ["log", "schema_loader"],
    "llm_helpers": ["schema_loader", "data_exchange"],
    "doc_generator": ["log", "schema_loader"],
    "validation_ux": ["schema_loader"],
    "file_bridge": ["log"],
    "github_loader": ["log"],
}
```

**Update `init_workbook()` (line 330-332):**
```python
builder = _load_module("excel_plan")
plan = builder["plan_sheets"](schema)
writer = _load_module("excel_writer")
writer["build_sheets"](book, plan)
# Cache field_locations for later reads
_field_index.update(plan.field_locations)  # NEW
```

**Update `initialize_sheets()` (line 372-374):** Same pattern as init_workbook.

**Add module-level cache:**
```python
_field_index: dict[str, tuple[str, int, int]] = {}
```

**Rewrite `_read_field_value()` (lines 189-196):**
```python
def _read_field_value(book: Any, field: Any) -> Any:
    """Read a single field value using cached location or fallback scan."""
    loc = _field_index.get(field.key)
    if loc:
        sheet_name, row, col = loc
        if sheet_name in [s.name for s in book.sheets]:
            return book.sheets[sheet_name].range((row, col)).value

    # Fallback: scan (handles sheets built before index was cached)
    for sheet in book.sheets:
        for row in range(2, 100):
            cell_value = sheet.range((row, 1)).value
            if cell_value and str(cell_value).strip() == field.label:
                return sheet.range((row, 2)).value
    return None
```

**Update `generate_llm_prompt()` (line 484-485):**
```python
llm = _load_module("llm_helpers")
prompt = llm["generate_llm_prompt"](schema, existing_data=data, redact=True)
```

---

## Execution Order

```
Phase 1 (parallel, no file conflicts):
├── Task A: file_bridge.py is_pyodide consolidation
├── Task B: data_exchange.py → data_exchange.py + llm_helpers.py
└── Task C: excel_builder.py → excel_plan.py + excel_control.py + excel_writer.py + field index

Phase 2 (sequential, after Phase 1):
└── Task D: runner.py integration (all _MODULE_DEPS + field index cache)
```

## Post-Implementation

- Run `PYTHONPATH=. python -m pytest tests/ -v` — all 96+ tests must pass
- Run `ruff check engine/ --fix` and `ruff format engine/`
- Update `CLAUDE.md` Architecture Quick Reference with new module names
- Update `docs/ARCHITECTURE.md` file tree and module descriptions
- Append to `docs/DEVLOG.md`
- Update `docs/PLAN.md` maintenance table

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| A (is_pyodide) | None | Identical implementations |
| B (data_exchange split) | Low | No circular deps; private imports within package |
| C (excel_builder 3-way split) | Medium | Must update all import paths; runner.py dynamic loading |
| D (runner.py + field index) | Medium | Fallback scan ensures backward compat; index is optional optimization |

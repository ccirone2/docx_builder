# Development Plan

## Status: All Core Phases Complete

All 12 build phases (1, 1b, 2a, A–H) and 5 maintenance plans are done.
149 tests across 12 files, all passing, lint clean.
See `docs/DEVLOG.md` for detailed history of each phase.

## Recently Completed (2026-03-02)

- [x] Local development harness (`dev/` package): MockBook, local_runner,
      CLI harness, sample data — 50 new tests (ADR-010)
- [x] Sheet name prefixes removed from `_group_sheet_name()` and
      `_table_sheet_name()` in `engine/excel_plan.py`
- [x] Sheets appended in order via `after=book.sheets[-1]` in
      `engine/excel_writer.py`
- [x] Sheet1 auto-deletion in `dev/local_runner.py` and `workbook/runner.py`
- [x] Row height removed from `_field_row_instructions()` and `apply_cell()`
- [x] Sheet name sanitization bug fixed in `_truncate_sheet_name()`

## Backlog

- [ ] More schemas: Change Order, Bid Tabulation, Safety Plan
- [ ] Template system v2: docxtpl hosted templates
- [ ] Contribution tooling: schema/template validation CLI
- [ ] Workbook distribution: pre-built .xlsx with embedded scripts

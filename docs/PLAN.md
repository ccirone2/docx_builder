# Development Plan

## Status: Issue #15 Complete

**Issue:** [#15 — Replace YAML data exchange with SCN text format](https://github.com/ccirone2/docx_builder/issues/15)

All 12 build phases (1, 1b, 2a, A–H), 5 maintenance plans, issues #14 and #15 done.
216 tests across 14 files, all passing, lint clean.

---

## Issue #15 — Tasks (all complete)

- ✅ **15a**: Migrate `data_exchange.py` from YAML to SCN
- ✅ **15b**: Migrate `llm_helpers.py` to SCN format
- ✅ **15c**: Workbook, control sheet, and local runner renames
- ✅ **15d**: Documentation and cleanup

---

## Issue #14 — Tasks (all complete)

- ✅ **14a** (#16): SCN parser module — `engine/scn.py` + 44 tests
- ✅ **14b** (#17): Rewrite `excel_plan.py` for single-column SCN layout
- ✅ **14c** (#18): Update `excel_control.py` labels (DATA STAGING AREA)
- ✅ **14d** (#19): Replace cell-coordinate readers with SCN parser
- ✅ **14e** (#20): Integration testing + final cleanup

---

## Backlog

- [ ] More schemas: Change Order, Bid Tabulation, Safety Plan
- [ ] Template system v2: docxtpl hosted templates
- [ ] Contribution tooling: schema/template validation CLI
- [ ] Workbook distribution: pre-built .xlsx with embedded scripts

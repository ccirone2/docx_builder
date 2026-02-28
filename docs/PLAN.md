# Development Plan

## Current Phase: Phase A — Complete Build (all phases)

### Status: 🟡 In Progress

### Completed Phases

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| 1 | Schema system | ✅ Done | YAML parser, validator, compound fields |
| 1b | Data exchange | ✅ Done | YAML import/export, LLM prompts, redaction |
| 2a | GitHub loader | ✅ Done | Core fetch, local registration, resolution |
| 2a | Registry | ✅ Done | Master schema index |

### Active Build Phases

| Phase | Task | Status | Notes |
|-------|------|--------|-------|
| A | Project setup — pyproject.toml, docs, CI, tests | 🟡 In Progress | |
| B | GitHub loader — TTL caching, bundled fallback | 🔲 Planned | |
| C | Excel builder — schema-driven sheet generation | 🔲 Planned | |
| D | Document builder — python-docx RFQ generation | 🔲 Planned | |
| E | Browser download bridge — generate-and-download | 🔲 Planned | |
| F | Workbook bootstrap — xlwings Lite scripts | 🔲 Planned | |
| G | Local customization & validation UX | 🔲 Planned | |
| H | Finalization — full test pass, docs, issues | 🔲 Planned | |

### Backlog

- [ ] Phase 9: Contribution tooling — schema/template validation CLI
- [ ] Phase 10: Template system v2 — docxtpl hosted templates
- [ ] More schemas: Change Order, Bid Tabulation, Safety Plan
- [ ] Workbook distribution — pre-built .xlsx with embedded scripts

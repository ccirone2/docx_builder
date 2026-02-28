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

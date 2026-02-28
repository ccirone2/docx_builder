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

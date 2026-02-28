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

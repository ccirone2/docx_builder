# Implement Next Task

1. Read `docs/PLAN.md` and find the next uncompleted task
2. Read the corresponding GitHub issue for full context
3. Ensure you are on `develop`: `git checkout develop && git pull origin develop`
4. Create a feature branch: `git checkout -b feature/ISSUE-NUMBER-short-description`
5. Implement the task, following conventions in CLAUDE.md
6. Write or update tests for the changed code
7. Run tests: `PYTHONPATH=. python -m pytest tests/ -v`
8. Run lint: `ruff check engine/ dev/ --fix && ruff format engine/ dev/`
9. Update the task status in `docs/PLAN.md` to ✅
10. Commit with conventional format referencing the issue
11. Push and open a PR targeting `develop`: `gh pr create --base develop`
12. Update `docs/DEVLOG.md` with what was done

**Branching:** All feature branches start from `develop`. PRs target `develop`.
Only `develop` → `main` merges happen for stable releases.

**Worktree:** If running in a worktree (isolated agent), you are in a
temporary copy of the repo. Create your branch, commit, and push — the
worktree will be cleaned up automatically.

If $ARGUMENTS is provided, implement that specific task/issue instead.

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

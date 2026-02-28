# Contributing to docx_builder

Thank you for your interest in contributing! This project welcomes contributions
of all kinds: new schemas, document templates, bug fixes, and documentation.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/docx_builder.git
   cd docx_builder
   ```
3. **Install** development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

1. Make your changes
2. Run tests: `pytest tests/ -v`
3. Run linter: `ruff check engine/ --fix && ruff format engine/`
4. Commit with conventional commit messages (see below)
5. Push and create a Pull Request

## Commit Message Format

Use conventional commits:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code restructuring without behavior change
- `test:` — Adding or updating tests
- `chore:` — Build, tooling, or infrastructure changes

Always reference the relevant GitHub issue: `feat: add change order schema (#42)`

## Contributing a Schema

1. Create a new YAML file in `schemas/` following the format in
   [SCHEMA_AUTHORING.md](SCHEMA_AUTHORING.md)
2. Add an entry to `schemas/registry.yaml`
3. Write a matching document template in `templates/`
4. Test locally:
   ```bash
   PYTHONPATH=. python -c "
   from engine.schema_loader import load_schema
   s = load_schema('schemas/your_schema.yaml')
   print(f'{s.name}: {len(s.all_fields)} fields')
   "
   ```
5. Submit a PR

## PR Checklist

- [ ] Schema YAML parses without errors
- [ ] All required fields have sensible placeholders
- [ ] Template builds a valid .docx from sample data
- [ ] Schema and template are documented (description, field hints)
- [ ] No sensitive or proprietary data in defaults or examples
- [ ] Category assigned in `registry.yaml`
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Lint clean: `ruff check engine/`

## Code Conventions

- Python 3.11+, type hints on all function signatures
- Google-style docstrings on all public functions
- All engine code must be Pyodide-compatible (pure Python, no C extensions)
- Use dataclasses for structured data, not raw dicts
- No `print()` in library code (only in `if __name__ == "__main__"` blocks)
- Keep modules under 400 lines

## Reporting Issues

Use the GitHub issue templates:
- **Feature Request** — For new capabilities
- **Bug Report** — For problems in existing code
- **Schema Request** — For new document type schemas

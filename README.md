# docx_builder

Template-driven document generator for electric utility RFQs and other structured documents.

## Key Features

- **Schema-driven** — Define document structures in YAML. Fields, groups, validation, and formatting are all declared, not coded.
- **LLM-friendly data exchange** — Export/import YAML snapshots with per-field redaction for safe LLM collaboration.
- **Zero-install** — Runs entirely in-browser via xlwings Lite (Pyodide/WebAssembly). No Python install needed for end users.
- **Professional output** — Generates formatted Word `.docx` files with tables, conditional sections, and consistent typography.
- **Open source** — Add your own schemas and templates, or contribute them back to the community.

## How It Works

```
Excel Workbook (xlwings Lite)
        |
        v
Schema (YAML) --> Python Engine (Pyodide) --> Word .docx
        |
        v
GitHub (schemas, templates, engine code)
```

1. User opens an Excel workbook with the xlwings Lite add-in
2. Workbook fetches schemas and engine code from this GitHub repo
3. User selects a document type and fills in data on auto-generated sheets
4. Engine validates data, generates a Word document, and triggers a browser download

## Quickstart (Users)

1. Install the [xlwings Lite](https://www.xlwings.org/lite) add-in from the Office add-in store
2. Open a blank workbook
3. Create a "Control" sheet following the layout in the [workbook README](workbook/README.md)
4. Paste the bootstrap script into the xlwings Lite code editor
5. Click **Initialize** to load available document types

## Quickstart (Contributors)

```bash
git clone https://github.com/ccirone2/docx_builder.git
cd docx_builder
pip install -e ".[dev]"
pytest tests/ -v
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for the full contributor workflow.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, data flow, and technical decisions
- [docs/SCHEMA_AUTHORING.md](docs/SCHEMA_AUTHORING.md) — How to write a new schema
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — Contribution guidelines
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — End-user documentation

## License

[MIT](LICENSE)

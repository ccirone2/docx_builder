# RFQ Document Generator — Architecture
## Open Source · GitHub-Hosted · xlwings Lite

---

## Overview

An open-source, template-driven document generation system for the electric
utility industry. Users enter structured data in Excel via xlwings Lite
(no Python install needed), and the system generates professional Word `.docx`
files from schema-defined templates.

**Distribution model:** A public GitHub repo is the single source of truth for
all engine code, schemas, and document templates. The Excel workbook is a thin
shell that fetches everything from GitHub at runtime. Users can also create
custom schemas and templates in a local folder, which serves as a staging area
for contributions back to the repo.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                            │
│                  (public, single source of truth)                   │
│                                                                     │
│  ├── engine/              Python modules (fetched at runtime)       │
│  │   ├── schema_loader.py                                          │
│  │   ├── data_exchange.py                                          │
│  │   ├── doc_generator.py                                          │
│  │   ├── excel_builder.py                                          │
│  │   ├── file_bridge.py                                            │
│  │   ├── validation_ux.py                                          │
│  │   └── log.py                                                    │
│  │                                                                  │
│  ├── schemas/             Official schema definitions               │
│  │   ├── registry.yaml        ← master index of all schemas        │
│  │   ├── rfq_electric_utility.yaml                                 │
│  │   └── ...                  (future: change_order, etc.)         │
│  │                                                                  │
│  ├── workbook/            Thin-shell workbook + setup instructions  │
│  │   ├── loader.py            ← paste into xlwings Lite (stable)   │
│  │   ├── runner.py            ← fetched at runtime from GitHub     │
│  │   └── README.md                                                 │
│  │                                                                  │
│  └── docs/                User & contributor documentation          │
│      ├── CONTRIBUTING.md                                           │
│      ├── SCHEMA_AUTHORING.md                                       │
│      └── USER_GUIDE.md                                             │
│                                                                     │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      │  raw.githubusercontent.com (CORS-friendly)
                      │
        ┌─────────────┼──────────────────┐
        ▼                                ▼
┌───────────────────┐          ┌─────────────────────────┐
│  Excel Workbook   │          │  Local Custom Folder     │
│  (thin shell)     │          │  ~/Documents/docgen/     │
│                   │          │                           │
│  • xlwings Lite   │          │  ├── schemas/             │
│    add-in code    │          │  │   └── my_custom.yaml   │
│  • Control sheet  │          │  └── templates/            │
│  • Fetches engine │          │      └── my_custom.py     │
│    + schemas from │          │                           │
│    GitHub at      │◄─────────│  User points workbook    │
│    runtime        │  merge   │  to this folder via a    │
│                   │  into    │  config cell or env var   │
│                   │  schema  │                           │
│                   │  list    │  (contributed back to     │
│                   │          │   repo via PR)            │
└───────────────────┘          └─────────────────────────┘
```

---

## GitHub Repository Structure

```
docgen/
│
├── README.md                           # Project overview, quickstart
├── LICENSE                             # Open source license
│
├── engine/                             # Core Python engine
│   ├── __init__.py
│   ├── config.py                       # Settings, GitHub URLs, paths
│   ├── log.py                          # Timestamped logging helpers
│   ├── schema_loader.py                # Parse YAML → Schema objects
│   ├── data_exchange.py                # Import/export YAML, LLM prompts
│   ├── doc_generator.py                # Merge data → .docx in memory
│   ├── excel_builder.py                # Build data entry sheets from schema
│   ├── file_bridge.py                  # Pyodide → browser download
│   ├── validation_ux.py                # Color-coded validation reports
│   ├── template_registry.py            # Schema ↔ template mapping
│   └── github_loader.py               # Fetch files from GitHub + local
│
├── schemas/                            # Official schema definitions
│   ├── registry.yaml                   # Master index (see below)
│   ├── rfq_electric_utility.yaml
│   └── ...                             # (future: change_order, etc.)
│
├── workbook/                           # Thin-shell workbook bootstrap
│   ├── loader.py                       # Stable loader (paste into xlwings Lite)
│   ├── runner.py                       # Business logic (fetched at runtime)
│   └── README.md                       # Setup instructions
│
├── docs/
│   ├── CONTRIBUTING.md                 # How to contribute schemas/templates
│   ├── SCHEMA_AUTHORING.md             # How to write a new schema
│   └── USER_GUIDE.md                   # End-user documentation
│
└── tests/                              # Schema + engine tests (64 tests)
    ├── conftest.py                     # Shared fixtures
    ├── test_schema_loader.py
    ├── test_data_exchange.py
    ├── test_github_loader.py
    ├── test_excel_builder.py
    ├── test_doc_generator.py
    ├── test_file_bridge.py
    └── test_validation_ux.py
```

### Schema Registry (`schemas/registry.yaml`)

The registry is the master index that the workbook fetches to discover
available schemas. It enables the workbook to show a dropdown of document
types without hardcoding them.

```yaml
# schemas/registry.yaml — Master index of all official schemas
registry_version: "1.0"

schemas:
  - id: rfq_electric_utility
    name: "RFQ - Electric Utility Services"
    version: "1.0"
    schema_file: "rfq_electric_utility.yaml"
    template_file: "rfq_electric_utility.py"
    description: "Request for Quotation for contractor services"
    category: "Procurement"

  - id: change_order
    name: "Change Order"
    version: "1.0"
    schema_file: "change_order.yaml"
    template_file: "change_order.py"
    description: "Contract change order form"
    category: "Contract Management"

  # ... more schemas added over time
```

---

## Data Flow

### Startup / Schema Discovery

```
User opens workbook
        │
        ▼
xlwings Lite loads Python (Pyodide)
        │
        ▼
Fetch registry.yaml from GitHub ◄──── raw.githubusercontent.com/.../registry.yaml
        │
        ▼
Check for local custom folder ◄────── path from config cell / env var
        │
        ▼
Scan local schemas/ for *.yaml
        │
        ▼
Merge: official (GitHub) + custom (local)
        │
        ▼
Populate "Document Type" dropdown on Control sheet
```

### Document Generation

```
User selects document type → fills in data → clicks "Generate"
        │
        ▼
Fetch schema YAML from GitHub (or read from local) ◄── cached after first fetch
        │
        ▼
Read user data from Excel sheets
        │
        ▼
Validate data against schema
        │                              ┌─── Errors? → Display in status area
        ▼                              │
Fetch template module from GitHub ◄────┘
        │
        ▼
Execute template builder (python-docx) in Pyodide
        │
        ▼
.docx bytes in memory (BytesIO)
        │
        ▼
Browser download via JS bridge
```

---

## Local Custom Folder

Since Pyodide can't directly access the local filesystem, there are
two mechanisms for loading custom schemas/templates:

### Mechanism A: Clipboard Paste (Simplest, works everywhere)

1. User authors a `.yaml` schema file locally
2. Opens it in a text editor, copies the contents
3. Pastes into a designated cell or the xlwings Lite editor
4. The workbook parses it and adds it to the schema list

This is crude but works on all platforms with zero setup.

### Mechanism B: File Picker via Task Pane (Better UX)

xlwings Lite task pane can include an HTML file picker. The user clicks
"Load Custom Schema", selects a `.yaml` file, and the browser reads it
via the File API (no server needed).

```python
# In the task pane HTML:
# <input type="file" accept=".yaml,.yml" id="schema-picker">
#
# The file contents are passed to Python via the xlwings bridge.
```

### Mechanism C: GitHub Fork (Best for contributors)

Power users fork the repo, add their schema/template, and configure the
workbook to fetch from their fork URL instead of (or in addition to) the
main repo. When ready, they submit a PR.

```
Control Sheet:
  GitHub URL: https://raw.githubusercontent.com/YOURFORK/docx_builder/main/
```

### Mechanism D: Local Development Server (Advanced)

For active development, users can run a simple local HTTP server that
serves their custom folder and is CORS-friendly:

```bash
cd ~/Documents/docgen
python -m http.server 8080 --bind 127.0.0.1
```

Then configure the workbook to also check `http://localhost:8080/` for
schemas. This gives a full edit-save-reload development loop.

### Recommended Approach

For most users: **Mechanism B** (file picker) for one-off use, **Mechanism C**
(fork) for ongoing development. The workbook should support all four, with
GitHub as the default and local overrides layered on top.

---

## Source Resolution Order

When the workbook needs a schema or template, it checks these sources
in order, with the first match winning:

```
1. Local override (file picker / pasted / fork URL)
     ↓ not found
2. Cached version (from a previous fetch in this session)
     ↓ not found
3. GitHub main repo (raw.githubusercontent.com)
     ↓ fetch error
4. Bundled fallback (baked into the workbook for offline use)
```

This means:
- Local customizations always take precedence
- Official schemas auto-update from GitHub
- The workbook still works offline (with whatever was last cached or bundled)

---

## GitHub Loader Module

The `github_loader.py` module handles fetching and caching from GitHub:

```python
# engine/github_loader.py

import requests  # works in Pyodide

GITHUB_BASE = "https://raw.githubusercontent.com/ccirone2/docx_builder/main"

_cache = {}  # in-memory cache for the session


def fetch_text(path: str, base_url: str = GITHUB_BASE) -> str:
    """Fetch a text file from GitHub (with session caching)."""
    url = f"{base_url}/{path}"
    if url in _cache:
        return _cache[url]
    response = requests.get(url)
    response.raise_for_status()
    _cache[url] = response.text
    return response.text


def fetch_registry(base_url: str = GITHUB_BASE) -> dict:
    """Fetch and parse the schema registry."""
    text = fetch_text("schemas/registry.yaml", base_url)
    return yaml.safe_load(text)


def fetch_schema(schema_file: str, base_url: str = GITHUB_BASE) -> str:
    """Fetch a schema YAML file."""
    return fetch_text(f"schemas/{schema_file}", base_url)


def fetch_template(template_file: str, base_url: str = GITHUB_BASE) -> str:
    """Fetch a template Python module as text (for exec())."""
    return fetch_text(f"templates/{template_file}", base_url)
```

### Template Execution

Since templates are Python modules fetched as text, they're executed via
`exec()` in a controlled namespace:

```python
def load_template_builder(template_source: str) -> callable:
    """Load a template module and return its build_document() function."""
    namespace = {}
    exec(template_source, namespace)
    return namespace["build_document"]
```

This is safe in our context because:
- Templates come from the repo we control (or user's own fork)
- Pyodide is sandboxed in the browser anyway
- Users who load custom templates are doing so intentionally

---

## Contribution Workflow

### User develops a custom schema/template locally:

```
~/Documents/docgen/
├── schemas/
│   └── pole_inspection.yaml      # their new schema
└── templates/
    └── pole_inspection.py        # their new template
```

### They test it in the workbook via file picker or local server.

### When ready to contribute:

1. Fork the repo on GitHub
2. Add their files to `schemas/` and `templates/`
3. Add an entry to `schemas/registry.yaml`
4. Submit a pull request

### PR review checklist (documented in CONTRIBUTING.md):

- [ ] Schema YAML parses without errors
- [ ] All required fields have sensible defaults/placeholders
- [ ] Template builds a valid .docx from sample data
- [ ] Schema + template are documented (description, field hints)
- [ ] No sensitive/proprietary data in defaults or examples
- [ ] Category assigned in registry.yaml

---

## Workbook Design (Loader / Runner)

The workbook uses a two-layer architecture: a **stable loader** pasted
into xlwings Lite once, and a **runner** fetched from GitHub at runtime.

### What lives IN the workbook:

- **loader.py**: ~120 lines of stable bootstrap code pasted into the
  xlwings Lite code editor. Fetches the runner from GitHub and exposes
  `@xw.script` entry points. Rarely needs updating.
- **requirements.txt**: `pyyaml`, `python-docx`

### What lives OUTSIDE the workbook (fetched at runtime):

- **runner.py** — All business logic (fetched by the loader)
- Engine modules (schema_loader, data_exchange, doc_generator, etc.)
- Schema definitions (YAML files)
- Registry (master index)

### Architecture

```
loader.py (pasted once into xlwings Lite)
  └── fetches runner.py from GitHub
        └── fetches engine/*.py from GitHub
              └── fetches schemas/*.yaml from GitHub
```

The loader defines thin `@xw.script` entry points that delegate to the
runner. The runner handles engine loading with a dependency graph,
Control sheet creation via `init_workbook()`, and all data operations.

### One-Click Setup

Users paste `loader.py` and click **Init Workbook**. The runner's
`init_workbook()` function:
1. Fetches the schema registry from GitHub
2. Creates the Control sheet with labels, buttons, and config cells
3. Builds data entry sheets for the default document type

No manual sheet creation required.

### Updating

- **Runner/engine changes**: Automatic — reopen workbook or click
  "Reload Scripts" to re-fetch
- **New script buttons**: Only needed when adding new `@xw.script`
  entry points to loader.py (rare)

---

## Configuration

The Control sheet has a configuration area where users can customize
the GitHub source and enable local overrides:

```
Control Sheet Layout:
┌─────────────────────────────────────────────────────────┐
│  A                    │  B              │  C             │
├─────────────────────────────────────────────────────────┤
│  DOCUMENT GENERATOR   │                 │                │
│                       │                 │                │
│  Document Type:       │  [▼ dropdown]   │                │
│                       │                 │                │
│  [Initialize Sheets]  │  [Generate Doc] │  [Validate]    │
│                       │                 │                │
│  [Export Data (YAML)] │  [Import Data]  │  [LLM Prompt]  │
│                       │                 │                │
│  Status:              │  Ready          │                │
│                       │                 │                │
├─────────────────────────────────────────────────────────┤
│  CONFIGURATION        │                 │                │
│                       │                 │                │
│  GitHub Repo URL:     │  https://raw.githubusercontent   │
│                       │  .com/ccirone2/docx_builder/main          │
│                       │                 │                │
│  Custom Schemas:      │  (use file picker or paste YAML) │
│                       │                 │                │
│  [Load Custom Schema] │  [Load Custom Template]          │
│                       │                 │                │
│  Redact on Export:    │  ☑ Yes          │                │
└─────────────────────────────────────────────────────────┘
```

---

## Build Phases

| Phase | Component                  | Description                                    |
|-------|----------------------------|------------------------------------------------|
| ✅ 1  | Schema system              | YAML format + loader + validator + compound     |
| ✅ 1b | Data exchange              | YAML import/export + LLM prompt + redaction     |
| ✅ 2  | GitHub loader              | Fetch registry, schemas from GitHub + caching   |
| ✅ 3  | Excel builder              | Auto-generate data entry sheets from schema     |
| ✅ 4  | Document builder           | python-docx programmatic templates              |
| ✅ 5  | Browser download bridge    | Pyodide → JS file download                      |
| ✅ 6  | Workbook bootstrap         | Loader/runner architecture + @script wiring     |
| ✅ 7  | Local customization        | File picker, paste, fork URL support            |
| ✅ 8  | Validation UX              | Color-coded validation reports                   |
| 🔲 9  | Contribution tooling       | Schema/template validation CLI, PR template      |
| 🔲 10 | Template system v2         | docxtpl + hosted .docx templates (optional)      |

---

## Dependencies (all Pyodide-compatible)

| Package      | Wheel Type       | Purpose                              |
|--------------|------------------|--------------------------------------|
| `xlwings`    | pure Python      | Excel ↔ Python bridge (Lite add-in) |
| `pyyaml`     | Pyodide built-in | Schema parsing                       |
| `python-docx`| pure Python      | Word document generation             |
| `requests`   | Pyodide built-in | HTTP fetching from GitHub            |
| `docxtpl`    | pure Python      | Template-based doc generation (v2)   |
| `lxml`       | Pyodide built-in | XML processing (python-docx dep)     |
| `jinja2`     | pure Python      | Template rendering (docxtpl dep)     |

---

## Key Design Decisions

### Why GitHub raw URLs?

GitHub's `raw.githubusercontent.com` serves files with CORS headers, which
means Pyodide (running in a browser) can fetch them directly. No proxy,
no server, no CORS workaround needed. The entire system runs with zero
infrastructure cost — GitHub hosts the code, Pyodide runs it client-side.

### Why fetch at runtime vs. bake into the workbook?

- **Schemas and templates update independently of the workbook.** Adding a
  new document type doesn't require redistributing an Excel file.
- **The workbook stays tiny.** It's just a shell with a bootstrap script.
- **Users always get the latest schemas.** No version mismatch.
- **Offline still works** via session cache and optional bundled fallbacks.

### Why `exec()` for templates?

Templates are Python modules fetched as text strings (since we can't import
files from a URL). `exec()` runs them in a controlled namespace. This is
acceptable because:
- The code comes from a repo we control (or the user's own fork)
- Pyodide is already sandboxed in the browser
- Users who load custom code are doing so intentionally
- There's no escalation path from the browser sandbox to the OS

### Why a local folder instead of just GitHub?

- **Privacy** — Custom schemas may contain proprietary field structures
- **Speed** — No network round-trip during development
- **Iteration** — Edit-save-test loop without pushing to GitHub
- **Staging** — Validate locally before contributing via PR

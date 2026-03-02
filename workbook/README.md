# Workbook Setup Guide

## Prerequisites

- Microsoft Excel (desktop or web)
- [xlwings Lite](https://www.xlwings.org/lite) add-in installed from the Office add-in store

## Quick Start (3 steps)

### 1. Install xlwings Lite

Install the xlwings Lite add-in from the Microsoft Office add-in store.

### 2. Paste the Loader

1. Open a new Excel workbook
2. Open the xlwings Lite code editor (in the add-in panel)
3. Copy the contents of **`loader.py`** from this directory
4. Paste into the code editor
5. In the xlwings Lite `requirements.txt` tab, add:

```
pyyaml
python-docx
```

### 3. Click "Init Workbook"

Click the **Init Workbook** button in the xlwings panel. That's it! The system will:
1. Fetch the latest runner logic from GitHub
2. Create the Control sheet with all labels and formatting
3. Fetch the schema registry from GitHub
4. Build data entry sheets for the default document type

No manual sheet creation or cell positioning required.

## How It Works

The **loader** (`loader.py`) is a thin ~120-line bootstrap you paste once.
It fetches the **runner** (`runner.py`) from GitHub at runtime. All business
logic lives in the runner, so bug fixes and new features take effect
automatically — you never need to re-paste code.

```
loader.py (pasted once)
  └── fetches runner.py from GitHub
        └── fetches engine/*.py from GitHub
              └── fetches schemas/*.yaml from GitHub
```

### Updating

- **Runner/engine changes**: Automatic — just reopen the workbook
- **New script buttons**: Rare — only if a new @xw.script entry point is added
- **Force refresh**: Click "Reload Scripts" to re-fetch without reopening

## Usage

1. **Select** a document type from the dropdown
2. **Initialize** sheets for that document type
3. **Fill in** data on the auto-generated sheets
4. **Validate** to check for errors
5. **Generate** to create and download the Word document

## Data Exchange

- **Export**: Saves your data as YAML to the staging cell
- **Import**: Reads YAML from the staging cell into the sheets
- **LLM Prompt**: Generates a redacted prompt for AI assistance

## Custom Schemas

To use schemas from your own fork:
1. Change the GitHub URL in the Configuration section (D12)
2. Click Initialize to reload schemas

To paste a custom schema:
1. Paste the YAML into the staging cell (D20)
2. Click "Load Custom Schema"

## Alternative: Self-Contained Script

If you prefer a single file with no remote fetching, you can paste
`scripts.py` instead. This bundles all logic inline but must be
re-pasted whenever the code is updated.

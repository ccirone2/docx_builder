# Workbook Setup Guide

## Prerequisites

- Microsoft Excel (desktop or web)
- [xlwings Lite](https://www.xlwings.org/lite) add-in installed from the Office add-in store

## Setup Steps

### 1. Install xlwings Lite

Install the xlwings Lite add-in from the Microsoft Office add-in store.

### 2. Open a Blank Workbook

Create a new Excel workbook.

### 3. Create the Control Sheet

Create a sheet named **"Control"** with the following layout:

```
Row 1:  A: DOCUMENT GENERATOR
Row 3:  A: Document Type:        B: [dropdown area]     D: [status area]
Row 5:  A: [Initialize Sheets]
Row 7:  A: [Generate Document]
Row 9:  A: [Validate Data]
Row 11: A: [Export Data (YAML)]
Row 13: A: [Import Data (YAML)]
Row 15: A: [LLM Prompt]
Row 16: A: Redact on Export:     D: TRUE

Row 10: A: CONFIGURATION
Row 12: A: GitHub Repo URL:      D: https://raw.githubusercontent.com/ccirone2/docx_builder/main

Row 20: D: [YAML staging area - for import/export/LLM prompts]
```

### 4. Paste the Bootstrap Script

1. Open the xlwings Lite code editor (in the add-in panel)
2. Copy the contents of `scripts.py` from this directory
3. Paste into the code editor

### 5. Set Pyodide Requirements

In the xlwings Lite settings, add these packages:

```
python-docx
docxtpl
pyyaml
```

### 6. Initialize

Click the **Initialize Sheets** button. The workbook will:
1. Fetch the schema registry from GitHub
2. Show available document types in the dropdown
3. Build data entry sheets for the selected document type

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
1. Change the GitHub URL in the Configuration section
2. Click Initialize to reload schemas

To paste a custom schema:
1. Paste the YAML into the staging cell (D20)
2. Use the custom schema loading features (Phase G)

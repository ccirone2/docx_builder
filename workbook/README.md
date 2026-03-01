# Workbook Setup Guide

## Prerequisites

- Microsoft Excel (desktop or web)
- [xlwings Lite](https://www.xlwings.org/lite) add-in installed from the Office add-in store

## Quick Start (3 steps)

### 1. Install xlwings Lite

Install the xlwings Lite add-in from the Microsoft Office add-in store.

### 2. Paste the Script

1. Open a new Excel workbook
2. Open the xlwings Lite code editor (in the add-in panel)
3. Copy the contents of `scripts.py` from this directory
4. Paste into the code editor
5. In the xlwings Lite settings, add these packages:

```
python-docx
docxtpl
pyyaml
```

### 3. Click "Init Workbook"

Click the **Init Workbook** button in the xlwings panel. That's it! The system will:
1. Create the Control sheet with all labels and formatting
2. Set up the configuration area and YAML staging cell
3. Fetch the schema registry from GitHub
4. Build data entry sheets for the default document type

No manual sheet creation or cell positioning required.

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

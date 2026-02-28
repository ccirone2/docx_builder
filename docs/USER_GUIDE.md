# User Guide

## Overview

docx_builder generates professional Word documents from structured data entered in Excel.
It runs entirely in your browser using xlwings Lite -- no Python installation needed.

## Getting Started

### Prerequisites

- Microsoft Excel (desktop or web)
- xlwings Lite add-in installed from the Office add-in store

### Setup

1. Open a blank Excel workbook
2. Create a "Control" sheet with the required layout
3. Paste the bootstrap script into the xlwings Lite code editor
4. Set Pyodide requirements: `python-docx`, `docxtpl`, `pyyaml`

### Basic Workflow

1. Click **Initialize** to load available document types
2. Select a document type from the dropdown
3. Fill in data on the auto-generated sheets
4. Click **Validate** to check for errors
5. Click **Generate** to create the Word document

## Features

### Data Entry

- Required fields are marked with a red indicator
- Choice fields have dropdown menus
- Date fields accept YYYY-MM-DD format
- Table fields have pre-populated headers and optional default rows

### Data Exchange

- **Export** your data as YAML for backup or sharing
- **Import** previously exported YAML data
- **LLM Prompt** generates a safe prompt for AI assistance with redacted PII

### Custom Schemas

- Load custom schemas via file picker or clipboard paste
- Point to your own GitHub fork for custom schema repositories
- See [SCHEMA_AUTHORING.md](SCHEMA_AUTHORING.md) for creating schemas

## Troubleshooting

### Common Issues

- **Initialize fails**: Check your internet connection (schemas are fetched from GitHub)
- **Validation errors**: Review the Validation sheet for specific field issues
- **Generate fails**: Ensure all required fields are filled in

### Getting Help

- Open an issue at https://github.com/ccirone2/docx_builder/issues
- Check [ARCHITECTURE.md](../ARCHITECTURE.md) for technical details

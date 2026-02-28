# Schema Authoring Guide

This guide explains how to create YAML schema definitions for the docx_builder system.

## Schema Structure

Every schema YAML file has four top-level sections:

```yaml
schema:
  id: my_document_type
  name: "My Document Type"
  version: "1.0"
  template: "my_document_type.py"
  description: "Description of this document type"

core_fields:
  - group: "Group Name"
    fields:
      - key: field_key
        label: "Field Label"
        type: text
        required: true

optional_fields:
  - group: "Optional Group"
    fields:
      - key: optional_field
        label: "Optional Field"
        type: text

flexible_fields:
  enabled: true
  max_entries: 20
  label: "Additional Information"
```

## Field Types

| Type | Description | YAML Value | Python Type |
|------|-------------|------------|-------------|
| `text` | Single-line text | string | `str` |
| `multiline` | Multi-line text | string (block) | `str` |
| `date` | Date | YYYY-MM-DD | `str` |
| `number` | Numeric value | number | `float` |
| `currency` | Money amount | number | `float` |
| `choice` | Dropdown selection | string | `str` |
| `boolean` | Yes/No | true/false | `bool` |
| `table` | Tabular data | list of dicts | `list[dict]` |
| `compound` | Nested sub-fields | dict | `dict` |

## Field Properties

```yaml
- key: field_key           # Unique identifier (snake_case)
  label: "Field Label"     # Human-readable label
  type: text               # Field type (see above)
  required: true           # Whether the field must be filled
  placeholder: "hint"      # Hint text for the user
  default: "value"         # Default value
  redact: true             # Mask in redacted exports (for PII)
  choices:                 # For choice type only
    - "Option A"
    - "Option B"
  validation:              # Optional validation rules
    pattern: "^[A-Z]+"     # Regex pattern
  conditional_on:          # Show only when another field has a value
    field: other_field
    value: true
```

## Compound Fields

Compound fields group related sub-fields into a nested structure:

```yaml
- key: safety_requirements
  label: "Safety Requirements"
  type: compound
  fields:
    - key: general
      label: "General Safety"
      type: multiline
      placeholder: "General safety rules..."
    - key: ppe
      label: "PPE Requirements"
      type: multiline
```

In data, compound fields are represented as dicts:
```python
data = {
    "safety_requirements": {
        "general": "OSHA 10-hr required",
        "ppe": "FR clothing, hard hat",
    }
}
```

## Table Fields

Table fields define columnar data:

```yaml
- key: work_items
  label: "Work Items"
  type: table
  required: true
  columns:
    - key: description
      label: "Description"
      type: text
    - key: quantity
      label: "Qty"
      type: number
    - key: unit_price
      label: "Unit Price"
      type: currency
      redact: true          # Column-level redaction
  default_rows:             # Pre-populated rows (optional)
    - description: "Item 1"
      quantity: 1
      unit_price: 0
```

## Conditional Fields

Fields can be shown/hidden based on another field's value:

```yaml
- key: bonding_required
  label: "Bond Required?"
  type: boolean
  required: true

- key: bonding_amount
  label: "Bond Amount"
  type: text
  conditional_on:
    field: bonding_required
    value: true
```

## Redaction

Mark sensitive fields with `redact: true`:

```yaml
- key: issuer_name
  label: "Organization Name"
  type: text
  redact: true              # Will show [REDACTED] in LLM exports
```

For tables, redaction is per-column:
```yaml
columns:
  - key: unit_price
    label: "Unit Price"
    type: currency
    redact: true            # Column-level redaction
```

## Testing Your Schema

```bash
# Load and validate
PYTHONPATH=. python -c "
from engine.schema_loader import load_schema
s = load_schema('schemas/your_schema.yaml')
print(f'{s.name}: {len(s.all_fields)} fields, {len(s.get_required_fields())} required')
for g in s.all_groups:
    print(f'  [{g.section}] {g.name}: {len(g.fields)} fields')
"

# Test data exchange round-trip
PYTHONPATH=. python -c "
from engine.schema_loader import load_schema
from engine.data_exchange import export_snapshot, import_snapshot
s = load_schema('schemas/your_schema.yaml')
data = {'your_field': 'test'}
yaml_out = export_snapshot(s, data)
data_back, warnings = import_snapshot(s, yaml_out)
print('Round-trip OK' if data_back.get('your_field') == 'test' else 'FAILED')
"
```

## Registry Entry

After creating your schema, add it to `schemas/registry.yaml`:

```yaml
schemas:
  - id: your_schema_id
    name: "Your Schema Name"
    version: "1.0"
    schema_file: "your_schema.yaml"
    template_file: "your_schema.py"
    description: "What this document type is for"
    category: "Your Category"
    tags:
      - relevant
      - tags
```

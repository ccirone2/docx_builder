---
name: schema-system
description: >
  Schema system architecture and patterns for the docx_builder project.
  Apply when working with schema_loader.py, data_exchange.py, YAML
  schema files, or any code that touches field definitions.
---

# Schema System Patterns

## Field Type Handling
Every function that processes fields must handle ALL types:
- text, multiline, date, number, currency, choice, boolean
- table (list of dicts, with columns)
- compound (dict of sub-field values, with sub_fields)

## Compound Field Pattern
```python
if field.is_compound and isinstance(value, dict):
    for sf in (field.sub_fields or []):
        sv = value.get(sf.key)
        # process sub-field value
elif field.is_table and isinstance(value, list):
    for row in value:
        # process table row
else:
    # process scalar value
```

## Redaction Pattern
Always check three levels:
1. Field-level: `field.redact`
2. Table column-level: `col.get("redact", False)`
3. Compound sub-field-level: `sf.redact`

## Round-Trip Safety
Any data transformation must survive: export → import without loss.
Test with: export → import → re-export → compare.

## Schema Resolution Order
1. Local override (registered via file picker or paste)
2. Session cache
3. GitHub raw URL
4. Bundled fallback

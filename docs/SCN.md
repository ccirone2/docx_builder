# Single-Column Notation (SCN)

A structured data format designed for entry in a single spreadsheet column, one value per cell. It can also be used in plain text files, one value per line.

All parsed values are returned as strings. Type casting and validation are the responsibility of a separate layer.

**Implementation:** `engine/scn.py`

---

## Constructs

SCN has six constructs and one whitespace rule.

### 1. Section — `[name]`

Declares a top-level group. Everything that follows belongs to this section until the next `[section]` appears.

~~~
[database]
~~~

- Creates a top-level key in the output dict.
- Section names should be unique. If repeated, the existing section dict is reopened.
- Sections are optional. Keys declared before any section live at the root level.

### 2. Key — `key:`

Declares a named key. The value is **always on the next line**, never on the same line as the colon.

~~~
host:
localhost
~~~

**Dot notation** creates nested keys:

~~~
connection.host:
localhost
connection.port:
5432
~~~

This produces `{"connection": {"host": "localhost", "port": "5432"}}`.

Rules:
- Key names may contain letters, digits, underscores, and dots.
- The colon must be the last character on the line (no inline values).
- The very next non-empty, non-comment line is consumed as the value.
- All values are returned as strings.

### 3. List Item — `- value`

Appends a value to a list. Must follow a `key:` declaration (the key with no value becomes the list name).

~~~
colors:
- red
- green
- blue
~~~

Produces `{"colors": ["red", "green", "blue"]}`.

Rules:
- A dash followed by a space (`- `) starts each item.
- All items are returned as strings.
- Consecutive `- ` lines all append to the same list.
- The list ends when any other construct appears (a new key, section, `+name`, etc).

### 4. Dict List Entry — `+name`

Starts a new dict inside a list called `name`. The `+` and the list name appear alone on one line. Subsequent `key:`/value pairs populate that dict.

~~~
+users
name:
Alice
role:
admin
+users
name:
Bob
role:
viewer
~~~

Produces `{"users": [{"name": "Alice", "role": "admin"}, {"name": "Bob", "role": "viewer"}]}`.

Rules:
- The first `+name` encountered creates the list and its first dict entry.
- Each subsequent `+name` appends a new dict to that same list.
- All `key:`/value pairs between two `+name` lines belong to the current dict.
- Dict entries may contain nested keys (dot notation), scalar lists (`- `), and even nested dict lists (`+othername`).

**Nesting dict lists:** When `+inner` appears inside a `+outer` block, the `inner` list is created as a key within the current `outer` dict. When `+outer` appears again, the parser pops back up and starts a fresh outer dict (with its own separate inner lists).

### 5. Comment — `;;`

A line starting with `;;` is ignored entirely.

~~~
;; This is a comment
host:
localhost
;; This is also a comment
port:
5432
~~~

Rules:
- Only recognized when `;;` appears at the very start of the line (after stripping whitespace).
- Comments can appear anywhere: between sections, between keys and values, inside list blocks.
- There is no inline comment syntax. A `;;` appearing mid-value is treated as part of the value.
- When a `key:` is waiting for its value, the next non-empty line is always consumed as the value. The double semicolon was chosen to minimize conflict with legitimate values. Single characters like `#` conflict with Slack channels, hex colors, and markdown.

### 6. Empty Rows

Blank lines (empty cells) are ignored everywhere. Use them freely for visual grouping.

---

## Parsing Order

When the parser encounters a line, it checks in this order:

1. **Empty** — skip
2. **Plain value** — if a `key:` is pending and no list is active, consume the line as that key's value (this means a value can be anything, including text starting with `;;`, `[`, `+`, or `- `)
3. **Comment** — starts with `;;`, skip
4. **Section** — starts with `[`, ends with `]`
5. **Dict list entry** — starts with `+` (not `+ `)
6. **List item** — starts with `- `
7. **Key declaration** — ends with `:`

---

## Scope and Nesting Summary

| Construct | Creates | Scope ends when |
|---|---|---|
| `[section]` | top-level dict | next `[section]` |
| `key:` + value | key-value pair (string) | value consumed on next line |
| `key:` + `- ` | key holding a list of strings | next non-`- ` line |
| `+name` | list of dicts called `name` | next `+name` (same level) or `[section]` |
| `;; text` | nothing (ignored) | end of line |

---

## Parser Variants

SCN provides two parsers:

- **`parse(cells)`** — General-purpose parser. The next non-empty line after a `key:` is consumed as its value. Suitable for configuration files and serialized snapshots.
- **`parse_entry(cells)`** — Data-entry variant. Always consumes the very next cell after `key:`, even if empty. Designed for Excel data entry sheets where unfilled fields are empty cells.

---

## Serializer

**`serialize(data)`** converts a Python dict back to SCN lines:

- Root-level non-dict values are emitted as `key:` / value pairs
- Top-level dict values become `[section]` blocks
- Nested dicts use dot notation
- Lists of strings use `- item` syntax
- Lists of dicts use `+name` entries

---

## Examples

### Simple Key-Value Config

~~~
[settings]
app_name:
TaskTracker
version:
1.4
debug:
false
~~~

Result: `{"settings": {"app_name": "TaskTracker", "version": "1.4", "debug": "false"}}`

### Nested Keys with Dot Notation

~~~
[email]
smtp.host:
mail.example.com
smtp.port:
587
smtp.tls:
true
~~~

Result: `{"email": {"smtp": {"host": "mail.example.com", "port": "587", "tls": "true"}}}`

### Simple Lists

~~~
[project]
languages:
- python
- javascript
- sql
~~~

Result: `{"project": {"languages": ["python", "javascript", "sql"]}}`

### List of Dicts

~~~
+users
name:
Alice
role:
admin
+users
name:
Bob
role:
viewer
~~~

Result: `{"users": [{"name": "Alice", "role": "admin"}, {"name": "Bob", "role": "viewer"}]}`

### Nested Dict Lists

~~~
[school]
+classes
name:
Biology 101
+students
name:
Emma
grade:
A
+students
name:
James
grade:
B+
+classes
name:
History 201
+students
name:
Olivia
grade:
A-
~~~

Result: Two classes, first with 2 students, second with 1 student.

### Data Exchange Snapshot

This is the format used by `data_exchange.py` for exporting/importing user data:

~~~
[_meta]
schema_id:
rfq_electric_utility
schema_version:
1.0
export_type:
full_snapshot
redacted:
false

[issuing_organization]
issuer_name:
Ozark Electric Cooperative
issuer_address:
516 E Hwy 76, Branson MO

[scope_of_work]
scope_summary:
Replace 45 wooden poles with steel
+work_items
item_number:
1
description:
Set steel poles
quantity:
45
~~~

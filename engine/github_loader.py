"""
github_loader.py — Fetch schemas, templates, and registry from GitHub.

Handles the full source resolution chain:
  1. Local overrides (custom schemas loaded via file picker or paste)
  2. Session cache (avoid re-fetching within the same session)
  3. GitHub raw URLs (primary source for official content)
  4. Bundled fallback (optional, for offline use)

All fetching uses `requests`, which works in Pyodide.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field as dc_field
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default GitHub base URL. Users can override this on the Control sheet
# to point at their fork or a different branch.
DEFAULT_GITHUB_BASE = (
    "https://raw.githubusercontent.com/ccirone2/docx_builder/main"
)

# Paths within the repo
REGISTRY_PATH = "schemas/registry.yaml"
SCHEMAS_DIR = "schemas"
TEMPLATES_DIR = "templates"
ENGINE_DIR = "engine"


# ---------------------------------------------------------------------------
# Session cache
# ---------------------------------------------------------------------------

_cache: dict[str, str] = {}


def clear_cache():
    """Clear the session cache (e.g., after changing GitHub URL)."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Core fetch function
# ---------------------------------------------------------------------------

def fetch_text(path: str, base_url: str = DEFAULT_GITHUB_BASE) -> str | None:
    """
    Fetch a text file from GitHub raw URL with session caching.

    Args:
        path: Relative path within the repo (e.g., "schemas/registry.yaml").
        base_url: GitHub raw base URL.

    Returns:
        File contents as string, or None if fetch fails.
    """
    url = f"{base_url}/{path}"

    # Check cache first
    if url in _cache:
        return _cache[url]

    try:
        import requests
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        _cache[url] = response.text
        return response.text
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class RegistryEntry:
    """Single entry from the schema registry."""
    id: str
    name: str
    version: str
    schema_file: str
    template_file: str
    description: str = ""
    category: str = ""
    tags: list[str] = dc_field(default_factory=list)
    source: str = "github"  # "github", "local", or "bundled"


def fetch_registry(base_url: str = DEFAULT_GITHUB_BASE) -> list[RegistryEntry]:
    """
    Fetch and parse the schema registry from GitHub.

    Returns:
        List of RegistryEntry objects.
    """
    text = fetch_text(REGISTRY_PATH, base_url)
    if text is None:
        return []

    raw = yaml.safe_load(text)
    entries = []
    for s in raw.get("schemas", []):
        entries.append(RegistryEntry(
            id=s["id"],
            name=s["name"],
            version=s.get("version", "1.0"),
            schema_file=s["schema_file"],
            template_file=s.get("template_file", ""),
            description=s.get("description", ""),
            category=s.get("category", ""),
            tags=s.get("tags", []),
            source="github",
        ))
    return entries


# ---------------------------------------------------------------------------
# Schema fetching
# ---------------------------------------------------------------------------

def fetch_schema_yaml(
    schema_file: str, base_url: str = DEFAULT_GITHUB_BASE
) -> str | None:
    """Fetch a schema YAML file from GitHub."""
    return fetch_text(f"{SCHEMAS_DIR}/{schema_file}", base_url)


def fetch_schema(
    schema_file: str, base_url: str = DEFAULT_GITHUB_BASE
) -> Any:
    """Fetch and parse a schema YAML file. Returns raw dict."""
    text = fetch_schema_yaml(schema_file, base_url)
    if text is None:
        return None
    return yaml.safe_load(text)


# ---------------------------------------------------------------------------
# Template fetching
# ---------------------------------------------------------------------------

def fetch_template_source(
    template_file: str, base_url: str = DEFAULT_GITHUB_BASE
) -> str | None:
    """Fetch a template Python module as source text."""
    return fetch_text(f"{TEMPLATES_DIR}/{template_file}", base_url)


def load_template_builder(template_source: str) -> callable | None:
    """
    Execute a template module source and return its build_document() function.

    Template modules must define:
        def build_document(data: dict) -> Document:
            ...

    Returns:
        The build_document callable, or None if not found.
    """
    namespace = {"__name__": "__template__"}
    try:
        exec(template_source, namespace)
    except Exception as e:
        print(f"Template execution error: {e}")
        return None

    builder = namespace.get("build_document")
    if builder is None:
        print("Template module does not define build_document()")
    return builder


# ---------------------------------------------------------------------------
# Engine module fetching
# ---------------------------------------------------------------------------

_engine_modules: dict[str, dict] = {}

ENGINE_MODULE_NAMES = [
    "config",
    "schema_loader",
    "data_exchange",
    "doc_generator",
    "excel_builder",
    "file_bridge",
]


def fetch_engine(base_url: str = DEFAULT_GITHUB_BASE) -> dict[str, dict]:
    """
    Fetch all engine modules from GitHub and execute them.

    Returns:
        Dict of {module_name: namespace_dict}.
    """
    if _engine_modules:
        return _engine_modules

    for name in ENGINE_MODULE_NAMES:
        source = fetch_text(f"{ENGINE_DIR}/{name}.py", base_url)
        if source is None:
            print(f"Warning: Could not fetch engine/{name}.py")
            continue
        ns = {"__name__": f"engine.{name}"}
        try:
            exec(source, ns)
            _engine_modules[name] = ns
        except Exception as e:
            print(f"Error loading engine/{name}.py: {e}")

    return _engine_modules


# ---------------------------------------------------------------------------
# Local custom schemas
# ---------------------------------------------------------------------------

# Local overrides are stored in-memory. They're populated by:
#   - File picker (user selects a .yaml file)
#   - Clipboard paste (user pastes YAML text)
#   - Fork URL (workbook fetches from user's GitHub fork)

_local_schemas: dict[str, RegistryEntry] = {}
_local_schema_yaml: dict[str, str] = {}
_local_template_source: dict[str, str] = {}


def register_local_schema(
    yaml_text: str,
    template_source: str = "",
) -> RegistryEntry | None:
    """
    Register a custom schema from YAML text (e.g., from file picker or paste).

    Args:
        yaml_text: The raw YAML schema definition.
        template_source: Optional Python source for the document template.

    Returns:
        RegistryEntry for the registered schema, or None on parse error.
    """
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        print(f"Invalid YAML: {e}")
        return None

    meta = raw.get("schema", {})
    schema_id = meta.get("id")
    if not schema_id:
        print("Schema YAML missing 'schema.id'")
        return None

    entry = RegistryEntry(
        id=schema_id,
        name=meta.get("name", schema_id),
        version=meta.get("version", "custom"),
        schema_file=f"_local_{schema_id}.yaml",
        template_file=f"_local_{schema_id}.py" if template_source else "",
        description=meta.get("description", "Custom schema"),
        category="Custom",
        tags=["custom"],
        source="local",
    )

    _local_schemas[schema_id] = entry
    _local_schema_yaml[schema_id] = yaml_text
    if template_source:
        _local_template_source[schema_id] = template_source

    return entry


def get_local_schema_yaml(schema_id: str) -> str | None:
    """Get YAML text for a locally registered schema."""
    return _local_schema_yaml.get(schema_id)


def get_local_template_source(schema_id: str) -> str | None:
    """Get template Python source for a locally registered schema."""
    return _local_template_source.get(schema_id)


# ---------------------------------------------------------------------------
# Unified schema resolution
# ---------------------------------------------------------------------------

def resolve_all_schemas(
    base_url: str = DEFAULT_GITHUB_BASE,
) -> list[RegistryEntry]:
    """
    Get the complete list of available schemas, merging GitHub + local.

    Local schemas override GitHub schemas with the same ID.

    Returns:
        List of RegistryEntry, sorted by category then name.
    """
    # Start with GitHub registry
    github_entries = {e.id: e for e in fetch_registry(base_url)}

    # Overlay local schemas (local wins on ID collision)
    merged = {**github_entries, **_local_schemas}

    # Sort: custom first, then by category and name
    entries = sorted(
        merged.values(),
        key=lambda e: (0 if e.source == "local" else 1, e.category, e.name),
    )
    return entries


def resolve_schema_yaml(
    schema_id: str,
    registry: list[RegistryEntry] | None = None,
    base_url: str = DEFAULT_GITHUB_BASE,
) -> str | None:
    """
    Resolve and fetch schema YAML by ID, checking local then GitHub.

    Args:
        schema_id: The schema ID to look up.
        registry: Optional pre-fetched registry (avoids re-fetch).
        base_url: GitHub base URL.

    Returns:
        Schema YAML text, or None if not found.
    """
    # Check local first
    local_yaml = get_local_schema_yaml(schema_id)
    if local_yaml is not None:
        return local_yaml

    # Find in registry
    if registry is None:
        registry = resolve_all_schemas(base_url)
    for entry in registry:
        if entry.id == schema_id:
            return fetch_schema_yaml(entry.schema_file, base_url)

    return None


def resolve_template_source(
    schema_id: str,
    registry: list[RegistryEntry] | None = None,
    base_url: str = DEFAULT_GITHUB_BASE,
) -> str | None:
    """
    Resolve and fetch template source by schema ID, checking local then GitHub.
    """
    # Check local first
    local_src = get_local_template_source(schema_id)
    if local_src is not None:
        return local_src

    # Find in registry
    if registry is None:
        registry = resolve_all_schemas(base_url)
    for entry in registry:
        if entry.id == schema_id and entry.template_file:
            return fetch_template_source(entry.template_file, base_url)

    return None


# ---------------------------------------------------------------------------
# CLI testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== GitHub Loader Test ===")
    print()

    # Test local schema registration
    sample_yaml = """
schema:
  id: test_custom
  name: "Test Custom Schema"
  version: "0.1"
  template: ""
  description: "A test schema registered locally"
core_fields:
  - group: "Basic Info"
    fields:
      - key: title
        label: "Title"
        type: text
        required: true
"""
    entry = register_local_schema(sample_yaml)
    print(f"Registered local schema: {entry.id} ({entry.name})")
    print(f"  source: {entry.source}")
    print(f"  category: {entry.category}")

    # Test local retrieval
    retrieved = get_local_schema_yaml("test_custom")
    print(f"  retrieved YAML: {len(retrieved)} chars")

    # Show what resolve_all_schemas would return
    # (GitHub fetch will fail in this test env, but local should work)
    print()
    print("Resolving all schemas (local only in test env):")
    all_schemas = resolve_all_schemas()
    for s in all_schemas:
        print(f"  [{s.source}] {s.id}: {s.name}")

"""Tests for engine/github_loader.py."""
from __future__ import annotations

from engine.github_loader import (
    RegistryEntry,
    get_local_schema_yaml,
    register_local_schema,
    resolve_schema_yaml,
    _local_schemas,
    _local_schema_yaml,
    _local_template_source,
)


SAMPLE_SCHEMA_YAML = """\
schema:
  id: test_local
  name: "Test Local Schema"
  version: "0.1"
  template: ""
  description: "A test schema for unit tests"
core_fields:
  - group: "Basic Info"
    fields:
      - key: title
        label: "Title"
        type: text
        required: true
"""


def _clear_local_state() -> None:
    """Reset local schema state between tests."""
    _local_schemas.clear()
    _local_schema_yaml.clear()
    _local_template_source.clear()


def test_register_local() -> None:
    """register_local_schema returns RegistryEntry with source='local'."""
    _clear_local_state()
    entry = register_local_schema(SAMPLE_SCHEMA_YAML)
    assert entry is not None
    assert isinstance(entry, RegistryEntry)
    assert entry.source == "local"
    assert entry.id == "test_local"
    assert entry.name == "Test Local Schema"


def test_local_retrieval() -> None:
    """Registered schema YAML can be retrieved."""
    _clear_local_state()
    register_local_schema(SAMPLE_SCHEMA_YAML)
    yaml_text = get_local_schema_yaml("test_local")
    assert yaml_text is not None
    assert "test_local" in yaml_text


def test_local_overrides() -> None:
    """Local schema overrides GitHub schema with the same ID."""
    _clear_local_state()
    register_local_schema(SAMPLE_SCHEMA_YAML)
    # resolve_schema_yaml should find local first
    yaml_text = resolve_schema_yaml("test_local")
    assert yaml_text is not None
    assert "test_local" in yaml_text


def test_resolve_local() -> None:
    """resolve_schema_yaml returns local content for registered schema."""
    _clear_local_state()
    register_local_schema(SAMPLE_SCHEMA_YAML)
    result = resolve_schema_yaml("test_local")
    assert result is not None
    assert "Test Local Schema" in result


def test_invalid_yaml() -> None:
    """Invalid YAML returns None."""
    _clear_local_state()
    result = register_local_schema("{{invalid yaml: [")
    assert result is None


def test_missing_id() -> None:
    """YAML without schema.id returns None."""
    _clear_local_state()
    result = register_local_schema("schema:\n  name: 'No ID'\n")
    assert result is None

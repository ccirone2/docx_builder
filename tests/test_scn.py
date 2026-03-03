"""Tests for engine/scn.py — SCN parser, data-entry parser, and serializer."""
from __future__ import annotations

import pytest

from engine.scn import _get_nested, parse, parse_entry, serialize


# ---------------------------------------------------------------------------
# parse() — general-purpose parser
# ---------------------------------------------------------------------------


class TestParseBasics:
    def test_empty_input(self) -> None:
        assert parse([]) == {}

    def test_all_empty_cells(self) -> None:
        assert parse(["", None, "", None]) == {}

    def test_single_key_value(self) -> None:
        assert parse(["key:", "value"]) == {"key": "value"}

    def test_multiple_key_values(self) -> None:
        result = parse(["a:", "1", "b:", "2"])
        assert result == {"a": "1", "b": "2"}

    def test_none_cells_treated_as_empty(self) -> None:
        result = parse([None, "key:", None, "value"])
        assert result == {"key": "value"}

    def test_integer_cells_converted_to_string(self) -> None:
        result = parse(["count:", 42])
        assert result == {"count": "42"}


class TestParseSections:
    def test_single_section(self) -> None:
        result = parse(["[db]", "host:", "localhost"])
        assert result == {"db": {"host": "localhost"}}

    def test_multiple_sections(self) -> None:
        result = parse(["[a]", "x:", "1", "[b]", "y:", "2"])
        assert result == {"a": {"x": "1"}, "b": {"y": "2"}}

    def test_consecutive_sections(self) -> None:
        result = parse(["[a]", "[b]", "key:", "val"])
        assert result == {"a": {}, "b": {"key": "val"}}

    def test_reopen_section(self) -> None:
        result = parse(["[s]", "a:", "1", "[s]", "b:", "2"])
        assert result == {"s": {"a": "1", "b": "2"}}


class TestParseDotNotation:
    def test_simple_nested_key(self) -> None:
        result = parse(["conn.host:", "localhost"])
        assert result == {"conn": {"host": "localhost"}}

    def test_deep_nesting(self) -> None:
        result = parse(["a.b.c:", "deep"])
        assert result == {"a": {"b": {"c": "deep"}}}


class TestParseLists:
    def test_simple_list(self) -> None:
        result = parse(["colors:", "- red", "- green", "- blue"])
        assert result == {"colors": ["red", "green", "blue"]}

    def test_list_ends_at_new_key(self) -> None:
        result = parse(["list:", "- a", "- b", "other:", "val"])
        assert result == {"list": ["a", "b"], "other": "val"}


class TestParseDictLists:
    def test_simple_dict_list(self) -> None:
        result = parse(["+users", "name:", "Alice", "+users", "name:", "Bob"])
        assert result == {"users": [{"name": "Alice"}, {"name": "Bob"}]}

    def test_dict_list_multiple_keys(self) -> None:
        result = parse(["+items", "a:", "1", "b:", "2", "+items", "a:", "3"])
        assert result == {"items": [{"a": "1", "b": "2"}, {"a": "3"}]}


class TestParseComments:
    def test_comment_ignored(self) -> None:
        result = parse([";; this is a comment", "key:", "value"])
        assert result == {"key": "value"}

    def test_comment_between_key_values(self) -> None:
        # Comment after key: is consumed as value (per SCN spec)
        result = parse(["key:", ";; comment"])
        assert result == {"key": ";; comment"}


class TestParseValuePriority:
    """Values starting with constructs are consumed when a key is pending."""

    def test_value_starting_with_bracket(self) -> None:
        result = parse(["key:", "[not a section]"])
        assert result == {"key": "[not a section]"}

    def test_value_starting_with_plus(self) -> None:
        result = parse(["key:", "+not_a_list"])
        assert result == {"key": "+not_a_list"}

    def test_value_starting_with_semicolons(self) -> None:
        result = parse(["key:", ";; looks like comment"])
        assert result == {"key": ";; looks like comment"}


# ---------------------------------------------------------------------------
# parse_entry() — data-entry parser
# ---------------------------------------------------------------------------


class TestParseEntry:
    def test_empty_cell_after_key(self) -> None:
        """Empty cell after key: does NOT consume the next key."""
        result = parse_entry(["key1:", "", "key2:", "value2"])
        assert result.get("key1") is None
        assert result["key2"] == "value2"

    def test_comment_not_consumed_as_value(self) -> None:
        """Comment after key: is skipped, not consumed as value."""
        result = parse_entry(["key:", "", ";; label", "other:", "val"])
        assert result.get("key") is None
        assert result["other"] == "val"

    def test_sections(self) -> None:
        result = parse_entry(["[sec]", "k:", "v"])
        assert result == {"sec": {"k": "v"}}

    def test_dot_notation(self) -> None:
        result = parse_entry(["[sec]", "a.b:", "val"])
        assert result == {"sec": {"a": {"b": "val"}}}

    def test_list_values(self) -> None:
        result = parse_entry(["items:", "- a", "- b"])
        assert result == {"items": ["a", "b"]}

    def test_dict_list(self) -> None:
        result = parse_entry(["+rows", "k:", "v1", "+rows", "k:", "v2"])
        assert result == {"rows": [{"k": "v1"}, {"k": "v2"}]}

    def test_dict_list_with_empty_values(self) -> None:
        result = parse_entry(["+rows", "a:", "", "b:", "val", "+rows", "a:", "x"])
        assert result == {"rows": [{"b": "val"}, {"a": "x"}]}

    def test_full_data_entry_layout(self) -> None:
        """Simulate a real data entry sheet with sections, comments, keys."""
        cells = [
            "[Issuing Organization]",
            ";; Utility Name *",
            "issuer_name:",
            "Ozark Electric",
            ";; Address",
            "issuer_address:",
            "",
            "",
            "[RFQ Details]",
            ";; RFQ Number *",
            "rfq_number:",
            "RFQ-2026-042",
        ]
        result = parse_entry(cells)
        assert result["Issuing Organization"]["issuer_name"] == "Ozark Electric"
        assert result["Issuing Organization"].get("issuer_address") is None
        assert result["RFQ Details"]["rfq_number"] == "RFQ-2026-042"


# ---------------------------------------------------------------------------
# serialize()
# ---------------------------------------------------------------------------


class TestSerialize:
    def test_simple_key_value(self) -> None:
        lines = serialize({"key": "value"})
        assert lines == ["key:", "value"]

    def test_section(self) -> None:
        lines = serialize({"sec": {"k": "v"}})
        assert "[sec]" in lines
        assert "k:" in lines
        assert "v" in lines

    def test_list(self) -> None:
        lines = serialize({"colors": ["red", "green"]})
        assert lines == ["colors:", "- red", "- green"]

    def test_dict_list(self) -> None:
        lines = serialize({"items": [{"a": "1"}, {"a": "2"}]})
        assert lines.count("+items") == 2
        assert lines.count("a:") == 2

    def test_nested_dict_in_section(self) -> None:
        lines = serialize({"sec": {"conn": {"host": "localhost"}}})
        assert "[sec]" in lines
        assert "conn.host:" in lines
        assert "localhost" in lines


class TestSerializeParseRoundTrip:
    def test_flat_key_values(self) -> None:
        data = {"a": "1", "b": "2"}
        assert parse(serialize(data)) == data

    def test_section_with_values(self) -> None:
        data = {"sec": {"x": "10", "y": "20"}}
        assert parse(serialize(data)) == data

    def test_list_round_trip(self) -> None:
        data = {"items": ["a", "b", "c"]}
        assert parse(serialize(data)) == data

    def test_dict_list_round_trip(self) -> None:
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        assert parse(serialize(data)) == data

    def test_complex_round_trip(self) -> None:
        data = {
            "meta": {"version": "1.0"},
            "db": {"host": "localhost", "port": "5432"},
        }
        assert parse(serialize(data)) == data

    def test_nested_dict_round_trip(self) -> None:
        data = {"sec": {"conn": {"host": "local", "port": "80"}}}
        assert parse(serialize(data)) == data


# ---------------------------------------------------------------------------
# _get_nested helper
# ---------------------------------------------------------------------------


class TestGetNested:
    def test_simple_key(self) -> None:
        assert _get_nested({"a": "1"}, "a") == "1"

    def test_dot_key(self) -> None:
        assert _get_nested({"a": {"b": "2"}}, "a.b") == "2"

    def test_missing_key(self) -> None:
        assert _get_nested({"a": "1"}, "b") is None

    def test_missing_nested(self) -> None:
        assert _get_nested({"a": "1"}, "a.b") is None

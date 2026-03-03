"""harness.py — CLI entry point for the local development harness.

Subcommands:
  init      — Initialize a workbook (mock or Excel)
  inspect   — Show workbook state
  verify    — Compare workbook against expected schema layout
  fill      — Write sample data into workbook
  validate  — Run schema validation on workbook data
  generate  — Produce a .docx from workbook data

Usage:
  python dev/harness.py init [--schema ID] [--backend mock|excel] [--output PATH]
  python dev/harness.py inspect [--input PATH]
  python dev/harness.py verify [--schema ID] [--input PATH]
  python dev/harness.py fill [--schema ID] [--input PATH] [--output PATH]
  python dev/harness.py validate [--schema ID] [--input PATH]
  python dev/harness.py generate [--schema ID] [--input PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as `python dev/harness.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dev.local_runner import (  # noqa: E402
    fill_data,
    generate,
    init_workbook,
    load_default_schema,
    read_data,
    validate,
)
from dev.mock_book import MockBook  # noqa: E402

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_SCHEMA = "rfq_electric_utility"
_DEFAULT_MOCK_STATE = "output/workbook_state.json"
_DEFAULT_XLSX = "output/workbook.xlsx"


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """Resolve input/output paths based on backend."""
    backend = getattr(args, "backend", "mock")
    default_path = _DEFAULT_MOCK_STATE if backend == "mock" else _DEFAULT_XLSX

    input_path = Path(getattr(args, "input", None) or default_path)
    output_path = Path(getattr(args, "output", None) or default_path)
    return input_path, output_path


def _load_mock_book(path: Path) -> MockBook:
    """Load a MockBook from a JSON state file."""
    if not path.exists():
        print(f"Error: State file not found: {path}")  # noqa: T201
        sys.exit(1)
    return MockBook.from_json(path.read_text(encoding="utf-8"))


def _save_mock_book(book: MockBook, path: Path) -> None:
    """Save a MockBook to a JSON state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(book.to_json(), encoding="utf-8")
    print(f"Saved: {path}")  # noqa: T201


def _open_excel_book(path: Path | None = None) -> tuple:
    """Open an xlwings Book (requires xlwings + Excel installed).

    Returns:
        Tuple of (app, book) for cleanup.
    """
    try:
        import xlwings as xw
    except ImportError:
        print("Error: xlwings not installed. Install with: pip install xlwings")  # noqa: T201
        sys.exit(1)

    app = xw.App(visible=False)
    if path and path.exists():
        book = app.books.open(str(path))
    else:
        book = app.books.add()
    return app, book


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a workbook with Control + data entry sheets."""
    schema = load_default_schema(args.schema)
    _, output_path = _resolve_paths(args)

    if args.backend == "excel":
        app, book = _open_excel_book()
        try:
            init_workbook(book, schema, schema_name=schema.name)
            book.save(str(output_path))
            print(f"Initialized Excel workbook: {output_path}")  # noqa: T201
            print(f"  Sheets: {len(book.sheets)}")  # noqa: T201
        finally:
            app.quit()
    else:
        book = MockBook()
        init_workbook(book, schema, schema_name=schema.name)
        _save_mock_book(book, output_path)
        print(f"  Sheets: {len(book.sheets)}")  # noqa: T201


def cmd_inspect(args: argparse.Namespace) -> None:
    """Show workbook state."""
    input_path, _ = _resolve_paths(args)
    book = _load_mock_book(input_path)

    fmt = getattr(args, "format", "summary")
    if fmt == "json":
        print(book.to_json())  # noqa: T201
    else:
        print(f"Workbook: {input_path}")  # noqa: T201
        print(f"Sheets ({len(book.sheets)}):")  # noqa: T201
        for sheet in book.sheets:
            non_empty = sum(1 for c in sheet._cells.values() if c.value is not None)
            print(f"  {sheet.name}: {non_empty} cells with data")  # noqa: T201


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify workbook structure matches expected schema layout."""
    schema = load_default_schema(args.schema)
    input_path, _ = _resolve_paths(args)
    book = _load_mock_book(input_path)

    # Re-init a reference book to compare
    ref = MockBook()
    init_workbook(ref, schema, schema_name=schema.name)
    ref_sheets = {s.name for s in ref.sheets}
    actual_sheets = {s.name for s in book.sheets}

    ok = True

    # Check sheets
    missing = ref_sheets - actual_sheets
    extra = actual_sheets - ref_sheets
    if missing:
        print(f"FAIL: Missing sheets: {missing}")  # noqa: T201
        ok = False
    if extra:
        print(f"WARN: Extra sheets: {extra}")  # noqa: T201

    if ok:
        print(f"PASS: {len(actual_sheets)} sheets verified")  # noqa: T201
    else:
        sys.exit(1)


def cmd_fill(args: argparse.Namespace) -> None:
    """Fill sample data into workbook."""
    schema = load_default_schema(args.schema)
    input_path, output_path = _resolve_paths(args)
    book = _load_mock_book(input_path)

    from dev.sample_data import get_sample_data

    data = get_sample_data()
    fill_data(book, schema, data)
    _save_mock_book(book, output_path)
    print(f"  Filled {len(data)} fields")  # noqa: T201


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate data currently in the workbook."""
    schema = load_default_schema(args.schema)
    input_path, _ = _resolve_paths(args)
    book = _load_mock_book(input_path)

    data = read_data(book, schema)
    result = validate(schema, data)

    if result.valid:
        msg = "PASS: Validation passed"
        if result.warnings:
            msg += f" ({len(result.warnings)} warnings)"
        print(msg)  # noqa: T201
    else:
        print(f"FAIL: {len(result.errors)} errors")  # noqa: T201
        for err in result.errors:
            print(f"  - {err}")  # noqa: T201

    if result.warnings:
        for warn in result.warnings:
            print(f"  WARN: {warn}")  # noqa: T201

    if not result.valid:
        sys.exit(1)


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a .docx document from workbook data."""
    schema = load_default_schema(args.schema)
    input_path, _ = _resolve_paths(args)
    book = _load_mock_book(input_path)

    data = read_data(book, schema)
    out_path = Path(getattr(args, "output", None) or "output/generated.docx")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    generate(schema, data, output_path=out_path)
    print(f"Generated: {out_path}")  # noqa: T201


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Local development harness for docx_builder",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- init --
    p_init = sub.add_parser("init", help="Initialize workbook")
    p_init.add_argument("--schema", default=_DEFAULT_SCHEMA, help="Schema ID")
    p_init.add_argument("--backend", choices=["mock", "excel"], default="mock")
    p_init.add_argument("--output", help="Output path")

    # -- inspect --
    p_inspect = sub.add_parser("inspect", help="Inspect workbook state")
    p_inspect.add_argument("--input", help="Input state file")
    p_inspect.add_argument("--format", choices=["json", "summary"], default="summary")

    # -- verify --
    p_verify = sub.add_parser("verify", help="Verify workbook structure")
    p_verify.add_argument("--schema", default=_DEFAULT_SCHEMA)
    p_verify.add_argument("--input", help="Input state file")

    # -- fill --
    p_fill = sub.add_parser("fill", help="Fill sample data")
    p_fill.add_argument("--schema", default=_DEFAULT_SCHEMA)
    p_fill.add_argument("--input", help="Input state file")
    p_fill.add_argument("--output", help="Output state file")

    # -- validate --
    p_validate = sub.add_parser("validate", help="Validate workbook data")
    p_validate.add_argument("--schema", default=_DEFAULT_SCHEMA)
    p_validate.add_argument("--input", help="Input state file")

    # -- generate --
    p_generate = sub.add_parser("generate", help="Generate .docx")
    p_generate.add_argument("--schema", default=_DEFAULT_SCHEMA)
    p_generate.add_argument("--input", help="Input state file")
    p_generate.add_argument("--output", help="Output .docx path")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_COMMANDS = {
    "init": cmd_init,
    "inspect": cmd_inspect,
    "verify": cmd_verify,
    "fill": cmd_fill,
    "validate": cmd_validate,
    "generate": cmd_generate,
}


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()

"""docx_builder — Stable workbook loader for xlwings Lite.

Paste this into the xlwings Lite code editor.  It never needs
updating — all business logic is fetched from GitHub at runtime.

Setup:
  1. Paste this code into the xlwings Lite script editor
  2. In requirements.txt add: pyyaml, python-docx
  3. Click "Init Workbook" in the task pane
"""

import types

import xlwings as xw

# --- Configuration (change only if you forked the repo) ---
GITHUB_REPO = "ccirone2/docx_builder"
GITHUB_BRANCH = "main"
GITHUB_BASE = (
    "https://raw.githubusercontent.com/"
    + GITHUB_REPO + "/" + GITHUB_BRANCH
)

_runner_mod = None
_STATUS_CELL = "D3"


# --- Bootstrap helpers ---


def _fetch_text(url):
    """Fetch a URL as text (Pyodide-compatible)."""
    from pyodide.http import open_url  # type: ignore[import-untyped]

    return open_url(url).read()


def _resolve_base(book):
    """Read custom GitHub URL from Control!D12 if available."""
    global GITHUB_BASE  # noqa: PLW0603
    try:
        url = book.sheets["Control"]["D12"].value
        if url and str(url).strip().startswith("http"):
            new_base = str(url).strip().rstrip("/")
            if new_base != GITHUB_BASE:
                GITHUB_BASE = new_base
                _invalidate_runner()
    except Exception:
        pass


def _invalidate_runner():
    """Clear the cached runner so the next call re-fetches it."""
    global _runner_mod  # noqa: PLW0603
    _runner_mod = None


def _get_runner():
    """Fetch and cache the runner module from GitHub."""
    global _runner_mod  # noqa: PLW0603
    if _runner_mod is not None:
        return _runner_mod
    url = GITHUB_BASE + "/workbook/runner.py"
    code = _fetch_text(url)
    # Guard against 404 pages or non-Python responses
    if "def init_workbook" not in code:
        raise RuntimeError(
            "Could not load runner from: " + url + " — "
            "check that the GitHub URL (Control!D12) points "
            "to a valid repo and branch"
        )
    mod = types.ModuleType("docx_runner")
    exec(code, mod.__dict__)  # noqa: S102
    _runner_mod = mod
    return mod


def _show_error(book, exc):
    """Display an error on the Control sheet (creating it if needed)."""
    try:
        names = [s.name for s in book.sheets]
        if "Control" not in names:
            book.sheets.add("Control")
            c = book.sheets["Control"]
            c["A1"].value = "DOCUMENT GENERATOR"
        msg = str(exc)
        if not msg:
            # Some exceptions (e.g. NotImplementedError) have no message —
            # include the traceback to help diagnose
            import traceback
            msg = traceback.format_exc()
        book.sheets["Control"][_STATUS_CELL].value = (
            "Error [" + type(exc).__name__ + "]: " + msg
        )
    except Exception:
        pass


def _call(book, func_name):
    """Fetch runner and call func_name(book) with error handling."""
    try:
        _resolve_base(book)
        runner = _get_runner()
        fn = getattr(runner, func_name, None)
        if fn is None:
            raise AttributeError("Runner has no function '" + func_name + "'")
        fn(book)
    except Exception as e:
        _show_error(book, e)


# --- Script entry points (stable — add new ones only to expose new buttons) ---


@xw.script
def init_workbook(book: xw.Book) -> None:
    """One-click setup: paste loader, click this, done."""
    _call(book, "init_workbook")


@xw.script
def initialize_sheets(book: xw.Book) -> None:
    """Fetch schemas and rebuild data entry sheets."""
    _call(book, "initialize_sheets")


@xw.script
def generate_document(book: xw.Book) -> None:
    """Generate and download the Word document."""
    _call(book, "generate_document")


@xw.script
def validate_data(book: xw.Book) -> None:
    """Validate all data against the schema."""
    _call(book, "validate_data")


@xw.script
def export_data_yaml(book: xw.Book) -> None:
    """Export data to YAML in the staging cell."""
    _call(book, "export_data_yaml")


@xw.script
def import_data_yaml(book: xw.Book) -> None:
    """Import YAML data from the staging cell."""
    _call(book, "import_data_yaml")


@xw.script
def generate_llm_prompt(book: xw.Book) -> None:
    """Generate an LLM fill-in prompt."""
    _call(book, "generate_llm_prompt")


@xw.script
def load_custom_schema(book: xw.Book) -> None:
    """Load a custom schema from the staging cell."""
    _call(book, "load_custom_schema")


@xw.script
def load_custom_template(book: xw.Book) -> None:
    """Load a custom template from the staging cell."""
    _call(book, "load_custom_template")


@xw.script
def reload_scripts(book: xw.Book) -> None:
    """Force re-fetch all scripts from GitHub (clears cache)."""
    global _runner_mod  # noqa: PLW0603
    _runner_mod = None
    try:
        _get_runner()
        try:
            book.sheets["Control"][_STATUS_CELL].value = "Scripts reloaded from GitHub"
        except Exception:
            pass
    except Exception as e:
        _show_error(book, e)

"""
config.py — Central configuration for the RFQ Document Generator.

Designed to work in both:
  - Pyodide/xlwings Lite (no filesystem, browser-based)
  - Standard Python (for development and testing)
"""

import sys

# --- Runtime detection ---
IS_PYODIDE = sys.platform == "emscripten"

# --- Sheet names ---
# These are the Excel sheet names used by the system.
# The Control sheet is the user's main interface.
SHEET_CONTROL = "Control"
SHEET_DATA_ENTRY = "Data Entry"
SHEET_SCHEMA = "_Schema"  # hidden sheet with schema data
SHEET_TEMPLATE_CONFIG = "_Config"  # hidden sheet with template settings

# --- SCN formatting ---
SCN_COMMENT_PREFIX = ";;"

# --- Excel formatting ---
HEADER_COLOR = "#1F4E79"  # dark blue for group/section headers
HEADER_FONT_COLOR = "#FFFFFF"  # white text on headers
OPTIONAL_BG_COLOR = "#F2F2F2"  # light gray for optional sections
INPUT_CELL_BORDER_COLOR = "#B4C6E7"  # light blue border for input cells

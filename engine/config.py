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
SHEET_DATA_CORE = "Data - Core"
SHEET_DATA_OPTIONAL = "Data - Optional"
SHEET_DATA_FLEXIBLE = "Data - Flexible"
SHEET_TABLES_PREFIX = "Tables"  # e.g., "Tables - Work Items"
SHEET_SCHEMA = "_Schema"  # hidden sheet with schema data
SHEET_TEMPLATE_CONFIG = "_Config"  # hidden sheet with template settings

# --- Excel formatting ---
HEADER_COLOR = "#1F4E79"  # dark blue for group headers
HEADER_FONT_COLOR = "#FFFFFF"  # white text on headers
REQUIRED_INDICATOR_COLOR = "#C00000"  # red asterisk for required fields
OPTIONAL_BG_COLOR = "#F2F2F2"  # light gray for optional sections
INPUT_CELL_BORDER_COLOR = "#B4C6E7"  # light blue border for input cells

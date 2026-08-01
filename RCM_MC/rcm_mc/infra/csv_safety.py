"""Shared CSV formula-injection defang (Report-0270).

The house convention (B149) is that every CSV cell exported to a partner
gets neutralized so a spreadsheet app can't execute a leading ``=``/``+``/
``-``/``@``/tab/CR as a formula. That rule was implemented four different
ways across the codebase with divergent character sets — two of them
missed tab and CR, and one exhibit exporter (TAM/SAM) defanged nothing —
so this is the single source of truth every cell-level exporter now calls.

The DataFrame-level path (``server.RCMHandler._defang_csv_df`` used by the
big deal/notes/corpus exports) shares the same ``FORMULA_LEAD`` constant.
"""
from __future__ import annotations

from typing import Any, Iterable, List

# A cell whose first character is one of these is treated as a formula by
# Excel / Google Sheets / LibreOffice. Leading tab and CR also trigger it.
FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def defang_cell(value: Any) -> Any:
    """Prefix a single-quote if ``value`` is a string that would parse as a
    spreadsheet formula. Non-strings (and safe strings) pass through
    unchanged so numeric columns keep their type.
    """
    if isinstance(value, str) and value[:1] in FORMULA_LEAD:
        return "'" + value
    return value


def defang_row(row: Iterable[Any]) -> List[Any]:
    """Defang every cell in a row (for ``csv.writer.writerow``)."""
    return [defang_cell(c) for c in row]

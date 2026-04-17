"""HTML post-processors that apply UI polish across all generators.

Used by the run-output HTML (report.html), the partner brief, the portfolio
dashboard, and the exit memo so the visual treatment stays consistent
without each generator re-implementing the same rules.

Primary use case: **numeric auto-alignment**. Many tables — especially
pandas ``DataFrame.to_html()`` output — emit data cells without the
``class="num"`` marker that the shared CSS uses to right-align numbers
with tabular-nums. The result is jagged columns that hurt readability.

``polish_tables_in_html(html)`` walks every ``<table>`` in the document,
inspects each data ``<td>``, and marks numeric-looking cells so the
stylesheet can right-align them.

Detection is conservative: a cell counts as numeric when its visible
text (after stripping nested HTML tags + common money/percent/unit
formatting) parses as a float, or equals a placeholder like ``—``.
Everything else is left unchanged — the worst case is a missed cell,
never a misclassified one.
"""
from __future__ import annotations

import re
from typing import Match

# ── Detection primitives ───────────────────────────────────────────────────

# Characters that are "decoration" on a number — stripped before parsing.
# Kept conservative: $, %, commas, parens (accounting negatives), and the
# common money-suffix letters M/B/K. Also "x" for multiples (5.4x) and
# "pts"/"pp" for points. Whitespace stripped separately.
_NUMERIC_DECORATIONS = re.compile(r"[\$,%()MBKx]|pts|pp", flags=re.IGNORECASE)

# Cells that are just these placeholders count as numeric (they'd be
# right-aligned with other numbers in the same column).
_PLACEHOLDER_TOKENS = {"—", "-", "n/a", "na", "null", ""}


def _strip_tags(html_fragment: str) -> str:
    """Remove nested HTML tags so `<strong>$50M</strong>` → `$50M`."""
    return re.sub(r"<[^>]+>", "", html_fragment)


def _is_numeric_cell(inner_html: str) -> bool:
    """Does the cell's visible content read as a number?

    Returns False for cells with embedded form controls, images, or nested
    tables (those shouldn't be right-aligned).
    """
    # Veto early: cells with inputs / imgs / nested tables aren't numeric layout
    lowered = inner_html.lower()
    for tag in ("<input", "<select", "<img", "<table", "<ul", "<ol"):
        if tag in lowered:
            return False

    text = _strip_tags(inner_html).strip()
    if not text:
        return False
    if text.lower() in _PLACEHOLDER_TOKENS:
        return True

    # Strip common decorations, collapse whitespace, check if what's left
    # is a number. Handles: "$1,234.56", "+12.3%", "-$4.5M", "5.4x", "(1.2B)"
    cleaned = _NUMERIC_DECORATIONS.sub("", text).replace(" ", "").replace(",", "")
    # Accounting convention: (1,234) → -1234
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    # Allow leading "+"
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


# ── Cell-level class injection ─────────────────────────────────────────────

_CELL_RE = re.compile(
    r"<td"                          # opening td
    r"(?P<attrs>[^>]*)"             # attributes blob
    r">"
    r"(?P<inner>.*?)"               # cell content (non-greedy)
    r"</td>",
    flags=re.DOTALL,
)


def _merge_num_class(attrs: str) -> str:
    """Add ``num`` to the class list; preserve any existing classes."""
    m = re.search(r'class\s*=\s*"([^"]*)"', attrs)
    if m is None:
        return f'{attrs} class="num"'
    existing = m.group(1)
    classes = set(existing.split()) | {"num"}
    return attrs.replace(m.group(0), f'class="{" ".join(sorted(classes))}"')


def _polish_cell(match: Match) -> str:
    attrs = match.group("attrs")
    inner = match.group("inner")
    # Already tagged — leave alone
    if re.search(r'class\s*=\s*"[^"]*\bnum\b[^"]*"', attrs):
        return match.group(0)
    if not _is_numeric_cell(inner):
        return match.group(0)
    return f"<td{_merge_num_class(attrs)}>{inner}</td>"


# ── Table-level walk ───────────────────────────────────────────────────────

_TABLE_RE = re.compile(r"<table[^>]*>.*?</table>", flags=re.DOTALL | re.IGNORECASE)


def polish_tables_in_html(html: str) -> str:
    """Return ``html`` with numeric cells tagged ``class="num"`` in every table.

    Safe to call repeatedly (idempotent): cells already marked are skipped.
    Tables are isolated so cell regex doesn't leak across table boundaries
    or match non-table ``<td>`` look-alikes (there shouldn't be any, but
    the isolation keeps the rewrite local).
    """
    def _polish_table(table_match: Match) -> str:
        table_html = table_match.group(0)
        return _CELL_RE.sub(_polish_cell, table_html)

    return _TABLE_RE.sub(_polish_table, html)

"""Export helpers for CDD outputs.

Analysts live in spreadsheets and data rooms, so any metric result (a list of
flat dicts) should drop straight to CSV/JSON. Stdlib-only; defends against
CSV formula injection (a leading =,+,-,@ in a cell is a spreadsheet macro
vector) the same way the rest of the platform's exporters do.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Sequence

_FORMULA_PREFIX = ("=", "+", "-", "@")


def _defang(value: Any) -> Any:
    """Neutralize spreadsheet formula injection in string cells."""
    if isinstance(value, str) and value[:1] in _FORMULA_PREFIX:
        return "'" + value
    return value


def rows_to_csv(rows: Sequence[Dict[str, Any]], *, columns: Sequence[str] = None) -> str:
    """Render a list of flat dicts as CSV text. Nested values are JSON-encoded.
    Column order follows ``columns`` if given, else first-row key order."""
    rows = list(rows)
    if not rows:
        return ""
    cols = list(columns) if columns else list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        out = {}
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, (list, dict, tuple)):
                v = json.dumps(v, default=str)
            out[c] = _defang(v)
        w.writerow(out)
    return buf.getvalue()


def write_csv(rows: Sequence[Dict[str, Any]], path: str, **kw) -> int:
    text = rows_to_csv(rows, **kw)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return len(list(rows))


def write_json(obj: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)

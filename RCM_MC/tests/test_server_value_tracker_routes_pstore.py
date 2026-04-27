"""Regression test for the dispatcher-bypass cleanup at
server.py value-tracker POST routes (campaign target 4E,
loop 96).

Pre-loop-96 the two POST handlers in the value-tracker
surface — _route_value_tracker_record (line 5354) and
_route_value_tracker_freeze (line 5388) — each used a lazy
local ``import sqlite3 as _sql_vtr`` / `_sql_vtf` followed
by ``_sql_*.connect(self.config.db_path)`` and a manual
``con.commit(); con.close()`` pair.

After the cleanup, both handlers route through ``with
PortfolioStore(self.config.db_path).connect() as con:``
blocks. The explicit ``con.commit()`` is preserved inside
each with-block (PortfolioStore.connect() closes on exit but
does not auto-commit). The aliased lazy imports are gone.

Asserts:
  - Migration: the two handler blocks no longer contain
    ``_sql_vtr.connect(`` / ``_sql_vtf.connect(`` /
    ``import sqlite3 as _sql_vt*``.
  - PortfolioStore is referenced in both handler blocks.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "server.py"
)


def _route_block(text: str, route_def: str) -> str:
    """Extract a single _route_* method body from server.py.

    Locates `def <route_def>` and returns text up to the next
    `def ` at the same indent (4 spaces — class methods)."""
    start_re = re.compile(r"    def " + re.escape(route_def) + r"\(")
    m = start_re.search(text)
    if not m:
        return ""
    end_re = re.compile(r"\n    def ", re.M)
    end_m = end_re.search(text, m.end())
    end = end_m.start() if end_m else len(text)
    return text[m.start():end]


class ServerValueTrackerRoutesBypassTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _MODULE_PATH.read_text(encoding="utf-8")

    def test_record_handler_no_longer_uses_sql_vtr_alias(self) -> None:
        block = _route_block(self.text, "_route_value_tracker_record")
        self.assertGreater(
            len(block), 0,
            "could not locate _route_value_tracker_record",
        )
        self.assertNotIn(
            "_sql_vtr.connect(", block,
            "value-tracker record handler still calls _sql_vtr.connect(",
        )
        self.assertNotIn(
            "import sqlite3 as _sql_vtr", block,
            "value-tracker record handler still imports sqlite3 as _sql_vtr",
        )
        self.assertNotIn(
            "sqlite3.connect(", block,
            "value-tracker record handler still contains sqlite3.connect(",
        )

    def test_record_handler_routes_through_PortfolioStore(self) -> None:
        block = _route_block(self.text, "_route_value_tracker_record")
        self.assertIn(
            "PortfolioStore", block,
            "value-tracker record handler should reference PortfolioStore",
        )

    def test_freeze_handler_no_longer_uses_sql_vtf_alias(self) -> None:
        block = _route_block(self.text, "_route_value_tracker_freeze")
        self.assertGreater(
            len(block), 0,
            "could not locate _route_value_tracker_freeze",
        )
        self.assertNotIn(
            "_sql_vtf.connect(", block,
            "value-tracker freeze handler still calls _sql_vtf.connect(",
        )
        self.assertNotIn(
            "import sqlite3 as _sql_vtf", block,
            "value-tracker freeze handler still imports sqlite3 as _sql_vtf",
        )
        self.assertNotIn(
            "sqlite3.connect(", block,
            "value-tracker freeze handler still contains sqlite3.connect(",
        )

    def test_freeze_handler_routes_through_PortfolioStore(self) -> None:
        block = _route_block(self.text, "_route_value_tracker_freeze")
        self.assertIn(
            "PortfolioStore", block,
            "value-tracker freeze handler should reference PortfolioStore",
        )


if __name__ == "__main__":
    unittest.main()

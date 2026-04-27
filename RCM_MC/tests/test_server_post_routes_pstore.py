"""Regression test for the dispatcher-bypass cleanup at the
4 sister POST handlers in server.py (campaign target 4E,
loop 97).

Pre-loop-97, four POST handlers each used a lazy local
``import sqlite3 as _sql_*`` followed by
``_sql_*.connect(self.config.db_path) ... con.commit();
con.close()``:
  - _route_add_comment (POST /team/comment, _sql_cm)
  - _route_pipeline_add (POST /pipeline/add, _sql_pa)
  - _route_save_search (POST /pipeline/save-search, _sql_ss)
  - _route_pipeline_stage (POST /pipeline/stage/{ccn},
    _sql_ps)

After the cleanup, all four handlers route through ``with
PortfolioStore(self.config.db_path).connect() as con:``
blocks. Each preserves its explicit ``con.commit()`` inside
the with-block (PortfolioStore.connect() closes on exit but
does not auto-commit). The aliased lazy imports are gone.
The dead `import sqlite3` in _route_data_room_add (which
already routed through PortfolioStore in an earlier loop)
is also dropped.

Asserts (per handler):
  - No `_sql_*.connect(`, no `import sqlite3 as _sql_*`,
    no bare `sqlite3.connect(`.
  - PortfolioStore is referenced inside the handler block.

Plus a global server.py assertion: there are now 0
sqlite3 connect calls in the entire module.
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
    """Extract a single _route_* method body from server.py."""
    start_re = re.compile(r"    def " + re.escape(route_def) + r"\(")
    m = start_re.search(text)
    if not m:
        return ""
    end_re = re.compile(r"\n    def ", re.M)
    end_m = end_re.search(text, m.end())
    end = end_m.start() if end_m else len(text)
    return text[m.start():end]


_HANDLERS = (
    ("_route_add_comment", "_sql_cm"),
    ("_route_pipeline_add", "_sql_pa"),
    ("_route_save_search", "_sql_ss"),
    ("_route_pipeline_stage", "_sql_ps"),
)


class ServerPostRoutesBypassTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _MODULE_PATH.read_text(encoding="utf-8")

    def test_all_four_handlers_no_longer_use_sql_aliases(self) -> None:
        for route, alias in _HANDLERS:
            with self.subTest(route=route, alias=alias):
                block = _route_block(self.text, route)
                self.assertGreater(
                    len(block), 0,
                    f"could not locate {route}",
                )
                self.assertNotIn(
                    f"{alias}.connect(", block,
                    f"{route} still calls {alias}.connect(",
                )
                self.assertNotIn(
                    f"import sqlite3 as {alias}", block,
                    f"{route} still imports sqlite3 as {alias}",
                )
                self.assertNotIn(
                    "sqlite3.connect(", block,
                    f"{route} still contains sqlite3.connect(",
                )

    def test_all_four_handlers_route_through_PortfolioStore(self) -> None:
        for route, _ in _HANDLERS:
            with self.subTest(route=route):
                block = _route_block(self.text, route)
                self.assertIn(
                    "PortfolioStore", block,
                    f"{route} should reference PortfolioStore",
                )

    def test_data_room_add_dead_import_removed(self) -> None:
        """_route_data_room_add already routed through
        PortfolioStore but had a leftover `import sqlite3` from
        a prior migration. Dropped in this loop."""
        block = _route_block(self.text, "_route_data_room_add")
        self.assertGreater(
            len(block), 0,
            "could not locate _route_data_room_add",
        )
        self.assertNotIn(
            "import sqlite3", block,
            "_route_data_room_add still imports sqlite3 (dead import)",
        )

    def test_server_py_has_zero_sqlite3_connect_calls(self) -> None:
        """Module-wide pin: server.py is now sqlite3-connect-free.
        The MIME-type string `application/x-sqlite3` and a
        historical-context comment do not match the strict
        regex `sqlite3\\.connect\\(` (which requires the open
        paren)."""
        matches = re.findall(r"sqlite3\.connect\(", self.text)
        self.assertEqual(
            len(matches), 0,
            f"server.py contains {len(matches)} sqlite3.connect( "
            f"calls — the bypass sweep has regressed",
        )


if __name__ == "__main__":
    unittest.main()

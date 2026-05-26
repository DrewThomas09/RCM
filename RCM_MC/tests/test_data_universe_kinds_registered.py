"""Data-honesty guard: every data-universe kind used in a source/purpose header
must be registered in ck_data_universe's _DATA_UNIVERSE.

An unregistered kind makes ck_data_universe() return "" (fail-safe) — so the
intended provenance chip silently disappears from the page, a quiet honesty
regression (e.g. the licensed Industry / Market-Intel chips, fixed 2026-05).
This scans the source for `universe="..."` / `ck_data_universe("...")` usages
and asserts each is registered, so a new page can't ship a silent-empty chip.
"""
from __future__ import annotations

import pathlib
import re
import unittest

from rcm_mc.ui._chartis_kit import _DATA_UNIVERSE

_ROOT = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc"
_PAT = re.compile(r'(?:universe=|ck_data_universe\()\s*"([a-z][a-z-]*)"')


class DataUniverseKindsRegistered(unittest.TestCase):
    def test_all_used_kinds_are_registered(self):
        used: set[str] = set()
        for p in _ROOT.rglob("*.py"):
            used |= set(_PAT.findall(p.read_text(encoding="utf-8", errors="replace")))
        unregistered = sorted(k for k in used if k not in _DATA_UNIVERSE)
        self.assertEqual(
            unregistered, [],
            f"data-universe kind(s) used but not in _DATA_UNIVERSE — their "
            f"chip renders empty (silent provenance loss): {unregistered}. "
            f"Register them in ck_data_universe's _DATA_UNIVERSE.",
        )

    def test_registry_entries_render(self):
        from rcm_mc.ui._chartis_kit import ck_data_universe
        for kind in _DATA_UNIVERSE:
            self.assertTrue(ck_data_universe(kind),
                            f"registered kind {kind!r} renders empty")


if __name__ == "__main__":
    unittest.main()

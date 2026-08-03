"""MR1019 (Report-0267): infra/exports.py path-traversal defenses.

deal_id is partner-supplied (import routes accept it with only a
non-empty check) and lands in a filesystem path, so a ``../`` or
absolute deal_id could escape the exports root. These pin the
component validation and the base-containment backstop.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcm_mc.infra.exports import (
    canonical_deal_export_path,
    canonical_portfolio_export_path,
)


class TestDealIdTraversal(unittest.TestCase):
    def test_parent_traversal_deal_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            with self.assertRaises(ValueError):
                canonical_deal_export_path("../escaped", "x.html", base=base)
            # …and nothing was created outside the base.
            self.assertFalse((Path(tmp) / "escaped").exists())

    def test_absolute_deal_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            with self.assertRaises(ValueError):
                canonical_deal_export_path("/etc", "passwd", base=base)

    def test_separator_deal_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            for bad in ("a/b", "a\\b", ".."):
                with self.assertRaises(ValueError):
                    canonical_deal_export_path(bad, "x.html", base=base)

    def test_filename_separator_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            with self.assertRaises(ValueError):
                canonical_deal_export_path("D1", "../x.html", base=base)

    def test_timestamp_separator_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            with self.assertRaises(ValueError):
                canonical_deal_export_path(
                    "D1", "x.html", timestamp="../../TS", base=base)

    def test_legit_deal_id_stays_within_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            p = canonical_deal_export_path("deal-7", "report.html", base=base)
            self.assertTrue(p.resolve().is_relative_to(base.resolve()))
            self.assertTrue(p.parent.is_dir())

    def test_portfolio_path_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            p = canonical_portfolio_export_path("lp_q1.html", base=base)
            self.assertTrue(p.resolve().is_relative_to(base.resolve()))


class TestSameSecondCollision(unittest.TestCase):
    """MR1070: two exports of the same (deal_id, filename) with the
    default (auto) timestamp must not collide within one wall-clock
    second — the auto stamp is microsecond-precise."""

    def test_auto_timestamp_has_subsecond_component(self):
        from rcm_mc.infra.exports import _now_utc_iso
        ts = _now_utc_iso()
        # %Y-%m-%dT%H-%M-%S-%f → 6 dash groups after the date, ending in
        # the microsecond field (all-digit, len 6).
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{1,6}$")

    def test_back_to_back_exports_get_distinct_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "exports"
            seen = {
                str(canonical_deal_export_path("D1", "report.html", base=base))
                for _ in range(5)
            }
            self.assertGreater(len(seen), 1, "same-second exports collided")


if __name__ == "__main__":
    unittest.main()

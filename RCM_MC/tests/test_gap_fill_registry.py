"""Regression: the gap → fill-source registry + census.

Every red dot must map to a known remediation: a public source to pull (beds
from the CMS Provider of Services file; Medicaid days from the other Worksheet
S-3 columns) or an honest "artifact — flag, don't fill" when the filing itself
is inconsistent. See rcm_mc.data.gap_fill_registry.
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass

from rcm_mc.data.gap_fill_registry import (
    GAP_FILL_SOURCES, fill_source_for, gap_census, gap_report,
)


@dataclass
class _M:
    medicaid_day_pct: object = 0.2
    beds: object = 100
    net_to_gross_ratio: object = 0.4
    contractual_allowance_rate: object = 0.5
    operating_margin_on_npr: object = 0.05
    occupancy_rate: object = 0.8
    net_revenue_per_bed: object = 1e6
    opex_per_bed: object = 9e5


class RegistryShapeTests(unittest.TestCase):
    def test_every_entry_has_a_valid_kind(self):
        for g in GAP_FILL_SOURCES:
            self.assertIn(g.fill_kind, ("external", "reingest", "artifact"))

    def test_fillable_entries_name_a_source_and_url_or_dataset(self):
        for g in GAP_FILL_SOURCES:
            if g.fill_kind in ("external", "reingest"):
                self.assertTrue(g.source)
                self.assertTrue(g.dataset_id or g.url,
                                f"{g.field} fillable but no dataset_id/url")

    def test_artifact_entries_are_marked_not_fillable(self):
        for g in GAP_FILL_SOURCES:
            if g.fill_kind == "artifact":
                self.assertEqual(g.access, "n/a")
                self.assertIn("artifact", g.status)

    def test_lookup(self):
        self.assertEqual(fill_source_for("beds").dataset_id, "xubh-q36u")
        self.assertEqual(fill_source_for("net_to_gross_ratio").fill_kind, "artifact")
        self.assertIsNone(fill_source_for("not_a_field"))


class CensusTests(unittest.TestCase):
    def test_census_counts_none_and_nan_as_gaps(self):
        rows = [
            _M(),                                           # complete
            _M(medicaid_day_pct=None),                      # gap
            _M(medicaid_day_pct=float("nan"), beds=None),   # 2 gaps
        ]
        c = gap_census(rows)
        self.assertEqual(c["_total"], 3)
        self.assertEqual(c["medicaid_day_pct"], 2)
        self.assertEqual(c["beds"], 1)
        self.assertEqual(c["net_to_gross_ratio"], 0)

    def test_report_is_sorted_by_gap_count(self):
        rows = [_M(medicaid_day_pct=None), _M(medicaid_day_pct=None), _M(beds=None)]
        rep = gap_report(rows)
        gaps = [r["gaps"] for r in rep]
        self.assertEqual(gaps, sorted(gaps, reverse=True))
        self.assertEqual(rep[0]["field"], "medicaid_day_pct")


class CliGapsTests(unittest.TestCase):
    def test_data_gaps_command_runs(self):
        import io
        import contextlib
        from rcm_mc.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["data", "gaps"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("HCRIS metric gaps", out)
        self.assertIn("Medicaid day share", out)
        self.assertIn("ARTIFACT", out)


if __name__ == "__main__":
    unittest.main()

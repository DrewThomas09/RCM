"""Platform datasets for the Chart Builder.

Pins the registry (keys are URL surface — renames break bookmarks),
that every dataset builds a parseable all-numeric table from the
vendored CMS snapshots, the cross-sector aggregates, the ownership
bucketing, and the one-click strip on the builder page.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.chart_datasets import (
    _ownership_bucket, build_chart_dataset, list_chart_datasets,
)
from rcm_mc.ui.cdd_chart_kit import parse_table, render_cdd_chart
from rcm_mc.ui.chart_builder_page import render_chart_builder_page


class RegistryTests(unittest.TestCase):
    def test_menu_keys_stable(self):
        keys = [m["key"] for m in list_chart_datasets()]
        self.assertEqual(keys, [
            "providers_by_sector", "ownership_mix", "snf_beds_by_state",
            "dialysis_stations_by_state", "snf_by_state",
            "home_health_by_state", "hospice_by_state",
            "dialysis_by_state", "irf_by_state", "ltch_by_state"])

    def test_every_dataset_builds_a_clean_numeric_table(self):
        for m in list_chart_datasets():
            d = build_chart_dataset(m["key"])
            t = parse_table(d["tsv"])
            self.assertGreaterEqual(len(t["rows"]), 5, m["key"])
            for lab, vals in t["rows"]:
                self.assertTrue(lab, m["key"])
                for v in vals:
                    self.assertIsNotNone(v, f'{m["key"]}: {lab}')
                    self.assertGreaterEqual(v, 0, f'{m["key"]}: {lab}')
            # And the suggested chart renders it without sentinel leaks.
            svg = render_cdd_chart(d["chart"], t, {"title": d["label"]})
            self.assertTrue(svg.startswith("<svg"), m["key"])
            self.assertNotIn("None", svg, m["key"])

    def test_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            build_chart_dataset("nope")


class AggregationTests(unittest.TestCase):
    def test_state_table_other_row_completes_the_universe(self):
        # Top-12 + Other must sum to the sector's full provider count.
        d = build_chart_dataset("snf_by_state")
        t = parse_table(d["tsv"])
        total = sum(v[0] for _, v in t["rows"])
        sector = build_chart_dataset("providers_by_sector")
        snf_total = next(v[0] for lab, v in parse_table(sector["tsv"])["rows"]
                         if lab.startswith("SNF"))
        self.assertEqual(total, snf_total)
        self.assertTrue(t["rows"][-1][0].startswith("Other ("))
        # Ranked: first state ≥ second.
        self.assertGreaterEqual(t["rows"][0][1][0], t["rows"][1][1][0])

    def test_ownership_mix_covers_all_sectors_and_sums(self):
        d = build_chart_dataset("ownership_mix")
        t = parse_table(d["tsv"])
        self.assertEqual(len(t["rows"]), 6)
        self.assertEqual(t["headers"][1:], ["For-profit", "Non-profit",
                                            "Government", "Other"])
        sector = {lab: v[0] for lab, v in
                  parse_table(build_chart_dataset(
                      "providers_by_sector")["tsv"])["rows"]}
        for lab, vals in t["rows"]:
            self.assertEqual(sum(vals), sector[lab], lab)

    def test_ownership_bucketing_vocabularies(self):
        cases = {
            "For profit - Corporation": "For-profit",
            "PROPRIETARY": "For-profit",
            "For-Profit": "For-profit",
            "Non-profit": "Non-profit",
            "NON-PROFIT RELIGIOUS": "Non-profit",
            "Government - State": "Government",
            "": "Other",
        }
        for raw, want in cases.items():
            self.assertEqual(_ownership_bucket(raw), want, raw)

    def test_footnote_cites_snapshot(self):
        # Sector datasets carry the file's snapshot date; cross-sector
        # ones span six files so they stay date-less.
        self.assertIn("vendored snapshot,",
                      build_chart_dataset("snf_by_state")["footnote"])
        self.assertNotIn("snapshot,",
                         build_chart_dataset("ownership_mix")["footnote"])


class BuilderStripTests(unittest.TestCase):
    def test_strip_renders_with_one_click_links(self):
        h = render_chart_builder_page({})
        self.assertIn("PLATFORM DATA", h)
        self.assertIn("SNF / nursing homes providers by state", h)
        self.assertIn("Ownership mix by sector", h)
        # Links carry the finished table + source footnote.
        self.assertIn("footnote=Source", h)

    def test_loaded_dataset_flows_into_chart(self):
        d = build_chart_dataset("snf_by_state")
        h = render_chart_builder_page({
            "type": [d["chart"]], "title": [d["label"]],
            "footnote": [d["footnote"]], "data": [d["tsv"]]})
        self.assertIn("TX", h)
        self.assertIn(d["label"], h)


if __name__ == "__main__":
    unittest.main()

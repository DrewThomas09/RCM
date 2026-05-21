"""Pin for the specialty-mix concentration chart on the providers page.

The provider roster's specialty mix was a table only; a lead bar chart
now shows share-of-roster by taxonomy so the structural-fragility read
(one specialty dominating) lands first. Bars flag red ≥50% (the
CONCENTRATION threshold), amber ≥30%, teal otherwise.
"""
from __future__ import annotations

import sqlite3
import unittest

from rcm_mc.data_public.nppes_cache import ensure_table
from rcm_mc.ui.hospital_providers_page import render_hospital_providers

_CCN = "999999"


def _seed(con, taxonomies):
    ensure_table(con)
    for i, taxo in enumerate(taxonomies):
        con.execute(
            "INSERT INTO nppes_live_cache "
            "(ccn, npi, entity_type, name, taxonomy_code, taxonomy_label, "
            " primary_specialty, city, state, fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (_CCN, f"npi{i}", 1, f"Dr {i}", f"T{i}", taxo, taxo,
             "Tampa", "FL", "2026-01-01T00:00:00+00:00"),
        )
    con.commit()


class ProvidersMixChartTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")

    def tearDown(self):
        self.con.close()

    # A rendered bar emits an inline style; the CSS rule (.ck-bar-row-fill
    # { … }) does not — so this fragment uniquely marks a real bar.
    _BAR = 'ck-bar-row-fill" style="width:'

    def test_concentration_chart_renders_with_flagged_tone(self):
        # 4 Cardiology / 1 Radiology → Cardiology 80% → red concentration.
        _seed(self.con, ["Cardiology"] * 4 + ["Radiology"])
        html = render_hospital_providers(self.con, _CCN)
        self.assertIn(self._BAR, html)                      # real bars present
        self.assertIn("%;background:var(--sc-negative)", html)  # ≥50% red tone
        self.assertIn("Cardiology", html)

    def test_balanced_roster_no_concentration_tone(self):
        # 2/2/1 spread → top share 40% → amber, never red.
        _seed(self.con, ["A", "A", "B", "B", "C"])
        html = render_hospital_providers(self.con, _CCN)
        self.assertIn(self._BAR, html)
        # 40% top share is amber (warning), not the ≥50% red flag.
        self.assertIn("%;background:var(--sc-warning)", html)
        self.assertNotIn("%;background:var(--sc-negative)", html)

    def test_empty_roster_does_not_crash(self):
        ensure_table(self.con)
        html = render_hospital_providers(self.con, _CCN)
        self.assertIsInstance(html, str)
        self.assertNotIn(self._BAR, html)  # no real bars without providers


if __name__ == "__main__":
    unittest.main()

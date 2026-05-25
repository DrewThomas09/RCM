"""CMS clinician MIPS performance loader — real PII-free score distribution.

Data is the committed aggregate of CMS's PY2023 per-clinician MIPS file
(NPIs/names dropped at ingest). Tests assert the loader reads real distribution
stats, the band histogram is complete, scopes resolve, no PII leaked into the
committed aggregate, and the source is registered. No runtime network.
"""
from __future__ import annotations

import unittest

from rcm_mc.data import mips_data as m


class MipsLoaderTests(unittest.TestCase):
    def test_overall_summary_is_real_and_sane(self):
        s = m.mips_score_summary()
        self.assertGreater(s["n"], 100000)              # ~541k scored clinicians
        self.assertTrue(0 <= s["mean"] <= 100, s["mean"])
        self.assertTrue(0 <= s["median"] <= 100, s["median"])
        # Percentiles are monotonic.
        self.assertLessEqual(s["p10"], s["p25"])
        self.assertLessEqual(s["p25"], s["median"])
        self.assertLessEqual(s["median"], s["p75"])
        self.assertLessEqual(s["p75"], s["p90"])
        self.assertEqual(s["performance_year"], "2023")

    def test_scopes_and_missing_scope_safe(self):
        scopes = m.mips_scopes()
        self.assertIn("All clinicians", scopes)
        self.assertTrue(any(x.startswith("source:") for x in scopes))
        # APM clinicians outscore individuals — a real, known MIPS pattern.
        apm = m.mips_score_summary("source: apm")
        ind = m.mips_score_summary("source: individual")
        if apm and ind:
            self.assertGreater(apm["mean"], ind["mean"])
        # Unknown scope → empty dict, never a crash.
        self.assertEqual(m.mips_score_summary("source: nope"), {})

    def test_bands_complete_and_sum_to_100(self):
        bands = m.mips_score_bands()
        self.assertEqual(len(bands), 5)
        self.assertAlmostEqual(sum(b["pct"] for b in bands), 100.0, delta=0.5)
        self.assertEqual(sum(b["count"] for b in bands), m.mips_score_summary()["n"])

    def test_category_scores_present(self):
        cats = {c["category"] for c in m.mips_category_scores()}
        self.assertIn("Quality", cats)
        self.assertIn("Cost", cats)

    def test_no_pii_in_committed_aggregate(self):
        # The committed files must carry NO identifying columns.
        import csv
        from pathlib import Path
        vendor = Path(m.__file__).resolve().parent / "vendor" / "mips"
        banned = {"npi", "provider last name", "provider first name",
                  "org_pac_id", "facility name"}
        for f in vendor.glob("*.csv"):
            with f.open(newline="") as fh:
                header = next(csv.reader(fh))
            cols = {c.strip().lower() for c in header}
            self.assertEqual(cols & banned, set(), f"{f.name} leaked PII: {cols & banned}")

    def test_source_registered(self):
        src = m.mips_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "cms_mips_py2023")
        self.assertIn("public", str(src[0]["uploaded_or_public"]).lower())


if __name__ == "__main__":
    unittest.main()

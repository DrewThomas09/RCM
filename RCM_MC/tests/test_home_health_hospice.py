"""Home Health + Hospice loaders (Sector Intelligence Phase 2A).

Vendored CMS Provider Data Catalog snapshots; loaders read local files only
(no runtime network). Tests pin: files load nonzero rows, CCN/state
normalize, state summaries compute, provenance carried, and missing-file
behavior is safe.
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.data import home_health as hh
from rcm_mc.data import hospice as hos


class HomeHealthTests(unittest.TestCase):
    def test_providers_and_quality_load_nonzero(self):
        providers = hh.load_home_health_providers()
        quality = hh.load_home_health_quality()
        self.assertGreater(len(providers), 5000)        # ~12,392 agencies
        self.assertGreater(len(quality), 5000)

    def test_ccn_and_state_normalized(self):
        for ccn, p in list(hh.load_home_health_providers().items())[:50]:
            self.assertEqual(ccn, p.ccn)
            self.assertEqual(p.state, p.state.upper())
            self.assertTrue(p.source and p.source_date)  # provenance

    def test_state_summary(self):
        s = hh.load_home_health_summary_by_state()
        self.assertIn("CA", s)
        ca = s["CA"]
        self.assertGreater(ca["agencies"], 100)
        self.assertLessEqual(ca["rated"], ca["agencies"])
        # avg star, when present, is a sane 1-5 rating
        if ca["avg_star_rating"] is not None:
            self.assertTrue(1.0 <= ca["avg_star_rating"] <= 5.0)

    def test_providers_for_state_filtered(self):
        ca = hh.home_health_providers_for_state("ca")  # case-insensitive
        self.assertTrue(ca)
        self.assertTrue(all(p.state == "CA" for p in ca))


class HospiceTests(unittest.TestCase):
    def test_providers_and_quality_load_nonzero(self):
        self.assertGreater(len(hos.load_hospice_providers()), 3000)   # ~6,852
        self.assertGreater(len(hos.load_hospice_quality()), 3000)

    def test_state_summary_and_provenance(self):
        s = hos.load_hospice_summary_by_state()
        self.assertIn("TX", s)
        self.assertGreater(s["TX"]["hospices"], 50)
        p = next(iter(hos.load_hospice_providers().values()))
        self.assertTrue(p.source and p.source_date)

    def test_quality_metrics_keys(self):
        q = hos.load_hospice_quality()
        sample = next(iter(q.values()))
        for m in ("composite_process", "care_index_overall", "visits_last_days"):
            self.assertIn(m, sample)


class MissingFileSafetyTests(unittest.TestCase):
    def test_missing_files_return_empty_not_raise(self):
        # Point a loader at a nonexistent file; it must return {} (the page
        # then shows an honest empty state rather than crashing).
        for mod, attr in ((hh, "_PROVIDERS_CSV"), (hos, "_PROVIDERS_CSV")):
            loader = (hh.load_home_health_providers if mod is hh
                      else hos.load_hospice_providers)
            orig = getattr(mod, attr)
            loader.cache_clear()
            setattr(mod, attr, pathlib.Path("/nonexistent/_missing_.csv"))
            try:
                self.assertEqual(loader(), {})
            finally:
                setattr(mod, attr, orig)
                loader.cache_clear()


class NoNetworkImportTests(unittest.TestCase):
    def test_loaders_have_no_network_imports(self):
        for mod in ("home_health.py", "hospice.py"):
            src = (pathlib.Path(__file__).resolve().parents[1]
                   / "rcm_mc" / "data" / mod).read_text()
            for bad in ("import requests", "urllib.request", "http.client",
                        "socket", "geocoding.geo.census", "data.cms.gov"):
                self.assertNotIn(bad, src, f"{mod} must not do network I/O")


if __name__ == "__main__":
    unittest.main()

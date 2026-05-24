"""PR 10 — honest labels on 3 more seed-corpus aggregate pages.

Geo Market, Sector Correlation, and Specialty Benchmarks aggregate the
bundled illustrative deal corpus directly (`_SEED_DEALS` + `extended_seed*`),
not the live ingested-deals DB. Each must carry the 'Illustrative template'
marker. Companion to test_diligence_corpus_seed_labels.py.
"""
import importlib
import unittest

_PAGES = {
    "geo_market": "render_geo_market",
    "sector_correlation": "render_sector_correlation",
    "specialty_benchmarks": "render_specialty_benchmarks",
}


def _render(stem: str, fn_name: str) -> str:
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{stem}_page")
    fn = getattr(mod, fn_name)
    try:
        return fn()
    except TypeError:
        return fn({})


class TestCorpusSeedLabels2(unittest.TestCase):
    def test_each_page_carries_illustrative_marker(self):
        for stem, fn_name in _PAGES.items():
            with self.subTest(page=stem):
                html = _render(stem, fn_name)
                self.assertIn("ck-illus-note", html,
                              f"{stem} missing illustrative marker")
                self.assertIn("Illustrative template", html)


if __name__ == "__main__":
    unittest.main()

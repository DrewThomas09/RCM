"""PR 9 — honest labels on the seed-corpus aggregate pages.

These 6 pages aggregate the bundled illustrative deal corpus directly
(`data_public.deals_corpus._SEED_DEALS` + `extended_seed*`) — NOT the live
ingested-deals DB. They previously presented the seed aggregates as a "deal
corpus" / "every deal we've ingested" with no user-facing disclosure. Each
must now carry the calm 'Illustrative template' marker.
"""
import importlib
import unittest

_PAGES = {
    "payer_intel": "render_payer_intel",
    "sector_intel": "render_sector_intel",
    "find_comps": "render_find_comps",
    "sponsor_league": "render_sponsor_league",
    "deals_library": "render_deals_library",
    "sector_momentum": "render_sector_momentum",
}


def _render(stem: str, fn_name: str) -> str:
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{stem}_page")
    fn = getattr(mod, fn_name)
    try:
        return fn()
    except TypeError:
        return fn({})


class TestCorpusSeedLabels(unittest.TestCase):
    def test_each_page_carries_illustrative_marker(self):
        for stem, fn_name in _PAGES.items():
            with self.subTest(page=stem):
                html = _render(stem, fn_name)
                self.assertIn("ck-illus-note", html,
                              f"{stem} missing illustrative marker")
                self.assertIn("Illustrative template", html)

    def test_deals_library_drops_misleading_ingested_claim(self):
        html = _render("deals_library", "render_deals_library")
        # The intro previously claimed "Every deal we've ingested" — false for
        # the seed corpus. Must be gone.
        self.assertNotIn("Every deal we've ingested", html)


if __name__ == "__main__":
    unittest.main()

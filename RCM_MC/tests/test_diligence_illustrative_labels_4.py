"""PR 7 — illustrative-label batch 4.

These 13 data_public analyzer pages delegate to compute modules with NO
real-data source (no DB, loader, CMS, or HCRIS reads) — they are pure
calculators over user inputs + hardcoded benchmark constants. Each must
carry the honest 'Illustrative template' marker so a partner never mistakes
the realistic-looking output for this portfolio's sourced, live data.
"""
import importlib
import unittest


# stem -> render-fn arg style ('params' takes a dict, 'none' takes nothing)
_PAGES = {
    "lbo_stress": "params",
    "peer_valuation": "params",
    "growth_runway": "params",
    "rollup_economics": "params",
    "reinvestment": "params",
    "concentration_risk": "none",
    "antitrust_screener": "params",
    "bolton_analyzer": "params",
    "cap_structure": "params",
    "deal_postmortem": "params",
    "platform_maturity": "params",
    "redflag_scanner": "params",
    "tax_structure": "params",
}


def _render(stem: str, style: str) -> str:
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{stem}_page")
    fn = next(getattr(mod, n) for n in dir(mod) if n.startswith("render"))
    return fn() if style == "none" else fn({})


class TestIllustrativeLabelsBatch4(unittest.TestCase):
    def test_each_page_carries_illustrative_marker(self):
        for stem, style in _PAGES.items():
            with self.subTest(page=stem):
                html = _render(stem, style)
                self.assertIn("ck-illus-note", html,
                              f"{stem} missing illustrative marker")
                self.assertIn("Illustrative template", html)


if __name__ == "__main__":
    unittest.main()

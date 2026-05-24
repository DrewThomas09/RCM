"""PR 7 — illustrative-label batch 4.

These 13 data_public analyzer pages delegate to compute modules with NO
real-data source (no DB, loader, CMS, or HCRIS reads) — they are pure
calculators over user inputs + hardcoded benchmark constants. Each must
carry the honest 'Illustrative template' marker so a partner never mistakes
the realistic-looking output for this portfolio's sourced, live data.
"""
import importlib
import unittest


# stem -> (render-fn name, arg style: 'params' takes a dict, 'none' takes nothing)
_PAGES = {
    "lbo_stress": ("render_lbo_stress", "params"),
    "peer_valuation": ("render_peer_valuation", "params"),
    "growth_runway": ("render_growth_runway", "params"),
    "rollup_economics": ("render_rollup_economics", "params"),
    "reinvestment": ("render_reinvestment", "params"),
    "concentration_risk": ("render_concentration_risk", "none"),
    "antitrust_screener": ("render_antitrust_screener", "params"),
    "bolton_analyzer": ("render_bolton_analyzer", "params"),
    "cap_structure": ("render_cap_structure", "params"),
    "deal_postmortem": ("render_deal_postmortem", "params"),
    "platform_maturity": ("render_platform_maturity", "params"),
    "redflag_scanner": ("render_redflag_scanner", "params"),
    "tax_structure": ("render_tax_structure", "params"),
    # batch 4b — non-`body` first-arg calculators
    "exit_multiple": ("render_exit_multiple", "params"),
    "value_creation": ("render_value_creation", "params"),
    "covenant_monitor": ("render_covenant_monitor", "params"),
    "underwriting_model": ("render_underwriting_model", "params"),
    "multiple_decomp": ("render_multiple_decomp", "params"),
    "capital_efficiency": ("render_capital_efficiency", "params"),
    "acq_timing": ("render_acq_timing", "params"),
    "qoe_analyzer": ("render_qoe_analyzer", "params"),
    "exit_readiness": ("render_exit_readiness", "params"),
}


def _render(stem: str, spec) -> str:
    fn_name, style = spec
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{stem}_page")
    fn = getattr(mod, fn_name)
    return fn() if style == "none" else fn({})


class TestIllustrativeLabelsBatch4(unittest.TestCase):
    def test_each_page_carries_illustrative_marker(self):
        for stem, spec in _PAGES.items():
            with self.subTest(page=stem):
                html = _render(stem, spec)
                self.assertIn("ck-illus-note", html,
                              f"{stem} missing illustrative marker")
                self.assertIn("Illustrative template", html)


if __name__ == "__main__":
    unittest.main()

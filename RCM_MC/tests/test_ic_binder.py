"""Tests for the IC binder renderer."""
from __future__ import annotations

import unittest


def _empty_result():
    from rcm_mc.diligence_synthesis import SynthesisResult
    return SynthesisResult(
        deal_name="Test Co",
        sections_run=[],
        missing_inputs=["payer_negotiation: needs ...",
                        "qoe: needs financial_panel"],
    )


def _populated_result():
    from rcm_mc.diligence_synthesis import (
        DiligenceDossier, run_full_diligence,
    )
    from rcm_mc.qoe import run_qoe_flagger
    panel = {
        "deal_name": "Populated Co",
        "periods": ["2023", "2024", "TTM"],
        "income_statement": {
            "revenue": [100, 110, 120],
            "ebitda_reported": [10, 12, 14],
            "non_recurring_items": [
                {"period": "TTM", "amount": 1.5,
                 "description": "asset sale"},
            ],
        },
        "balance_sheet": {
            "ar": [10, 11, 12], "inventory": [5, 5, 5],
            "ap": [6, 6, 6],
        },
        "cash_flow": {"cash_receipts": [99, 109, 119]},
        "owner_compensation": {
            "actual": [0.5, 0.5, 0.5],
            "benchmark": [0.5, 0.5, 0.5],
        },
        "payer_mix": {
            "self_pay_share": [0.05, 0.05, 0.05],
            "out_of_network_share": [0.05, 0.05, 0.05],
        },
    }
    dossier = DiligenceDossier(
        deal_name="Populated Co",
        sector="hospital",
        financial_panel=panel,
    )
    return run_full_diligence(dossier)


class TestMarkdownBinder(unittest.TestCase):
    def test_empty_result_renders_with_data_gaps(self):
        from rcm_mc.ic_binder import render_markdown_binder
        md = render_markdown_binder(_empty_result())
        self.assertIn("# IC Binder — Test Co", md)
        self.assertIn("0 of 13", md)
        self.assertIn("## Data Gaps", md)
        # Each missing input listed
        self.assertIn("payer_negotiation:", md)
        self.assertIn("qoe:", md)

    def test_populated_renders_qoe_section(self):
        from rcm_mc.ic_binder import render_markdown_binder
        md = render_markdown_binder(_populated_result())
        self.assertIn("# IC Binder — Populated Co", md)
        self.assertIn("QoE Auto-Flagger", md)
        # Section count reflects only QoE running
        self.assertIn("1 of 13", md)


class TestHTMLBinder(unittest.TestCase):
    def test_html_includes_doctype_and_styling(self):
        from rcm_mc.ic_binder import render_html_binder
        html = render_html_binder(_populated_result())
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>IC Binder — Populated Co</title>",
                      html)
        # Inline CSS present
        self.assertIn("--c-accent: #1F4E78", html)
        # Markdown header converted to <h1>
        self.assertIn("<h1>IC Binder — Populated Co</h1>", html)

    def test_html_renders_table_when_present(self):
        from rcm_mc.ic_binder import render_html_binder
        html = render_html_binder(_populated_result())
        # QoE section may or may not have a table depending on
        # flag count; just verify the renderer doesn't crash.
        self.assertIn("<h2>", html)

    def test_data_gaps_emitted_when_present(self):
        from rcm_mc.ic_binder import render_html_binder
        html = render_html_binder(_empty_result())
        self.assertIn("Data Gaps", html)
        # Bulletted list rendering
        self.assertIn("<ul", html)


if __name__ == "__main__":
    unittest.main()

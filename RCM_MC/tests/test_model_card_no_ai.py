"""Model-card spec pins: click-through target + no-AI-claim property.

Backlog #9 B / #29 require (1) the screener footer "model card" link to
actually land on the page that renders the holdout model card, and (2) a
test asserting the card/footer NEVER claims AI/LLM — the (currently-holding)
no-AI property was previously unpinned, so a future edit could reintroduce
an AI claim uncaught.

These assertions are scoped to the helper output (footer line + the isolated
margin-model-card panel), NOT the full page shell, so the unrelated Cmd-K
palette chrome ("AI Settings", "big players & AI") does not produce false
positives.
"""
from __future__ import annotations

import re
import unittest

import pandas as pd

from rcm_mc.ui.predictive_screener import (
    _model_card_line,
    render_predictive_screener,
)

_BASE = dict(bed_days_available=73000, total_patient_days=50000,
             medicare_day_pct=0.4, medicaid_day_pct=0.15)

# AI/LLM claim tokens the card must never assert. The acronyms are matched
# case-sensitively with word boundaries so incidental lowercase "ai" inside
# words like "Trained"/"chain"/"domain" is not a false hit; the multi-word
# phrases are matched case-insensitively.
_ACRONYM_RE = re.compile(r"\b(?:AI|LLM)\b")
_PHRASES = ("artificial intelligence", "neural", "machine learning")


def _assert_no_ai_claim(testcase: unittest.TestCase, fragment: str, where: str):
    hit = _ACRONYM_RE.search(fragment)
    testcase.assertIsNone(
        hit,
        f"{where} unexpectedly claims "
        f"'{hit.group(0) if hit else ''}': {fragment!r}")
    low = fragment.lower()
    for phrase in _PHRASES:
        testcase.assertNotIn(
            phrase, low, f"{where} unexpectedly claims '{phrase}'")


def _isolate_margin_card(page_html: str) -> str:
    """Slice just the margin-model-card panel out of render_methodology's
    output so the no-AI assertion sees the card body + limitations only,
    not the surrounding page/palette chrome. The card is the first model
    card in the Financial Models grid; the next card is 'Discounted Cash
    Flow', which bounds the slice."""
    start = page_html.find("Margin Predictor")
    assert start != -1, "margin model card not found in methodology page"
    end = page_html.find("Discounted Cash Flow", start)
    assert end != -1, "could not bound the margin model card slice"
    return page_html[start:end]


class ClickThroughTargetTests(unittest.TestCase):
    """The footer 'model card' link must resolve to the surface that
    actually renders the card (/methodology/calculations → render_methodology),
    not the reference-library hub (/methodology → render_library)."""

    def test_footer_link_targets_the_calculations_page(self):
        line = _model_card_line()
        self.assertIn('href="/methodology/calculations"', line)

    def test_link_target_renders_the_holdout_card(self):
        # /methodology/calculations is served by render_methodology (see
        # server.py route table). Assert that target actually contains the card.
        from rcm_mc.ui.methodology_page import render_methodology
        target_html = render_methodology()
        self.assertIn("holdout model card", target_html)

    def test_library_hub_does_not_render_the_card(self):
        # Guards the defect this fix closes: /methodology (render_library) is
        # the hub, which must NOT be where the "model card" link lands.
        from rcm_mc.ui.library_page import render_library
        self.assertNotIn("holdout model card", render_library())

    def test_rendered_page_footer_uses_calculations_href(self):
        h = render_predictive_screener(pd.DataFrame([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9,
             **_BASE}]), "")
        self.assertIn('href="/methodology/calculations"', h)


class NoAiClaimTests(unittest.TestCase):
    """Pin the no-AI-claim property: neither the footer line nor the
    margin-model-card panel may claim AI/LLM/ML — the model is a Ridge
    regression with split-conformal intervals, and the platform's NO-LLM-on-
    prediction-paths invariant must be visible-facing, not just internal."""

    def test_footer_line_makes_no_ai_claim(self):
        _assert_no_ai_claim(self, _model_card_line(), "screener footer line")

    def test_margin_card_panel_makes_no_ai_claim(self):
        from rcm_mc.ui.methodology_page import render_methodology
        panel = _isolate_margin_card(render_methodology())
        # sanity: we sliced the right region
        self.assertIn("Ridge regression with split-conformal intervals", panel)
        _assert_no_ai_claim(self, panel, "margin model-card panel")


if __name__ == "__main__":
    unittest.main()

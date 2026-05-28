"""Editorial head contract for /portfolio (2026-05-28 style sweep).

Locks the Tier-1 5-block anatomy on the portfolio overview page so a
later edit can't silently regress the head back to a legacy
`<div class="sect"><h2>` shape. Pin-down only — does NOT police the
analytical body below the head; that content remains free to change.

Pins:
  · ONE <h1> on the page (the #1036 a11y invariant).
  · Eyebrow + 24×1px green dash present at the masthead.
  · Mono meta-line quotes REAL counts from the deals frame
    (deal count, sector count, active/pipeline split, NPR sum).
  · Italic-first-phrase serif lede.
  · Status-dot legend (4 dots: live / computed / needs /
    illustrative).
  · The spec-forbidden "card with left-border accent" trope is gone
    from portfolio_overview's own emissions (opportunity + synergy
    cards). Shared-kit helpers retain their borders — that is out
    of scope for this sweep.
"""
from __future__ import annotations

import re
import unittest

import pandas as pd


def _populated_deals() -> pd.DataFrame:
    return pd.DataFrame({
        "deal_id": ["D1", "D2", "D3", "D4"],
        "name": ["Alpha", "Beta", "Gamma", "Delta"],
        "stage": ["active", "active", "pipeline", "active"],
        "sector": ["hospital", "snf", "hospital", "behavioral"],
        "denial_rate": [11.5, 14.2, 9.8, 13.1],
        "days_in_ar": [45, 52, 38, 60],
        "net_revenue": [250e6, 480e6, 120e6, 310e6],
        "net_collection_rate": [0.94, 0.91, 0.96, 0.89],
        "health_score": [72, 55, 81, 47],
    })


class EmptyStateEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        cls.html = render_portfolio_overview(pd.DataFrame())

    def test_one_h1_per_page(self) -> None:
        # Accessibility invariant from #1036.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_empty_head_eyebrow_with_dash(self) -> None:
        self.assertIn("po-empty-head", self.html)
        self.assertIn('class="eyebrow"', self.html)
        self.assertIn('class="dash"', self.html)
        # The dash precedes the eyebrow text per Tier-2 §2.1.
        self.assertRegex(
            self.html,
            r'<span class="dash"></span>\s*PORTFOLIO',
        )

    def test_empty_head_h1_is_portfolio(self) -> None:
        self.assertIn("<h1>Portfolio</h1>", self.html)

    def test_empty_lede_is_italic_first_phrase(self) -> None:
        # Spec §2.3 — italic first phrase, then roman body, all serif.
        self.assertIn("<em>No deals tracked yet.</em>", self.html)

    def test_empty_cta_uses_editorial_tokens(self) -> None:
        # CTA group lands on the editorial primary/ghost button
        # pattern, NOT the legacy cad-btn.
        self.assertIn("po-empty-cta", self.html)
        self.assertIn('class="primary"', self.html)


class PopulatedEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        cls.deals = _populated_deals()
        cls.html = render_portfolio_overview(cls.deals)

    def test_one_h1_per_page(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block_present(self) -> None:
        self.assertIn('class="po-head"', self.html)

    def test_eyebrow_has_green_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*PORTFOLIO',
        )

    def test_h1_present(self) -> None:
        self.assertIn("<h1>Portfolio</h1>", self.html)

    def test_meta_line_quotes_real_deal_count(self) -> None:
        # Frame has 4 deals → "4 DEALS" must appear in the meta line.
        self.assertRegex(self.html, r'class="meta">[^<]*4 DEALS')

    def test_meta_line_quotes_real_sector_count(self) -> None:
        # Frame has 3 unique sectors → "3 SECTORS" in meta.
        self.assertIn("3 SECTORS", self.html)

    def test_meta_line_quotes_active_pipeline_split(self) -> None:
        # 3 active + 1 pipeline → "3 ACTIVE · 1 PIPELINE"
        self.assertIn("3 ACTIVE", self.html)
        self.assertIn("1 PIPELINE", self.html)

    def test_meta_line_quotes_real_npr_sum(self) -> None:
        # 250 + 480 + 120 + 310 = $1,160M (or "$1.16B" — depends on
        # _fmt_money's threshold). The meta line must carry a real
        # NPR sum, not a hard-coded placeholder. Format is one of
        # "$1,160M" / "$1.16B" / "$1.2B" — accept any leading dollar
        # amount followed by an M/B suffix and " NPR".
        self.assertRegex(
            self.html,
            r'class="meta">[^<]*\$[0-9][0-9,.]*[MB]\s+NPR',
        )

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn("<em>Active deals, at a glance.</em>", self.html)
        # The body is serif (no marketing-sans inline override on the
        # lede block itself).
        self.assertIn('class="lede"', self.html)

    def test_status_dot_legend_present(self) -> None:
        # Four-bucket legend from Tier-2 §2.4.
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
                f"missing legend dot: {cls_name}",
            )
        # And the human-readable labels.
        for label in ("Live data", "Computed", "Needs data", "Illustrative"):
            self.assertIn(label, self.html)

    def test_opportunity_card_no_left_border_accent(self) -> None:
        # The spec-forbidden "card with left-border accent" trope was
        # stripped from the portfolio_overview's own emissions. The
        # opportunity card must NOT carry `border-left:3px solid` in
        # its own opening div (kit-emitted borders elsewhere stay).
        m = re.search(
            r'<div class="cad-card"[^>]*>'
            r'\s*<div[^>]*>\s*<h2[^>]*>Portfolio Value Opportunity',
            self.html,
        )
        self.assertIsNotNone(
            m, "Opportunity card opening sequence not found",
        )
        # The opening tag of the opportunity card must not contain
        # border-left:3px in its style attribute.
        opening = m.group(0).split(">", 1)[0]
        self.assertNotIn("border-left:3px", opening)

    def test_synergy_card_no_left_border_accent(self) -> None:
        m = re.search(
            r'<div class="cad-card"[^>]*>'
            r'\s*<div[^>]*>\s*<h2[^>]*>Cross-Deal RCM Synergy',
            self.html,
        )
        self.assertIsNotNone(
            m, "Synergy card opening sequence not found",
        )
        opening = m.group(0).split(">", 1)[0]
        self.assertNotIn("border-left:3px", opening)


class TokenAdditiveContractTests(unittest.TestCase):
    """The chartis_tokens.css spec-token additions are PURELY
    additive — no existing --sc-* / --cad-* / --bg / --paper / --ink
    / --green / --rule token had its value changed.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path
        cls.css = Path(
            "rcm_mc/ui/static/chartis_tokens.css"
        ).read_text(encoding="utf-8")

    def test_new_spec_tokens_present(self) -> None:
        # The new 2026-05-28 spec tokens land with their literal hex
        # values (NOT as aliases of existing tokens) so a page can
        # opt into the spec palette without recoloring its neighbors.
        for token, value in [
            ("--paper-2",   "#ebe5d4"),
            ("--paper-3",   "#e2dcc8"),
            ("--paper-hi",  "#fbf6e8"),
            ("--paper-card", "#fefcf3"),
            ("--ink-3",     "#506478"),
            ("--ink-deep",  "#0e1a29"),
            ("--muted-2",   "#9a9e8a"),
            ("--rule-soft", "#ddd1ac"),
            ("--rule-hi",   "#b6a87f"),
            ("--green-2",   "#2d8964"),
            ("--green-deep", "#154e36"),
            ("--green-tint", "#e6efe1"),
            ("--coral",     "#b04a3a"),
            ("--coral-soft", "#ecd4cc"),
            ("--amber-soft", "#ecdfb4"),
            ("--gold",      "#a08227"),
        ]:
            self.assertRegex(
                self.css,
                rf"{re.escape(token)}\s*:\s*{re.escape(value)}",
                f"missing or mis-valued spec token: {token} = {value}",
            )

    def test_existing_tokens_unchanged(self) -> None:
        # Sanity — the pre-sweep token definitions weren't altered.
        # We pin the exact pre-sweep value (whether literal hex or
        # var(--sc-*) alias) so the additive sweep can't silently
        # re-anchor a value and shift every page that already used it.
        for token, value in [
            ("--bg",     "var(--sc-parchment)"),
            ("--paper",  "#ffffff"),
            ("--ink",    "var(--sc-ink)"),
            ("--ink-2",  "var(--sc-navy)"),
            ("--rule",   "var(--sc-rule)"),
            ("--green",  "var(--sc-positive)"),
            ("--muted",  "var(--sc-text-dim)"),
        ]:
            self.assertRegex(
                self.css,
                rf"{re.escape(token)}\s*:\s*{re.escape(value)}",
                f"existing token value changed: {token} should still be {value}",
            )


if __name__ == "__main__":
    unittest.main()

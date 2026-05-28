"""Editorial-head + score-breakdown contract for /hospital/<ccn>
(sweep batch 10).

Pins the strict Tier-1 5-block head on every hospital profile drill-in
plus the new auto-derived score-breakdown verdict in the lede. Also
locks the removal of the spec-forbidden `border-left:4px solid
{grade_color}` accent from the .hp-grade-block rule.

Pins:
  · ONE <h1> per page (the #1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph at masthead.
  · Mono uppercase meta-line quoting REAL identity (city, state,
    beds, NPR, margin, score, grade).
  · Italic-first-phrase serif lede wrapping the hospital name.
  · Auto-derived score-breakdown verdict in the lede ("Strongest on
    X (n); weakest on Y (m).") quoting real component fields.
  · 4-bucket status-dot legend.
  · The spec-forbidden `border-left:4px solid` accent is gone from
    the .hp-grade-block CSS rule body (the explanatory comment can
    still mention it for traceability — we read only the rule).
"""
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from typing import Dict


@dataclass
class _Score:
    score: int
    grade: str
    components: Dict[str, float]


def _sample_hospital() -> dict:
    return {
        "ccn": "050001",
        "name": "Mercy Medical Center",
        "city": "Pomona",
        "state": "CA",
        "beds": 350,
        "net_patient_revenue": 480_000_000,
        "operating_expenses": 430_000_000,
        "net_income": 22_000_000,
        "medicare_day_pct": 0.42,
        "medicaid_day_pct": 0.18,
        "occupancy_rate": 0.72,
    }


class HospitalProfileHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.hospital_profile import render_hospital_profile
        cls.html = render_hospital_profile(
            _sample_hospital(),
            _Score(
                78, "B+",
                {"Margin": 92.0, "Scale": 84.0, "Volume": 61.0},
            ),
        )

    def test_one_h1_per_page(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="hp-head"', self.html)

    def test_eyebrow_with_dash_carries_ccn(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*'
            r'HOSPITAL PROFILE · CCN 050001',
        )

    def test_h1_is_hospital_name(self) -> None:
        self.assertIn("<h1>Mercy Medical Center</h1>", self.html)

    def test_meta_line_quotes_real_identity(self) -> None:
        # city · state · beds · NPR · margin · score · grade — all
        # real fields from the hospital dict, never hard-coded.
        self.assertRegex(
            self.html,
            r'class="meta">[^<]*'
            r'Pomona, CA[^<]*'
            r'350 BEDS[^<]*'
            r'\$480\.0M NPR[^<]*'
            r'10\.4% OP MARGIN[^<]*'
            r'PE DESK SCORE 78/100 \(B\+\)',
        )

    def test_lede_italic_first_phrase_is_name(self) -> None:
        # <em>Mercy Medical Center</em> — Pomona, CA.
        self.assertIn("<em>Mercy Medical Center</em>", self.html)

    def test_auto_score_breakdown_verdict(self) -> None:
        # Top component Margin (92), bottom Volume (61) — both quoted
        # by name + value in the lede.
        self.assertRegex(
            self.html,
            r"Strongest on <strong>Margin</strong> \(92\)",
        )
        self.assertRegex(
            self.html,
            r"weakest on <strong>Volume</strong> \(61\)",
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_grade_block_no_left_border_accent(self) -> None:
        # The .hp-grade-block CSS RULE body must NOT carry the
        # spec-forbidden `border-left:Npx solid <color>`. The
        # explanatory comment in the CSS may still mention it for
        # traceability — we check only the rule.
        m = re.search(r"\.hp-grade-block\{([^}]+)\}", self.html)
        self.assertIsNotNone(m, "hp-grade-block rule not found")
        self.assertNotIn("border-left:4px solid", m.group(1))
        self.assertNotIn("border-left:3px solid", m.group(1))
        # The grade value text still flips to the severity color
        # (color-the-text, not the background — Tier-2 §2.10).
        m_val = re.search(r"\.hp-grade-val\{([^}]+)\}", self.html)
        self.assertIsNotNone(m_val)
        self.assertIn("color:", m_val.group(1))


class HospitalProfileScoreFallbackTests(unittest.TestCase):
    """When ``score`` lacks components, the verdict cleanly omits
    the strongest/weakest line — never editorial filler."""

    def test_empty_components_skips_verdict_extras(self) -> None:
        from rcm_mc.ui.hospital_profile import render_hospital_profile
        html = render_hospital_profile(
            _sample_hospital(),
            _Score(70, "B", {}),
        )
        # The lede still renders with the identity sentence, but
        # without the strongest/weakest follow-up.
        self.assertIn("<em>Mercy Medical Center</em>", html)
        self.assertNotIn("Strongest on", html)

    def test_single_component_skips_strongest_weakest(self) -> None:
        # When top and bottom component are the same we don't render
        # a tautology ("Strongest on X; weakest on X").
        from rcm_mc.ui.hospital_profile import render_hospital_profile
        html = render_hospital_profile(
            _sample_hospital(),
            _Score(70, "B", {"Only": 70.0}),
        )
        self.assertNotIn("Strongest on", html)


if __name__ == "__main__":
    unittest.main()

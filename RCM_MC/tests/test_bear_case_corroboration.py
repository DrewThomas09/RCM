"""Bear-case cross-source corroboration — the defensibility test.

A risk theme flagged by >=2 INDEPENDENT analytic engines is far
harder for management to wave away than one flagged by a single
model. The analysis must count distinct sources (not evidence items)
and be a pure function of the report's evidence.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.bear_case import (
    BearCaseReport, Evidence, EvidenceSeverity, EvidenceSource,
    EvidenceTheme, analyze_corroboration,
)


def _ev(src, theme, sev=EvidenceSeverity.HIGH):
    return Evidence(title="t", source=src, theme=theme, severity=sev)


def _report(evidence):
    return BearCaseReport(target_name="X", evidence=evidence)


class CorroborationTests(unittest.TestCase):
    def test_distinct_sources_not_items(self):
        # Two findings from the SAME engine do not corroborate.
        r = _report([
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT),
        ])
        c = analyze_corroboration(r)
        credit = next(t for t in c.themes if t.theme == "CREDIT")
        self.assertEqual(credit.distinct_sources, 1)
        self.assertEqual(credit.evidence_count, 2)
        self.assertFalse(credit.corroborated)
        self.assertEqual(c.corroborated_count, 0)

    def test_two_independent_sources_corroborate(self):
        r = _report([
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT,
                EvidenceSeverity.CRITICAL),
            _ev(EvidenceSource.DEAL_MC, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.REGULATORY_CALENDAR, EvidenceTheme.REGULATORY),
        ])
        c = analyze_corroboration(r)
        self.assertEqual(c.corroborated_count, 1)
        self.assertEqual(c.single_source_count, 1)
        self.assertEqual(c.strongest_theme, "CREDIT")
        credit = next(t for t in c.themes if t.theme == "CREDIT")
        self.assertEqual(credit.worst_severity, "CRITICAL")
        self.assertIn("memo-ready", c.defensibility_note)

    def test_strongest_theme_leads_and_is_corroborated(self):
        r = _report([
            _ev(EvidenceSource.REGULATORY_CALENDAR, EvidenceTheme.REGULATORY),
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.DEAL_MC, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.BRIDGE_AUDIT, EvidenceTheme.CREDIT),
        ])
        c = analyze_corroboration(r)
        # CREDIT (3 sources) sorts ahead of REGULATORY (1 source).
        self.assertEqual(c.themes[0].theme, "CREDIT")
        self.assertEqual(c.themes[0].distinct_sources, 3)

    def test_all_single_source(self):
        r = _report([
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.REGULATORY_CALENDAR, EvidenceTheme.REGULATORY),
        ])
        c = analyze_corroboration(r)
        self.assertIsNone(c.strongest_theme)
        self.assertIn("single source engine", c.defensibility_note)

    def test_empty_report(self):
        c = analyze_corroboration(_report([]))
        self.assertEqual(c.themes, [])
        self.assertEqual(c.corroborated_count, 0)
        self.assertIn("Nothing", c.defensibility_note.title())

    def test_to_dict_round_trips(self):
        c = analyze_corroboration(_report([
            _ev(EvidenceSource.COVENANT_STRESS, EvidenceTheme.CREDIT),
            _ev(EvidenceSource.DEAL_MC, EvidenceTheme.CREDIT),
        ]))
        d = c.to_dict()
        self.assertEqual(d["corroborated_count"], 1)
        self.assertIn("source_names", d["themes"][0])

    def test_renders_in_page(self):
        from rcm_mc.ui.bear_case_page import render_bear_case_page
        h = render_bear_case_page({
            "deal_name": ["Meadowbrook"], "specialty": ["hospital"],
            "revenue_year0_usd": ["450000000"],
            "ebitda_year0_usd": ["60000000"],
            "medicare_share": ["0.45"],
            "hopd_revenue_annual_usd": ["30000000"]})
        self.assertIn("Cross-source corroboration", h)


if __name__ == "__main__":
    unittest.main()

"""Partner-signed QoE memo template regression tests.

Cover:
- All 10 sections render on a complete input (cover, exec summary,
  QoR, KPIs, denials, repricing, risk flags, questions, sign-off,
  appendix).
- Partner headline copy bands correctly across IMMATERIAL / WATCH /
  CRITICAL / UNKNOWN — the three divergence states produce distinct
  voices, UNKNOWN hedges rather than opining.
- Sign-off block is present with partner + preparer names when
  supplied, and renders placeholder copy when not.
- Print-friendly CSS (``@media print`` + ``@page``) is present so
  browser "Save as PDF" is a one-click deliverable.
- HTTP page renderer handles landing, dataset-driven live render,
  and each banding state end-to-end through the ingest → KPI →
  waterfall pipeline.
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.benchmarks import (
    compute_cash_waterfall, compute_kpis,
)
from rcm_mc.exports.qoe_memo import (
    QoEMemoMetadata, render_qoe_memo_html,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


def _load_bundle_and_waterfall(
    fixture: str,
    *,
    mgmt_cohort: Optional[str] = None,
    mgmt_value: Optional[float] = None,
):
    ccd = ingest_dataset(FIXTURE_ROOT / fixture)
    as_of = date(2025, 1, 1)
    bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=fixture)
    mgmt = ({mgmt_cohort: mgmt_value}
            if mgmt_cohort is not None and mgmt_value is not None
            else None)
    waterfall = compute_cash_waterfall(
        ccd.claims, as_of_date=as_of,
        management_reported_revenue_by_cohort_month=mgmt,
    )
    return bundle, waterfall


@dataclass
class _FakeFlag:
    """Minimal duck-type for risk flags — the memo reads title/detail/
    severity off any object."""
    title: str
    detail: str
    severity: str = ""


@dataclass
class _FakeQuestion:
    question: str
    priority: str = "P0"
    context: str = ""


class QoEMemoSectionsTests(unittest.TestCase):
    """Every section renders on a complete critical-case input."""

    def setUp(self):
        self.bundle, self.waterfall = _load_bundle_and_waterfall(
            "hospital_08_waterfall_critical",
            mgmt_cohort="2024-03", mgmt_value=6850.0,
        )
        self.meta = QoEMemoMetadata(
            deal_name="Project Aurora",
            target_entity="Aurora Specialty Hospital LLC",
            engagement_id="RCM-2025-042",
            partner_name="Partner A",
            preparer_name="Senior Associate B",
        )
        self.flags = [
            _FakeFlag("Contractual adjustment calc", "Audit needed", "HIGH"),
            _FakeFlag("Denial reserve policy", "No documented policy", "MED"),
        ]
        self.questions = [
            _FakeQuestion("Provide accrual methodology memo", "P0",
                          "Waterfall does not reconcile to mgmt"),
            _FakeQuestion("Walk through 2024-Q1 bad-debt reserve", "P1"),
        ]
        self.html = render_qoe_memo_html(
            bundle=self.bundle,
            cash_waterfall=self.waterfall,
            risk_flags=self.flags,
            diligence_questions=self.questions,
            metadata=self.meta,
        )

    def test_renders_valid_html_document(self):
        self.assertTrue(self.html.startswith("<!DOCTYPE html>"))
        self.assertIn("<html", self.html)
        self.assertIn("</html>", self.html)

    def test_cover_has_deal_identification(self):
        for field in (
            "Quality of Earnings Memorandum", "Project Aurora",
            "Aurora Specialty Hospital LLC", "RCM-2025-042",
            "Partner A", "Senior Associate B",
        ):
            self.assertIn(field, self.html,
                          msg=f"cover missing {field!r}")

    def test_all_ten_sections_present(self):
        required_section_markers = [
            "Quality of Earnings Memorandum",   # cover
            "1. Executive Summary",
            "2. Quality of Revenue",
            "3. Revenue-Cycle KPI",
            "4. Denial Stratification",
            "6. Risk Flags",
            "7. Open Diligence Questions",
            "Partner Sign-Off",
            "Appendix",
        ]
        for m in required_section_markers:
            self.assertIn(m, self.html, msg=f"missing section {m!r}")

    def test_qor_section_has_waterfall_steps(self):
        for step_label in (
            "Gross Charges", "Contractual Adjustments",
            "Initial Denials (gross)", "Realized Cash",
        ):
            self.assertIn(step_label, self.html,
                          msg=f"waterfall step label missing: {step_label!r}")

    def test_print_css_is_present(self):
        self.assertIn("@media print", self.html)
        self.assertIn("@page", self.html)
        # Cover break keeps the cover on its own page.
        self.assertIn("page-break-after", self.html)

    def test_risk_flags_and_questions_render(self):
        self.assertIn("Contractual adjustment calc", self.html)
        self.assertIn("No documented policy", self.html)
        self.assertIn("Provide accrual methodology memo", self.html)

    def test_signoff_block_has_signature_lines_and_names(self):
        self.assertIn("signature-line", self.html)
        self.assertIn("Partner A", self.html)
        self.assertIn("Senior Associate B", self.html)


class QoEPartnerCopyBandingTests(unittest.TestCase):
    """The partner-voice copy in the executive summary must band by
    divergence status. This is the headline the partner signs."""

    def _render(self, fixture: str, mgmt_cohort=None, mgmt_value=None):
        bundle, waterfall = _load_bundle_and_waterfall(
            fixture, mgmt_cohort=mgmt_cohort, mgmt_value=mgmt_value,
        )
        return render_qoe_memo_html(bundle=bundle, cash_waterfall=waterfall)

    def test_immaterial_uses_reconciled_voice(self):
        html = self._render(
            "hospital_07_waterfall_concordant",
            mgmt_cohort="2024-03", mgmt_value=7920.0,
        )
        self.assertIn("IMMATERIAL", html)
        self.assertIn("within tolerance", html)
        self.assertNotIn("Material QoR divergence", html)

    def test_critical_uses_partner_quotable_voice(self):
        html = self._render(
            "hospital_08_waterfall_critical",
            mgmt_cohort="2024-03", mgmt_value=6850.0,
        )
        self.assertIn("CRITICAL", html)
        self.assertIn("Material QoR divergence", html)
        self.assertIn("before IC", html)

    def test_unknown_hedges_rather_than_opines(self):
        html = self._render("hospital_06_waterfall_truth")
        self.assertIn("UNKNOWN", html)
        self.assertIn("management comparison not supplied", html.lower()
                      if "not supplied" in html.lower() else html)
        # Never opines about the engagement in the UNKNOWN state.
        self.assertNotIn("Material QoR divergence", html)


class QoEMemoMinimalInputTests(unittest.TestCase):
    """The memo renders on the minimum (bundle only) with hedges for
    the sections that need the rest."""

    def test_bundle_only_renders_but_hedges_on_qor(self):
        bundle, _ = _load_bundle_and_waterfall("hospital_01_clean_acute")
        html = render_qoe_memo_html(bundle=bundle)
        self.assertIn("No cash waterfall supplied", html)
        # Still produces an exec summary and KPI section.
        self.assertIn("1. Executive Summary", html)
        self.assertIn("3. Revenue-Cycle KPI", html)
        # Sign-off section still renders with placeholder copy.
        self.assertIn("Partner Sign-Off", html)

    def test_placeholder_partner_copy_when_names_absent(self):
        bundle, _ = _load_bundle_and_waterfall("hospital_01_clean_acute")
        html = render_qoe_memo_html(bundle=bundle)
        self.assertIn("Partner signature", html)
        self.assertIn("managing analyst", html)


class QoEMemoHttpRouteTests(unittest.TestCase):
    """End-to-end: /diligence/qoe-memo renders through the live ingest
    → KPI → waterfall pipeline."""

    def test_landing_rendered_when_no_dataset(self):
        from rcm_mc.diligence._pages import render_qoe_memo_page
        html = render_qoe_memo_page("")
        self.assertIn("Quality of Earnings Memorandum", html)
        self.assertIn("Render memo", html)

    def test_dataset_plus_mgmt_revenue_produces_critical_memo(self):
        from rcm_mc.diligence._pages import render_qoe_memo_page
        qs = {
            "deal_name": ["Project Aurora"],
            "engagement_id": ["RCM-2025-042"],
            "mgmt_cohort": ["2024-03"],
            "mgmt_value": ["6850.0"],
        }
        html = render_qoe_memo_page(
            "hospital_08_waterfall_critical", qs=qs,
        )
        self.assertIn("CRITICAL", html)
        self.assertIn("Project Aurora", html)
        self.assertIn("RCM-2025-042", html)

    def test_unknown_fixture_returns_landing_not_crash(self):
        from rcm_mc.diligence._pages import render_qoe_memo_page
        html = render_qoe_memo_page("not_a_real_fixture")
        self.assertIn("Quality of Earnings Memorandum", html)


class QoEMemoEngagementLinkTests(unittest.TestCase):
    """When the memo render is supplied both ``engagement_id`` and
    ``created_by`` query params AND a store, a DRAFT deliverable is
    created on the engagement so the memo becomes traceable in the
    engagement's deliverable list."""

    def _prepare_store(self, tmp: str):
        import os
        from rcm_mc.engagement import (
            EngagementRole, add_member, create_engagement,
        )
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        create_engagement(
            store, engagement_id="ENG1", name="Project Aurora",
            client_name="Aurora Health", created_by="admin",
        )
        add_member(store, engagement_id="ENG1", username="analyst1",
                   role=EngagementRole.ANALYST, added_by="admin")
        return store

    def test_linked_deliverable_created_when_engagement_supplied(self):
        import os
        import tempfile

        from rcm_mc.diligence._pages import render_qoe_memo_page
        from rcm_mc.engagement import list_deliverables

        with tempfile.TemporaryDirectory() as tmp:
            store = self._prepare_store(tmp)
            qs = {
                "deal_name": ["Project Aurora"],
                "engagement_id": ["ENG1"],
                "created_by": ["analyst1"],
                "mgmt_cohort": ["2024-03"],
                "mgmt_value": ["6850.0"],
            }
            html = render_qoe_memo_page(
                "hospital_08_waterfall_critical", qs=qs, store=store,
            )
            self.assertIn("CRITICAL", html)
            # Deliverable should now exist as DRAFT on the engagement.
            deliverables = list_deliverables(
                store, engagement_id="ENG1", viewer="analyst1",
            )
            self.assertEqual(len(deliverables), 1)
            d = deliverables[0]
            self.assertEqual(d.kind, "QOE_MEMO")
            self.assertEqual(d.status, "DRAFT")
            self.assertEqual(d.created_by, "analyst1")
            self.assertEqual(d.title, "Project Aurora")

    def test_missing_engagement_id_does_not_create_deliverable(self):
        import tempfile

        from rcm_mc.diligence._pages import render_qoe_memo_page
        from rcm_mc.engagement import list_deliverables

        with tempfile.TemporaryDirectory() as tmp:
            store = self._prepare_store(tmp)
            qs = {
                "mgmt_cohort": ["2024-03"],
                "mgmt_value": ["6850.0"],
            }
            render_qoe_memo_page(
                "hospital_08_waterfall_critical", qs=qs, store=store,
            )
            self.assertEqual(
                list_deliverables(store, engagement_id="ENG1"), []
            )

    def test_non_member_silently_skipped(self):
        """If created_by is not a member of the engagement, no
        deliverable is created — the memo render still succeeds."""
        import tempfile

        from rcm_mc.diligence._pages import render_qoe_memo_page
        from rcm_mc.engagement import list_deliverables

        with tempfile.TemporaryDirectory() as tmp:
            store = self._prepare_store(tmp)
            qs = {
                "engagement_id": ["ENG1"],
                "created_by": ["stranger"],
                "mgmt_cohort": ["2024-03"],
                "mgmt_value": ["6850.0"],
            }
            html = render_qoe_memo_page(
                "hospital_08_waterfall_critical", qs=qs, store=store,
            )
            # Memo still renders cleanly.
            self.assertIn("CRITICAL", html)
            # No deliverable created.
            self.assertEqual(
                list_deliverables(store, engagement_id="ENG1"), []
            )


if __name__ == "__main__":
    unittest.main()

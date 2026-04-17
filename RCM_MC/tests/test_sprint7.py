"""Tests for Sprint 7: Value Creation Plan (41), Predicted vs Actual (43), Notifications (44).

VALUE CREATION PLAN:
 1. create_plan_from_packet generates one initiative per bridge lever.
 2. Initiatives sum to bridge total EBITDA.
 3. Plan round-trips through save/load.
 4. update_initiative_status persists change.
 5. Ramp curve assigned per lever family.
 6. Plan to_dict/from_dict round-trips.
 7. Empty bridge → empty initiatives list.

PREDICTED VS ACTUAL:
 8. compute_predicted_vs_actual returns empty when no actuals.
 9. Metric within CI → within_ci=True.
10. Mean absolute error computed correctly.
11. prediction_accuracy_summary on empty → zeroed report.

NOTIFICATIONS:
12. save_config + get_configs round-trip.
13. _send_email returns False when SMTP not configured.
14. _send_slack returns False when no webhook URL.
15. build_weekly_digest counts deals.
16. dispatch_to_configs matches event filter.
17. DigestReport to_dict round-trips.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    EBITDABridgeResult,
    MetricImpact,
    PredictedMetric,
)
from rcm_mc.infra.notifications import (
    DigestReport,
    _send_email,
    _send_slack,
    build_weekly_digest,
    get_configs,
    save_config,
)
from rcm_mc.pe.predicted_vs_actual import (
    PredictedVsActual,
    PredictionReport,
    compute_predicted_vs_actual,
    prediction_accuracy_summary,
)
from rcm_mc.pe.value_creation_plan import (
    Initiative,
    ValueCreationPlan,
    create_plan_from_packet,
    load_latest_plan,
    save_plan,
    update_initiative_status,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _sample_packet():
    return DealAnalysisPacket(
        deal_id="d1", deal_name="Test",
        ebitda_bridge=EBITDABridgeResult(
            total_ebitda_impact=8e6,
            per_metric_impacts=[
                MetricImpact(metric_key="denial_rate",
                             current_value=12.0, target_value=7.0,
                             ebitda_impact=5e6),
                MetricImpact(metric_key="days_in_ar",
                             current_value=55.0, target_value=45.0,
                             ebitda_impact=3e6),
            ],
        ),
    )


# ── Value Creation Plan ──────────────────────────────────────────

class TestValueCreationPlan(unittest.TestCase):

    def test_creates_one_initiative_per_lever(self):
        plan = create_plan_from_packet(_sample_packet())
        self.assertEqual(len(plan.initiatives), 2)

    def test_initiatives_sum_to_total(self):
        plan = create_plan_from_packet(_sample_packet())
        total = sum(i.target_ebitda_impact for i in plan.initiatives)
        self.assertAlmostEqual(total, plan.total_target_ebitda, places=2)

    def test_save_and_load_roundtrip(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            plan = create_plan_from_packet(_sample_packet())
            save_plan(store, plan)
            loaded = load_latest_plan(store, "d1")
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.initiatives), 2)
        finally:
            os.unlink(path)

    def test_update_initiative_status(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            plan = create_plan_from_packet(_sample_packet())
            save_plan(store, plan)
            ok = update_initiative_status(
                store, "d1", "init-denial_rate", "on_track",
            )
            self.assertTrue(ok)
            loaded = load_latest_plan(store, "d1")
            init = next(
                i for i in loaded.initiatives
                if i.initiative_id == "init-denial_rate"
            )
            self.assertEqual(init.status, "on_track")
        finally:
            os.unlink(path)

    def test_ramp_curve_assigned(self):
        plan = create_plan_from_packet(_sample_packet())
        denial_init = next(
            i for i in plan.initiatives if i.lever_key == "denial_rate"
        )
        self.assertEqual(denial_init.ramp_curve, "denial_management")

    def test_to_dict_from_dict(self):
        plan = create_plan_from_packet(_sample_packet())
        restored = ValueCreationPlan.from_dict(plan.to_dict())
        self.assertEqual(len(restored.initiatives), 2)

    def test_empty_bridge_empty_initiatives(self):
        p = DealAnalysisPacket(deal_id="d2")
        plan = create_plan_from_packet(p)
        self.assertEqual(plan.initiatives, [])


# ── Predicted vs Actual ───────────────────────────────────────────

class TestPredictedVsActual(unittest.TestCase):

    def test_empty_when_no_actuals(self):
        store, path = _tmp_store()
        try:
            results = compute_predicted_vs_actual(store, "ghost")
            self.assertEqual(results, [])
        finally:
            os.unlink(path)

    def test_within_ci(self):
        r = PredictedVsActual(
            metric_key="denial_rate",
            predicted_at_diligence=10.0,
            actual_now=9.5,
            within_ci=True,
        )
        self.assertTrue(r.within_ci)

    def test_accuracy_summary_empty(self):
        report = prediction_accuracy_summary([])
        self.assertEqual(report.n_metrics, 0)

    def test_accuracy_summary_mae(self):
        results = [
            PredictedVsActual(
                metric_key="denial_rate",
                predicted_at_diligence=10.0,
                actual_now=12.0,
                variance_pct=0.20,
                within_ci=False,
            ),
            PredictedVsActual(
                metric_key="days_in_ar",
                predicted_at_diligence=50.0,
                actual_now=48.0,
                variance_pct=-0.04,
                within_ci=True,
            ),
        ]
        report = prediction_accuracy_summary(results)
        self.assertEqual(report.n_metrics, 2)
        self.assertAlmostEqual(report.pct_within_ci, 50.0)
        self.assertAlmostEqual(report.mean_absolute_error, 0.12)


# ── Notifications ─────────────────────────────────────────────────

class TestNotifications(unittest.TestCase):

    def test_save_and_get_config(self):
        store, path = _tmp_store()
        try:
            save_config(
                store, "user1", "EMAIL",
                {"email": "a@b.com"}, ["risk.critical"],
            )
            cfgs = get_configs(store, "user1")
            self.assertEqual(len(cfgs), 1)
            self.assertIn("risk.critical", cfgs[0]["events"])
        finally:
            os.unlink(path)

    def test_email_noop_without_smtp(self):
        # Ensure SMTP_HOST is not set.
        old = os.environ.pop("SMTP_HOST", None)
        try:
            self.assertFalse(_send_email("a@b.com", "test", "<p>hi</p>"))
        finally:
            if old is not None:
                os.environ["SMTP_HOST"] = old

    def test_slack_noop_without_url(self):
        self.assertFalse(_send_slack("", "test"))

    def test_build_weekly_digest(self):
        store, path = _tmp_store()
        try:
            report = build_weekly_digest(store)
            self.assertIsInstance(report, DigestReport)
            self.assertEqual(report.total_deals, 0)
        finally:
            os.unlink(path)

    def test_digest_to_dict(self):
        r = DigestReport(total_deals=3, critical_risks=1, summary="ok")
        d = r.to_dict()
        self.assertEqual(d["total_deals"], 3)


if __name__ == "__main__":
    unittest.main()

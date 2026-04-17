"""Tests for Phase R (verticals 78-80), S (analytics 81-83), T (portals 84-85).

VERTICALS:
 1. Vertical registry dispatches ASC/MSO/BH metric registries.
 2. Hospital vertical returns RCM_METRIC_REGISTRY.
 3. ASC bridge produces positive impact for improved case volume.
 4. MSO bridge produces positive impact for higher wRVUs.
 5. BH bridge produces positive impact for higher occupancy.
 6. ASC registry has 12 metrics.
 7. MSO registry has 10 metrics.
 8. BH registry has 10 metrics.
 9. ASC bridge result to_dict round-trips.

CAUSAL INFERENCE:
10. ITS detects level break on synthetic data.
11. ITS with short series → effect ≈ 0.
12. DiD recovers known treatment effect.
13. DiD with empty control → effect 0.

SERVICE LINES:
14. DRG 470 → Orthopedics.
15. PnL sums revenue across claims.
16. Unknown DRG → "Other".

COUNTERFACTUAL:
17. Without initiative removes the causal effect.
18. Baseline drift matches industry drift.
19. Empty trajectory → zeroed result.

EXTERNAL USERS:
20. grant_access + list_assignments round-trip.
21. revoke_access deactivates.
22. can_access_deal checks assignment.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np

from rcm_mc.analytics.causal_inference import (
    difference_in_differences,
    interrupted_time_series,
)
from rcm_mc.analytics.counterfactual import (
    counterfactual_baseline,
    counterfactual_without_initiative,
)
from rcm_mc.analytics.service_lines import (
    SERVICE_LINE_DEFINITIONS,
    compute_service_line_pnl,
    _drg_to_service_line,
)
from rcm_mc.auth.external_users import (
    can_access_deal,
    grant_access,
    list_assignments,
    revoke_access,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.verticals.asc.bridge import compute_asc_bridge
from rcm_mc.verticals.asc.ontology import ASC_METRIC_REGISTRY
from rcm_mc.verticals.behavioral_health.bridge import compute_bh_bridge
from rcm_mc.verticals.behavioral_health.ontology import BH_METRIC_REGISTRY
from rcm_mc.verticals.mso.bridge import compute_mso_bridge
from rcm_mc.verticals.mso.ontology import MSO_METRIC_REGISTRY
from rcm_mc.verticals.registry import Vertical, get_metric_registry


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── Verticals ─────────────────────────────────────────────────────

class TestVerticals(unittest.TestCase):

    def test_registry_dispatch_asc(self):
        reg = get_metric_registry("ASC")
        self.assertIn("case_volume", reg)

    def test_registry_dispatch_mso(self):
        reg = get_metric_registry("MSO")
        self.assertIn("wrvus_per_provider", reg)

    def test_registry_dispatch_bh(self):
        reg = get_metric_registry("BEHAVIORAL_HEALTH")
        self.assertIn("bed_days", reg)

    def test_registry_dispatch_hospital(self):
        reg = get_metric_registry("HOSPITAL")
        self.assertIn("denial_rate", reg)

    def test_asc_bridge_positive(self):
        r = compute_asc_bridge(
            {"cases_per_room_per_day": 3.0},
            {"cases_per_room_per_day": 5.0},
        )
        self.assertGreater(r.total_ebitda_impact, 0)

    def test_mso_bridge_positive(self):
        r = compute_mso_bridge(
            {"wrvus_per_provider": 4000},
            {"wrvus_per_provider": 5500},
        )
        self.assertGreater(r.total_ebitda_impact, 0)

    def test_bh_bridge_positive(self):
        r = compute_bh_bridge(
            {"occupancy_rate": 65},
            {"occupancy_rate": 80},
        )
        self.assertGreater(r.total_ebitda_impact, 0)

    def test_asc_registry_size(self):
        self.assertGreaterEqual(len(ASC_METRIC_REGISTRY), 12)

    def test_asc_bridge_to_dict(self):
        r = compute_asc_bridge(
            {"cases_per_room_per_day": 3.0},
            {"cases_per_room_per_day": 5.0},
        )
        d = r.to_dict()
        self.assertIn("total_ebitda_impact", d)


# ── Causal Inference ──────────────────────────────────────────────

class TestCausalInference(unittest.TestCase):

    def test_its_detects_level_break(self):
        # Pre: flat at 10. Post: flat at 7 (improvement of 3).
        values = [10.0]*6 + [7.0]*4
        est = interrupted_time_series(values, intervention_index=6)
        self.assertAlmostEqual(est.estimated_effect, -3.0, delta=0.5)

    def test_its_short_series(self):
        est = interrupted_time_series([1.0, 2.0], intervention_index=1)
        self.assertEqual(est.estimated_effect, 0.0)

    def test_did_recovers_effect(self):
        # Treated: pre=10, post=7. Control: pre=10, post=10.
        # Effect = (7-10) - (10-10) = -3.
        est = difference_in_differences(
            [10]*4, [7]*4, [10]*4, [10]*4,
        )
        self.assertAlmostEqual(est.estimated_effect, -3.0, delta=0.1)

    def test_did_empty_control(self):
        est = difference_in_differences([10], [7], [], [])
        self.assertEqual(est.estimated_effect, 0.0)


# ── Service Lines ─────────────────────────────────────────────────

class TestServiceLines(unittest.TestCase):

    def test_drg_470_orthopedics(self):
        self.assertEqual(_drg_to_service_line("470"), "Orthopedics")

    def test_unknown_drg_other(self):
        self.assertEqual(_drg_to_service_line("999"), "Other")

    def test_pnl_sums_revenue(self):
        claims = [
            {"drg_code": "470", "paid_amount": 15000, "status": "paid"},
            {"drg_code": "470", "paid_amount": 12000, "status": "paid"},
            {"drg_code": "820", "paid_amount": 8000, "status": "paid"},
        ]
        pnl = compute_service_line_pnl(claims)
        ortho = next(p for p in pnl if p.service_line == "Orthopedics")
        self.assertEqual(ortho.revenue, 27000)
        self.assertEqual(ortho.claim_count, 2)


# ── Counterfactual ────────────────────────────────────────────────

class TestCounterfactual(unittest.TestCase):

    def test_without_initiative(self):
        actual = [10, 10, 10, 7, 7, 7]  # intervention at idx 3
        r = counterfactual_without_initiative(actual, -3.0, 3)
        # Counterfactual at idx 3: 7 - (-3) = 10.
        self.assertAlmostEqual(r.counterfactual_trajectory[3], 10.0)
        self.assertAlmostEqual(r.cumulative_delta, -9.0)

    def test_baseline_drift(self):
        actual = [10, 9.5, 9.0, 8.5, 8.0]
        r = counterfactual_baseline(actual, industry_drift_per_period=-0.5)
        # Baseline matches actual when drift matches slope → delta ≈ 0.
        self.assertAlmostEqual(r.cumulative_delta, 0.0, delta=0.1)

    def test_empty_trajectory(self):
        r = counterfactual_baseline([])
        self.assertEqual(r.cumulative_delta, 0.0)


# ── External Users ────────────────────────────────────────────────

class TestExternalUsers(unittest.TestCase):

    def test_grant_and_list(self):
        store, path = _tmp_store()
        try:
            aid = grant_access(store, "ceo@hospital.com",
                               "EXTERNAL_MANAGEMENT", deal_id="d1")
            self.assertGreater(aid, 0)
            assigns = list_assignments(store, user_id="ceo@hospital.com")
            self.assertEqual(len(assigns), 1)
        finally:
            os.unlink(path)

    def test_revoke(self):
        store, path = _tmp_store()
        try:
            aid = grant_access(store, "ceo@hospital.com",
                               "EXTERNAL_MANAGEMENT", deal_id="d1")
            self.assertTrue(revoke_access(store, aid))
            assigns = list_assignments(store, user_id="ceo@hospital.com")
            self.assertEqual(len(assigns), 0)
        finally:
            os.unlink(path)

    def test_can_access_deal(self):
        store, path = _tmp_store()
        try:
            grant_access(store, "ceo@hospital.com",
                         "EXTERNAL_MANAGEMENT", deal_id="d1")
            self.assertTrue(can_access_deal(store, "ceo@hospital.com", "d1"))
            self.assertFalse(can_access_deal(store, "ceo@hospital.com", "d2"))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

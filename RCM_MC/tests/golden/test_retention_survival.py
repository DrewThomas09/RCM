"""Golden test for NEW-05 cohort retention (Kaplan-Meier).

Hand-computed 10-member cohort:
    2 churn at month 1, 2 churn at month 3, 1 churn at month 6, 5 censored at 6.
    S(1) = 1 - 2/10                 = 0.8
    S(3) = 0.8 * (1 - 2/8)          = 0.6
    S(6) = 0.6 * (1 - 1/6)          = 0.5
A 10-member cohort is below 30, so it must raise the small_cohort flag.
Steepest conditional hazard is month 3 (2/8 = 0.25).
"""
import unittest

from rcm_mc.cdd.retention_survival import retention_curves


def _cohort(label, plan):
    rows = []
    i = 0
    for months, churned, count in plan:
        for _ in range(count):
            rows.append({"entity_id": f"{label}-{i}", "cohort": label,
                         "duration_months": months, "churned": bool(churned)})
            i += 1
    return rows


PLAN_10 = [(1, 1, 2), (3, 1, 2), (6, 1, 1), (6, 0, 5)]


class TestRetention(unittest.TestCase):
    def test_km_values_match_fixture(self):
        ex = retention_curves(_cohort("2024", PLAN_10), times=(1, 3, 6),
                              source="Golden", vintage="2026")
        surv = ex.meta["cohorts"]["2024"]["survival"]
        self.assertAlmostEqual(surv[1], 0.8, delta=1e-9)
        self.assertAlmostEqual(surv[3], 0.6, delta=1e-9)
        self.assertAlmostEqual(surv[6], 0.5, delta=1e-9)

    def test_small_cohort_flag_fires(self):
        ex = retention_curves(_cohort("2024", PLAN_10), times=(1, 3, 6),
                              source="Golden", vintage="2026")
        self.assertIn("small_cohort", ex.flag_codes())
        self.assertFalse(ex.meta["cohorts"]["2024"]["reliable"])

    def test_large_cohort_not_flagged(self):
        # 40 members: 8 churn at m1, rest active at m12 -> reliable.
        plan = [(1, 1, 8), (12, 0, 32)]
        ex = retention_curves(_cohort("big", plan), times=(1, 12),
                              source="Golden", vintage="2026")
        self.assertTrue(ex.meta["cohorts"]["big"]["reliable"])
        self.assertNotIn("small_cohort", ex.flag_codes())

    def test_cliff_detection(self):
        ex = retention_curves(_cohort("2024", PLAN_10), times=(1, 3, 6),
                              source="Golden", vintage="2026")
        cliffs = ex.meta["cohorts"]["2024"]["cliffs"]
        self.assertTrue(cliffs, "expected at least one cliff month")
        # Steepest hazard is month 3 (0.25).
        self.assertEqual(cliffs[0]["month"], 3.0)
        self.assertAlmostEqual(cliffs[0]["hazard"], 0.25, delta=1e-9)

    def test_vintage_overlay_newer_retains_worse(self):
        old = _cohort("2023", [(1, 1, 5), (12, 0, 35)])   # 12.5% churn at m1
        new = _cohort("2024", [(1, 1, 20), (12, 0, 20)])  # 50% churn at m1
        ex = retention_curves(old + new, times=(1, 12), source="Golden", vintage="2026")
        self.assertIn("newer_cohorts_retain_worse", ex.flag_codes())
        vf = ex.meta["vintage_flag"]
        self.assertEqual(vf["newest"][0], "2024")
        self.assertLess(vf["newest"][1], vf["oldest"][1])

    def test_dates_contract_month_diff(self):
        rows = [
            {"entity_id": "a", "cohort_start": "2024-01", "last_active": "2024-04", "status": "churned"},
            {"entity_id": "b", "cohort_start": "2024-01", "last_active": "2024-07", "status": "active"},
        ]
        ex = retention_curves(rows, times=(3,), source="Golden", vintage="2026")
        # one churn at month 3 out of 2 at risk -> S(3) = 0.5
        self.assertAlmostEqual(ex.meta["cohorts"]["2024-01"]["survival"][3], 0.5, delta=1e-9)

    def test_single_member_degenerate(self):
        ex = retention_curves([{"entity_id": "x", "cohort": "solo",
                                "duration_months": 5, "churned": True}],
                              times=(1, 5), source="Golden", vintage="2026")
        self.assertIn("small_cohort", ex.flag_codes())
        self.assertEqual(ex.meta["cohorts"]["solo"]["size"], 1)

    def test_aggregate_monotone(self):
        ex = retention_curves(_cohort("2024", PLAN_10), times=(1, 3, 6),
                              source="Golden", vintage="2026")
        self.assertTrue(ex.reconciled)


if __name__ == "__main__":
    unittest.main()

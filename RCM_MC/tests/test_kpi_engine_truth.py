"""KPI engine — hand-computed truth must match to machine precision.

Each fixture in ``tests/fixtures/kpi_truth/`` has an ``expected.json``
with KPI values a reasonable analyst can compute on paper. The engine
matches those values exactly (or returns None with the documented
reason).

This is the regression lock on the HFMA formulas. A formula change
trips this test and we see it before the number lands in a packet.
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from rcm_mc.diligence import ingest_dataset, compute_kpis


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


def _load(name: str):
    d = FIXTURE_ROOT / name
    expected = json.loads((d / "expected.json").read_text("utf-8"))
    ds = ingest_dataset(d)
    return ds, expected


class KPIEngineTruthTests(unittest.TestCase):

    def _check_kpi(self, actual, expected_spec, label: str):
        if expected_spec.get("value") is None:
            self.assertIsNone(actual.value, msg=f"{label} should be None")
            reason = expected_spec.get("reason_contains")
            if reason:
                self.assertIn(reason, (actual.reason or ""),
                              msg=f"{label} reason mismatch")
        else:
            self.assertIsNotNone(actual.value, msg=f"{label} should not be None")
            self.assertAlmostEqual(
                actual.value, expected_spec["value"], places=3,
                msg=f"{label} value mismatch",
            )
        if "sample_size" in expected_spec:
            self.assertEqual(
                actual.sample_size, expected_spec["sample_size"],
                msg=f"{label} sample_size mismatch",
            )

    # ── hospital_01: clean acute ────────────────────────────────────

    def test_hospital_01_kpis_match_truth(self):
        ds, exp = _load("hospital_01_clean_acute")
        bundle = compute_kpis(
            ds, as_of_date=date.fromisoformat(exp["as_of_date"]),
            provider_id=exp["provider_id"],
        )
        spec = exp["expected_kpis"]
        self._check_kpi(bundle.days_in_ar, spec["days_in_ar"], "days_in_ar")
        self._check_kpi(bundle.first_pass_denial_rate,
                        spec["first_pass_denial_rate"], "fpdr")
        self._check_kpi(bundle.ar_aging_over_90,
                        spec["ar_aging_over_90"], "ar_aging")
        self._check_kpi(bundle.cost_to_collect,
                        spec["cost_to_collect"], "ctc")
        self._check_kpi(bundle.net_revenue_realization,
                        spec["net_revenue_realization"], "nrr")
        self._check_kpi(bundle.lag_service_to_bill,
                        spec["lag_service_to_bill"], "lag_stb")
        self._check_kpi(bundle.lag_bill_to_cash,
                        spec["lag_bill_to_cash"], "lag_btc")

    # ── hospital_02: denial-heavy ───────────────────────────────────

    def test_hospital_02_kpis_match_truth(self):
        ds, exp = _load("hospital_02_denial_heavy")
        bundle = compute_kpis(
            ds, as_of_date=date.fromisoformat(exp["as_of_date"]),
            provider_id=exp["provider_id"],
        )
        spec = exp["expected_kpis"]
        self._check_kpi(bundle.days_in_ar, spec["days_in_ar"], "days_in_ar")
        self._check_kpi(bundle.first_pass_denial_rate,
                        spec["first_pass_denial_rate"], "fpdr")
        self._check_kpi(bundle.ar_aging_over_90,
                        spec["ar_aging_over_90"], "ar_aging")
        self._check_kpi(bundle.lag_service_to_bill,
                        spec["lag_service_to_bill"], "lag_stb")
        self._check_kpi(bundle.lag_bill_to_cash,
                        spec["lag_bill_to_cash"], "lag_btc")

        # Denial stratification: top category must be CLINICAL (CARC 50),
        # with 4 claims totalling $1600 open balance.
        spec_den = exp["expected_denial_stratification"]
        top = bundle.denial_stratification[0]
        self.assertEqual(top.category, spec_den["top_category"])
        self.assertEqual(top.count, spec_den["top_category_count"])
        self.assertAlmostEqual(
            top.dollars_denied, spec_den["top_category_dollars"], places=2,
        )

    # ── hospital_04: mixed payer ────────────────────────────────────

    def test_hospital_04_payer_class_counts(self):
        ds, exp = _load("hospital_04_mixed_payer")
        observed = ds.distinct_payer_classes()
        for k, v in exp["expected_payer_class_counts"].items():
            self.assertEqual(observed.get(k, 0), v,
                             msg=f"payer class {k} count mismatch")

    # ── hospital_05: dental DSO — KPI shape ─────────────────────────

    def test_hospital_05_kpis_compute(self):
        ds, exp = _load("hospital_05_dental_dso")
        bundle = compute_kpis(
            ds, as_of_date=date.fromisoformat(exp["as_of_date"]),
        )
        spec = exp["expected_kpis"]
        self._check_kpi(bundle.days_in_ar, spec["days_in_ar"], "days_in_ar")
        self._check_kpi(bundle.first_pass_denial_rate,
                        spec["first_pass_denial_rate"], "fpdr")

    # ── No fabrication when inputs missing ──────────────────────────

    def test_cost_to_collect_requires_inputs(self):
        ds, _ = _load("hospital_01_clean_acute")
        bundle = compute_kpis(ds, as_of_date=date(2025, 1, 1))
        self.assertIsNone(bundle.cost_to_collect.value)
        self.assertIn("cost-of-collection", (bundle.cost_to_collect.reason or ""))

    def test_nrr_requires_contracted_rate_fn(self):
        ds, _ = _load("hospital_01_clean_acute")
        bundle = compute_kpis(ds, as_of_date=date(2025, 1, 1))
        self.assertIsNone(bundle.net_revenue_realization.value)


if __name__ == "__main__":
    unittest.main()

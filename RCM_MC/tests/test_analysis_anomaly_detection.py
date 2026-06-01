"""Tests for ``rcm_mc/analysis/anomaly_detection.py``.

Calibration QA module — flags suspicious values in a calibrated cfg
that may indicate data-quality issues (DAR > 90 days, IDR > 25%,
FWR > 50%, near-zero revenue share). Output feeds the diligence
'data quality' callout and the LP digest red-flag section.

Module had no direct unit-test coverage. Locks the four threshold
gates + the report dataclass before any tweak silently raises or
lowers the partner-visible bar.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.anomaly_detection import (
    AnomalyReport,
    detect_anomalies,
)


# ---------------------------------------------------------------------------
# AnomalyReport
# ---------------------------------------------------------------------------


class AnomalyReportTests(unittest.TestCase):

    def test_empty_report_has_no_warnings(self):
        r = AnomalyReport()
        self.assertFalse(r.has_warnings)
        self.assertEqual(r.to_list(), [])

    def test_add_appends_warning(self):
        r = AnomalyReport()
        r.add("Medicare", "IDR", 0.30, 0.25, "unusually high")
        self.assertTrue(r.has_warnings)
        self.assertEqual(len(r.to_list()), 1)

    def test_add_stores_all_fields(self):
        r = AnomalyReport()
        r.add("Medicare", "IDR", 0.30, 0.25, "unusually high")
        w = r.to_list()[0]
        self.assertEqual(w["payer"], "Medicare")
        self.assertEqual(w["metric"], "IDR")
        self.assertEqual(w["value"], 0.30)
        self.assertEqual(w["threshold"], 0.25)
        self.assertEqual(w["direction"], "unusually high")

    def test_add_rounds_to_4_decimals(self):
        # The report dict carries rounded values so partner-facing
        # JSON output is compact + stable across precision drift.
        r = AnomalyReport()
        r.add("X", "DAR", 91.123456789, 90.0, "unusually high")
        w = r.to_list()[0]
        self.assertEqual(w["value"], 91.1235)
        self.assertEqual(w["threshold"], 90.0)

    def test_multiple_warnings_preserve_order(self):
        # Insertion order matters — partner reads the report top-down.
        r = AnomalyReport()
        r.add("A", "DAR", 100, 90, "high")
        r.add("B", "IDR", 0.30, 0.25, "high")
        r.add("C", "FWR", 0.60, 0.50, "high")
        payers = [w["payer"] for w in r.to_list()]
        self.assertEqual(payers, ["A", "B", "C"])

    def test_default_factory_isolates_instances(self):
        # Default-factory list must not be shared across instances
        # (classic dataclass mutable-default trap).
        r1 = AnomalyReport()
        r2 = AnomalyReport()
        r1.add("X", "Y", 1.0, 0.5, "z")
        self.assertEqual(r2.to_list(), [])
        self.assertNotEqual(r1.to_list(), r2.to_list())


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------


def _cfg(**payers):
    return {"payers": payers}


class DetectAnomaliesTests(unittest.TestCase):
    """Each threshold is a contract — board-visible, change requires
    discussion. Tests lock each gate at its current value."""

    def test_empty_cfg_returns_empty_report(self):
        r = detect_anomalies({})
        self.assertFalse(r.has_warnings)

    def test_no_payers_key_returns_empty(self):
        r = detect_anomalies({"appeals": {}})
        self.assertFalse(r.has_warnings)

    def test_non_dict_pconf_skipped_silently(self):
        # Robust to corrupt/legacy cfgs.
        r = detect_anomalies({"payers": {"Medicare": "not_a_dict"}})
        self.assertFalse(r.has_warnings)

    def test_idr_above_25pct_fires(self):
        cfg = _cfg(Medicare={
            "include_denials": True,
            "denials": {"idr": {"mean": 0.30},
                         "fwr": {"mean": 0.05}},
        })
        r = detect_anomalies(cfg)
        idr_warnings = [w for w in r.to_list() if w["metric"] == "IDR"]
        self.assertEqual(len(idr_warnings), 1)
        self.assertEqual(idr_warnings[0]["payer"], "Medicare")
        self.assertEqual(idr_warnings[0]["threshold"], 0.25)

    def test_idr_at_or_below_25pct_does_not_fire(self):
        # Strict greater-than → 0.25 exactly is OK.
        cfg = _cfg(Medicare={
            "include_denials": True,
            "denials": {"idr": {"mean": 0.25},
                         "fwr": {"mean": 0.05}},
        })
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "IDR" for w in r.to_list()))

    def test_idr_skipped_when_denials_disabled(self):
        # include_denials=False → IDR/FWR never evaluated.
        cfg = _cfg(Medicare={
            "include_denials": False,
            "denials": {"idr": {"mean": 0.99}, "fwr": {"mean": 0.99}},
        })
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] in ("IDR", "FWR")
                              for w in r.to_list()))

    def test_fwr_above_50pct_fires(self):
        cfg = _cfg(Commercial={
            "include_denials": True,
            "denials": {"idr": {"mean": 0.05}, "fwr": {"mean": 0.60}},
        })
        r = detect_anomalies(cfg)
        fwr_warnings = [w for w in r.to_list() if w["metric"] == "FWR"]
        self.assertEqual(len(fwr_warnings), 1)
        self.assertEqual(fwr_warnings[0]["payer"], "Commercial")
        self.assertEqual(fwr_warnings[0]["threshold"], 0.50)

    def test_fwr_at_50pct_does_not_fire(self):
        cfg = _cfg(Commercial={
            "include_denials": True,
            "denials": {"idr": {"mean": 0.05}, "fwr": {"mean": 0.50}},
        })
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "FWR" for w in r.to_list()))

    def test_dar_above_90_fires(self):
        # DAR fires regardless of include_denials (always evaluated).
        cfg = _cfg(Other={"dar_clean_days": {"mean": 120}})
        r = detect_anomalies(cfg)
        dar_warnings = [w for w in r.to_list() if w["metric"] == "DAR"]
        self.assertEqual(len(dar_warnings), 1)
        self.assertEqual(dar_warnings[0]["threshold"], 90)

    def test_dar_at_90_does_not_fire(self):
        cfg = _cfg(Other={"dar_clean_days": {"mean": 90}})
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "DAR" for w in r.to_list()))

    def test_dar_missing_treated_as_zero(self):
        # Missing dar_clean_days → 0 mean → no warning.
        cfg = _cfg(Other={})
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "DAR" for w in r.to_list()))

    def test_tiny_revenue_share_fires(self):
        # 0 < rs < 0.02 → fires (likely a typo or unit confusion).
        cfg = _cfg(Tiny={"revenue_share": 0.005,
                          "dar_clean_days": {"mean": 32}})
        r = detect_anomalies(cfg)
        rs_warnings = [w for w in r.to_list()
                       if w["metric"] == "revenue_share"]
        self.assertEqual(len(rs_warnings), 1)
        self.assertEqual(rs_warnings[0]["direction"], "very small share")

    def test_zero_revenue_share_does_not_fire(self):
        # rs == 0 → the payer is intentionally absent; no warning.
        cfg = _cfg(NotInModel={"revenue_share": 0,
                                "dar_clean_days": {"mean": 32}})
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "revenue_share"
                              for w in r.to_list()))

    def test_revenue_share_at_threshold_does_not_fire(self):
        # rs == 0.02 → boundary, no warning (strict less-than).
        cfg = _cfg(Boundary={"revenue_share": 0.02,
                              "dar_clean_days": {"mean": 32}})
        r = detect_anomalies(cfg)
        self.assertFalse(any(w["metric"] == "revenue_share"
                              for w in r.to_list()))

    def test_multiple_gates_can_fire_per_payer(self):
        # One payer can trigger every gate independently.
        cfg = _cfg(BadData={
            "include_denials": True,
            "denials": {"idr": {"mean": 0.30}, "fwr": {"mean": 0.60}},
            "dar_clean_days": {"mean": 120},
            "revenue_share": 0.005,
        })
        r = detect_anomalies(cfg)
        metrics = {w["metric"] for w in r.to_list()}
        self.assertEqual(metrics, {"IDR", "FWR", "DAR", "revenue_share"})

    def test_per_payer_isolation(self):
        # Warnings for one payer don't leak into another's count.
        cfg = _cfg(
            A={"dar_clean_days": {"mean": 120}},          # DAR
            B={"dar_clean_days": {"mean": 50}},           # clean
        )
        r = detect_anomalies(cfg)
        payers = [w["payer"] for w in r.to_list()]
        self.assertEqual(payers, ["A"])

    def test_returns_anomaly_report_type(self):
        # Caller asserts the .has_warnings / .to_list contract — keep
        # the return type stable so packet_builder doesn't break.
        r = detect_anomalies(_cfg())
        self.assertIsInstance(r, AnomalyReport)

    def test_min_observations_kwarg_accepts_override(self):
        # min_observations kwarg is reserved for future expansion; for
        # now it must accept any int without crashing the call.
        r = detect_anomalies(_cfg(), min_observations=100)
        self.assertIsInstance(r, AnomalyReport)


if __name__ == "__main__":
    unittest.main()

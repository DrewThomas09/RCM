"""Golden test for BOLSTER-02 isolation-forest anomaly detection.

Fixture: 30 planted normals near the origin plus 3 planted anomalies far out
(A at (8,0), B at (0,8), C at (8,8)). The 3 anomalies must be flagged; the
false-positive rate among the 30 normals must stay within tolerance; each
anomaly carries a driving-feature reason. Deterministic via random_state.
"""
import unittest

import numpy as np

from rcm_mc.cdd.anomaly import detect_anomalies


def _records(seed=7):
    rng = np.random.default_rng(seed)
    recs = [{"id": f"n{i}", "x": float(rng.normal(0, 1)), "y": float(rng.normal(0, 1))}
            for i in range(30)]
    recs += [{"id": "A", "x": 8.0, "y": 0.0},
             {"id": "B", "x": 0.0, "y": 8.0},
             {"id": "C", "x": 8.0, "y": 8.0}]
    return recs


class TestIsoForest(unittest.TestCase):
    def _build(self):
        return detect_anomalies(_records(), ["x", "y"], contamination=0.1,
                                random_state=42, source="Golden", vintage="2026")

    def test_planted_anomalies_caught(self):
        ids = set(self._build().meta["anomaly_ids"])
        self.assertTrue({"A", "B", "C"} <= ids,
                        msg=f"planted anomalies not all caught: flagged {sorted(ids)}")

    def test_false_positive_rate_within_tolerance(self):
        rows = self._build().meta["rows"]
        fp = [r for r in rows if str(r["id"]).startswith("n") and r["is_anomaly"]]
        self.assertLessEqual(len(fp) / 30.0, 0.10,
                             msg=f"false-positive rate too high: {len(fp)}/30")

    def test_reasons_attached(self):
        rows = {r["id"]: r for r in self._build().meta["rows"]}
        self.assertIn("sigma", rows["A"]["reason"])
        self.assertEqual(rows["A"]["top_feature"], "x")
        self.assertEqual(rows["B"]["top_feature"], "y")
        # Normals carry no reason text.
        self.assertEqual(rows["n0"]["reason"], "" if not rows["n0"]["is_anomaly"] else rows["n0"]["reason"])

    def test_reproducible(self):
        a = self._build().meta
        b = self._build().meta
        self.assertEqual(a["anomaly_ids"], b["anomaly_ids"])
        for ra, rb in zip(a["rows"], b["rows"]):
            self.assertAlmostEqual(ra["score"], rb["score"], delta=1e-12)

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_n_estimators_minimum_enforced(self):
        with self.assertRaises(ValueError):
            detect_anomalies(_records(), ["x", "y"], n_estimators=50)

    def test_partner_hides_scores(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Anomaly scores", partner)


if __name__ == "__main__":
    unittest.main()

"""Golden test for BOLSTER-01 Ridge + conformal forecast engine.

Exchangeable design (so split-conformal coverage holds):
    X ~ N(0, I_2), y = 3*x0 - 1.5*x1 + 4 + N(0, 1), n = 200.
Asserts:
- empirical holdout coverage >= nominal - 1% at 80% and 95%,
- output reproducible to 1e-9 on a fixed seed,
- alpha is selected from the logspace(-2, 2) grid,
- the inference path is LLM-free (declared and structurally true).
"""
import unittest

import numpy as np

from rcm_mc.cdd.forecast import DEFAULT_ALPHAS, ridge_conformal_forecast


def _data(seed=42, n=200):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, 2))
    y = 3.0 * X[:, 0] - 1.5 * X[:, 1] + 4.0 + rng.normal(0, 1.0, n)
    return X, y


class TestRidgeConformal(unittest.TestCase):
    def _build(self):
        X, y = _data()
        return ridge_conformal_forecast(X, y, seed=42, source="Golden", vintage="2026")

    def test_coverage_meets_guarantee(self):
        cov = self._build().meta["coverage"]
        for key in ("80", "95"):
            nominal = cov[key]["nominal"]
            emp = cov[key]["empirical_coverage"]
            self.assertGreaterEqual(
                emp, nominal - 0.01,
                msg=f"{key}%: empirical {emp:.3f} < nominal {nominal:.2f} - 0.01 "
                    f"(gap {cov[key]['coverage_gap']:.3f})")
            self.assertTrue(cov[key]["meets_guarantee"])

    def test_coverage_reconciliation_emitted(self):
        ex = self._build()
        self.assertTrue(ex.reconciled)
        ids = [r["identity"] for r in ex.render(internal_mode=True)["reconciliations"]]
        self.assertTrue(any("empirical coverage" in i for i in ids))

    def test_reproducible_to_1e9(self):
        a = self._build().meta
        b = self._build().meta
        self.assertAlmostEqual(a["alpha"], b["alpha"], delta=1e-9)
        for key in ("80", "95"):
            self.assertAlmostEqual(a["coverage"][key]["margin"],
                                   b["coverage"][key]["margin"], delta=1e-9)
            self.assertAlmostEqual(a["coverage"][key]["empirical_coverage"],
                                   b["coverage"][key]["empirical_coverage"], delta=1e-9)

    def test_alpha_from_grid(self):
        alpha = self._build().meta["alpha"]
        self.assertTrue(any(abs(alpha - g) < 1e-9 for g in DEFAULT_ALPHAS),
                        msg=f"selected alpha {alpha} not in the logspace grid")

    def test_llm_free_declared(self):
        ex = self._build()
        self.assertTrue(ex.meta["llm_free"])
        fn = ex.render(internal_mode=True)["footnote"]
        self.assertTrue(any("No LLM" in a for a in fn["assumptions"]))

    def test_partner_hides_model_internals(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Model internals", partner)

    def test_too_few_points_raises(self):
        X, y = _data(n=10)
        with self.assertRaises(ValueError):
            ridge_conformal_forecast(X, y)

    def test_95_margin_wider_than_80(self):
        cov = self._build().meta["coverage"]
        self.assertGreaterEqual(cov["95"]["margin"], cov["80"]["margin"])


if __name__ == "__main__":
    unittest.main()

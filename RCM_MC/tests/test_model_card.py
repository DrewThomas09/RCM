"""B workstream — margin-model holdout card: artifact schema + UI claim.

The /methodology coverage claim must come from the checked-in eval artifact
(scripts/eval_margin_model.py → rcm_mc/ml/model_card_margin.json), never a
hand-typed number, and must name the engine correctly.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

_CARD = Path(__file__).resolve().parent.parent / "rcm_mc" / "ml" / "model_card_margin.json"


class ArtifactTests(unittest.TestCase):
    def test_card_exists_with_required_schema(self):
        self.assertTrue(_CARD.exists(), "run scripts/eval_margin_model.py")
        c = json.loads(_CARD.read_text())
        for key in ("model", "nominal_coverage", "empirical_holdout_coverage",
                    "conformal_half_width", "holdout_mae", "n_train", "n_test",
                    "data_vintage", "eval_seed", "script", "limitations"):
            self.assertIn(key, c)

    def test_coverage_near_nominal(self):
        c = json.loads(_CARD.read_text())
        # Split conformal at 90% should land in a sane finite-sample band on
        # a ~1k holdout; far outside means the pipeline broke.
        self.assertGreaterEqual(c["empirical_holdout_coverage"], 0.85)
        self.assertLessEqual(c["empirical_holdout_coverage"], 0.97)
        self.assertEqual(c["nominal_coverage"], 0.90)

    def test_engine_named_correctly(self):
        c = json.loads(_CARD.read_text())
        self.assertEqual(c["model"],
                         "Ridge regression with split-conformal intervals")


class MethodologyPanelTests(unittest.TestCase):
    def test_panel_states_the_artifact_numbers(self):
        from rcm_mc.ui.methodology_page import render_methodology
        c = json.loads(_CARD.read_text())
        h = render_methodology()
        self.assertIn("holdout model card", h)
        self.assertIn(f'{c["empirical_holdout_coverage"]*100:.1f}%', h)
        self.assertIn("Ridge regression with split-conformal intervals", h)
        self.assertIn("eval_margin_model.py", h)   # reproducibility path
        self.assertIn(str(c["n_test"]), h.replace(",", ""))


if __name__ == "__main__":
    unittest.main()

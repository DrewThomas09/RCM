"""Tests for the optional ML-surrogate stub functions.

`rcm_mc/analysis/surrogate.py` is a 47-line module reserved for a
future fast surrogate / ML layer that's NOT yet wired into the
main CLI or report. The 2 public functions are stubs intended to
hold a documented contract:

  - predict_mean_ebitda_drag_stub(_features) → Optional[float]
    Returns None until a real model lands. Locks the 'partner
    sees a value or sees nothing' contract — never a fabricated
    number from an untrained model.
  - training_data_schema() → Dict[str, Any]
    Documents the expected columns for a future training export.
    The schema strings drive what a future training-export script
    would emit; changing them silently would silently change the
    training data shape.

Stubs need locking BEFORE a real model lands so the swap doesn't
silently change the contract the rest of the platform was built
against.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.surrogate import (
    predict_mean_ebitda_drag_stub,
    training_data_schema,
)


class PredictMeanEbitdaDragStubTests(unittest.TestCase):
    """The stub MUST return None until a real model is wired —
    the rest of the platform treats None as 'no surrogate
    prediction available', which is the only honest answer from
    an untrained model."""

    def test_returns_none_for_any_features(self):
        for features in [
            {},
            {"payer.Medicare.idr.mean": 0.1},
            {"hospital.annual_revenue": 1e9,
             "payers.Commercial.denials.idr.mean": 0.08},
            {"a": 1.0, "b": 2.0, "c": 3.0},
        ]:
            self.assertIsNone(
                predict_mean_ebitda_drag_stub(features),
                f"stub returned non-None for {features!r}")

    def test_returns_none_for_empty_dict(self):
        self.assertIsNone(predict_mean_ebitda_drag_stub({}))

    def test_returns_none_does_not_raise_on_unexpected_input(self):
        # The function is a guardrail — should never crash regardless
        # of what's passed in. Tolerating bad input is preferable to
        # raising during a fast 'what-if' screen.
        self.assertIsNone(predict_mean_ebitda_drag_stub({"nan": float("nan")}))


class TrainingDataSchemaTests(unittest.TestCase):
    """The schema dict documents the contract a future training-
    export script would emit. Lock the shape so the future export
    + the future trainer agree on column names."""

    def test_returns_dict(self):
        out = training_data_schema()
        self.assertIsInstance(out, dict)

    def test_has_documented_keys(self):
        out = training_data_schema()
        # Documented contract — every key MUST be present.
        for k in ("description", "suggested_targets",
                  "suggested_features", "source_artifacts"):
            self.assertIn(k, out, f"missing schema key {k!r}")

    def test_description_is_non_empty_string(self):
        out = training_data_schema()
        self.assertIsInstance(out["description"], str)
        self.assertTrue(out["description"].strip())

    def test_suggested_targets_includes_ebitda_drag_metrics(self):
        # Documented headline targets — partners would expect to
        # surface mean_ebitda_drag and p90_ebitda_drag.
        out = training_data_schema()
        self.assertIn("mean_ebitda_drag", out["suggested_targets"])
        self.assertIn("p90_ebitda_drag", out["suggested_targets"])

    def test_suggested_features_uses_dotted_paths(self):
        # The platform's config is a nested dict; suggested feature
        # keys use dotted paths to address the leaves. Lock that
        # convention — changing it would invalidate a future
        # exporter.
        out = training_data_schema()
        feats = out["suggested_features"]
        self.assertGreater(len(feats), 0)
        for f in feats:
            self.assertIn(".", f, f"feature {f!r} missing dotted path")

    def test_source_artifacts_match_simulator_outputs(self):
        # The simulator writes these three files; if a column-export
        # script is added it should read from THESE three files.
        out = training_data_schema()
        self.assertIn("simulations.csv", out["source_artifacts"])
        self.assertIn("summary.csv", out["source_artifacts"])

    def test_returns_a_new_dict_each_call(self):
        # Defensive: callers can safely mutate the returned dict
        # without polluting a shared reference (next caller sees
        # the original schema).
        a = training_data_schema()
        b = training_data_schema()
        a["mutated"] = "x"
        self.assertNotIn("mutated", b)


if __name__ == "__main__":
    unittest.main()

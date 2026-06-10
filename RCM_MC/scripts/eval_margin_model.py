#!/usr/bin/env python3
"""Holdout evaluation of the margin predictor — writes the model card.

Freezes a seeded 20% outer holdout the model NEVER sees, trains the
production path (rcm_mc.ml.margin_predictor.train_margin_model — ridge
regression with split-conformal intervals) on the remaining 80%, then
reports on the holdout:

  - empirical coverage of the 90% conformal band  (the headline claim)
  - MAE / median absolute error of the point prediction
  - n_train / n_test, features used, train R²
  - data vintage (HCRIS FY range) + run date

Output: rcm_mc/ml/model_card_margin.json — consumed by the /methodology
model-card panel, so the UI's coverage claim is reproducible by re-running
this script (no hand-typed numbers).

Usage: python3 scripts/eval_margin_model.py [--seed 7] [--test-frac 0.2]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rcm_mc.data.hcris import _get_latest_per_ccn          # noqa: E402
from rcm_mc.ml.margin_predictor import (                    # noqa: E402
    _FEATURE_COLS, _engineer_features, train_margin_model,
)
from rcm_mc.ui.regression_page import _add_computed_features  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--test-frac", type=float, default=0.20)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent
                                         / "rcm_mc" / "ml" / "model_card_margin.json"))
    args = ap.parse_args()

    raw = _get_latest_per_ccn()
    # Same feature pipeline production uses: the regression page's computed
    # columns (margin/occupancy/n2g with the plausibility gates) + the margin
    # predictor's own engineered features on top.
    df = _engineer_features(_add_computed_features(raw))
    target = "operating_margin"
    available = [f for f in _FEATURE_COLS if f in df.columns]
    clean = df.dropna(subset=[target] + available).copy()
    clean = clean[clean[target].between(-1, 1)]

    rng = np.random.RandomState(args.seed)
    perm = rng.permutation(len(clean))
    n_test = int(len(clean) * args.test_frac)
    test_idx, train_idx = perm[:n_test], perm[n_test:]
    test, train = clean.iloc[test_idx], clean.iloc[train_idx]

    model = train_margin_model(train)
    if model.n == 0:
        print("training failed — no model card written", file=sys.stderr)
        return 1

    X = test[model.features_used].values.astype(float)
    Xn = (X - model.x_mean) / model.x_std
    Xa = np.column_stack([np.ones(len(Xn)), Xn])
    y = test[target].values.astype(float)
    y_hat = Xa @ model.beta

    resid = np.abs(y - y_hat)
    coverage = float((resid <= model.conformal_margin).mean())
    card = {
        "model": "Ridge regression with split-conformal intervals",
        "target": "operating_margin (HCRIS, latest filing per CCN)",
        "nominal_coverage": 0.90,
        "empirical_holdout_coverage": round(coverage, 4),
        "conformal_half_width": round(float(model.conformal_margin), 4),
        "holdout_mae": round(float(resid.mean()), 4),
        "holdout_median_ae": round(float(np.median(resid)), 4),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "train_r2": float(model.r2),
        "features": list(model.features_used),
        "data_vintage": f"HCRIS FY{int(raw['fiscal_year'].min())}–"
                        f"{int(raw['fiscal_year'].max())} filings",
        "eval_seed": args.seed,
        "eval_date": date.today().isoformat(),
        "script": "scripts/eval_margin_model.py",
        "limitations": [
            "Cross-sectional model: predicts a hospital's margin from peer "
            "structure, not its own trajectory.",
            "Trained on filings that pass the plausible-margin screen "
            "(|margin| ≤ 100%); junk-opex filings excluded.",
            "Conformal band assumes exchangeability of filings; structural "
            "breaks (payer-mix shocks, ownership changes) void it.",
        ],
    }
    Path(args.out).write_text(json.dumps(card, indent=2) + "\n")
    print(f"coverage {coverage:.1%} (nominal 90%) · MAE {card['holdout_mae']:.4f} "
          f"· n_test {n_test} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

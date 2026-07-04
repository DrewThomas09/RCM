"""
recovery_model.py  (v43)
========================

A calibrated probability that a recovered billing NPI is correct, learned from
the toolkit's own back-test folds, built to be measured against the incumbent
confidence rather than assumed better.

Why not a black box. The incumbent confidence is tier_weight times dominance: a
hand-set product. It ranks reasonably but is not guaranteed to be calibrated (a
stated 0.8 need not hit 80 percent), and the tier weights are fixed constants, not
learned from the data in front of you. The improvement is to learn how much each
piece of evidence is actually worth on THIS file and to calibrate the output so a
stated probability means what it says.

Why it stays defensible. The model is a logistic regression over a short list of
interpretable evidence signals, then an isotonic recalibration. No embeddings, no
trees, no opacity. Every score decomposes into per-signal contributions
(coefficient times standardized feature), so "why is this 0.86" has a real answer
you can put in front of a seller. It is hand-rolled: the logistic fit is a plain
Newton-IRLS on numpy, the calibration is pool-adjacent-violators isotonic
regression, both in this file, no sklearn dependency.

The evidence signals (all already produced per prediction by impute.py):
  purity        dominance of the winning biller for the matched key (score)
  margin        purity gap between the winner and runner-up
  log_support   log1p of the observation count behind the key
  tier_rank     how specific the matched key was (1 = full key, higher = coarser)
  is_in_panel   matched an in-file pattern (1) vs a CMS candidate pool (0)
  tax_coherent  recovered NPI's taxonomy is consistent with the billed drug/HCPCS
                (1 coherent, 0 incoherent, 0.5 unknown); see taxonomy_coherence

Head-to-head is the product. fit_and_compare() trains on masked folds, scores the
held-out rows, and reports Brier / ECE / AUC for BOTH the incumbent confidence and
the calibrated model on the same rows. If the model does not win, that is the
finding, and the deterministic path stays the default.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import prob_calibration as C

FEATURES = ["purity", "margin", "log_support", "tier_rank", "is_in_panel",
            "tax_coherent"]


# --------------------------------------------------------------------------- #
# hand-rolled logistic regression (Newton-IRLS), L2-regularized, numpy only
# --------------------------------------------------------------------------- #
class _Logit:
    def __init__(self, l2=1.0, iters=50, tol=1e-8):
        self.l2 = l2
        self.iters = iters
        self.tol = tol
        self.beta = None
        self.mu = None
        self.sd = None

    def _standardize(self, X, fit):
        if fit:
            self.mu = X.mean(axis=0)
            self.sd = X.std(axis=0)
            self.sd[self.sd == 0] = 1.0
        return (X - self.mu) / self.sd

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        Xs = self._standardize(X, fit=True)
        Xs = np.hstack([np.ones((len(Xs), 1)), Xs])  # intercept
        n, p = Xs.shape
        beta = np.zeros(p)
        ridge = self.l2 * np.eye(p)
        ridge[0, 0] = 0.0  # do not penalize intercept
        for _ in range(self.iters):
            eta = Xs @ beta
            mu = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
            W = np.clip(mu * (1 - mu), 1e-6, None)
            grad = Xs.T @ (y - mu) - ridge @ beta
            H = Xs.T @ (Xs * W[:, None]) + ridge
            try:
                step = np.linalg.solve(H, grad)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(H, grad, rcond=None)[0]
            beta = beta + step
            if np.max(np.abs(step)) < self.tol:
                break
        self.beta = beta
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        Xs = self._standardize(X, fit=False)
        Xs = np.hstack([np.ones((len(Xs), 1)), Xs])
        eta = Xs @ self.beta
        return 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))

    def contributions(self, X):
        """Per-feature standardized contribution (coefficient times standardized
        value) for each row, so a score can be explained."""
        X = np.asarray(X, dtype=float)
        Xs = self._standardize(X, fit=False)
        contrib = Xs * self.beta[1:]
        return pd.DataFrame(contrib, columns=FEATURES)


# --------------------------------------------------------------------------- #
# isotonic regression (pool adjacent violators) for recalibration
# --------------------------------------------------------------------------- #
class _Isotonic:
    def __init__(self):
        self.x = None
        self.y = None

    def fit(self, x, y, w=None):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        w = np.ones_like(x) if w is None else np.asarray(w, dtype=float)
        order = np.argsort(x, kind="mergesort")
        x, y, w = x[order], y[order], w[order]
        # PAV
        yv = y.copy()
        wv = w.copy()
        blocks = list(range(len(yv)))
        i = 0
        vals = list(yv)
        wts = list(wv)
        xs = list(x)
        out_y = []
        out_w = []
        out_x = []
        for k in range(len(vals)):
            cy = vals[k]
            cw = wts[k]
            cx = xs[k]
            while out_y and out_y[-1] >= cy:
                py = out_y.pop()
                pw = out_w.pop()
                out_x.pop()
                cy = (py * pw + cy * cw) / (pw + cw)
                cw = pw + cw
            out_y.append(cy)
            out_w.append(cw)
            out_x.append(cx)
        # expand block means back onto sorted x knots
        self.x = np.array(out_x)
        self.y = np.array(out_y)
        return self

    def predict(self, x):
        x = np.asarray(x, dtype=float)
        if self.x is None or len(self.x) == 0:
            return x
        return np.interp(x, self.x, self.y, left=self.y[0], right=self.y[-1])


# --------------------------------------------------------------------------- #
# feature extraction from a prediction frame
# --------------------------------------------------------------------------- #
# lower tier_rank = more specific key. Map tier names to a rank if present.
def _tier_rank_map():
    try:
        from . import config
        return {t["name"]: i + 1 for i, t in enumerate(config.IMPUTE_TIERS)}
    except Exception:
        return {}


def build_features(pred: pd.DataFrame, std: pd.DataFrame = None,
                   ref_dir=None, mapping=None) -> pd.DataFrame:
    """Turn a prediction frame (impute.py output) into the model feature matrix.
    Missing signals degrade to neutral values so the model still runs."""
    rank = _tier_rank_map()
    n = len(pred)
    purity = pd.to_numeric(pred.get("confidence"), errors="coerce")
    # confidence is tier_weight * score; recover a rough purity by using it directly
    # as the dominance proxy when a separate score is absent
    if "score" in pred.columns:
        purity = pd.to_numeric(pred["score"], errors="coerce")
    margin = pd.to_numeric(pred.get("margin"), errors="coerce")
    support = pd.to_numeric(pred.get("support"), errors="coerce")
    tier = pred.get("tier", pd.Series(["none"] * n))
    tier_rank = tier.map(lambda t: rank.get(t, len(rank) + 1 if rank else 6)).astype(float)
    src = pred.get("tier_source", pd.Series([""] * n))
    is_in_panel = (src.astype(str) == "in_panel").astype(float)

    feats = pd.DataFrame({
        "purity": purity.fillna(0.0).clip(0, 1).to_numpy(),
        "margin": margin.fillna(0.0).clip(0, 1).to_numpy(),
        "log_support": np.log1p(support.fillna(0.0).clip(lower=0).to_numpy()),
        "tier_rank": tier_rank.fillna(float(len(rank) + 1 if rank else 6)).to_numpy(),
        "is_in_panel": is_in_panel.to_numpy(),
    })
    # taxonomy coherence: 0.5 neutral unless we can compute it. v48 prefers the
    # graded specialty-drug plausibility model over the binary taxonomy gate.
    tax = np.full(n, 0.5)
    if std is not None and "recovered_npi" in pred.columns:
        got = False
        try:
            from . import specialty_drug as SD
            _model = ctx_model if (ctx_model := None) else SD.default_model()
            _p = SD.plausibility_series(pred, std, _model, mapping=mapping).to_numpy()
            # only adopt where the model actually had an opinion (not all-neutral)
            if np.any(_p != 0.5):
                tax = _p
                got = True
        except Exception:
            got = False
        if not got:
            try:
                from . import taxonomy_coherence as TC
                tax = TC.coherence_series(pred, std, ref_dir=ref_dir, mapping=mapping).to_numpy()
            except Exception:
                pass
    feats["tax_coherent"] = tax
    return feats[FEATURES]


# --------------------------------------------------------------------------- #
# the trainable, calibrated scorer
# --------------------------------------------------------------------------- #
class CalibratedRecoveryModel:
    def __init__(self, l2=1.0):
        self.logit = _Logit(l2=l2)
        self.iso = _Isotonic()
        self.fitted = False

    def fit(self, feats: pd.DataFrame, correct):
        X = feats[FEATURES].to_numpy(dtype=float)
        y = pd.Series(correct).astype(float).to_numpy()
        self.logit.fit(X, y)
        raw = self.logit.predict_proba(X)
        self.iso.fit(raw, y)
        self.fitted = True
        return self

    def predict_proba(self, feats: pd.DataFrame):
        X = feats[FEATURES].to_numpy(dtype=float)
        raw = self.logit.predict_proba(X)
        return self.iso.predict(raw)

    def explain(self, feats: pd.DataFrame) -> pd.DataFrame:
        return self.logit.contributions(feats)


def fit_and_compare(holdout: pd.DataFrame, std: pd.DataFrame = None, ref_dir=None,
                    mapping=None, seed=7, n_bins=10) -> dict:
    """Train the calibrated model on half the held-out rows and score the other
    half, then report Brier / ECE / AUC for the incumbent confidence AND the model
    on the SAME evaluation rows. holdout must carry the incumbent 'confidence',
    the 0/1 't1' outcome, dollar 'amt', and the prediction evidence columns.

    Returns both reports and a verdict on whether the model wins.
    """
    df = holdout.reset_index(drop=True).copy()
    if "t1" not in df.columns:
        return {"status": "no_outcome_column"}
    y = df["t1"].astype(float).to_numpy()
    w = pd.to_numeric(df.get("amt", 1.0), errors="coerce").fillna(0.0).to_numpy()
    if len(df) < 80 or y.sum() < 5 or (len(y) - y.sum()) < 5:
        return {"status": "insufficient_holdout", "n": int(len(df))}

    feats = build_features(df, std=std, ref_dir=ref_dir, mapping=mapping)
    rng = np.random.default_rng(seed)
    half = rng.random(len(df)) < 0.5
    tr, ev = half, ~half
    # guard against a degenerate split
    if y[tr].sum() < 3 or y[ev].sum() < 3 or (1 - y[tr]).sum() < 3 or (1 - y[ev]).sum() < 3:
        tr = ev = np.ones(len(df), dtype=bool)

    model = CalibratedRecoveryModel().fit(feats[tr], y[tr])
    p_model = model.predict_proba(feats[ev])
    p_incum = pd.to_numeric(df.get("confidence"), errors="coerce").fillna(0.0).to_numpy()[ev]
    ye, we = y[ev], w[ev]

    rep_incum = C.calibration_report(p_incum, ye, weight=we, n_bins=n_bins,
                                     label="incumbent_confidence")
    rep_model = C.calibration_report(p_model, ye, weight=we, n_bins=n_bins,
                                     label="calibrated_model")

    better_brier = (rep_model["brier"] is not None and rep_incum["brier"] is not None
                    and rep_model["brier"] < rep_incum["brier"])
    better_ece = (not np.isnan(rep_model["ece"]) and not np.isnan(rep_incum["ece"])
                  and rep_model["ece"] < rep_incum["ece"])
    better_auc = (not np.isnan(rep_model["auc"]) and not np.isnan(rep_incum["auc"])
                  and rep_model["auc"] >= rep_incum["auc"])
    wins = better_brier and better_ece

    coefs = pd.DataFrame({"feature": FEATURES,
                          "coefficient": np.round(model.logit.beta[1:], 4)})
    return {
        "status": "ok", "n_eval": int(ev.sum()),
        "incumbent": rep_incum, "model": rep_model,
        "model_wins": bool(wins),
        "delta_brier": (None if rep_model["brier"] is None else
                        round(rep_incum["brier"] - rep_model["brier"], 4)),
        "delta_ece": round(rep_incum["ece"] - rep_model["ece"], 4)
        if not np.isnan(rep_model["ece"]) else None,
        "delta_auc": round(rep_model["auc"] - rep_incum["auc"], 4)
        if not np.isnan(rep_model["auc"]) else None,
        "coefficients": coefs,
        "verdict": (
            "Calibrated model beats incumbent confidence on Brier and ECE; "
            "recommend using it for the reported probability."
            if wins else
            "Calibrated model does not beat the incumbent on both Brier and ECE; "
            "keep the deterministic confidence as the reported number."),
    }

"""Naive Bayes denial model — stdlib-only.

Model form:
    P(denial=1 | features)
        ∝ P(denial=1) × ∏_f P(f | denial=1)

with Laplace (+1) smoothing on every feature's empirical
denial-rate estimate to handle zero-count categories.

Why Naive Bayes, not logistic regression or random forest:
    1. **Interpretable** — each feature's contribution is a single
       probability ratio. Partners can read "CPT 99285 × UHC
       contributes +0.18 to denial odds" straight off the model.
    2. **No dependencies** — logistic regression needs an
       optimiser; scikit-learn isn't permitted by the repo's
       zero-dep rule.
    3. **Calibrates reasonably** on RCM data — denial events are
       well-characterised by the CPT × payer interaction which
       Naive Bayes captures cleanly.
    4. **Handles small fixtures** — the kpi_truth suite has 10-50
       claims per hospital; Naive Bayes doesn't overfit at that
       scale the way logistic regression with many features would.

Limitations acknowledged in the docstrings that consumers see:
    - Assumes feature independence (the N in NB). Payer × CPT
      correlation is real; the model underestimates denial risk
      when a payer × CPT combination is systematically refused
      vs. predicted by the marginals.
    - Point estimate, not a distribution. For uncertainty bands
      we'd bootstrap — not implemented here; the Brier score and
      calibration plot are the quality signals.

API:
    model = train_naive_bayes(claims_train)
    probs = [model.predict_proba(c) for c in claims_test]
    brier, reliability = calibration_report(model, claims_test)
    save_model(model, path) / load_model(path)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


LAPLACE_ALPHA = 1.0          # smoothing strength


@dataclass
class NaiveBayesDenialModel:
    """Fitted model. Every field is JSON-serialisable."""
    prior_denial: float = 0.10
    prior_not_denial: float = 0.90

    # per-feature conditional probabilities:
    # feat_name → { feat_value → (P(v|denial=1), P(v|denial=0)) }
    feature_probs: Dict[str, Dict[str, Tuple[float, float]]] = \
        field(default_factory=dict)

    # Count of each feature's observed categories (for fallback
    # smoothing when a predict-time value hasn't been seen).
    feature_category_count: Dict[str, int] = field(default_factory=dict)

    n_train: int = 0
    n_train_denied: int = 0
    n_train_paid: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prior_denial": self.prior_denial,
            "prior_not_denial": self.prior_not_denial,
            "feature_probs": {
                feat: {
                    val: list(probs) for val, probs in vmap.items()
                }
                for feat, vmap in self.feature_probs.items()
            },
            "feature_category_count":
                dict(self.feature_category_count),
            "n_train": self.n_train,
            "n_train_denied": self.n_train_denied,
            "n_train_paid": self.n_train_paid,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NaiveBayesDenialModel":
        m = cls(
            prior_denial=float(d.get("prior_denial", 0.1)),
            prior_not_denial=float(d.get("prior_not_denial", 0.9)),
            feature_probs={
                feat: {
                    val: tuple(probs) for val, probs in vmap.items()
                }
                for feat, vmap in (d.get("feature_probs") or {}).items()
            },
            feature_category_count=dict(
                d.get("feature_category_count") or {},
            ),
            n_train=int(d.get("n_train", 0) or 0),
            n_train_denied=int(d.get("n_train_denied", 0) or 0),
            n_train_paid=int(d.get("n_train_paid", 0) or 0),
        )
        return m

    def predict_proba(self, features: Dict[str, str]) -> float:
        """Return P(denial=1 | features). Uses log-space to avoid
        underflow on long feature vectors."""
        if self.prior_denial <= 0:
            return 0.0
        log_d = math.log(max(self.prior_denial, 1e-10))
        log_nd = math.log(max(self.prior_not_denial, 1e-10))
        for feat, val in features.items():
            vmap = self.feature_probs.get(feat)
            if not vmap:
                continue
            if val in vmap:
                p_d, p_nd = vmap[val]
            else:
                # Unseen category — Laplace-smooth against the
                # full-category prior.
                k = max(self.feature_category_count.get(feat, 1), 1)
                p_d = LAPLACE_ALPHA / (
                    max(self.n_train_denied, 0) + LAPLACE_ALPHA * (k + 1)
                )
                p_nd = LAPLACE_ALPHA / (
                    max(self.n_train_paid, 0) + LAPLACE_ALPHA * (k + 1)
                )
            log_d += math.log(max(p_d, 1e-10))
            log_nd += math.log(max(p_nd, 1e-10))
        # Convert log-odds to probability.
        max_lp = max(log_d, log_nd)
        exp_d = math.exp(log_d - max_lp)
        exp_nd = math.exp(log_nd - max_lp)
        denom = exp_d + exp_nd
        return exp_d / denom if denom > 0 else 0.0

    def top_features_by_denial_lift(
        self, k: int = 10,
    ) -> List[Tuple[str, str, float]]:
        """Return the top-k (feature, value, lift) triples where
        lift = P(v | denial=1) / P(v | denial=0). Used for the
        "here's where to act" section of the diligence memo."""
        out: List[Tuple[str, str, float]] = []
        for feat, vmap in self.feature_probs.items():
            for val, (p_d, p_nd) in vmap.items():
                if p_nd <= 0:
                    continue
                lift = p_d / p_nd
                out.append((feat, val, lift))
        out.sort(key=lambda t: -t[2])
        return out[:k]


def train_naive_bayes(
    labelled_claims: Sequence[Tuple[Dict[str, str], bool]],
) -> NaiveBayesDenialModel:
    """Fit the NB model on a sequence of (features_dict, is_denied)
    pairs. Laplace smoothing handles zero counts."""
    n = len(labelled_claims)
    if n == 0:
        return NaiveBayesDenialModel()
    denied = [f for f, d in labelled_claims if d]
    paid = [f for f, d in labelled_claims if not d]
    prior_d = len(denied) / n
    prior_nd = 1 - prior_d

    # Collect categories.
    categories: Dict[str, set] = {}
    for features, _ in labelled_claims:
        for feat, val in features.items():
            categories.setdefault(feat, set()).add(str(val))

    feature_probs: Dict[str, Dict[str, Tuple[float, float]]] = {}
    for feat, vals in categories.items():
        k = len(vals)                              # categories
        vmap: Dict[str, Tuple[float, float]] = {}
        for val in vals:
            cnt_d = sum(
                1 for f in denied if str(f.get(feat, "")) == val
            )
            cnt_nd = sum(
                1 for f in paid if str(f.get(feat, "")) == val
            )
            # Laplace: (count + alpha) / (total + alpha × categories)
            p_d = (cnt_d + LAPLACE_ALPHA) / (
                len(denied) + LAPLACE_ALPHA * k
            ) if (len(denied) + LAPLACE_ALPHA * k) > 0 else 0.0
            p_nd = (cnt_nd + LAPLACE_ALPHA) / (
                len(paid) + LAPLACE_ALPHA * k
            ) if (len(paid) + LAPLACE_ALPHA * k) > 0 else 0.0
            vmap[val] = (p_d, p_nd)
        feature_probs[feat] = vmap

    return NaiveBayesDenialModel(
        prior_denial=prior_d,
        prior_not_denial=prior_nd,
        feature_probs=feature_probs,
        feature_category_count={
            f: len(v) for f, v in categories.items()
        },
        n_train=n,
        n_train_denied=len(denied),
        n_train_paid=len(paid),
    )


# ── Calibration ────────────────────────────────────────────────────

@dataclass
class CalibrationBucket:
    lower: float
    upper: float
    count: int
    predicted_mean: float
    actual_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class CalibrationReport:
    brier_score: float
    log_loss: float
    accuracy: float
    auc_rough: float                           # 2×MWU-approximation
    buckets: List[CalibrationBucket] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "accuracy": self.accuracy,
            "auc_rough": self.auc_rough,
            "buckets": [b.to_dict() for b in self.buckets],
        }


def calibration_report(
    model: NaiveBayesDenialModel,
    labelled_claims: Sequence[Tuple[Dict[str, str], bool]],
    n_buckets: int = 10,
) -> CalibrationReport:
    """Produce Brier score, log loss, accuracy, an AUC approximation
    (via Mann-Whitney-U-style rank-sum), and a reliability
    diagram. Partners read these to decide whether to trust the
    model's outputs.

    The AUC approximation uses the Mann-Whitney-U identity:
        AUC = P(score_denied > score_paid)
    computed by pairwise comparison. O(n_d × n_p) but fine for
    diligence-scale datasets (~100k claims)."""
    if not labelled_claims:
        return CalibrationReport(
            brier_score=0, log_loss=0, accuracy=0, auc_rough=0.5,
        )
    scores = [
        (model.predict_proba(f), d)
        for f, d in labelled_claims
    ]
    n = len(scores)
    # Brier + log-loss + accuracy.
    brier = sum((p - int(d)) ** 2 for p, d in scores) / n
    log_loss = -sum(
        int(d) * math.log(max(p, 1e-10)) +
        (1 - int(d)) * math.log(max(1 - p, 1e-10))
        for p, d in scores
    ) / n
    correct = sum(
        1 for p, d in scores
        if (p >= 0.5) == bool(d)
    )
    accuracy = correct / n

    # Rough AUC: average rank of denied > paid.
    denied = [p for p, d in scores if d]
    paid = [p for p, d in scores if not d]
    if denied and paid:
        wins = sum(
            1 for pd in denied for pp in paid if pd > pp
        )
        ties = sum(
            1 for pd in denied for pp in paid if pd == pp
        )
        auc = (wins + 0.5 * ties) / (len(denied) * len(paid))
    else:
        auc = 0.5

    # Reliability buckets.
    step = 1.0 / n_buckets
    buckets: List[CalibrationBucket] = []
    for i in range(n_buckets):
        lo = i * step
        hi = (i + 1) * step
        in_bucket = [
            (p, d) for p, d in scores
            if lo <= p < hi or (i == n_buckets - 1 and p == 1.0)
        ]
        if not in_bucket:
            buckets.append(CalibrationBucket(
                lower=lo, upper=hi, count=0,
                predicted_mean=0.0, actual_rate=0.0,
            ))
            continue
        predicted_mean = sum(p for p, _ in in_bucket) / len(in_bucket)
        actual_rate = sum(int(d) for _, d in in_bucket) / len(in_bucket)
        buckets.append(CalibrationBucket(
            lower=lo, upper=hi, count=len(in_bucket),
            predicted_mean=predicted_mean,
            actual_rate=actual_rate,
        ))
    return CalibrationReport(
        brier_score=brier, log_loss=log_loss,
        accuracy=accuracy, auc_rough=auc,
        buckets=buckets,
    )


# ── Persistence ────────────────────────────────────────────────────

def save_model(model: NaiveBayesDenialModel, path: Any) -> None:
    Path(path).write_text(json.dumps(model.to_dict()), "utf-8")


def load_model(path: Any) -> NaiveBayesDenialModel:
    d = json.loads(Path(path).read_text("utf-8"))
    return NaiveBayesDenialModel.from_dict(d)

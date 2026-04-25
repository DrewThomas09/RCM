"""Propensity-score matching with caliper-NN.

Pipeline:

  1. Concatenate (corpus, target) as a single dataset; label =
     1 for the target, 0 for corpus deals (single-target
     "treatment" indicator).
  2. Fit logistic regression: P(treatment | covariates).
  3. Compute propensity scores for every row.
  4. Caliper-NN match: rank corpus deals by |p_corpus − p_target|;
     return the top-K within an absolute-distance caliper.

This is the textbook treatment-effects approach (Rosenbaum &
Rubin, 1983) and the standard for "rigorous comp set" claims in
diligence packets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .logistic import LogisticRegression, fit_logistic
from .features import FeatureVector


@dataclass
class PSMConfig:
    caliper: float = 0.10           # absolute propensity-score distance
    k_matches: int = 15
    l2_penalty: float = 0.01
    learning_rate: float = 0.05
    max_iter: int = 500


@dataclass
class PSMResult:
    """Output of a PSM run."""
    propensity_scores: np.ndarray   # (n_corpus,)
    target_propensity: float
    matches: List[Tuple[FeatureVector, float, float]]
        # (deal, propensity_distance, similarity_weight)
    model: LogisticRegression


def fit_propensity_scores(
    corpus: List[FeatureVector],
    target: FeatureVector,
    *,
    l2_penalty: float = 0.01,
    learning_rate: float = 0.05,
    max_iter: int = 500,
) -> Tuple[np.ndarray, float, LogisticRegression]:
    """Fit a logistic-regression treatment classifier and return
    the per-corpus propensity score + target's propensity.

    Returns: (corpus_propensities, target_propensity, model)
    """
    if not corpus:
        raise ValueError("Empty corpus")

    # Build matrix + labels — but a single "treatment" deal is a
    # rank-deficient classification problem (1 positive vs N
    # negatives). We mitigate by adding small label-smoothing
    # noise to the target rows (replicate the target 5× to give
    # the optimizer something to balance against).
    target_replicas = 5
    n_corpus = len(corpus)
    X = np.vstack(
        [fv.vector for fv in corpus]
        + [target.vector for _ in range(target_replicas)]
    )
    y = np.concatenate(
        [np.zeros(n_corpus), np.ones(target_replicas)]
    )

    model = fit_logistic(
        X, y,
        l2_penalty=l2_penalty,
        learning_rate=learning_rate,
        max_iter=max_iter,
    )
    all_p = model.predict_proba(X)
    corpus_p = all_p[:n_corpus]
    target_p = float(all_p[n_corpus:].mean())
    return corpus_p, target_p, model


def psm_match(
    corpus: List[FeatureVector],
    target: FeatureVector,
    config: Optional[PSMConfig] = None,
) -> PSMResult:
    """Run the full PSM pipeline + caliper-NN matching.

    Returns a PSMResult with the K top matches inside the caliper,
    each tagged with the propensity-score distance and a
    similarity weight (1 - dist/caliper, clipped to [0, 1]).
    """
    cfg = config or PSMConfig()
    corpus_p, target_p, model = fit_propensity_scores(
        corpus, target,
        l2_penalty=cfg.l2_penalty,
        learning_rate=cfg.learning_rate,
        max_iter=cfg.max_iter,
    )

    distances = np.abs(corpus_p - target_p)
    in_caliper_mask = distances <= cfg.caliper
    candidate_idx = np.argsort(distances)
    matches: List[Tuple[FeatureVector, float, float]] = []
    for idx in candidate_idx:
        if not in_caliper_mask[idx]:
            break
        if len(matches) >= cfg.k_matches:
            break
        weight = max(0.0, min(1.0,
                              1.0 - distances[idx] / max(
                                  1e-9, cfg.caliper)))
        matches.append(
            (corpus[idx], float(distances[idx]), float(weight))
        )

    # If caliper is too tight, fall back to the K nearest (no caliper)
    if len(matches) < min(3, cfg.k_matches):
        matches = []
        for idx in candidate_idx[:cfg.k_matches]:
            d = float(distances[idx])
            weight = max(0.0, min(1.0,
                                  1.0 - d / max(
                                      1e-9, distances.max())))
            matches.append((corpus[idx], d, weight))

    return PSMResult(
        propensity_scores=corpus_p,
        target_propensity=target_p,
        matches=matches,
        model=model,
    )

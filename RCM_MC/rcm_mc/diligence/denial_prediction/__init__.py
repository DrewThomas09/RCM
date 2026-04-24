"""Claim-level denial prediction — the CCD-native predictive
analytic that feeds the EBITDA bridge's denial-reduction lever
with a data-driven target instead of an industry-aggregate guess.

What it does:

    Given a Canonical Claims Dataset, learn per-feature empirical
    denial probabilities on a training split (provider-disjoint
    when providers are available), score every claim in the
    validation split, and surface:

    1. **Systematic misses** — claims the model predicted would be
       denied that WEREN'T. These are the audit opportunities;
       sum them for the recoverable-revenue estimate.

    2. **Systematic false positives** — claims the model predicted
       would NOT be denied that were. These reveal where the
       seller's billing logic is broken in ways not captured by
       our feature set.

    3. **Feature-level attribution** — which CPT × payer × charge
       bands are most associated with denials. Partners quote
       these in the diligence memo as "here's where to act."

    4. **EBITDA bridge input** — annualised recoverable revenue
       from addressing the systematic misses, ready to hand to
       the denial-reduction lever.

Design philosophy:
    - Naive Bayes with Laplace smoothing — stdlib-only, no sklearn,
      interpretable per-feature contributions (partners ask "why
      did you flag this?" and the answer is a concrete feature
      list, not a black-box coefficient).
    - Provider-disjoint split when provider_id is available; pure
      random split otherwise. Test fold is always held out.
    - Calibration check via Brier score + calibration plot
      (10-bucket reliability diagram).
    - No imported ML library. ~400 lines of pure Python.

Why this is a moat:
    Chartis / VMG / A&M produce descriptive denial Paretos. Nobody
    runs a per-claim predictive model on the CCD because they
    don't have the CCD. We do. Every claim's denial probability
    + attribution is a line of partner-quotable output.
"""
from __future__ import annotations

from .analyzer import (
    ClaimFeatures, DenialPredictionReport, EBITDABridgeInput,
    FeatureAttribution, analyze_ccd, extract_features,
)
from .model import (
    NaiveBayesDenialModel, calibration_report, load_model,
    save_model, train_naive_bayes,
)

__all__ = [
    "ClaimFeatures",
    "DenialPredictionReport",
    "EBITDABridgeInput",
    "FeatureAttribution",
    "NaiveBayesDenialModel",
    "analyze_ccd",
    "calibration_report",
    "extract_features",
    "load_model",
    "save_model",
    "train_naive_bayes",
]

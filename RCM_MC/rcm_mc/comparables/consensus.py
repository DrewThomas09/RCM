"""Consensus matching + balance diagnostics.

The two existing match methods (PSM, Mahalanobis) each produce
a top-K comp list. They agree on most deals, disagree on edges.
Comps in BOTH lists are higher-confidence comps; comps in ONE
are method-dependent and warrant manual review.

Plus: PSM literature requires post-match BALANCE — the matched
comp set should have similar covariate means to the target.
Without that, the partner can't defend the comp set to an IC or
LP. Standard reporting metric: ``standardized_mean_difference``
(SMD) per feature. SMD < 0.10 = excellent balance, < 0.25 =
acceptable, > 0.25 = concerning.

This module wires:
  consensus_match: run both methods, return union / intersection
  balance_diagnostics: per-feature SMD between target + comp set
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .features import FeatureVector, extract_features
from .mahalanobis import mahalanobis_match
from .psm import PSMConfig, psm_match


@dataclass
class ConsensusMatch:
    """One comp deal + how it ranked under each method."""
    deal_id: str
    in_psm: bool
    in_mahalanobis: bool
    psm_weight: float = 0.0
    mahalanobis_weight: float = 0.0
    consensus_weight: float = 0.0       # average of the two
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BalanceDiagnostic:
    """Per-feature balance metric."""
    feature_name: str
    target_value: float
    comp_mean: float
    comp_std: float
    standardized_mean_difference: float
    band: str           # "excellent" | "acceptable" | "concerning"


@dataclass
class ConsensusResult:
    target_id: str
    n_psm_only: int
    n_mahalanobis_only: int
    n_consensus: int                    # in BOTH lists
    matches: List[ConsensusMatch] = field(default_factory=list)
    balance: List[BalanceDiagnostic] = field(default_factory=list)


def _smd_band(smd: float) -> str:
    a = abs(smd)
    if a < 0.10:
        return "excellent"
    if a < 0.25:
        return "acceptable"
    return "concerning"


def balance_diagnostics(
    target_fv: FeatureVector,
    matched_fvs: List[FeatureVector],
) -> List[BalanceDiagnostic]:
    """Per-feature SMD between the target and the matched comp set.

    SMD = |target_value − comp_mean| / comp_std
    With comp_std = 0 (constant feature), the SMD is reported as
    0 if the target matches the comp value exactly, else as ``inf``.
    """
    if not matched_fvs:
        return []
    feature_names = target_fv.feature_names
    if not feature_names:
        return []
    target_vec = target_fv.vector
    matched_matrix = np.vstack([fv.vector for fv in matched_fvs])

    diagnostics: List[BalanceDiagnostic] = []
    for i, name in enumerate(feature_names):
        if i >= len(target_vec):
            continue
        t_val = float(target_vec[i])
        col = matched_matrix[:, i]
        c_mean = float(col.mean())
        c_std = float(col.std(ddof=1)) if len(col) > 1 else 0.0
        if c_std <= 1e-9:
            smd = 0.0 if abs(t_val - c_mean) <= 1e-9 \
                else float("inf")
        else:
            smd = abs(t_val - c_mean) / c_std
        # Cap absurdly large SMDs for readability
        if smd > 100:
            smd = 100.0
        diagnostics.append(BalanceDiagnostic(
            feature_name=name,
            target_value=round(t_val, 4),
            comp_mean=round(c_mean, 4),
            comp_std=round(c_std, 4),
            standardized_mean_difference=round(smd, 4),
            band=_smd_band(smd),
        ))
    return diagnostics


def consensus_match(
    corpus: List[Dict[str, Any]],
    target: Dict[str, Any],
    *,
    k_matches: int = 15,
    psm_config: Optional[PSMConfig] = None,
) -> ConsensusResult:
    """Run PSM + Mahalanobis on the same target × corpus and
    return the consensus view + balance diagnostics.

    The consensus view labels each match as PSM-only, Mahalanobis-
    only, or BOTH (high-confidence). Balance diagnostics report
    SMD per feature for the union of the matched comps, banded
    excellent/acceptable/concerning.
    """
    corpus_fvs, target_fv = extract_features(corpus, target)
    cfg = psm_config or PSMConfig(k_matches=k_matches)

    psm_result = psm_match(corpus_fvs, target_fv, config=cfg)
    psm_index = {
        fv.deal_id: (fv, weight)
        for fv, _, weight in psm_result.matches
    }
    mh_matches = mahalanobis_match(
        corpus_fvs, target_fv, k_matches=k_matches)
    mh_index = {
        fv.deal_id: (fv, weight)
        for fv, _, weight in mh_matches
    }

    # Build the union, marking each match's membership
    all_ids = set(psm_index.keys()) | set(mh_index.keys())
    matches: List[ConsensusMatch] = []
    consensus_fvs: List[FeatureVector] = []
    n_psm_only = n_mh_only = n_both = 0

    for did in all_ids:
        in_psm = did in psm_index
        in_mh = did in mh_index
        psm_w = psm_index[did][1] if in_psm else 0.0
        mh_w = mh_index[did][1] if in_mh else 0.0
        if in_psm and in_mh:
            n_both += 1
            consensus_fvs.append(psm_index[did][0])
            consensus = (psm_w + mh_w) / 2.0
        elif in_psm:
            n_psm_only += 1
            consensus = psm_w * 0.5  # half weight: only one method agreed
        else:
            n_mh_only += 1
            consensus = mh_w * 0.5

        fv = (psm_index[did][0] if in_psm
              else mh_index[did][0])
        matches.append(ConsensusMatch(
            deal_id=did,
            in_psm=in_psm,
            in_mahalanobis=in_mh,
            psm_weight=round(psm_w, 4),
            mahalanobis_weight=round(mh_w, 4),
            consensus_weight=round(consensus, 4),
            raw={
                "deal_name": fv.raw.get("deal_name")
                              or fv.raw.get("company_name"),
                "year": fv.raw.get("year"),
                "buyer": fv.raw.get("buyer"),
                "ev_mm": fv.raw.get("ev_mm"),
                "realized_moic": (
                    fv.raw.get("realized_moic")
                    or fv.raw.get("moic")),
            },
        ))

    matches.sort(
        key=lambda m: m.consensus_weight, reverse=True)

    # Balance diagnostics computed against the consensus comps
    # (the high-confidence subset). If empty, fall back to PSM
    # matches; if those are empty, fall back to Mahalanobis.
    if consensus_fvs:
        diagnostic_fvs = consensus_fvs
    elif psm_index:
        diagnostic_fvs = [pair[0] for pair in psm_index.values()]
    else:
        diagnostic_fvs = [pair[0] for pair in mh_index.values()]
    balance = balance_diagnostics(target_fv, diagnostic_fvs)

    return ConsensusResult(
        target_id=target_fv.deal_id,
        n_psm_only=n_psm_only,
        n_mahalanobis_only=n_mh_only,
        n_consensus=n_both,
        matches=matches,
        balance=balance,
    )

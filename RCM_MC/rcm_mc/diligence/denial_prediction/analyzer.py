"""End-to-end analyzer: CCD → features → model → report.

What a diligence associate runs:

    from rcm_mc.diligence import ingest_dataset
    from rcm_mc.diligence.denial_prediction import analyze_ccd

    ccd = ingest_dataset("tests/fixtures/kpi_truth/hospital_06_...")
    report = analyze_ccd(ccd, train_fraction=0.7)

    report.calibration.brier_score        # 0.08 typical
    report.systematic_miss_count          # claims NOT denied but
                                          # predicted >0.5
    report.systematic_miss_dollars        # recoverable revenue $
    report.bridge_input.annualised_usd    # hand to the bridge

The analyzer is deterministic given a seed (default 42) so two
runs against the same CCD produce byte-identical reports.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import (
    CalibrationReport, NaiveBayesDenialModel, calibration_report,
    train_naive_bayes,
)


# ── Feature engineering ────────────────────────────────────────────

@dataclass
class ClaimFeatures:
    """The feature vector extracted from a single claim.

    Every field is a string because Naive Bayes works on
    categorical data. Numeric fields are bucketed into bands
    (charge_amount, paid_days_lag) because PE-style analysts want
    the model to reason in bands they'd quote in a memo ("your
    $5-10k commercial claims are 3x more likely to be denied than
    under-$1k Medicare")."""
    cpt_family: str
    payer_class: str
    charge_band: str           # UNDER_1K / 1K_5K / 5K_10K / OVER_10K
    place_of_service: str
    has_modifier: str          # 'yes' / 'no'
    network_status: str        # IN / OON / UNKNOWN
    has_adjustment_code: str   # 'yes' / 'no'
    service_weekday: str       # Mon..Sun

    def to_dict(self) -> Dict[str, str]:
        return self.__dict__.copy()


def _cpt_family(cpt: Optional[str]) -> str:
    if not cpt:
        return "UNKNOWN"
    c = str(cpt).strip()
    if not c:
        return "UNKNOWN"
    try:
        prefix = int(c[:1])
    except (ValueError, IndexError):
        return f"CPT_{c[:3]}"
    # Group by AMA CPT high-level range.
    if c.startswith(("10", "11", "12", "13", "14", "15", "16", "17", "18", "19")):
        return "SURGERY_10K_19K"
    if c.startswith("2"):
        return "SURGERY_2XXXX"
    if c.startswith("3"):
        return "SURGERY_3XXXX"
    if c.startswith("4"):
        return "SURGERY_4XXXX"
    if c.startswith("5"):
        return "SURGERY_5XXXX"
    if c.startswith(("60", "61", "62", "63", "64", "65", "66", "67", "68", "69")):
        return "SURGERY_6XXXX"
    if c.startswith("7"):
        return "RADIOLOGY_7XXXX"
    if c.startswith(("80", "81", "82", "83", "84", "85", "86", "87", "88", "89")):
        return "LAB_PATH_8XXXX"
    if c.startswith(("90", "91", "92", "93", "94", "95", "96", "97", "98")):
        return "MEDICINE_9XXXX"
    if c.startswith("99"):
        return "E_M_99XXX"
    return f"CPT_{c[:3]}"


def _charge_band(charge_amount: Optional[float]) -> str:
    try:
        amt = float(charge_amount or 0.0)
    except (ValueError, TypeError):
        return "UNKNOWN"
    if amt <= 0:
        return "UNKNOWN"
    if amt < 1000:
        return "UNDER_1K"
    if amt < 5000:
        return "1K_5K"
    if amt < 10000:
        return "5K_10K"
    return "OVER_10K"


def _weekday(iso: Any) -> str:
    if not iso:
        return "UNKNOWN"
    try:
        from datetime import date as _date
        if hasattr(iso, "weekday"):
            wd = iso.weekday()
        else:
            wd = _date.fromisoformat(str(iso)[:10]).weekday()
    except (ValueError, AttributeError):
        return "UNKNOWN"
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[wd]


def extract_features(claim: Any) -> ClaimFeatures:
    """Extract the 8-feature vector from a claim object."""
    return ClaimFeatures(
        cpt_family=_cpt_family(getattr(claim, "cpt_code", None)),
        payer_class=str(
            getattr(
                getattr(claim, "payer_class", None), "value",
                getattr(claim, "payer_class", None) or "UNKNOWN",
            ),
        ).upper(),
        charge_band=_charge_band(getattr(claim, "charge_amount", None)),
        place_of_service=str(
            getattr(claim, "place_of_service", "") or "UNKNOWN",
        ),
        has_modifier=(
            "yes" if getattr(claim, "modifier_codes", None)
            else "no"
        ),
        network_status=str(
            (getattr(claim, "network_status", "") or "UNKNOWN"),
        ).upper(),
        has_adjustment_code=(
            "yes" if getattr(claim, "adjustment_reason_codes", None)
            else "no"
        ),
        service_weekday=_weekday(
            getattr(claim, "service_date_from", None),
        ),
    )


def _is_denied(claim: Any) -> bool:
    status = getattr(claim, "status", None)
    status_val = status.value if hasattr(status, "value") else str(status or "")
    return status_val.upper() in ("DENIED", "WRITTEN_OFF")


# ── Report dataclasses ────────────────────────────────────────────

@dataclass
class FeatureAttribution:
    feature: str
    value: str
    lift: float                      # p(v|denial) / p(v|paid)
    marginal_denial_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class FlaggedClaim:
    claim_id: str
    predicted_denial_probability: float
    actually_denied: bool
    paid_amount_usd: float
    charge_amount_usd: float
    cpt_family: str
    payer_class: str
    reason: str                      # "systematic_miss" /
                                     # "systematic_fp"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class EBITDABridgeInput:
    """Shape that the v2 EBITDA bridge's denial-reduction lever
    can consume. Produced by :func:`analyze_ccd`."""
    recoverable_revenue_usd: float
    annualised_usd: float
    realization_probability: float = 0.5
    confidence: str = "MEDIUM"
    claim_count_flagged: int = 0
    top_intervention_targets: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class DenialPredictionReport:
    provider_id: Optional[str]
    n_claims: int
    n_train: int
    n_test: int
    baseline_denial_rate: float

    calibration: CalibrationReport
    top_features: List[FeatureAttribution] = field(default_factory=list)

    systematic_miss_count: int = 0
    systematic_miss_charge_dollars: float = 0.0
    systematic_miss_paid_dollars: float = 0.0   # could-have-paid

    systematic_fp_count: int = 0
    systematic_fp_dollars: float = 0.0

    flagged_claims: List[FlaggedClaim] = field(default_factory=list)
    bridge_input: Optional[EBITDABridgeInput] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "n_claims": self.n_claims,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "baseline_denial_rate": self.baseline_denial_rate,
            "calibration": self.calibration.to_dict(),
            "top_features": [f.to_dict() for f in self.top_features],
            "systematic_miss_count": self.systematic_miss_count,
            "systematic_miss_charge_dollars":
                self.systematic_miss_charge_dollars,
            "systematic_miss_paid_dollars":
                self.systematic_miss_paid_dollars,
            "systematic_fp_count": self.systematic_fp_count,
            "systematic_fp_dollars": self.systematic_fp_dollars,
            "flagged_claims":
                [f.to_dict() for f in self.flagged_claims],
            "bridge_input": (
                self.bridge_input.to_dict()
                if self.bridge_input else None
            ),
        }


# ── Train/test split ──────────────────────────────────────────────

def _split(
    claims: Sequence[Any], train_fraction: float, seed: int,
) -> Tuple[List[Any], List[Any]]:
    """Provider-disjoint split when provider_id is present on at
    least half the claims; otherwise random."""
    rng = random.Random(seed)
    provider_counts: Dict[str, int] = {}
    for c in claims:
        pid = getattr(c, "provider_id", None) or getattr(
            c, "billing_provider_id", None,
        )
        if pid:
            provider_counts[str(pid)] = \
                provider_counts.get(str(pid), 0) + 1
    total_with_prov = sum(provider_counts.values())
    if (total_with_prov > 0.5 * len(claims)
            and len(provider_counts) >= 2):
        # Provider-disjoint split.
        providers = sorted(provider_counts.keys())
        rng.shuffle(providers)
        cumulative = 0
        train_providers: set = set()
        for p in providers:
            cumulative += provider_counts[p]
            train_providers.add(p)
            if cumulative >= train_fraction * total_with_prov:
                break
        train, test = [], []
        for c in claims:
            pid = str(
                getattr(c, "provider_id", None)
                or getattr(c, "billing_provider_id", None)
                or "",
            )
            if not pid:
                # Route prov-less claims by coin flip.
                (train if rng.random() < train_fraction else test).append(c)
            elif pid in train_providers:
                train.append(c)
            else:
                test.append(c)
        return train, test
    # Random split.
    indices = list(range(len(claims)))
    rng.shuffle(indices)
    k = int(train_fraction * len(claims))
    train = [claims[i] for i in indices[:k]]
    test = [claims[i] for i in indices[k:]]
    return train, test


# ── Public entry point ────────────────────────────────────────────

def analyze_ccd(
    ccd: Any,
    *,
    train_fraction: float = 0.7,
    seed: int = 42,
    systematic_threshold: float = 0.5,
    max_flagged: int = 50,
    annualization_factor: float = 1.0,
) -> DenialPredictionReport:
    """Train + score + assemble the report.

    ``annualization_factor`` scales the recoverable-revenue number
    if the CCD covers less than 12 months; set to 12/N_months of
    the CCD's coverage.

    Returns a :class:`DenialPredictionReport` whose
    ``bridge_input`` attribute is ready to attach as a v2 bridge
    lever (see rcm_mc.pe.value_bridge_v2).
    """
    claims = list(getattr(ccd, "claims", []) or [])
    provider_id = getattr(ccd, "provider_id", None) or getattr(
        ccd, "ingest_id", None,
    )
    if len(claims) < 4:
        return DenialPredictionReport(
            provider_id=provider_id,
            n_claims=len(claims),
            n_train=0, n_test=0,
            baseline_denial_rate=0.0,
            calibration=CalibrationReport(
                brier_score=0, log_loss=0, accuracy=0, auc_rough=0.5,
            ),
        )

    train, test = _split(claims, train_fraction, seed)
    if not train or not test:
        # Fall back to using the whole set for both — degraded but
        # useful on micro-fixtures.
        train = list(claims)
        test = list(claims)

    labelled_train = [
        (extract_features(c).to_dict(), _is_denied(c))
        for c in train
    ]
    model = train_naive_bayes(labelled_train)

    labelled_test = [
        (extract_features(c).to_dict(), _is_denied(c))
        for c in test
    ]
    cal = calibration_report(model, labelled_test)

    # Top features by denial lift.
    top = []
    for feat, val, lift in model.top_features_by_denial_lift(k=12):
        # Compute the marginal denial rate for this (feat, val):
        # claims in TEST with this value that were denied.
        matching = [
            c for c in test
            if extract_features(c).to_dict().get(feat) == val
        ]
        if not matching:
            continue
        marginal = sum(1 for c in matching if _is_denied(c)) / len(matching)
        top.append(FeatureAttribution(
            feature=feat, value=val, lift=lift,
            marginal_denial_rate=marginal,
        ))

    # Systematic miss/FP detection against the TEST split.
    flagged: List[FlaggedClaim] = []
    miss_cnt = 0
    miss_charge = 0.0
    miss_paid = 0.0
    fp_cnt = 0
    fp_dollars = 0.0
    for c in test:
        f = extract_features(c).to_dict()
        p = model.predict_proba(f)
        denied = _is_denied(c)
        paid = float(getattr(c, "paid_amount", 0) or 0)
        charge = float(getattr(c, "charge_amount", 0) or 0)
        if p >= systematic_threshold and not denied:
            miss_cnt += 1
            miss_charge += charge
            miss_paid += paid
            flagged.append(FlaggedClaim(
                claim_id=str(getattr(c, "claim_id", "")),
                predicted_denial_probability=p,
                actually_denied=False,
                paid_amount_usd=paid,
                charge_amount_usd=charge,
                cpt_family=f["cpt_family"],
                payer_class=f["payer_class"],
                reason="systematic_miss",
            ))
        elif p < (1 - systematic_threshold) and denied:
            fp_cnt += 1
            allowed = float(getattr(c, "allowed_amount", 0) or 0)
            fp_dollars += allowed if allowed > 0 else charge
            flagged.append(FlaggedClaim(
                claim_id=str(getattr(c, "claim_id", "")),
                predicted_denial_probability=p,
                actually_denied=True,
                paid_amount_usd=paid,
                charge_amount_usd=charge,
                cpt_family=f["cpt_family"],
                payer_class=f["payer_class"],
                reason="systematic_fp",
            ))

    # Sort flagged by charge descending, cap.
    flagged.sort(key=lambda f: -f.charge_amount_usd)
    flagged = flagged[:max_flagged]

    # Assemble the EBITDA bridge input. The recoverable revenue is
    # the systematic-miss charge total (audit + appeal can recover
    # up to 60-80% of charges that shouldn't have been denied in
    # the first place). Conservative floor: 50%.
    recoverable_pv = miss_charge * 0.60
    annualised = recoverable_pv * annualization_factor
    # Top-3 intervention targets (by lift).
    top_targets = [
        {"feature": t.feature, "value": t.value,
         "lift": t.lift, "denial_rate": t.marginal_denial_rate}
        for t in top[:3]
    ]
    confidence = (
        "HIGH" if cal.auc_rough > 0.75 else
        "MEDIUM" if cal.auc_rough > 0.6 else
        "LOW"
    )
    bridge = EBITDABridgeInput(
        recoverable_revenue_usd=recoverable_pv,
        annualised_usd=annualised,
        realization_probability=0.5,
        confidence=confidence,
        claim_count_flagged=miss_cnt,
        top_intervention_targets=top_targets,
    )

    baseline = sum(1 for c in claims if _is_denied(c)) / max(len(claims), 1)
    return DenialPredictionReport(
        provider_id=str(provider_id) if provider_id else None,
        n_claims=len(claims),
        n_train=len(train),
        n_test=len(test),
        baseline_denial_rate=baseline,
        calibration=cal,
        top_features=top,
        systematic_miss_count=miss_cnt,
        systematic_miss_charge_dollars=miss_charge,
        systematic_miss_paid_dollars=miss_paid,
        systematic_fp_count=fp_cnt,
        systematic_fp_dollars=fp_dollars,
        flagged_claims=flagged,
        bridge_input=bridge,
    )

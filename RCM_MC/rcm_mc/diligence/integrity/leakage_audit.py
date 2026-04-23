"""Target leakage audit.

The trap this module guards against:

    Hospital X's CCD gets ingested → KPIs computed from that CCD join
    the training corpus → ridge predictor trains on the corpus →
    predictor is asked to fill a missing metric for hospital X →
    prediction is effectively memorising X's own data.

In-sample performance looks brilliant. At IC the partner asks why the
predicted NRR matches the observed cost-to-collect to four decimals,
the model fails under scrutiny, and the entire ML story collapses.

This module catches the chain *before* it happens. Given a target
provider_id and the feature set the predictor is about to use, we
assert that no feature's source provider matches the target. If one
does, :class:`LeakageError` fires with the specific feature(s) that
leaked.

Usage pattern at the packet-builder seam:

    from rcm_mc.diligence.integrity import audit_features, LeakageError

    try:
        audit_features(
            target_provider_id=deal.provider_id,
            features=predictor_inputs,
        )
    except LeakageError as exc:
        # Record in packet audit + refuse to run the ridge predictor.
        packet.risk_flags.append(RiskFlag(
            category="data_integrity", severity=RiskSeverity.HIGH,
            title=exc.title, detail=str(exc),
        ))
        predictor_inputs = []

Every feature that enters the predictor carries a :class:`FeatureSource`
stamp. The audit is a set-intersection — O(|features|) — and runs at
every prediction call, not just once per build.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


# ── Types ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FeatureSource:
    """Describes where a single feature value came from.

    ``provider_ids`` is the set of hospital IDs whose data contributed
    to this feature. For a peer-aggregated feature (e.g. "P50 denial
    rate across comparable set"), it's the peer pool. For a target-
    specific feature, it's a single-element set — and if that element
    equals the target, we've leaked.

    ``dataset`` distinguishes CCD-derived (``"CCD"``) from public-data
    (``"HCRIS"``, ``"IRS990"``) from registry defaults
    (``"BENCHMARK"``). Leakage only applies to deal-specific datasets
    — a BENCHMARK P50 touching the target's provider_id is fine
    because it's a median across thousands.
    """
    feature_name: str
    dataset: str                        # "CCD" | "HCRIS" | "IRS990" | "BENCHMARK" | …
    provider_ids: Tuple[str, ...] = ()
    description: str = ""


@dataclass
class LeakageFinding:
    feature_name: str
    target_provider_id: str
    leaked_provider_id: str
    dataset: str
    description: str = ""

    def chain(self) -> str:
        """One-line chain suitable for a risk-flag detail string."""
        return (
            f"feature {self.feature_name!r} in dataset {self.dataset} "
            f"includes target provider {self.target_provider_id!r} "
            f"via source provider {self.leaked_provider_id!r}"
        )


class LeakageError(Exception):
    """Fires when ``audit_features`` finds at least one leaking feature.

    Title is a short summary suitable for a risk-flag row; ``findings``
    carries the full chain detail for the packet audit log.
    """
    title: str = "Target leakage in predictor inputs"

    def __init__(self, findings: Sequence[LeakageFinding]):
        self.findings: Tuple[LeakageFinding, ...] = tuple(findings)
        chains = "\n  ".join(f.chain() for f in self.findings)
        super().__init__(
            f"{len(self.findings)} leaking feature(s) detected:\n  {chains}"
        )


# ── Audit ───────────────────────────────────────────────────────────

# Datasets whose rows we consider deal-specific. Public / benchmark
# datasets are exempt because a median across 4,000 hospitals does
# not leak a single hospital's signal.
_DEAL_SPECIFIC_DATASETS: Set[str] = {"CCD", "OBSERVED", "EXTRACTED"}


def audit_features(
    *,
    target_provider_id: str,
    features: Iterable[FeatureSource],
    deal_specific_datasets: Optional[Set[str]] = None,
) -> None:
    """Raise :class:`LeakageError` if any feature leaks.

    Silent success if everything is clean — by design: a positive
    result is the expected path and shouldn't noise the packet audit
    log. Violations get logged by the caller via the exception.
    """
    if not target_provider_id:
        # An empty target is a malformed call — we fail closed with an
        # explicit message rather than accepting a no-op.
        raise ValueError("target_provider_id must be a non-empty string")

    deal_specific = deal_specific_datasets or _DEAL_SPECIFIC_DATASETS
    findings: List[LeakageFinding] = []
    for f in features:
        if f.dataset.upper() not in deal_specific:
            continue
        for pid in f.provider_ids:
            if _provider_match(pid, target_provider_id):
                findings.append(LeakageFinding(
                    feature_name=f.feature_name,
                    target_provider_id=target_provider_id,
                    leaked_provider_id=pid,
                    dataset=f.dataset,
                    description=f.description,
                ))
    if findings:
        raise LeakageError(findings)


def _provider_match(a: str, b: str) -> bool:
    """Normalised equality — tolerates CCN vs NPI-style formatting
    differences (leading zeros, casing, hyphens)."""
    return _normalise(a) == _normalise(b)


def _normalise(pid: str) -> str:
    return "".join(ch for ch in str(pid).lower() if ch.isalnum())


# ── Helpers for callers ─────────────────────────────────────────────

def features_from_peer_pool(
    peer_records: Iterable[Dict[str, object]],
    *,
    feature_names: Sequence[str],
    dataset: str = "CCD",
    provider_id_key: str = "provider_id",
) -> List[FeatureSource]:
    """Build a :class:`FeatureSource` list from a list of peer dicts.

    The ridge predictor consumes peer records as a list of feature
    dicts; this shim annotates each feature with the set of provider
    IDs that contributed, so the audit can run without the predictor
    having to grow a dependency on this module.
    """
    provider_ids = tuple(
        str(r.get(provider_id_key))
        for r in peer_records
        if r.get(provider_id_key) is not None
    )
    return [
        FeatureSource(
            feature_name=name,
            dataset=dataset,
            provider_ids=provider_ids,
            description=f"peer-aggregated {name} across {len(provider_ids)} providers",
        )
        for name in feature_names
    ]


def feature_from_target(
    feature_name: str,
    *,
    target_provider_id: str,
    dataset: str = "CCD",
) -> FeatureSource:
    """Build a FeatureSource whose single source provider IS the
    target. Useful for constructing deliberate leaks in test code —
    production callers never build one of these; if they did, the
    audit would always flag it, which is the point."""
    return FeatureSource(
        feature_name=feature_name,
        dataset=dataset,
        provider_ids=(target_provider_id,),
        description=f"{feature_name} derived from target hospital's own data",
    )


# ── Structured-result wrapper ─────────────────────────────────────

def check_leakage(
    *,
    target_provider_id: str,
    features: Iterable[FeatureSource],
    deal_specific_datasets: Optional[Set[str]] = None,
    allow_temporal_self: bool = True,
) -> "GuardrailResult":
    """Packet-facing leakage check. Returns a
    :class:`GuardrailResult`:

    - **PASS**: no deal-specific feature names the target as a source.
    - **PASS** with a note if the only self-references are *temporal*
      (hospital X's prior-period data predicting its current-period
      data — legitimate when clearly temporal).
    - **FAIL**: peer-comparable-style cross-hospital leakage.

    ``allow_temporal_self`` controls whether a feature whose
    ``description`` hints at temporality (``"prior_period"`` /
    ``"lag_"`` / ``"temporal"``) is exempt. Default True per spec.
    """
    from .split_enforcer import GuardrailResult

    feature_list = list(features)
    temporal_exempt: List[str] = []
    try:
        audit_features(
            target_provider_id=target_provider_id,
            features=feature_list,
            deal_specific_datasets=deal_specific_datasets,
        )
    except LeakageError as exc:
        # Partition findings into "temporal" vs "cross-hospital peer".
        peer_findings: List[LeakageFinding] = []
        for f in exc.findings:
            desc = (f.description or "").lower()
            if allow_temporal_self and (
                "prior_period" in desc
                or "lag_" in desc
                or "temporal" in desc
                or "hospital's own" in desc and "prior" in desc
            ):
                temporal_exempt.append(f.feature_name)
                continue
            peer_findings.append(f)
        if peer_findings:
            return GuardrailResult(
                guardrail="leakage_audit", ok=False, status="FAIL",
                reason=(
                    f"{len(peer_findings)} feature(s) leak the target into "
                    f"peer comparables: "
                    + "; ".join(f.chain() for f in peer_findings[:3])
                    + (" …" if len(peer_findings) > 3 else "")
                ),
                details={
                    "leaked_features": [
                        {"feature": f.feature_name,
                         "dataset": f.dataset,
                         "leaked_provider": f.leaked_provider_id,
                         "description": f.description}
                        for f in peer_findings
                    ],
                    "temporal_self_features": temporal_exempt,
                },
            )
        # Only temporal self-references remained: PASS with note.
        return GuardrailResult(
            guardrail="leakage_audit", ok=True, status="PASS",
            reason=(
                f"{len(temporal_exempt)} temporal self-feature(s) allowed "
                f"(target's prior-period data feeding target's current "
                f"prediction is legitimate); no peer-comparable leakage."
            ),
            details={"temporal_self_features": temporal_exempt},
        )
    return GuardrailResult(
        guardrail="leakage_audit", ok=True, status="PASS",
        reason=(
            f"{len(feature_list)} feature(s) audited; no deal-specific "
            f"feature names the target as a source."
        ),
    )

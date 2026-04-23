"""Packet-builder pre-flight for CCD-derived metrics.

One function — :func:`run_ccd_guardrails` — that the packet builder
calls before trusting any CCD-derived ObservedMetric. Runs every
guardrail in the integrity subpackage and returns a
:class:`PreflightReport` summarising PASS/WARN/FAIL across the six
checks.

The builder's contract:

1. When no CCD is attached to a deal, this is not called and nothing
   changes vs pre-session-4 behaviour.
2. When a CCD IS attached, the builder calls
   ``run_ccd_guardrails(...)`` and appends a :class:`RiskFlag` for
   any FAIL'ed guardrail before deciding whether to emit the
   CCD-derived metrics into ``observed_metrics`` at
   confidence=1.0 (PASS/WARN) or downgrade them (FAIL).

Design note: the pre-flight does *not* mutate the CCD or the
packet's observed_metrics — it only produces a verdict. The builder
caller decides what to do with it. This keeps the guardrails
independent of the builder's exact shape so a future re-org of
packet_builder.py doesn't ripple through this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .cohort_censoring import CensoringCheck, check_cohort_censoring
from .distribution_shift import check_distribution_shift
from .leakage_audit import FeatureSource, check_leakage
from .split_enforcer import GuardrailResult, SplitManifest, check_split_manifest
from .temporal_validity import scan_for_discontinuities


# ── Exception: raised by packet_builder on any FAIL'd guardrail ────

class GuardrailViolation(Exception):
    """Raised by ``build_analysis_packet`` when at least one guardrail
    returns ``ok=False`` during a CCD-attached build.

    Fails loud by design: a packet built from CCD data that violates
    a data-integrity guardrail (target leakage, censored-cohort
    fabrication, OOD distribution, broken provenance chain) should
    never reach an IC memo. Partners see this exception with the full
    list of failed guardrails; an analyst who sees it knows exactly
    which check blocked the build and why.

    Attributes:
        results: every ``GuardrailResult`` produced by the preflight
            (both PASS and FAIL) so the caller can render the full
            context, not just the failures.
        failed: shorthand for ``[r for r in results if not r.ok]``.
    """
    def __init__(self, results: Iterable[GuardrailResult]):
        self.results: List[GuardrailResult] = list(results)
        self.failed: List[GuardrailResult] = [r for r in self.results if not r.ok]
        names = ", ".join(r.guardrail for r in self.failed)
        super().__init__(
            f"{len(self.failed)} guardrail(s) FAILED during CCD-attached "
            f"packet build: {names}"
        )


@dataclass
class PreflightReport:
    """Envelope holding one :class:`GuardrailResult` per guardrail run.

    ``any_fail`` is True iff at least one guardrail's ``ok`` is False.
    The packet builder reads this field to decide whether to emit
    CCD-derived metrics at full confidence or to downgrade.
    """
    results: List[GuardrailResult] = field(default_factory=list)
    ran_at_ingest_id: str = ""

    def by_guardrail(self) -> Dict[str, GuardrailResult]:
        return {r.guardrail: r for r in self.results}

    @property
    def any_fail(self) -> bool:
        return any(not r.ok for r in self.results)

    @property
    def any_warn(self) -> bool:
        return any(r.status == "WARN" for r in self.results)

    @property
    def status(self) -> str:
        if self.any_fail:
            return "FAIL"
        if self.any_warn:
            return "WARN"
        return "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "any_fail": self.any_fail,
            "any_warn": self.any_warn,
            "ran_at_ingest_id": self.ran_at_ingest_id,
            "results": [asdict(r) for r in self.results],
        }


def run_ccd_guardrails(
    ccd: Any,
    *,
    as_of_date: date,
    target_provider_id: str,
    peer_provider_pool: Optional[Sequence[str]] = None,
    peer_features: Optional[Iterable[FeatureSource]] = None,
    corpus_features: Optional[Mapping[str, Sequence[float]]] = None,
    requested_cohort_cells: Optional[Sequence[tuple]] = None,
    split_manifest: Optional[SplitManifest] = None,
) -> PreflightReport:
    """Run all six guardrails against a CCD. Inputs that aren't
    available are skipped with a neutral PASS — better to run four
    guardrails than zero because one input is missing.

    Returns a :class:`PreflightReport`.
    """
    report = PreflightReport(
        ran_at_ingest_id=getattr(ccd, "ingest_id", ""),
    )
    claims = list(getattr(ccd, "claims", ()))

    # 1. Leakage audit — only when we have peer features to audit.
    if peer_features is not None:
        report.results.append(
            check_leakage(
                target_provider_id=target_provider_id,
                features=peer_features,
            )
        )
    else:
        report.results.append(GuardrailResult(
            guardrail="leakage_audit", ok=True, status="PASS",
            reason="skipped — no peer features supplied (no ridge "
                   "prediction requested)",
        ))

    # 2. Split enforcer — only when the caller is about to train.
    if split_manifest is not None:
        report.results.append(check_split_manifest(split_manifest))
    else:
        report.results.append(GuardrailResult(
            guardrail="split_enforcer", ok=True, status="PASS",
            reason="skipped — no SplitManifest supplied (no conformal "
                   "fit requested)",
        ))

    # 3. Cohort censoring — always runs; windows come from defaults.
    report.results.append(
        check_cohort_censoring(CensoringCheck(
            claims=claims, as_of_date=as_of_date,
            requested_cells=requested_cohort_cells,
        ))
    )

    # 4. Distribution shift — when corpus features are supplied.
    if corpus_features is not None:
        from .distribution_shift import features_from_ccd
        new_features = features_from_ccd(ccd)
        report.results.append(
            check_distribution_shift(new_features, corpus_features)
        )
    else:
        report.results.append(GuardrailResult(
            guardrail="distribution_shift", ok=True, status="PASS",
            reason="skipped — no benchmark corpus supplied",
        ))

    # 5. Temporal validity — always runs; reads the built-in reg
    # calendar from temporal_validity.
    report.results.append(scan_for_discontinuities(claims))

    # 6. Provenance chain completeness — runs at packet build time
    # against the packet's provenance graph, not here at the pre-
    # flight stage. We emit a neutral PASS so the guardrail count
    # stays at 6; the real check happens in explain_for_ui when the
    # API endpoint is hit.
    report.results.append(GuardrailResult(
        guardrail="provenance_chain", ok=True, status="PASS",
        reason="deferred to explain_for_ui when a metric is queried; "
               "chain_is_complete() runs there on every request",
    ))

    return report


# ── Boundary converter: GuardrailResult → IntegrityCheck ────────────

def to_integrity_checks(
    results: Iterable[GuardrailResult],
) -> List[Any]:
    """Convert ``GuardrailResult`` instances into the packet-side
    ``IntegrityCheck`` type.

    Lazy import of ``rcm_mc.analysis.packet.IntegrityCheck`` keeps
    this module free of an ``analysis/`` dependency at load time —
    partners who use the preflight without the packet never import
    packet.py.
    """
    from ...analysis.packet import IntegrityCheck

    return [
        IntegrityCheck(
            guardrail=r.guardrail,
            ok=r.ok,
            status=r.status,
            reason=r.reason,
            details=dict(r.details or {}),
        )
        for r in results
    ]

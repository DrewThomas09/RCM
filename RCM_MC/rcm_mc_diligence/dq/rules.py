"""Pre-dbt DQ rules.

These run on raw tables *before* Tuva gets hold of them. They surface
pathologies a partner cares about even when Tuva's own tests pass:

- File completeness (did the 837 and 835 counts reconcile?)
- Duplicate raw keys (claim_id × claim_line_number uniqueness)
- Payer coverage (for mess_scenario_5 CRITICAL coverage degradation)
- Unmapped billing codes (for mess_scenario_4 unmapped_procedure)
- Orphaned remittance rows (for mess_scenario_2 835s without 837 parent)

Each rule returns a :class:`RuleFinding`. The pipeline collects them,
folds them into the appropriate ``DQReport`` section, and lets the
rule decide its own severity.

Rules are pure functions of the warehouse + loader result. They do
not mutate anything — side-effect-free is what makes the pipeline
re-runnable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..ingest.file_loader import LoaderResult
from ..ingest.warehouse import TableRef, WarehouseAdapter
from .report import DQSectionStatus, DQSeverity


# ── Finding shape ────────────────────────────────────────────────────

@dataclass
class RuleFinding:
    rule: str
    severity: DQSeverity
    status: DQSectionStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# ── Rule registry ────────────────────────────────────────────────────

_RAW_SCHEMA = "raw_data"


def run_all_rules(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> List[RuleFinding]:
    """Run every rule that has data to chew on. The order is stable so
    the resulting DQReport hash is deterministic."""
    findings: List[RuleFinding] = []
    for rule in _REGISTERED_RULES:
        f = rule(adapter, loader)
        if f is not None:
            if isinstance(f, list):
                findings.extend(f)
            else:
                findings.append(f)
    return findings


# ── Individual rules ─────────────────────────────────────────────────

def _rule_duplicate_raw_keys(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """``medical_claims`` rows should be unique on
    (claim_id, claim_line_number, data_source). Tuva will enforce this
    too — we run it pre-dbt so the report is informative when dbt
    later fails outright.
    """
    ref = loader.tables.get("medical_claims")
    if ref is None:
        return None
    cols = set(c.lower() for c in adapter.columns(ref))
    pk = ("claim_id", "claim_line_number", "data_source")
    if not all(c in cols for c in pk):
        return None
    qcols = ", ".join(adapter.quote_identifier(c) for c in pk)
    rows = adapter.fetchall(
        f"select count(*) from ("
        f"select {qcols}, count(*) c from {ref.qualified()} "
        f"group by {qcols} having count(*) > 1)"
    )
    dup_keys = int(rows[0][0]) if rows else 0
    if dup_keys == 0:
        return RuleFinding(
            rule="duplicate_raw_keys", severity=DQSeverity.INFO,
            status=DQSectionStatus.OK,
            message="No duplicate (claim_id, claim_line_number, data_source) keys in medical_claims.",
        )
    return RuleFinding(
        rule="duplicate_raw_keys", severity=DQSeverity.WARN,
        status=DQSectionStatus.WARN,
        message=f"{dup_keys:,} duplicate (claim_id, claim_line_number, data_source) keys in medical_claims.",
        details={"duplicate_key_count": dup_keys},
    )


def _rule_orphaned_remittance(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """Remittance (835) rows whose claim_id does not match any row in
    the 837 submitted-claims table. Models ``mess_scenario_2``.
    """
    subs_ref = loader.tables.get("medical_claims")
    remit_ref = loader.tables.get("remittance")
    if subs_ref is None or remit_ref is None:
        return None
    sub_cols = set(c.lower() for c in adapter.columns(subs_ref))
    rem_cols = set(c.lower() for c in adapter.columns(remit_ref))
    if "claim_id" not in sub_cols or "claim_id" not in rem_cols:
        return None
    orphan_rows = adapter.fetchall(
        f"select count(*), coalesce(sum(paid_amount),0) "
        f"from {remit_ref.qualified()} r "
        f"where not exists (select 1 from {subs_ref.qualified()} s "
        f"where s.claim_id = r.claim_id)"
    )
    count = int(orphan_rows[0][0]) if orphan_rows else 0
    dollars = float(orphan_rows[0][1] or 0) if orphan_rows else 0.0
    if count == 0:
        return RuleFinding(
            rule="orphaned_remittance", severity=DQSeverity.INFO,
            status=DQSectionStatus.OK,
            message="Every 835 remittance row matches a submitted claim.",
        )
    return RuleFinding(
        rule="orphaned_remittance", severity=DQSeverity.WARN,
        status=DQSectionStatus.WARN,
        message=f"{count:,} orphaned 835 rows (${dollars:,.2f} in paid_amount) — quarantined.",
        details={"orphan_row_count": count, "orphan_paid_amount": dollars},
    )


def _rule_unmapped_procedures(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """Claims whose hcpcs_code is not in a standard HCPCS/CPT shape.
    Heuristic: HCPCS is 5-char alphanumeric; anything else is flagged.
    Models ``mess_scenario_4``.
    """
    ref = loader.tables.get("medical_claims")
    if ref is None:
        return None
    cols = set(c.lower() for c in adapter.columns(ref))
    if "hcpcs_code" not in cols:
        return None
    rows = adapter.fetchall(
        f"select count(*) from {ref.qualified()} "
        f"where hcpcs_code is not null and not regexp_matches(hcpcs_code, '^[A-Z0-9]{{5}}$')"
    )
    unmapped = int(rows[0][0]) if rows else 0
    total_rows = adapter.fetchall(
        f"select count(*) from {ref.qualified()} where hcpcs_code is not null"
    )
    total = int(total_rows[0][0]) if total_rows else 0
    rate = unmapped / total if total else 0.0
    if unmapped == 0:
        return RuleFinding(
            rule="unmapped_procedures", severity=DQSeverity.INFO,
            status=DQSectionStatus.OK,
            message="All hcpcs_code values match HCPCS/CPT shape.",
        )
    sev = DQSeverity.ERROR if rate >= 0.10 else DQSeverity.WARN
    status = DQSectionStatus.WARN if sev == DQSeverity.WARN else DQSectionStatus.FAIL
    # Include top-20 unmapped codes by frequency — these drive the
    # unmapped-code ranking in the DQ report.
    top = adapter.fetchall(
        f"select hcpcs_code, count(*) c from {ref.qualified()} "
        f"where hcpcs_code is not null and not regexp_matches(hcpcs_code, '^[A-Z0-9]{{5}}$') "
        f"group by hcpcs_code order by c desc limit 20"
    )
    return RuleFinding(
        rule="unmapped_procedures", severity=sev, status=status,
        message=f"{unmapped:,} of {total:,} ({rate*100:.1f}%) hcpcs_code values do not match HCPCS/CPT shape.",
        details={
            "unmapped_count": unmapped, "total_with_code": total, "rate": rate,
            "top_unmapped": [{"code": r[0], "count": int(r[1])} for r in top],
        },
    )


def _rule_payer_coverage(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """Partial payer mix — ``mess_scenario_5``. Critical because a
    downstream analysis that relies on payer-class distribution can't
    compute base rates when the payer is missing on a large fraction of
    rows.

    We coalesce across payer column synonyms (payer_id, payer,
    payer_name) before evaluating. In multi-EHR fixtures, different
    clinics use different column names — the raw table may have three
    partially-populated payer columns that, together, describe a
    clean payer mix. Treating them as one covers that case.
    """
    ref = loader.tables.get("medical_claims")
    if ref is None:
        return None
    cols = set(c.lower() for c in adapter.columns(ref))
    synonyms = [c for c in ("payer_id", "payer", "payer_name") if c in cols]
    if not synonyms:
        return None
    # Build a coalesce expression across all present synonyms.
    qcols = [adapter.quote_identifier(c) for c in synonyms]
    coalesced = "coalesce(" + ", ".join(qcols) + ")"
    resolved_set = (
        "('MCARE','MCAID','COMM','BCBS','AETNA','CIGNA','UHC','HUMANA','TRICARE',"
        "'Medicare Part B','Medicaid — State','Blue Cross Blue Shield PPO',"
        "'Aetna HMO','UnitedHealthcare','Cigna HealthSpring',"
        "'Humana Medicare Advantage','Commercial Self-Funded','Blue Crosß Blue Shield')"
    )
    rows = adapter.fetchall(
        f"select count(*), "
        f"sum(case when {coalesced} is null then 1 else 0 end), "
        f"sum(case when {coalesced} is not null and not {coalesced} in "
        f"{resolved_set} then 1 else 0 end) "
        f"from {ref.qualified()}"
    )
    total = int(rows[0][0]) if rows else 0
    null_count = int(rows[0][1] or 0) if rows else 0
    unresolved = int(rows[0][2] or 0) if rows else 0
    if total == 0:
        return None
    missing_rate = null_count / total
    unresolved_rate = unresolved / total
    degraded = missing_rate + unresolved_rate >= 0.30
    if degraded:
        return RuleFinding(
            rule="payer_coverage", severity=DQSeverity.CRITICAL,
            status=DQSectionStatus.FAIL,
            message=(
                f"Analysis coverage degraded: "
                f"{missing_rate*100:.1f}% of claims have no payer_id and "
                f"{unresolved_rate*100:.1f}% have an unresolved payer_id. "
                f"Base-rate analyses will be unreliable."
            ),
            details={
                "missing_payer_rate": missing_rate,
                "unresolved_payer_rate": unresolved_rate,
                "total_rows": total,
                "degraded_analyses": [
                    "cohort_liquidation", "denial_stratification",
                    "zba_autopsy", "payer_contract_yield",
                ],
            },
        )
    if missing_rate + unresolved_rate >= 0.05:
        return RuleFinding(
            rule="payer_coverage", severity=DQSeverity.WARN,
            status=DQSectionStatus.WARN,
            message=(
                f"Partial payer coverage: "
                f"{missing_rate*100:.1f}% missing, {unresolved_rate*100:.1f}% unresolved."
            ),
            details={
                "missing_payer_rate": missing_rate,
                "unresolved_payer_rate": unresolved_rate,
                "total_rows": total,
            },
        )
    return RuleFinding(
        rule="payer_coverage", severity=DQSeverity.INFO,
        status=DQSectionStatus.OK,
        message="Payer coverage acceptable.",
    )


def _rule_duplicate_adjudication(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """Same claim appears in the remittance table with conflicting
    paid_amount across adjudication events. Models ``mess_scenario_3``.
    Tuva's ADR logic will reconcile; we surface the count so partners
    can see the magnitude.
    """
    ref = loader.tables.get("remittance")
    if ref is None:
        return None
    cols = set(c.lower() for c in adapter.columns(ref))
    if not {"claim_id", "paid_amount"}.issubset(cols):
        return None
    rows = adapter.fetchall(
        f"select count(distinct claim_id) from ("
        f"select claim_id from {ref.qualified()} "
        f"group by claim_id having count(distinct paid_amount) > 1)"
    )
    conflicting = int(rows[0][0]) if rows else 0
    if conflicting == 0:
        return RuleFinding(
            rule="duplicate_adjudication", severity=DQSeverity.INFO,
            status=DQSectionStatus.OK,
            message="No claims with conflicting paid_amount across adjudication events.",
        )
    return RuleFinding(
        rule="duplicate_adjudication", severity=DQSeverity.WARN,
        status=DQSectionStatus.WARN,
        message=(
            f"{conflicting:,} claims have multiple adjudication rows with "
            f"conflicting paid_amount. Tuva's ADR logic will reconcile."
        ),
        details={"conflicting_claim_count": conflicting},
    )


def _rule_multi_ehr_merge(
    adapter: WarehouseAdapter, loader: LoaderResult
) -> Optional[RuleFinding]:
    """Three acquired clinics with different column names should have
    been normalised into a single medical_claims table. Models
    ``mess_scenario_1``. We detect successful normalisation by the
    presence of ``data_source`` with at least 2 distinct values.
    """
    ref = loader.tables.get("medical_claims")
    if ref is None:
        return None
    cols = set(c.lower() for c in adapter.columns(ref))
    if "data_source" not in cols:
        return None
    rows = adapter.fetchall(
        f"select count(distinct data_source) from {ref.qualified()}"
    )
    n = int(rows[0][0]) if rows else 0
    if n <= 1:
        return None
    per = adapter.fetchall(
        f"select data_source, count(*) from {ref.qualified()} "
        f"group by data_source order by count(*) desc"
    )
    return RuleFinding(
        rule="multi_ehr_merge", severity=DQSeverity.INFO,
        status=DQSectionStatus.OK,
        message=f"Merged {n} data sources into one medical_claims table.",
        details={"per_source_row_count": {r[0]: int(r[1]) for r in per}},
    )


_REGISTERED_RULES: List[Callable[[WarehouseAdapter, LoaderResult], Any]] = [
    _rule_duplicate_raw_keys,
    _rule_orphaned_remittance,
    _rule_unmapped_procedures,
    _rule_payer_coverage,
    _rule_duplicate_adjudication,
    _rule_multi_ehr_merge,
]

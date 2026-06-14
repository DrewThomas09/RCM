"""Data-quality checks over the canonical NPPES tables.

Each check returns a ``DQResult`` (name, passed, metric, detail). The
pipeline runs them all and records the report; ``all_passed`` gates the
Definition-of-Done. Checks are read-only.

Covered (per the contract):
  • NPI Luhn validation — every dim_provider NPI is well-formed.
  • Deactivation-flag coverage — status is set for every row and matches
    the presence/absence of a deactivation date.
  • Taxonomy resolution rate — share of bridge taxonomy codes that resolve
    in dim_taxonomy (the NUCC code set).
  • Duplicate-NPI check — dim_provider PK holds; no NPI appears twice.
  • Row-count reconciliation — dim_provider count vs the source-file header
    count recorded in nppes_load_state (within tolerance).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .luhn import is_valid_npi


@dataclass
class DQResult:
    name: str
    passed: bool
    metric: float
    detail: str


def check_npi_luhn(store: Any, *, sample_limit: Optional[int] = None) -> DQResult:
    bad = 0
    total = 0
    with store.connect() as con:
        cur = con.execute("SELECT npi FROM dim_provider")
        for r in cur:
            total += 1
            if not is_valid_npi(r["npi"]):
                bad += 1
            if sample_limit and total >= sample_limit:
                break
    rate = 1.0 if total == 0 else (total - bad) / total
    return DQResult("npi_luhn_validation", bad == 0, rate,
                    f"{total - bad}/{total} valid; {bad} invalid in dim_provider")


def check_deactivation_coverage(store: Any) -> DQResult:
    with store.connect() as con:
        total = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
        null_status = con.execute(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE status IS NULL OR status=''").fetchone()["c"]
        # status must be 'deactivated' exactly when a deactivation date with
        # no later reactivation is present.
        mismatch = con.execute(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE (deactivation_date IS NOT NULL AND deactivation_date<>'' "
            "       AND (reactivation_date IS NULL OR reactivation_date='' "
            "            OR reactivation_date < deactivation_date) "
            "       AND status<>'deactivated') "
            "   OR ((deactivation_date IS NULL OR deactivation_date='') "
            "       AND status='deactivated')").fetchone()["c"]
        deact = con.execute(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE status='deactivated'").fetchone()["c"]
    passed = (null_status == 0 and mismatch == 0)
    cov = 1.0 if total == 0 else (total - null_status) / total
    return DQResult("deactivation_flag_coverage", passed, cov,
                    f"status set on {total - null_status}/{total}; "
                    f"{deact} deactivated; {mismatch} flag mismatches")


def check_taxonomy_resolution(store: Any, *, threshold: float = 0.95) -> DQResult:
    with store.connect() as con:
        total = con.execute(
            "SELECT COUNT(DISTINCT taxonomy_code) c "
            "FROM bridge_provider_taxonomy").fetchone()["c"]
        unresolved = con.execute(
            "SELECT COUNT(*) c FROM (SELECT DISTINCT b.taxonomy_code "
            "FROM bridge_provider_taxonomy b "
            "LEFT JOIN dim_taxonomy t ON t.taxonomy_code=b.taxonomy_code "
            "WHERE t.taxonomy_code IS NULL)").fetchone()["c"]
    resolved = total - unresolved
    rate = 1.0 if total == 0 else resolved / total
    return DQResult("taxonomy_resolution_rate", rate >= threshold, rate,
                    f"{resolved}/{total} distinct taxonomy codes resolve in NUCC "
                    f"(threshold {threshold:.0%})")


def check_duplicate_npi(store: Any) -> DQResult:
    with store.connect() as con:
        dupes = con.execute(
            "SELECT COUNT(*) c FROM (SELECT npi FROM dim_provider "
            "GROUP BY npi HAVING COUNT(*) > 1)").fetchone()["c"]
    return DQResult("duplicate_npi_check", dupes == 0, float(dupes),
                    f"{dupes} duplicated NPIs in dim_provider")


def check_rowcount_reconciliation(store: Any, *, tolerance: float = 0.02) -> DQResult:
    with store.connect() as con:
        loaded = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
        st = con.execute(
            "SELECT monthly_header_count FROM nppes_load_state WHERE id=1").fetchone()
        header = (st["monthly_header_count"] if st else None)
        quarantined = con.execute(
            "SELECT COUNT(*) c FROM nppes_invalid_npi").fetchone()["c"]
    if not header:
        return DQResult("rowcount_reconciliation", False, 0.0,
                        "no monthly_header_count recorded in nppes_load_state")
    # loaded + quarantined should reconcile to the header count (weeklies can
    # add net-new rows, so loaded may exceed header — we allow >= within band).
    accounted = loaded + quarantined
    delta = abs(accounted - header) / header
    passed = (accounted >= header * (1 - tolerance))
    return DQResult("rowcount_reconciliation", passed, 1 - delta,
                    f"header={header} loaded={loaded} quarantined={quarantined} "
                    f"accounted={accounted} delta={delta:.3%} (tol {tolerance:.0%})")


def run_all(store: Any, *, taxonomy_threshold: float = 0.95) -> Dict[str, Any]:
    results: List[DQResult] = [
        check_npi_luhn(store),
        check_deactivation_coverage(store),
        check_taxonomy_resolution(store, threshold=taxonomy_threshold),
        check_duplicate_npi(store),
        check_rowcount_reconciliation(store),
    ]
    return {
        "all_passed": all(r.passed for r in results),
        "results": results,
        "summary": {r.name: {"passed": r.passed, "metric": round(r.metric, 4),
                             "detail": r.detail} for r in results},
    }

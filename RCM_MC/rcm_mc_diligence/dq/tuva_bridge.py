"""Translate the dbt connector output into ``DQReport`` sections.

Why a separate module: the dbt output is a moving target across
versions, and Tuva's test tags have semantic meaning partners want to
see preserved. Keeping the translation here means the DQReport schema
stays stable even if Tuva changes its tag vocabulary.

The two public functions map, respectively:
- A :class:`DbtRunResult` → ``DQReport.tuva_dq_results`` section
- A connector run + warehouse introspection → ``connector_mapping`` rows
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..ingest.connector import DbtRunResult, DbtTestResult, CONNECTOR_ROOT
from ..ingest.warehouse import TableRef, WarehouseAdapter
from .report import DQSectionStatus, DQSeverity, Section, TuvaDQFinding


def fold_tuva_results(run: DbtRunResult) -> Section:
    """Produce the ``tuva_dq_results`` section."""
    findings: List[TuvaDQFinding] = []
    for t in run.tests:
        findings.append(TuvaDQFinding(
            test_name=t.name,
            unique_id=t.unique_id,
            status=t.status,
            severity=t.severity,
            failures=t.failures,
            tags=list(t.tags or []),
            sample_failing_rows=[],  # sampling left for Phase 0.B
        ))

    # Roll up section status.
    has_error_fail = any(
        f.status in ("fail", "error") and f.severity == "error" for f in findings
    )
    has_warn_fail = any(
        (f.status in ("fail", "warn")) and f.severity == "warn" for f in findings
    )
    status = (
        DQSectionStatus.FAIL if has_error_fail
        else DQSectionStatus.WARN if has_warn_fail
        else DQSectionStatus.OK
    )
    severity = (
        DQSeverity.ERROR if has_error_fail
        else DQSeverity.WARN if has_warn_fail
        else DQSeverity.INFO
    )
    msg = (
        f"{len(findings)} Tuva DQ tests. "
        f"{sum(1 for f in findings if f.status == 'pass')} passed, "
        f"{sum(1 for f in findings if f.status == 'warn')} warn, "
        f"{sum(1 for f in findings if f.status in ('fail','error'))} failed."
    ) if findings else (
        "No Tuva DQ tests executed — check that dbt build selected "
        "the input_layer models."
    )

    return Section(
        status=status, severity=severity, message=msg,
        rows=[_finding_to_row(f) for f in findings],
    )


def _finding_to_row(f: TuvaDQFinding) -> Dict[str, Any]:
    return {
        "test_name": f.test_name,
        "unique_id": f.unique_id,
        "status": f.status,
        "severity": f.severity,
        "failures": f.failures,
        "tags": list(f.tags),
        "sample_failing_rows": list(f.sample_failing_rows),
    }


def build_connector_mapping_rows(
    adapter: WarehouseAdapter, run: DbtRunResult
) -> List[Dict[str, Any]]:
    """Introspect the ``main`` schema (where Tuva input-layer models
    land) and pull the rationale comments out of our connector SQL.

    We don't parse the dbt AST — we just read the .sql files we shipped
    and extract ``-- RATIONALE:`` comments keyed by the preceding
    column alias. It's a scruffy regex, but the SQL is ours and we
    control its shape.
    """
    rationales = _extract_rationales()
    rows: List[Dict[str, Any]] = []
    for tuva_table in ("medical_claim", "pharmacy_claim", "eligibility"):
        tref = TableRef(name=f"input_layer__{tuva_table}")
        if not adapter.table_exists(tref):
            # Tuva didn't build it (likely failed upstream) — skip
            continue
        cols = adapter.columns(tref)
        for col in cols:
            try:
                rate = adapter.null_rate(tref, col)
            except Exception:
                rate = 0.0
            source_field, transform, rationale = rationales.get(
                (tuva_table, col), ("", "", "")
            )
            rows.append({
                "tuva_table": tuva_table,
                "tuva_column": col,
                "source_field": source_field,
                "transformation": transform,
                "null_rate": rate,
                "rows_dropped": 0,
                "rationale": rationale,
            })
    return rows


def _extract_rationales() -> Dict[Tuple[str, str], Tuple[str, str, str]]:
    """Parse our connector .sql files for RATIONALE comments.

    Expected shape inside the SQL:

        -- RATIONALE: the reason we did this
        <expr> as <col>,

    We scan every line for ``as <colname>,?`` and attach the most
    recent ``-- RATIONALE:`` comment above it. A trailing
    ``-- SOURCE: <field>`` comment is also captured for the source
    field column.
    """
    import re

    table_map = {
        "medical_claim.sql": "medical_claim",
        "pharmacy_claim.sql": "pharmacy_claim",
        "eligibility.sql": "eligibility",
    }
    models_dir = CONNECTOR_ROOT / "models" / "input_layer"
    out: Dict[Tuple[str, str], Tuple[str, str, str]] = {}
    rationale_re = re.compile(r"--\s*RATIONALE:\s*(.+)", re.IGNORECASE)
    source_re = re.compile(r"--\s*SOURCE:\s*(.+)", re.IGNORECASE)
    # Accept `as colname,`, `as "colname",`, `as colname\n`
    as_re = re.compile(r'\b[Aa][Ss]\s+"?([A-Za-z_][A-Za-z0-9_]*)"?\s*,?\s*$')
    for fname, tuva_table in table_map.items():
        path = models_dir / fname
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        last_rationale = ""
        last_source = ""
        for line in text.splitlines():
            stripped = line.strip()
            m = rationale_re.search(stripped)
            if m:
                last_rationale = m.group(1).strip()
                continue
            m = source_re.search(stripped)
            if m:
                last_source = m.group(1).strip()
                continue
            m = as_re.search(stripped)
            if m:
                col = m.group(1)
                transform = stripped.rsplit(" as ", 1)[0].strip() if " as " in stripped.lower() else ""
                # Lowercase 'as' match — handle case-insensitive split.
                idx = stripped.lower().rfind(" as ")
                if idx >= 0:
                    transform = stripped[:idx].strip().rstrip(",")
                out[(tuva_table, col.lower())] = (last_source, transform, last_rationale)
                last_rationale = ""
                last_source = ""
    return out


def build_raw_load_rows(
    adapter: WarehouseAdapter, raw_tables: Dict[str, TableRef]
) -> List[Dict[str, Any]]:
    """Row per raw_data table — what landed, how many rows, null rates."""
    rows: List[Dict[str, Any]] = []
    for name, ref in sorted(raw_tables.items()):
        try:
            rc = adapter.row_count(ref)
        except LookupError:
            continue
        cols = adapter.columns(ref)
        null_rates: Dict[str, float] = {}
        for c in cols:
            try:
                null_rates[c] = adapter.null_rate(ref, c)
            except Exception:
                null_rates[c] = 0.0
        rows.append({
            "table": ref.name,
            "schema": ref.schema or "",
            "row_count": rc,
            "load_duration_seconds": 0.0,
            "column_null_rates": null_rates,
        })
    return rows


def build_analysis_coverage_rows(
    adapter: WarehouseAdapter,
    tuva_input_tables_present: Dict[str, bool],
    findings: List[Any],
) -> List[Dict[str, Any]]:
    """Map each Phase 0.B analysis to its required inputs and whether
    we can compute it.

    The required-field lists are deliberately conservative — these are
    the *minimum* fields; real analyses may want more, and Phase 0.B
    will tighten them. The point of this table is that a partner can
    read it before spending an afternoon running analyses that won't
    terminate for lack of input.
    """
    # Collect which fields are present and sufficiently populated.
    med_ref = TableRef(name="input_layer__medical_claim")
    elig_ref = TableRef(name="input_layer__eligibility")
    raw_med = TableRef(name="medical_claims", schema="raw_data")

    def _present(ref: TableRef, col: str, max_null_rate: float = 0.50) -> bool:
        if not adapter.table_exists(ref):
            return False
        try:
            if col.lower() not in [c.lower() for c in adapter.columns(ref)]:
                return False
            return adapter.null_rate(ref, col) <= max_null_rate
        except Exception:
            return False

    # Payer-coverage finding can downgrade computability.
    critical_coverage_degraded = any(
        getattr(f, "severity", None) == DQSeverity.CRITICAL
        and getattr(f, "rule", "") == "payer_coverage"
        for f in findings
    )

    analyses = [
        {
            "analysis": "cohort_liquidation",
            "required": [("medical_claim", "claim_start_date"),
                         ("medical_claim", "paid_amount"),
                         ("medical_claim", "charge_amount")],
            "note": "Monthly liquidation curves by service-month cohort.",
        },
        {
            "analysis": "zba_autopsy",
            "required": [("medical_claim", "claim_id"),
                         ("medical_claim", "paid_amount"),
                         ("medical_claim", "allowed_amount")],
            "note": "Zero-balance-adjustment root cause scan.",
        },
        {
            "analysis": "denial_stratification",
            "required": [("medical_claim", "claim_id"),
                         ("medical_claim", "payer"),
                         ("medical_claim", "paid_amount")],
            "note": "Denial rate by payer × CPT category.",
        },
        {
            "analysis": "lag_analytics",
            "required": [("medical_claim", "claim_start_date"),
                         ("medical_claim", "paid_date")],
            "note": "DOS→paid lag distribution.",
        },
        {
            "analysis": "nrr",
            "required": [("eligibility", "enrollment_start_date"),
                         ("eligibility", "enrollment_end_date"),
                         ("medical_claim", "paid_amount")],
            "note": "Net revenue retention by member cohort.",
        },
        {
            "analysis": "payer_contract_yield",
            "required": [("medical_claim", "payer"),
                         ("medical_claim", "allowed_amount"),
                         ("medical_claim", "charge_amount")],
            "note": "Contract-level yield vs charge.",
        },
    ]

    rows: List[Dict[str, Any]] = []
    for a in analyses:
        missing: List[str] = []
        for tbl, col in a["required"]:
            ref = {"medical_claim": med_ref, "eligibility": elig_ref}.get(tbl)
            if ref is None or not _present(ref, col):
                missing.append(f"{tbl}.{col}")
        computable = not missing
        note = a["note"]
        if critical_coverage_degraded and a["analysis"] in (
            "cohort_liquidation", "denial_stratification",
            "zba_autopsy", "payer_contract_yield",
        ):
            computable = False
            missing = missing or ["<payer coverage degraded>"]
            note = note + " Disabled — payer coverage below threshold."
        rows.append({
            "analysis": a["analysis"],
            "computable": computable,
            "required_fields": [f"{t}.{c}" for t, c in a["required"]],
            "missing_fields": missing,
            "note": note,
        })
    return rows

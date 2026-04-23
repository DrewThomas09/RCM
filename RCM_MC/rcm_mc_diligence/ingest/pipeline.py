"""The top-level ingestion pipeline.

``run_ingest`` is what the CLI calls. It:

1. Hashes the input files (so identical inputs → identical output hash).
2. Loads raw files into the adapter's ``raw_data`` schema.
3. Runs our pre-dbt DQ rules.
4. Invokes dbt against the seekingchartis connector — this builds the
   Tuva Input Layer (medical_claim, pharmacy_claim, eligibility) and
   runs Tuva's built-in DQ tests on them.
5. Introspects the built tables to populate the mapping + raw_load
   sections of the DQ report.
6. Folds everything into a :class:`DQReport`, writes JSON + HTML to
   ``output_dir``, returns the report.

The pipeline is idempotent when the inputs are fixed. We guarantee
this by:

- Deriving ``run_id`` from ``hash_ingest_inputs`` (not ``datetime.now``)
  unless the caller overrides it.
- Sorting everything iterable at serialisation.
- Excluding ``wall_time_utc``, dbt ``invocation_id``, and per-run file
  timestamps from :meth:`DQReport.content_hash`.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..dq.report import (
    DQReport,
    DQSectionStatus,
    DQSeverity,
    Provenance,
    Section,
)
from ..dq.rules import RuleFinding, run_all_rules
from ..dq.tuva_bridge import (
    build_analysis_coverage_rows,
    build_connector_mapping_rows,
    build_raw_load_rows,
    fold_tuva_results,
)
from .connector import CONNECTOR_VERSION, run_connector
from .file_loader import RAW_SCHEMA, LoaderResult, load_directory
from .warehouse import DuckDBAdapter, TableRef, WarehouseAdapter


# ── Hashing ──────────────────────────────────────────────────────────

def hash_ingest_inputs(
    directory: Path,
    *,
    connector: str = "seekingchartis",
    connector_version: str = CONNECTOR_VERSION,
    tuva_version: str = "",
) -> str:
    """Deterministic sha256 over every file in ``directory`` + the
    connector + Tuva version. Mirrors the pattern in
    :func:`rcm_mc.analysis.packet.hash_inputs`.

    Files are sorted by relative path so filesystem iteration order
    doesn't affect the result.
    """
    directory_p = Path(directory)
    parts: List[Dict[str, Any]] = []
    for p in sorted(directory_p.rglob("*")):
        if not p.is_file():
            continue
        parts.append({
            "rel": str(p.relative_to(directory_p)),
            "sha256": _file_sha256(p),
            "size": p.stat().st_size,
        })
    payload = {
        "connector": connector,
        "connector_version": connector_version,
        "tuva_version": tuva_version,
        "files": parts,
    }
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _file_sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def hash_file_map(directory: Path) -> Dict[str, str]:
    """Per-file sha256 map, used for provenance."""
    directory_p = Path(directory)
    return {
        str(p.relative_to(directory_p)): _file_sha256(p)
        for p in sorted(directory_p.rglob("*"))
        if p.is_file()
    }


# ── Run options ──────────────────────────────────────────────────────

def default_run_id(input_dir: Path, connector_version: str, tuva_version: str) -> str:
    """A deterministic run id so the same inputs produce the same id.
    Format: ``sc-<first-12-of-input-hash>``. Timestamp is not included
    — by design, so idempotency holds.
    """
    h = hash_ingest_inputs(
        input_dir,
        connector_version=connector_version,
        tuva_version=tuva_version,
    )
    return f"sc-{h[:12]}"


# ── Main entry point ─────────────────────────────────────────────────

def run_ingest(
    dataset_dir: Path | str,
    *,
    output_dir: Path | str,
    adapter: Optional[WarehouseAdapter] = None,
    run_id: Optional[str] = None,
    dry_run: bool = False,
    tuva_version_hint: str = "",
) -> DQReport:
    """Run the ingestion pipeline end-to-end.

    ``adapter`` defaults to a fresh DuckDB adapter writing to
    ``<output_dir>/<run_id>/diligence.duckdb``. When ``dry_run=True``,
    we validate everything up to and including pre-dbt DQ rules but
    skip the dbt invocation and do not write JSON/HTML artefacts.
    """
    dataset_dir_p = Path(dataset_dir)
    if not dataset_dir_p.is_dir():
        raise FileNotFoundError(f"dataset is not a directory: {dataset_dir_p}")

    resolved_run_id = run_id or default_run_id(
        dataset_dir_p, CONNECTOR_VERSION, tuva_version_hint
    )
    run_output = Path(output_dir) / resolved_run_id
    run_output.mkdir(parents=True, exist_ok=True)

    own_adapter = adapter is None
    if adapter is None:
        adapter = DuckDBAdapter(run_output / "diligence.duckdb")

    report = DQReport()
    report.provenance = Provenance(
        connector="seekingchartis",
        connector_version=CONNECTOR_VERSION,
        adapter_backend=adapter.backend_name,
        input_file_hashes=hash_file_map(dataset_dir_p),
        run_id=resolved_run_id,
        wall_time_utc=datetime.now(timezone.utc).isoformat(),
    )

    try:
        # 1 — Load raw files.
        t0 = time.perf_counter()
        loader = load_directory(adapter, dataset_dir_p, schema=RAW_SCHEMA)
        load_elapsed = time.perf_counter() - t0
        report.source_inventory = _build_inventory_section(loader)

        if loader.failed_count() > 0 and loader.ok_count() == 0:
            report.source_inventory.status = DQSectionStatus.FAIL
            report.source_inventory.severity = DQSeverity.ERROR
            report.overall_status = DQSectionStatus.FAIL
            report.overall_message = "All input files failed to load."
            _finalise(report, run_output, dry_run)
            return report

        # 2 — Pre-dbt DQ rules.
        findings = run_all_rules(adapter, loader)

        # 3 — Populate raw load summary now (used even if dbt fails).
        raw_rows = build_raw_load_rows(adapter, loader.tables)
        for r in raw_rows:
            r["load_duration_seconds"] = load_elapsed / max(len(raw_rows), 1)
        report.raw_load_summary = _rollup_section(
            raw_rows,
            default_message=f"{len(raw_rows)} raw table(s) loaded.",
            source=loader,
        )

        # 4 — dbt invocation (skipped on dry_run).
        if dry_run:
            report.connector_mapping = Section(
                status=DQSectionStatus.SKIPPED,
                severity=DQSeverity.INFO,
                message="Dry-run: dbt build skipped.",
            )
            report.tuva_dq_results = Section(
                status=DQSectionStatus.SKIPPED,
                severity=DQSeverity.INFO,
                message="Dry-run: Tuva DQ tests skipped.",
            )
            report.analysis_coverage = _coverage_from_findings_only(
                findings, raw_only=True
            )
        else:
            # Release our adapter connection so dbt can take it.
            adapter.close()
            try:
                dbt_result = run_connector(adapter, run_dir=run_output)
            finally:
                # Re-open for post-dbt introspection.
                adapter.connect()

            report.provenance.dbt_version = dbt_result.dbt_version
            report.provenance.tuva_version = dbt_result.tuva_version

            # 5 — Mapping + Tuva DQ sections.
            report.tuva_dq_results = fold_tuva_results(dbt_result)
            mapping_rows = build_connector_mapping_rows(adapter, dbt_result)
            report.connector_mapping = _rollup_mapping_section(mapping_rows, dbt_result)

            # 6 — Coverage.
            tuva_present = {
                "medical_claim": adapter.table_exists(TableRef("input_layer__medical_claim")),
                "pharmacy_claim": adapter.table_exists(TableRef("input_layer__pharmacy_claim")),
                "eligibility": adapter.table_exists(TableRef("input_layer__eligibility")),
            }
            coverage_rows = build_analysis_coverage_rows(
                adapter, tuva_present, findings,
            )
            report.analysis_coverage = _rollup_coverage_section(coverage_rows, findings)

        # Fold pre-dbt findings into the right sections.
        _apply_findings_to_report(report, findings)

        report.recompute_overall()
        _finalise(report, run_output, dry_run)
        return report
    finally:
        if own_adapter:
            adapter.close()


# ── Section builders ─────────────────────────────────────────────────

def _build_inventory_section(loader: LoaderResult) -> Section:
    rows: List[Dict[str, Any]] = []
    for f in loader.files:
        rows.append({
            "path": f.path, "size_bytes": f.size_bytes, "format": f.format,
            "row_count": f.rows_loaded,
            "columns_detected": list(f.columns_detected),
            "columns_dropped": list(f.columns_dropped),
            "encoding": f.encoding, "status": f.status, "note": f.note,
        })
    if not rows:
        return Section(
            status=DQSectionStatus.FAIL, severity=DQSeverity.ERROR,
            message="No supported files found in dataset directory.", rows=rows,
        )
    any_fail = any(f.status == "FAILED" for f in loader.files)
    any_warn = any(f.status == "WARN" for f in loader.files)
    status = (
        DQSectionStatus.FAIL if any_fail
        else DQSectionStatus.WARN if any_warn
        else DQSectionStatus.OK
    )
    severity = (
        DQSeverity.ERROR if any_fail
        else DQSeverity.WARN if any_warn
        else DQSeverity.INFO
    )
    msg = f"{len(rows)} file(s) scanned. {loader.ok_count()} ok, {loader.failed_count()} failed."
    return Section(status=status, severity=severity, message=msg, rows=rows)


def _rollup_section(
    rows: List[Dict[str, Any]], *, default_message: str, source: Any = None
) -> Section:
    return Section(
        status=DQSectionStatus.OK if rows else DQSectionStatus.WARN,
        severity=DQSeverity.INFO,
        message=default_message if rows else "No raw tables materialised.",
        rows=rows,
    )


def _rollup_mapping_section(
    rows: List[Dict[str, Any]], dbt_result: Any
) -> Section:
    if not rows:
        return Section(
            status=DQSectionStatus.FAIL, severity=DQSeverity.ERROR,
            message="dbt did not materialise any input-layer table.",
            rows=rows,
        )
    high_null = [r for r in rows if r.get("null_rate", 0) >= 0.75]
    status = DQSectionStatus.WARN if high_null else DQSectionStatus.OK
    severity = DQSeverity.WARN if high_null else DQSeverity.INFO
    msg = f"{len(rows)} Tuva input-layer columns mapped."
    if high_null:
        msg += f" {len(high_null)} column(s) ≥75% null — review mapping."
    return Section(status=status, severity=severity, message=msg, rows=rows)


def _rollup_coverage_section(
    rows: List[Dict[str, Any]], findings: List[RuleFinding]
) -> Section:
    non_computable = [r for r in rows if not r.get("computable")]
    critical = any(f.severity == DQSeverity.CRITICAL for f in findings)
    if critical:
        status = DQSectionStatus.FAIL
        severity = DQSeverity.CRITICAL
        msg = "Analysis coverage degraded — critical coverage finding."
    elif non_computable:
        status = DQSectionStatus.WARN
        severity = DQSeverity.WARN
        msg = f"{len(non_computable)} of {len(rows)} diligence analyses are not computable."
    else:
        status = DQSectionStatus.OK
        severity = DQSeverity.INFO
        msg = f"All {len(rows)} diligence analyses are computable."
    return Section(status=status, severity=severity, message=msg, rows=rows)


def _coverage_from_findings_only(
    findings: List[RuleFinding], raw_only: bool
) -> Section:
    """Used in dry-run: we only know what the pre-dbt rules said."""
    critical = any(f.severity == DQSeverity.CRITICAL for f in findings)
    status = DQSectionStatus.SKIPPED
    severity = DQSeverity.CRITICAL if critical else DQSeverity.INFO
    msg = "Dry-run: full coverage matrix requires dbt build."
    if critical:
        msg += " Pre-dbt rules flagged CRITICAL coverage degradation."
    return Section(status=status, severity=severity, message=msg, rows=[])


def _apply_findings_to_report(
    report: DQReport, findings: List[RuleFinding]
) -> None:
    """Merge pre-dbt rule findings into the already-populated report.

    We append each finding as a row to the most appropriate section and
    bump the section's status/severity if the finding is stronger.
    """
    for f in findings:
        row = {
            "rule": f.rule, "severity": f.severity.value,
            "status": f.status.value, "message": f.message,
            **{k: v for k, v in f.details.items()},
        }
        target = _target_section_for_rule(report, f.rule)
        target.rows.append(row)
        if _status_rank(f.status) > _status_rank(target.status):
            target.status = f.status
        if _severity_rank(f.severity) > _severity_rank(target.severity):
            target.severity = f.severity


def _target_section_for_rule(report: DQReport, rule: str) -> Section:
    """Route a rule-finding to the section it belongs in."""
    mapping = {
        "duplicate_raw_keys": report.raw_load_summary,
        "multi_ehr_merge": report.raw_load_summary,
        "orphaned_remittance": report.raw_load_summary,
        "duplicate_adjudication": report.raw_load_summary,
        "unmapped_procedures": report.connector_mapping,
        "payer_coverage": report.analysis_coverage,
    }
    return mapping.get(rule, report.raw_load_summary)


def _status_rank(s: DQSectionStatus) -> int:
    return {
        DQSectionStatus.OK: 0, DQSectionStatus.SKIPPED: 1,
        DQSectionStatus.WARN: 2, DQSectionStatus.FAIL: 3,
    }[s]


def _severity_rank(s: DQSeverity) -> int:
    return {
        DQSeverity.INFO: 0, DQSeverity.WARN: 1,
        DQSeverity.ERROR: 2, DQSeverity.CRITICAL: 3,
    }[s]


def _finalise(report: DQReport, run_output: Path, dry_run: bool) -> None:
    report.recompute_overall()
    if dry_run:
        return
    report.write(run_output)

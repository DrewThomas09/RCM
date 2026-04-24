"""rcm-mc-diligence — CLI entry point.

Usage:

    rcm-mc-diligence ingest --connector seekingchartis \\
        --dataset mess_scenario_1_multi_ehr \\
        [--warehouse duckdb|snowflake|postgres] \\
        [--output-dir ./output] \\
        [--run-id <slug>] \\
        [--vacuum]

``--vacuum`` regenerates every fixture into a temp dir, runs the full
ingestion pipeline as a dry-run (no dbt, no artefacts), and reports
per-fixture pass/fail.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .dq.report import DQReport, DQSectionStatus
from .fixtures import FIXTURES
from .ingest.pipeline import run_ingest
from .ingest.warehouse import warehouse_from_name


# ── Argument parsing ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rcm-mc-diligence",
        description="SeekingChartis — Tuva-wrapped diligence ingestion.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Run the ingestion pipeline.")
    ingest.add_argument(
        "--connector", default="seekingchartis",
        choices=["seekingchartis"],
        help="dbt connector project to run. Only seekingchartis in Phase 0.A.",
    )
    ingest.add_argument(
        "--dataset", required=False, default=None,
        help="Fixture name (see `list`) or a filesystem path to a raw data directory.",
    )
    ingest.add_argument(
        "--warehouse", default="duckdb",
        choices=["duckdb", "snowflake", "postgres"],
        help="Target warehouse adapter. Only duckdb is implemented.",
    )
    ingest.add_argument(
        "--output-dir", default="./output",
        help="Where run artefacts land (dq_report.json, dq_report.html, diligence.duckdb).",
    )
    ingest.add_argument(
        "--run-id", default=None,
        help="Override the auto-generated run ID. Default is derived from the input hash.",
    )
    ingest.add_argument(
        "--vacuum", action="store_true",
        help="Dry-run mode: validate every fixture without writing output.",
    )

    sub.add_parser("list", help="List available fixtures.")

    return p


# ── Commands ─────────────────────────────────────────────────────────

def cmd_list(_args: argparse.Namespace) -> int:
    """Print the fixture registry in a copy-pasteable form."""
    print("Available fixtures:")
    for name, meta in sorted(FIXTURES.items()):
        expected = meta.get("expected") or {}
        overall = expected.get("overall_status", "?")
        print(f"  {name:55s}  expected overall = {overall}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    if args.vacuum:
        return _vacuum(args)

    if not args.dataset:
        print("error: --dataset is required unless --vacuum is set", file=sys.stderr)
        return 2

    dataset_path = _resolve_dataset(args.dataset)
    if dataset_path is None:
        print(
            f"error: dataset {args.dataset!r} is neither a known fixture "
            f"nor an existing directory.",
            file=sys.stderr,
        )
        print("Known fixtures:", ", ".join(sorted(FIXTURES)), file=sys.stderr)
        return 2

    adapter = _build_adapter(args.warehouse, Path(args.output_dir))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = run_ingest(
        dataset_path,
        output_dir=output_dir,
        adapter=adapter,
        run_id=args.run_id,
    )
    _print_report_summary(report, output_dir)
    # Exit code reflects the overall status.
    return 0 if report.overall_status != DQSectionStatus.FAIL else 1


# ── Vacuum (dry-run) ─────────────────────────────────────────────────

def _vacuum(args: argparse.Namespace) -> int:
    """Run every fixture as a dry-run and report per-fixture pass/fail.

    Each fixture regenerates into a fresh temp dir so vacuum is free of
    cross-fixture state. A fixture is "pass" when the dry-run DQReport's
    ``overall_status`` matches the fixture's ``EXPECTED_OUTCOME[overall_status]``
    — or when dry-run coverage isn't enough to evaluate that, we relax
    to "no FAIL on any pre-dbt rule that wasn't expected".
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="rcm-mc-diligence-vacuum-"))
    results: List[Dict[str, Any]] = []
    try:
        for name, meta in sorted(FIXTURES.items()):
            gen = meta["generate"]
            expected = meta.get("expected", {})
            fixture_dir = gen(tmp_root)
            adapter = _build_adapter("duckdb", tmp_root / "wh" / name)
            try:
                report = run_ingest(
                    fixture_dir,
                    output_dir=tmp_root / "out" / name,
                    adapter=adapter,
                    dry_run=True,
                )
            finally:
                adapter.close()
            passed = _evaluate_vacuum(report, expected)
            results.append({
                "fixture": name, "pass": passed,
                "overall": report.overall_status.value,
                "expected_overall": expected.get("overall_status", "?"),
            })
            status = "PASS" if passed else "FAIL"
            print(
                f"[{status}] {name:55s} overall={report.overall_status.value} "
                f"(expected {expected.get('overall_status', '?')})"
            )
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    n_fail = sum(1 for r in results if not r["pass"])
    print(
        f"\nvacuum: {len(results) - n_fail}/{len(results)} fixtures passed dry-run."
    )
    return 0 if n_fail == 0 else 1


def _evaluate_vacuum(report: DQReport, expected: Dict[str, Any]) -> bool:
    """Dry-run evaluation is weaker than a full run because we don't
    know Tuva's outcome. We accept:

    - If fixture expects ``FAIL`` (e.g. payer_coverage CRITICAL,
      unmapped ≥10%) we require ``overall_status`` to be FAIL.
    - If fixture expects ``WARN`` or ``OK`` we accept any status that
      is not worse than FAIL driven by an unexpected rule.

    The full-fidelity check is in
    ``tests/test_diligence_mess_scenarios.py`` which runs against real
    dbt output. Vacuum is a smoke test, not the canonical gate.
    """
    expected_overall = expected.get("overall_status", "OK")
    if expected_overall == "FAIL":
        return report.overall_status == DQSectionStatus.FAIL
    return report.overall_status != DQSectionStatus.FAIL or any(
        (row.get("rule") or "") in set(expected.get("fail_rules", []))
        for row in report.analysis_coverage.rows + report.connector_mapping.rows
    )


# ── Helpers ──────────────────────────────────────────────────────────

def _resolve_dataset(val: str) -> Optional[Path]:
    """Return a real directory from either a fixture name or a path.

    Fixture names regenerate into a temp dir so we always start from
    a fresh, deterministic snapshot. Partners can pin a fixture to a
    persistent location with ``rcm-mc-diligence ingest --dataset
    /path/to/dir`` — we accept that path as-is.
    """
    if val in FIXTURES:
        tmp = Path(tempfile.mkdtemp(prefix=f"sc-fixture-{val}-"))
        gen = FIXTURES[val]["generate"]
        return gen(tmp)
    p = Path(val)
    if p.is_dir():
        return p
    return None


def _build_adapter(name: str, output_dir: Path) -> Any:
    """Construct the warehouse adapter. DuckDB is the only path that
    returns a working object; Snowflake/Postgres raise on construction
    to fail fast with a clear NotImplementedError.
    """
    if name == "duckdb":
        db_path = Path(output_dir) / "wh" / "diligence.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return warehouse_from_name("duckdb", db_path=db_path)
    return warehouse_from_name(name)


def _print_report_summary(report: DQReport, output_dir: Path) -> None:
    run_id = report.provenance.run_id
    run_out = output_dir / run_id
    print(f"\nSeekingChartis diligence ingest — {run_id}")
    print(f"  overall    : {report.overall_status.value}")
    print(f"  message    : {report.overall_message}")
    for name in ("source_inventory", "raw_load_summary", "connector_mapping",
                 "tuva_dq_results", "analysis_coverage"):
        sec = getattr(report, name)
        print(f"  {name:22s}: {sec.status.value:8s}  {sec.message}")
    print(f"\n  artefacts: {run_out}")
    print(f"    json  : {run_out/'dq_report.json'}")
    print(f"    html  : {run_out/'dq_report.html'}")
    print(f"    duckdb: {run_out/'diligence.duckdb'}")


# ── Entry point ──────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return cmd_ingest(args)
    if args.command == "list":
        return cmd_list(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

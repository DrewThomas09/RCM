"""Compliance CLI entry point.

Two subcommands:

    python -m rcm_mc.compliance scan <path> [<path>...]
        Scan each path (file or directory) for PHI patterns.
        Exit code 0 on no findings, 1 on any finding. Intended as a
        pre-commit / CI gate.

    python -m rcm_mc.compliance verify-audit --db <path>
        Run verify_audit_chain() against the store at <db> and emit
        a JSON attestation to stdout. Exit code 0 on ok, 1 on any
        mismatch / linkage break.

Both commands are read-only and stdlib-only (no external deps beyond
the package itself).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from .audit_chain import chain_status, verify_audit_chain
from .phi_scanner import PHIScanReport, scan_file


# ── scan ────────────────────────────────────────────────────────────

_DEFAULT_IGNORE_SUFFIXES = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".db", ".sqlite",
    ".lock", ".bin",
}

_DEFAULT_IGNORE_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".idea", ".vscode",
}


def _iter_target_files(
    paths: Iterable[str],
) -> List[Path]:
    """Expand directory paths to a flat file list, honouring
    ``_DEFAULT_IGNORE_DIRS`` and ``_DEFAULT_IGNORE_SUFFIXES``."""
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_file():
            if p.suffix.lower() not in _DEFAULT_IGNORE_SUFFIXES:
                out.append(p)
            continue
        for child in p.rglob("*"):
            if child.is_dir():
                continue
            if any(part in _DEFAULT_IGNORE_DIRS for part in child.parts):
                continue
            if child.suffix.lower() in _DEFAULT_IGNORE_SUFFIXES:
                continue
            out.append(child)
    return out


def _cmd_scan(args: argparse.Namespace) -> int:
    targets = _iter_target_files(args.paths)
    if not targets:
        print("no files to scan", file=sys.stderr)
        return 0

    findings_total = 0
    reports: List[PHIScanReport] = []
    for p in targets:
        rep = scan_file(p)
        if rep.findings:
            findings_total += len(rep.findings)
            reports.append(rep)

    if args.json:
        print(json.dumps(
            {
                "scanned_files": len(targets),
                "files_with_findings": len(reports),
                "findings_total": findings_total,
                "reports": [r.to_dict() for r in reports],
            },
            indent=2,
        ))
    else:
        print(
            f"scanned {len(targets)} files; "
            f"{len(reports)} with findings; "
            f"{findings_total} total"
        )
        for rep in reports:
            print(
                f"  {rep.source}: {rep.highest_severity} · "
                f"{dict(rep.count_by_pattern)}"
            )
            for f in rep.findings[: args.max_per_file]:
                print(
                    f"    [{f.severity}] {f.pattern}: "
                    f"{f.context.strip()[:100]}"
                )
    return 1 if findings_total else 0


# ── verify-audit ────────────────────────────────────────────────────

def _cmd_verify_audit(args: argparse.Namespace) -> int:
    try:
        from ..portfolio.store import PortfolioStore
    except Exception as exc:  # noqa: BLE001
        print(f"cannot import PortfolioStore: {exc}", file=sys.stderr)
        return 2
    store = PortfolioStore(args.db)
    status = chain_status(store)
    report = verify_audit_chain(store)
    payload = {
        "db": args.db,
        "status": status,
        "verification": report.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 0 if report.ok else 1


# ── argparse plumbing ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m rcm_mc.compliance",
        description=(
            "Compliance utilities — PHI scanner + audit-chain verifier. "
            "Both commands are read-only."
        ),
    )
    sub = ap.add_subparsers(dest="command", required=True)

    sc = sub.add_parser("scan", help="Scan files/directories for PHI patterns")
    sc.add_argument("paths", nargs="+",
                    help="Files or directories to scan")
    sc.add_argument("--json", action="store_true",
                    help="Emit a JSON report instead of the summary text")
    sc.add_argument("--max-per-file", type=int, default=5,
                    help="Max findings to print per file (text mode)")
    sc.set_defaults(func=_cmd_scan)

    va = sub.add_parser(
        "verify-audit",
        help="Verify the audit_events hash chain in a store",
    )
    va.add_argument("--db", required=True, help="Path to the SQLite store")
    va.set_defaults(func=_cmd_verify_audit)

    return ap


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

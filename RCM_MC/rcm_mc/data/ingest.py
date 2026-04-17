"""``rcm-mc ingest`` — turn a messy seller data pack into a calibration-ready directory.

The calibration pipeline expects three canonical CSVs (``claims_summary.csv``,
``denials.csv``, ``ar_aging.csv``). Real diligence data rarely arrives that
way: it's usually a single Excel with six sheets, or a zipfile, or a folder
with inconsistent names. This command handles each of those and emits the
three canonical files plus a ``data_intake_report.md`` audit trail.

The classifier reuses the alias-aware column matcher from
:mod:`rcm_mc._calib_schema`, so whatever name the seller uses for "payer"
(``payor``, ``financial_class``, etc.) still gets recognized.

Typical call::

    rcm-mc ingest ~/Downloads/target_pack.zip --out intake_out/
    rcm-mc run --actual-data-dir intake_out/ ...

Exit codes:

- ``0`` — at least one known table classified and written
- ``1`` — nothing usable found (all sources ``unknown``)
- ``2`` — argparse / usage error
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from ..core._calib_schema import _first_matching_col


# ── Signatures ──────────────────────────────────────────────────────────────

# Each kind declares REQUIRED columns (all must match, via alias lookup) and
# OPTIONAL columns (count of matches breaks ties between candidate kinds).
# The first-matching-col candidates mirror the alias maps calibration uses.
_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "claims_summary": {
        "required": ["payer", "net_revenue"],
        "optional": ["claim_count"],
    },
    "denials": {
        "required": ["payer", "denial_amount"],
        "optional": ["claim_id", "stage", "denial_reason", "writeoff_amount",
                     "denial_date", "resolved_date"],
    },
    "ar_aging": {
        "required": ["payer", "ar_amount"],
        "optional": [],
    },
}


# ── Report dataclasses ──────────────────────────────────────────────────────

@dataclass
class DetectedTable:
    """One classified data frame from the source pack."""
    source: str                           # e.g. "claims.xlsx:Sheet2" or "denials.csv"
    kind: str                             # "claims_summary" / "denials" / "ar_aging" / "unknown"
    rows: int
    columns_matched: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class IngestReport:
    """Full record of an ingest run. Serialized to ``data_intake_report.md``."""
    source_path: str
    out_dir: str
    detected: List[DetectedTable] = field(default_factory=list)
    output_files: Dict[str, str] = field(default_factory=dict)   # kind -> written path
    skipped: List[Tuple[str, str]] = field(default_factory=list)  # (source, reason)
    generated_at: str = ""

    @property
    def classified_count(self) -> int:
        return sum(1 for t in self.detected if t.kind != "unknown")

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append(f"# Data Intake Report")
        lines.append("")
        lines.append(f"- **Source:** `{self.source_path}`")
        lines.append(f"- **Output directory:** `{self.out_dir}`")
        lines.append(f"- **Generated:** {self.generated_at}")
        lines.append(f"- **Tables classified:** {self.classified_count} of {len(self.detected)}")
        lines.append("")

        if self.output_files:
            lines.append("## Canonical files written")
            lines.append("")
            for kind, path in sorted(self.output_files.items()):
                lines.append(f"- `{kind}.csv` ← {path}")
            lines.append("")

        if self.detected:
            lines.append("## Detected tables")
            lines.append("")
            lines.append("| Source | Kind | Rows | Columns mapped |")
            lines.append("|--------|------|------|----------------|")
            for t in self.detected:
                cm = ", ".join(f"{k}←{v}" for k, v in t.columns_matched.items()) or "—"
                lines.append(f"| `{t.source}` | **{t.kind}** | {t.rows:,} | {cm} |")
            lines.append("")

        warnings = [(t.source, w) for t in self.detected for w in t.warnings]
        if warnings:
            lines.append("## Warnings")
            lines.append("")
            for src, w in warnings:
                lines.append(f"- `{src}`: {w}")
            lines.append("")

        if self.skipped:
            lines.append("## Skipped")
            lines.append("")
            for src, reason in self.skipped:
                lines.append(f"- `{src}`: {reason}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("Run the calibrated simulation with:")
        lines.append("")
        lines.append(f"```bash")
        lines.append(f"rcm-mc run --actual actual.yaml --benchmark configs/benchmark.yaml \\")
        lines.append(f"           --actual-data-dir {self.out_dir} --outdir outputs")
        lines.append(f"```")
        lines.append("")
        return "\n".join(lines)


# ── Classification ──────────────────────────────────────────────────────────

def classify_dataframe(df: pd.DataFrame) -> Tuple[str, Dict[str, str]]:
    """Return ``(kind, column_map)`` for ``df``.

    ``column_map`` maps canonical names back to the actual source column names
    that matched. Returns ``("unknown", {})`` if no signature's required
    columns are all present.
    """
    if df is None or df.empty:
        return ("unknown", {})

    candidates: List[Tuple[str, Dict[str, str], int]] = []
    for kind, sig in _SIGNATURES.items():
        matched: Dict[str, str] = {}
        all_required = True
        for req in sig["required"]:
            col = _first_matching_col(df, [req])
            if col is None:
                all_required = False
                break
            matched[req] = col
        if not all_required:
            continue
        optional_hits = sum(
            1 for o in sig["optional"] if _first_matching_col(df, [o]) is not None
        )
        candidates.append((kind, matched, optional_hits))

    if not candidates:
        return ("unknown", {})

    # Most-specific signature wins (most optional columns matched).
    # Tie-breaker: signature with more required columns (claims/denials beat ar_aging).
    candidates.sort(key=lambda c: (-c[2], -len(_SIGNATURES[c[0]]["required"])))
    return (candidates[0][0], candidates[0][1])


# ── Source loader ──────────────────────────────────────────────────────────

_CSV_EXTS = {".csv", ".tsv", ".txt"}
_EXCEL_EXTS = {".xlsx", ".xls"}


def _read_csv_flexible(path: Path) -> Optional[pd.DataFrame]:
    """Read a CSV/TSV/TXT with best-effort delimiter + encoding detection."""
    ext = path.suffix.lower()
    sep = "\t" if ext == ".tsv" else None  # None = pandas sniff
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, sep=sep, encoding=enc, engine="python")
        except (UnicodeDecodeError, UnicodeError):
            continue
        except pd.errors.ParserError:
            return None
    return None


def _read_excel_all_sheets(path: Path) -> List[Tuple[str, pd.DataFrame]]:
    """Return ``[(sheet_name, df), ...]`` for every sheet in an Excel file."""
    try:
        with pd.ExcelFile(path) as xl:
            out: List[Tuple[str, pd.DataFrame]] = []
            for sheet in xl.sheet_names:
                try:
                    df = xl.parse(sheet)
                    if df is not None and not df.empty:
                        out.append((sheet, df))
                except Exception:
                    continue
            return out
    except (FileNotFoundError, ValueError, OSError):
        return []


def load_source(src: Path) -> Iterator[Tuple[str, pd.DataFrame]]:
    """Yield ``(label, DataFrame)`` for every table found under ``src``.

    Handles single CSV, single multi-sheet Excel, folder (recurses one level),
    and zip (extracts to temp dir then recurses).
    """
    src = Path(src)
    if not src.exists():
        return

    # Zipfile → extract to tempdir, recurse
    if src.is_file() and src.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with zipfile.ZipFile(src) as zf:
                zf.extractall(tmp_path)
            # Eagerly materialize all tables so the tempdir can clean up
            for label, df in _load_dir_or_file(tmp_path, prefix=src.name):
                yield (label, df)
        return

    yield from _load_dir_or_file(src)


def _load_dir_or_file(src: Path, prefix: Optional[str] = None) -> Iterator[Tuple[str, pd.DataFrame]]:
    """Internal recursion helper for load_source."""
    if src.is_dir():
        for child in sorted(src.iterdir()):
            if child.is_file():
                ext = child.suffix.lower()
                if ext in _CSV_EXTS or ext in _EXCEL_EXTS:
                    yield from _load_dir_or_file(child, prefix=prefix)
            elif child.is_dir():
                yield from _load_dir_or_file(child, prefix=prefix)
        return

    if not src.is_file():
        return

    ext = src.suffix.lower()
    label_stem = src.name if prefix is None else f"{prefix}/{src.name}"

    if ext in _EXCEL_EXTS:
        for sheet, df in _read_excel_all_sheets(src):
            yield (f"{label_stem}:{sheet}", df)
    elif ext in _CSV_EXTS:
        df = _read_csv_flexible(src)
        if df is not None and not df.empty:
            yield (label_stem, df)


# ── Main ingest orchestration ──────────────────────────────────────────────

def ingest_path(src: str, out_dir: str) -> IngestReport:
    """Classify every table under ``src`` and write canonical CSVs to ``out_dir``.

    Multiple tables classified as the same kind are concatenated row-wise
    (common when sellers split denials by quarter). Unknown tables are
    recorded in the report but not written.
    """
    os.makedirs(out_dir, exist_ok=True)
    report = IngestReport(
        source_path=os.path.abspath(src),
        out_dir=os.path.abspath(out_dir),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Group detected tables by kind
    by_kind: Dict[str, List[Tuple[str, pd.DataFrame]]] = {
        "claims_summary": [], "denials": [], "ar_aging": [],
    }

    for label, df in load_source(Path(src)):
        kind, col_map = classify_dataframe(df)
        detected = DetectedTable(
            source=label,
            kind=kind,
            rows=int(len(df)),
            columns_matched=col_map,
        )
        # Warn if a claims_summary-like table has no claim_count (downstream
        # calibration falls back to NaN, but flag it for the analyst).
        if kind == "claims_summary" and "claim_count" not in col_map:
            if _first_matching_col(df, ["claim_count"]) is None:
                detected.warnings.append(
                    "no claim_count column found — average claim size will use template prior"
                )
        report.detected.append(detected)
        if kind in by_kind:
            by_kind[kind].append((label, df))
        else:
            report.skipped.append((label, "no signature matched"))

    # Concatenate per kind and write canonical CSVs
    for kind, entries in by_kind.items():
        if not entries:
            continue
        if len(entries) == 1:
            _, df = entries[0]
        else:
            df = pd.concat([e[1] for e in entries], ignore_index=True)
        out_path = os.path.join(out_dir, f"{kind}.csv")
        df.to_csv(out_path, index=False)
        report.output_files[kind] = out_path

    # Write markdown report
    with open(os.path.join(out_dir, "data_intake_report.md"), "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    return report


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None, prog: str = "rcm-mc ingest") -> int:
    ap = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Turn a messy seller data pack (folder / zip / multi-sheet Excel) "
            "into a calibration-ready directory of canonical CSVs."
        ),
        epilog=(
            "Example:\n"
            "  rcm-mc ingest ~/Downloads/target_pack.zip --out intake/\n"
            "  rcm-mc run --actual actual.yaml --benchmark configs/benchmark.yaml \\\n"
            "             --actual-data-dir intake/ --outdir outputs\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("source", nargs="?", default=None,
                    help="File, folder, or zipfile to ingest (legacy path)")
    ap.add_argument("--out", default=None,
                    help="Destination directory for canonical CSVs "
                         "(required for the legacy `source` flow)")
    ap.add_argument("-q", "--quiet", action="store_true", help="Suppress per-table progress")
    # Prompt 25: drag-drop-style data-room extraction.
    ap.add_argument("--data-room",
                    help="Directory of seller files (xlsx/csv/tsv) to run "
                         "through the document reader — emits extracted "
                         "metrics JSON to stdout or --json-out.")
    ap.add_argument("--deal-id", default=None,
                    help="With --data-room, tag extracted metrics with "
                         "this deal id in the output report.")
    ap.add_argument("--json-out", default=None,
                    help="With --data-room, write the extraction JSON "
                         "to this path instead of stdout.")
    args = ap.parse_args(argv)

    # ── Prompt 25 path — document reader.
    if args.data_room:
        import json as _json
        from .document_reader import read_data_room
        room = Path(args.data_room)
        if not room.is_dir():
            sys.stderr.write(f"data-room not a directory: {room}\n")
            return 2
        result = read_data_room(room)
        payload = result.to_dict()
        if args.deal_id:
            payload["deal_id"] = args.deal_id
        out_str = _json.dumps(payload, indent=2, default=str)
        if args.json_out:
            Path(args.json_out).write_text(out_str, encoding="utf-8")
            sys.stdout.write(
                f"wrote {len(result.metrics)} metric(s) → {args.json_out}\n"
            )
        else:
            sys.stdout.write(out_str + "\n")
        return 0

    if args.source is None or args.out is None:
        ap.error("positional source and --out are required unless --data-room is set")

    src = Path(args.source)
    if not src.exists():
        sys.stderr.write(f"source not found: {src}\n")
        return 2

    # Lazy import of the terminal helpers so `rcm-mc ingest --help` stays light
    from ..infra._terminal import banner, info, success, warn, wrote

    if not args.quiet:
        print(banner(f"Ingesting {src}"))

    report = ingest_path(str(src), args.out)

    if not args.quiet:
        for t in report.detected:
            if t.kind == "unknown":
                print(warn(f"{t.source} — no signature matched; skipped"))
            else:
                cm = ", ".join(t.columns_matched.keys())
                print(info(f"{t.source} → {t.kind} ({t.rows:,} rows; matched {cm})"))
        print()
        for kind, path in sorted(report.output_files.items()):
            print(wrote(path, label=f"{kind}"))
        print(wrote(os.path.join(args.out, "data_intake_report.md"), label="report"))

    if report.classified_count == 0:
        sys.stderr.write(
            "\nNo claims_summary / denials / ar_aging tables classified.\n"
            "Check column names and try again, or pass --help for format details.\n"
        )
        return 1

    if not args.quiet:
        print()
        print(success(
            f"Classified {report.classified_count} of {len(report.detected)} tables. "
            f"Ready for: --actual-data-dir {args.out}"
        ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

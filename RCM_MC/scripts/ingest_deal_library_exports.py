#!/usr/bin/env python3
"""Ingest user-provided licensed market-data exports into the Deal Library.

Compliance posture (see docs/PEDESK_LICENSED_MARKET_DATA_INGEST_PLAN.md): this
reads **export files the user produced under their own license** (Capital IQ
Screening / plug-in workbooks, or any CSV). It does NOT scrape, automate a web
UI, or extract a vendor backend. Licensed data and anything derived from it
stay out of git (see data/vendor/deal_library/.gitignore); only this pipeline
and a synthetic fixture are tracked.

Honesty rules enforced here:
  * Missing means unavailable — blanks / "-" / "NM" become None, never 0.
  * No value is inferred from a blank; no multiples/EV/EBITDA are invented.
  * Every row keeps source_file / source_sheet / source_row_id + a
    missing_fields list + a completeness_score, so provenance and gaps are
    auditable downstream.
  * Estimates (none are produced here) would be labeled, never written as
    observed facts.

Usage::

    python scripts/ingest_deal_library_exports.py \
        --in data/vendor/deal_library \
        --source-system "Capital IQ" \
        --out data/vendor/deal_library

Output (all gitignored): deal_library_companies.csv, deal_library_sources.csv,
deal_library_ingest_report.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import the alias map from the tracked vendor module.
_VENDOR = Path(__file__).resolve().parent.parent / "data" / "vendor" / "deal_library"
sys.path.insert(0, str(_VENDOR))
import column_aliases as aliases  # noqa: E402

_MISSING_TOKENS = {"", "-", "--", "n/a", "na", "nm", "null", "none", "nan"}


# ── value normalization ──────────────────────────────────────────────────
def norm_str(v: Any) -> Optional[str]:
    """Trim; map vendor missing-tokens to None. Never invents a value."""
    if v is None:
        return None
    s = str(v).replace("\n", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return None if s.lower() in _MISSING_TOKENS else s


def parse_money(v: Any) -> Optional[float]:
    """Parse a $USDmm cell. Tolerates $ , parens(neg) and 'x'. Blank→None.
    Critically: a missing financial is None, NOT 0."""
    s = norm_str(v)
    if s is None:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "")
    s = re.sub(r"[xX]\s*$", "", s).strip()
    try:
        f = float(s)
        return -f if neg else f
    except ValueError:
        return None


_SUFFIX = re.compile(
    r"[,.]?\s*\b(inc|incorporated|llc|l\.l\.c|lp|l\.p|ltd|limited|corp|"
    r"corporation|co|company|holdings|group|plc|sa|ag|gmbh)\b\.?",
    re.IGNORECASE,
)


def clean_company_name(name: Optional[str]) -> Optional[str]:
    """Conservative normalized key for dedup/resolution: lowercase, drop
    common corporate suffixes + punctuation. Leading digits are KEPT (they are
    part of names like '100% Chiropractic', not rank prefixes)."""
    if not name:
        return None
    s = _SUFFIX.sub("", name)
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def parse_sponsor(ownership_status: Optional[str]) -> Optional[str]:
    """Pull the current PE sponsor from CapIQ's Ownership Status, e.g.
    'AgeTech Capital (Current Sponsor); BIP Capital ...' → 'AgeTech Capital'.
    Prefers a (Current Sponsor) tag; falls back to the first listed owner.
    Returns None if the field is empty — never guesses."""
    s = norm_str(ownership_status)
    if not s:
        return None
    parts = [p.strip() for p in s.split(";") if p.strip()]
    current = [p for p in parts if "current sponsor" in p.lower()]
    pick = (current or parts)[0] if (current or parts) else None
    if not pick:
        return None
    # strip the trailing "(... Sponsor)" / "(NYSE:WELL) (Current Sponsor)" tags
    return re.sub(r"\s*\([^)]*\)\s*$", "", pick).strip() or None


_STATE_ABBR = {
    # minimal USPS set used for deterministic state pulls from addresses
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
_STATE_RE = re.compile(r",\s*([A-Z]{2})\b")


def parse_state(address: Optional[str]) -> Optional[str]:
    """Deterministic 2-letter state from an address, or None. No guessing —
    only an explicit ', XX' token or a spelled-out state name counts."""
    s = norm_str(address)
    if not s:
        return None
    m = _STATE_RE.search(s)
    if m and m.group(1) in set(_STATE_ABBR.values()):
        return m.group(1)
    low = s.lower()
    for name, ab in _STATE_ABBR.items():
        if re.search(rf"\b{name}\b", low):
            return ab
    return None


# ── canonical record ─────────────────────────────────────────────────────
_CANONICAL_FIELDS = [
    "company_id", "source_system", "source_batch_id", "source_file",
    "source_sheet", "source_row_id", "ticker", "company_name", "clean_name",
    "industry", "ownership_status", "sponsor_owner", "company_status",
    "website", "address", "geography", "state",
    "enterprise_value", "ebitda", "revenue", "market_cap", "employees",
    "amount_raised", "missing_fields", "completeness_score",
    "duplicate_candidate", "provenance_note",
]

_NUMERIC_FIELDS = {"enterprise_value", "ebitda", "revenue", "market_cap",
                   "amount_raised", "employees"}


def _deal_id(source_system: str, source_file: str, clean: str, row_id: int) -> str:
    """Deterministic id: stable across re-ingests of the same file/row."""
    key = f"{source_system}|{Path(source_file).name}|{clean or ''}|{row_id}"
    return "dl_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _row_to_record(
    mapped: Dict[str, Any], *, source_system: str, source_file: str,
    source_sheet: str, source_row_id: int, batch_id: str,
) -> Dict[str, Any]:
    name = norm_str(mapped.get("company_name"))
    clean = clean_company_name(name)
    rec: Dict[str, Any] = {f: None for f in _CANONICAL_FIELDS}
    rec.update({
        "company_id": _deal_id(source_system, source_file, clean or name or "", source_row_id),
        "source_system": source_system,
        "source_batch_id": batch_id,
        "source_file": Path(source_file).name,
        "source_sheet": source_sheet,
        "source_row_id": source_row_id,
        "company_name": name,
        "clean_name": clean,
        "ticker": norm_str(mapped.get("ticker")),
        "industry": norm_str(mapped.get("industry")),
        "ownership_status": norm_str(mapped.get("ownership_status")),
        "sponsor_owner": parse_sponsor(mapped.get("ownership_status")),
        "company_status": norm_str(mapped.get("company_status")),
        "website": norm_str(mapped.get("website")),
        "address": norm_str(mapped.get("address")),
        "geography": norm_str(mapped.get("geography")),
        "enterprise_value": parse_money(mapped.get("enterprise_value")),
        "ebitda": parse_money(mapped.get("ebitda")),
        "revenue": parse_money(mapped.get("revenue")),
        "market_cap": parse_money(mapped.get("market_cap")),
        "amount_raised": parse_money(mapped.get("amount_raised")),
        "employees": parse_money(mapped.get("employees")),
    })
    rec["state"] = parse_state(rec["address"]) or parse_state(rec["geography"])
    # missingness + completeness over the declared core fields
    missing = [f for f in aliases.CORE_COMPANY_FIELDS if rec.get(f) in (None, "")]
    rec["missing_fields"] = ";".join(missing)
    rec["completeness_score"] = round(
        1 - len(missing) / len(aliases.CORE_COMPANY_FIELDS), 4)
    rec["provenance_note"] = (
        f"{source_system} export '{Path(source_file).name}' "
        f"sheet '{source_sheet}' row {source_row_id}")
    return rec


# ── header detection + readers ─────────────────────────────────────────────
def _detect_header_row(rows: List[List[Any]], scan: int = 25) -> int:
    """Return the index of the header row: the first row within ``scan`` whose
    cells map to >=3 canonical fields (CapIQ exports prepend title rows)."""
    best_i, best_n = 0, 0
    for i, row in enumerate(rows[:scan]):
        hits = sum(1 for c in row if aliases.map_header(c))
        if hits > best_n:
            best_i, best_n = i, hits
    return best_i if best_n >= 3 else 0


def _records_from_matrix(
    matrix: List[List[Any]], *, source_system: str, source_file: str,
    source_sheet: str, batch_id: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not matrix:
        return [], []
    hr = _detect_header_row(matrix)
    headers = matrix[hr]
    col_map: Dict[int, str] = {}
    unmapped: List[str] = []
    for ci, h in enumerate(headers):
        canon = aliases.map_header(h)
        if canon:
            col_map[ci] = canon
        elif norm_str(h):
            unmapped.append(str(h).strip())
    records: List[Dict[str, Any]] = []
    for ri, row in enumerate(matrix[hr + 1:], start=1):
        mapped = {col_map[ci]: row[ci] for ci in col_map if ci < len(row)}
        if not norm_str(mapped.get("company_name")):
            continue
        records.append(_row_to_record(
            mapped, source_system=source_system, source_file=source_file,
            source_sheet=source_sheet, source_row_id=ri, batch_id=batch_id))
    return records, unmapped


def read_csv_matrix(path: Path) -> Dict[str, List[List[Any]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return {"Sheet1": [list(r) for r in csv.reader(fh)]}


def read_excel_matrix(path: Path) -> Dict[str, List[List[Any]]]:
    """Read every sheet of an .xls/.xlsx into raw matrices. Requires xlrd
    (.xls) / openpyxl (.xlsx) — an offline ingestion-tool dependency, not a
    PEdesk runtime dependency."""
    import pandas as pd
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    book = pd.read_excel(path, sheet_name=None, header=None, engine=engine)
    out: Dict[str, List[List[Any]]] = {}
    for sheet, df in book.items():
        out[sheet] = df.where(df.notna(), None).values.tolist()
    return out


# Which sheet to ingest from a multi-sheet workbook: prefer a data sheet.
_DATA_SHEET_HINTS = ("screening", "transactions", "companies", "data", "sheet1")


def ingest_file(path: Path, *, source_system: str, batch_id: str = "") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        sheets = read_csv_matrix(path)
    elif suffix in (".xls", ".xlsx"):
        sheets = read_excel_matrix(path)
    else:
        return [], {"file": path.name, "skipped": "unsupported extension"}
    # pick the data sheet
    name = next((s for s in sheets if any(h in s.lower() for h in _DATA_SHEET_HINTS)),
                next(iter(sheets)))
    recs, unmapped = _records_from_matrix(
        sheets[name], source_system=source_system, source_file=str(path),
        source_sheet=name, batch_id=batch_id or path.stem)
    info = {"file": path.name, "sheet": name, "rows_out": len(recs),
            "unmapped_columns": unmapped, "all_sheets": list(sheets)}
    return recs, info


def flag_duplicates(records: List[Dict[str, Any]]) -> int:
    """Mark duplicate_candidate=1 for records sharing a (clean_name, state)
    key beyond the first. Conservative — only an exact normalized-name+state
    collision is flagged; nothing is merged or dropped."""
    seen: Dict[Tuple[str, str], int] = {}
    n = 0
    for r in records:
        key = (r.get("clean_name") or "", r.get("state") or "")
        if not key[0]:
            r["duplicate_candidate"] = 0
            continue
        if key in seen:
            r["duplicate_candidate"] = 1
            n += 1
        else:
            seen[key] = 1
            r["duplicate_candidate"] = 0
    return n


def build_report(records, file_infos, source_system) -> Dict[str, Any]:
    n = len(records)
    miss = {}
    for f in _CANONICAL_FIELDS:
        if f in ("missing_fields", "completeness_score", "duplicate_candidate",
                 "provenance_note"):
            continue
        empty = sum(1 for r in records if r.get(f) in (None, ""))
        miss[f] = round(100 * empty / n, 1) if n else 0.0
    return {
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source_system": source_system,
        "files": file_infos,
        "rows_output": n,
        "duplicate_candidates": sum((r.get("duplicate_candidate") or 0) for r in records),
        "missingness_pct_by_field": miss,
        "completeness_mean": round(
            sum(r["completeness_score"] for r in records) / n, 4) if n else 0.0,
        "warnings": [],
    }


_SOURCE_FIELDS = ["source_id", "source_system", "source_type", "source_file",
                  "source_date", "license_scope_note", "ingestion_date",
                  "row_count", "notes"]


def build_sources(file_infos, source_system: str) -> List[Dict[str, Any]]:
    """One provenance row per ingested export (the deal_library_sources table).
    Deterministic source_id from system+file so re-ingests upsert cleanly."""
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for info in file_infos:
        fname = info.get("file", "")
        sid = "src_" + hashlib.sha1(
            f"{source_system}|{fname}".encode("utf-8")).hexdigest()[:16]
        out.append({
            "source_id": sid,
            "source_system": source_system,
            "source_type": "screening_export",
            "source_file": fname,
            "source_date": "",   # filled from the manifest if one is supplied
            "license_scope_note": ("Licensed vendor export, user-provided; "
                                   "not redistributed beyond licensed env"),
            "ingestion_date": now,
            "row_count": info.get("rows_out", 0),
            "notes": f"sheet={info.get('sheet', '')}",
        })
    return out


def write_outputs(records, report, out_dir: Path,
                  sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    comp = out_dir / "deal_library_companies.csv"
    with comp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_CANONICAL_FIELDS)
        w.writeheader()
        w.writerows(records)
    paths = {"companies": comp}
    if sources is not None:
        src = out_dir / "deal_library_sources.csv"
        with src.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=_SOURCE_FIELDS)
            w.writeheader()
            w.writerows(sources)
        paths["sources"] = src
    rep = out_dir / "deal_library_ingest_report.json"
    rep.write_text(json.dumps(report, indent=2))
    paths["report"] = rep
    return paths


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest licensed exports → Deal Library")
    ap.add_argument("--in", dest="indir", required=True,
                    help="folder of .xls/.xlsx/.csv exports")
    ap.add_argument("--out", dest="outdir", default=None)
    ap.add_argument("--source-system", default="Capital IQ")
    args = ap.parse_args(argv)
    indir = Path(args.indir)
    outdir = Path(args.outdir) if args.outdir else indir
    files = sorted(p for p in indir.iterdir()
                   if p.suffix.lower() in (".xls", ".xlsx", ".csv")
                   and not p.name.startswith("deal_library_"))
    if not files:
        print(f"No exports found in {indir}", file=sys.stderr)
        return 1
    all_recs: List[Dict[str, Any]] = []
    infos = []
    for p in files:
        recs, info = ingest_file(p, source_system=args.source_system)
        infos.append(info)
        all_recs.extend(recs)
        print(f"  {p.name}: {info.get('rows_out', 0)} rows "
              f"(sheet '{info.get('sheet')}')", file=sys.stderr)
    dups = flag_duplicates(all_recs)
    report = build_report(all_recs, infos, args.source_system)
    sources = build_sources(infos, args.source_system)
    paths = write_outputs(all_recs, report, outdir, sources=sources)
    print(f"\nWrote {len(all_recs)} records ({dups} dup candidates) → {paths['companies']}",
          file=sys.stderr)
    print(f"Sources ({len(sources)}) → {paths['sources']}", file=sys.stderr)
    print(f"Ingest report → {paths['report']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

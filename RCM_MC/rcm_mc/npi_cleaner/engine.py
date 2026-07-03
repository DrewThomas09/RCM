"""Self-contained NPI claims-cleaner engine — stdlib only.

Backs the ``/npi-cleaner`` page. Reads a delimited claims file (CSV / TSV),
auto-detects NPI-bearing columns, validates every NPI against the official
Luhn check, de-duplicates exact-duplicate rows, normalizes whitespace, flags
missing / malformed / checksum-failing billing NPIs, and emits a cleaned CSV
plus a scorecard.

Why stdlib-only, and why not the uploaded ``npi_recovery`` package
--------------------------------------------------------------------
The uploaded ``NPI_Recovery_and_Cleaner_v48`` package ships 43 modules but is
**missing its engine core** — its ``__init__`` imports ``pipeline.py`` and
``entity.py``, neither of which is in the archive, so ``run_pipeline`` (the
full Steps 0–8 recovery orchestrator) cannot be imported. It also needs
pandas / numpy / live CMS network access, which the stdlib ``rcm-mc serve``
server deliberately avoids. Those modules are kept for provenance under
``vendor_v48/`` (see its README).

This engine implements the genuinely deliverable, offline cleaning steps with
zero third-party dependencies, so the page works end-to-end. ``run_pipeline``
is attempted first (guarded) — if a complete ``npi_recovery`` is ever dropped
in, it is used automatically; otherwise we fall back to the built-in cleaner.

The Luhn rule mirrors ``vendor_v48/npi_recovery/field_validators.py`` exactly:
Luhn over the constant prefix ``80840`` plus the first 9 NPI digits.
"""
from __future__ import annotations

import csv
import io
import re
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Scratch area for in-flight jobs and their cleaned output. /tmp keeps this off
# the repo tree and matches the vendored webapp's WORKDIR convention.
WORKDIR = Path("/tmp/npi_cleaner_web")
WORKDIR.mkdir(parents=True, exist_ok=True)

# Column names (case/space/punct-insensitive) that carry an NPI.
_NPI_HINTS = (
    "npi", "billingnpi", "renderingnpi", "referringnpi", "providernpi",
    "attendingnpi", "billingprovidernpi", "facilitynpi", "servicingnpi",
)
# A "billing" NPI is the one that must be present for a claim to be payable —
# missing values here are the headline recovery target.
_BILLING_HINTS = ("billing", "billingprovider", "pay")

# Columns that carry a provider / organization name, used to recover a missing
# NPI by searching NPPES. Order = priority.
_NAME_HINTS = (
    "organizationname", "orgname", "providername", "billingprovidername",
    "facilityname", "practicename", "provider", "name",
)
_STATE_HINTS = ("providerstate", "billingstate", "state", "provstate", "st")
# Columns carrying a drug identifier, for the RxNorm / openFDA connectors.
_NDC_HINTS = ("ndc11", "ndc", "drugndc", "ndccode")
_DRUG_HINTS = ("drugname", "drug", "productname", "medication", "labelname")

ProgressCb = Callable[[str, float], None]


def _norm_key(name: str) -> str:
    """Fold a header to a comparison key: lowercase, strip non-alphanumerics."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def luhn_npi_valid(npi: object) -> bool:
    """True when a 10-digit NPI passes the Luhn check over ``80840`` + first 9.

    Mirrors ``npi_recovery.field_validators.luhn_npi_valid`` byte-for-byte so
    this offline engine agrees with the full package's verdicts.
    """
    s = "".join(ch for ch in str(npi) if ch.isdigit())
    if len(s) != 10:
        return False
    full = "80840" + s[:9]
    total = 0
    for i, ch in enumerate(reversed(full)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10 == int(s[9])


def _digits(v: object) -> str:
    return "".join(ch for ch in str(v) if ch.isdigit())


def classify_npi(raw: object) -> str:
    """One of: ``blank`` · ``malformed`` (not 10 digits) · ``checksum`` (10
    digits but Luhn-fails) · ``valid``."""
    s = str(raw).strip() if raw is not None else ""
    if s == "" or s.lower() in ("nan", "none", "null", "na"):
        return "blank"
    d = _digits(s)
    if len(d) != 10:
        return "malformed"
    return "valid" if luhn_npi_valid(d) else "checksum"


# ---------------------------------------------------------------- data model --
@dataclass
class CleanResult:
    n_rows_in: int = 0
    n_rows_out: int = 0
    n_dupes_removed: int = 0
    npi_columns: List[str] = field(default_factory=list)
    billing_column: Optional[str] = None
    # Per-column tallies: col -> {"valid","blank","malformed","checksum","cells"}
    column_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    n_cells_trimmed: int = 0
    delimiter: str = ","
    headers: List[str] = field(default_factory=list)
    out_path: Optional[str] = None
    out_name: str = "cleaned.csv"
    workbook_path: Optional[str] = None
    workbook_name: str = "report.xlsx"
    # Corrections companion (v49 suggested_fixes): row-level current→suggested
    # fixes with provenance. Written to its own CSV for download.
    companion_path: Optional[str] = None
    companion_name: str = "corrections.csv"
    suggestions_records: List[Dict[str, str]] = field(default_factory=list)
    # NPPES-recovered NPIs written into the cleaned output, keyed by the
    # 1-based row index → recovered NPI. Populated only when enrich resolves
    # a single confident candidate for a row's provider name+state.
    recovered_rows: Dict[int, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    # Real-engine findings from the vendored v48 field/consistency/dedup
    # screens (via vendor_adapter). None when pandas / the modules are
    # unavailable and we ran the stdlib path only.
    advanced: Optional[Dict[str, object]] = None
    # Live NPPES verify/recover results (via nppes_bridge). None unless the
    # user opted into the CMS cross-check. See nppes_bridge.py.
    nppes: Optional[Dict[str, object]] = None
    # Live drug connectors (RxNorm / openFDA) results, and the available-source
    # catalog. None unless online mode ran. See connectors.py.
    connectors: Optional[List[Dict[str, object]]] = None
    catalog: Optional[List[Dict[str, object]]] = None

    @property
    def total_npi_cells(self) -> int:
        return sum(c.get("cells", 0) for c in self.column_stats.values())

    @property
    def total_valid(self) -> int:
        return sum(c.get("valid", 0) for c in self.column_stats.values())

    @property
    def total_issues(self) -> int:
        return sum(
            c.get("blank", 0) + c.get("malformed", 0) + c.get("checksum", 0)
            for c in self.column_stats.values()
        )

    def billing_issue_count(self) -> int:
        if not self.billing_column:
            return 0
        c = self.column_stats.get(self.billing_column, {})
        return c.get("blank", 0) + c.get("malformed", 0) + c.get("checksum", 0)

    def as_scorecard(self) -> Dict[str, object]:
        cells = self.total_npi_cells
        valid = self.total_valid
        health = round(100.0 * valid / cells, 1) if cells else 0.0
        return {
            "rows_in": self.n_rows_in,
            "rows_out": self.n_rows_out,
            "duplicates_removed": self.n_dupes_removed,
            "cells_trimmed": self.n_cells_trimmed,
            "npi_columns": self.npi_columns,
            "billing_column": self.billing_column,
            "npi_cells": cells,
            "npi_valid": valid,
            "npi_issues": self.total_issues,
            "billing_issues": self.billing_issue_count(),
            "health_pct": health,
            "column_stats": self.column_stats,
            "delimiter": {",": "comma", "\t": "tab", ";": "semicolon",
                          "|": "pipe", "xlsx": "xlsx (Excel)"}.get(
                              self.delimiter, self.delimiter),
            "out_name": self.out_name,
            "workbook_name": self.workbook_name if self.workbook_path else None,
            "companion_name": self.companion_name if self.companion_path else None,
            "companion_n": len(self.suggestions_records),
            "recovered_written": len(self.recovered_rows),
            "warnings": self.warnings,
            "advanced": self.advanced,
            "nppes": self.nppes,
            "connectors": self.connectors,
            "catalog": self.catalog,
        }


# ------------------------------------------------------------------ decoding --
def _sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        # Fall back to whichever candidate the header line uses most.
        first = sample.splitlines()[0] if sample else ""
        return max(",\t;|", key=first.count) if first else ","


# Leading characters Excel/Sheets treat as a formula — a CSV export of
# untrusted claims data must neutralize these to avoid CSV-injection.
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def _defang_cell(value: str) -> str:
    """Prefix a lone quote when a CSV cell would otherwise start a formula."""
    if value and value[0] in _FORMULA_LEAD:
        return "'" + value
    return value


def _looks_like_xlsx(data: bytes) -> bool:
    # .xlsx is a zip; the local-file-header magic is "PK\x03\x04". A CSV that
    # happens to start with "PK" is vanishingly unlikely to also be valid zip.
    return data[:4] == b"PK\x03\x04"


def _read_xlsx(data: bytes) -> Tuple[List[str], List[List[str]]]:
    """Read the first worksheet of an .xlsx via openpyxl (read-only mode).

    Raises if openpyxl is unavailable or the workbook is unreadable — the
    caller turns that into a friendly warning telling the user to export CSV.
    """
    from openpyxl import load_workbook  # base dependency

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        rows: List[List[str]] = []
        for r in ws.iter_rows(values_only=True):
            if r is None:
                continue
            cells = ["" if c is None else str(c) for c in r]
            if any(c.strip() for c in cells):
                rows.append(cells)
    finally:
        wb.close()
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    return headers, rows[1:]


def _read_table(data: bytes) -> Tuple[List[str], List[List[str]], str]:
    """Decode bytes → (headers, rows, format). Handles CSV/TSV and .xlsx.

    ``format`` is the delimiter for text files, or ``"xlsx"`` for spreadsheets.
    """
    if _looks_like_xlsx(data):
        headers, body = _read_xlsx(data)
        return headers, body, "xlsx"
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
    sample = text[:8192]
    delim = _sniff_delimiter(sample)
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    all_rows = [r for r in reader if r != []]
    if not all_rows:
        return [], [], delim
    headers = [h.strip() for h in all_rows[0]]
    body = all_rows[1:]
    return headers, body, delim


def _detect_npi_columns(headers: List[str]) -> Tuple[List[int], Optional[int]]:
    """Return (indices of NPI columns, index of the billing NPI column or None)."""
    npi_idx: List[int] = []
    billing_idx: Optional[int] = None
    for i, h in enumerate(headers):
        key = _norm_key(h)
        if any(hint in key for hint in _NPI_HINTS) or key == "npi":
            npi_idx.append(i)
            if billing_idx is None and any(b in key for b in _BILLING_HINTS):
                billing_idx = i
    # No explicit billing column? Treat the first NPI column as billing.
    if billing_idx is None and npi_idx:
        billing_idx = npi_idx[0]
    return npi_idx, billing_idx


def _detect_one(headers: List[str], hints: tuple) -> Optional[int]:
    """First header whose folded key contains any hint (hint order = priority)."""
    keys = [_norm_key(h) for h in headers]
    for hint in hints:
        for i, k in enumerate(keys):
            if hint in k:
                return i
    return None


# -------------------------------------------------------------------- cleaner --
def detect_columns_preview(data: bytes) -> Optional[Dict[str, object]]:
    """Detect the column→role mapping for the pre-clean mapping editor.

    Delegates to the v49 detector via ``vendor_adapter``; returns None when
    pandas / the vendored engine is unavailable (the page then skips the
    confirm step and cleans directly on auto-detection).
    """
    try:
        from . import vendor_adapter
        return vendor_adapter.detect(data)
    except Exception:  # noqa: BLE001
        return None


def clean_bytes(
    data: bytes,
    src_name: str,
    *,
    drop_duplicates: bool = True,
    enrich: bool = False,
    overrides: Optional[Dict[str, str]] = None,
    progress: Optional[ProgressCb] = None,
) -> CleanResult:
    """Clean a delimited claims file given as raw bytes.

    Offline by default. When ``enrich`` is set, the distinct NPIs are verified
    against the live NPPES registry and rows with a missing/bad billing NPI but
    a provider name are run through NPPES recovery — both via the app's shared
    CMS connection (``nppes_bridge``), fully guarded.
    """
    def cb(msg: str, frac: float) -> None:
        if progress:
            progress(msg, frac)

    cb("Reading file", 0.05)
    try:
        headers, rows, delim = _read_table(data)
    except ImportError:
        headers, rows, delim = [], [], "xlsx"
        _res = CleanResult(delimiter="xlsx", headers=[])
        _res.warnings.append(
            "This looks like an .xlsx file but the Excel reader isn't "
            "available on the server. Please export the sheet as CSV and "
            "re-upload.")
        _res.out_name = _out_name(src_name)
        _write_output(_res, [], [])
        cb("Done", 1.0)
        return _res
    except Exception as exc:  # noqa: BLE001 — malformed spreadsheet
        _res = CleanResult(delimiter="xlsx", headers=[])
        _res.warnings.append(f"Could not read the file: {exc}. If this is an "
                             "Excel file, try exporting it as CSV.")
        _res.out_name = _out_name(src_name)
        _write_output(_res, [], [])
        cb("Done", 1.0)
        return _res
    res = CleanResult(delimiter=delim, headers=headers)
    res.n_rows_in = len(rows)
    if not headers:
        res.warnings.append("File appears to be empty — no header row found.")
        res.out_name = _out_name(src_name)
        _write_output(res, headers, [])
        cb("Done", 1.0)
        return res

    cb("Detecting NPI columns", 0.15)
    npi_idx, billing_idx = _detect_npi_columns(headers)
    res.npi_columns = [headers[i] for i in npi_idx]
    res.billing_column = headers[billing_idx] if billing_idx is not None else None
    if not npi_idx:
        res.warnings.append(
            "No NPI column detected (looked for headers containing 'NPI'). "
            "Rows were still trimmed and de-duplicated.")

    name_idx = _detect_one(headers, _NAME_HINTS)
    state_idx = _detect_one(headers, _STATE_HINTS)
    ndc_idx = _detect_one(headers, _NDC_HINTS)
    drug_idx = _detect_one(headers, _DRUG_HINTS)

    # User column-mapping overrides (canonical role → header) win over
    # auto-detection. Only roles the stdlib path acts on are honored here; the
    # rest flow to the v49 engine via vendor_adapter.
    if overrides:
        hidx = {h: i for i, h in enumerate(headers)}

        def _ov(role):
            col = overrides.get(role)
            return hidx.get(col) if col else None

        _b = _ov("billing_npi")
        if _b is not None:
            billing_idx = _b
            if _b not in npi_idx:
                npi_idx = sorted(set(npi_idx) | {_b})
                res.npi_columns = [headers[i] for i in npi_idx]
            res.billing_column = headers[_b]
        for role, setter in (("billing_name", "name"), ("state", "state"),
                             ("ndc", "ndc"), ("drug_name", "drug")):
            _i = _ov(role)
            if _i is not None:
                if setter == "name":
                    name_idx = _i
                elif setter == "state":
                    state_idx = _i
                elif setter == "ndc":
                    ndc_idx = _i
                elif setter == "drug":
                    drug_idx = _i

    ncols = len(headers)
    for i in npi_idx:
        res.column_stats[headers[i]] = {
            "valid": 0, "blank": 0, "malformed": 0, "checksum": 0, "cells": 0}

    cb("Cleaning rows", 0.30)
    cleaned: List[List[str]] = []
    seen = set()
    total = max(len(rows), 1)
    for ri, row in enumerate(rows):
        # Pad / trim ragged rows to the header width.
        if len(row) < ncols:
            row = row + [""] * (ncols - len(row))
        elif len(row) > ncols:
            row = row[:ncols]
        # Trim surrounding whitespace on every cell.
        new_row = []
        for cell in row:
            stripped = cell.strip()
            if stripped != cell:
                res.n_cells_trimmed += 1
            new_row.append(stripped)
        # Tally NPI health per detected column.
        for i in npi_idx:
            cstat = res.column_stats[headers[i]]
            cstat["cells"] += 1
            cstat[classify_npi(new_row[i])] += 1
        if drop_duplicates:
            key = tuple(new_row)
            if key in seen:
                res.n_dupes_removed += 1
                continue
            seen.add(key)
        cleaned.append(new_row)
        if ri % 500 == 0:
            cb("Cleaning rows", 0.30 + 0.55 * (ri / total))

    res.n_rows_out = len(cleaned)

    # Optional live NPPES cross-check via the app's shared CMS connection.
    # Guarded end-to-end: any failure leaves res.nppes with a note and the
    # offline results stand.
    if enrich:
        cb("Verifying NPIs against the live NPPES registry", 0.58)
        try:
            res.nppes, res.recovered_rows = _enrich_via_nppes(
                cleaned, npi_idx, billing_idx, name_idx, state_idx)
        except Exception as exc:  # noqa: BLE001
            res.nppes = {"error": f"{type(exc).__name__}: {exc}"}
        # Drug connectors (RxNorm / openFDA) + the available-source catalog.
        cb("Resolving drugs via RxNorm / openFDA", 0.68)
        try:
            from . import connectors
            res.catalog = connectors.catalog()
            ndcs = ([row[ndc_idx] for row in cleaned
                     if ndc_idx is not None and ndc_idx < len(row)]
                    if ndc_idx is not None else [])
            drugs = ([row[drug_idx] for row in cleaned
                      if drug_idx is not None and drug_idx < len(row)]
                     if drug_idx is not None else [])
            if ndcs or drugs:
                res.connectors = connectors.resolve_drugs(ndcs, drugs)
            else:
                res.connectors = []
        except Exception as exc:  # noqa: BLE001
            res.connectors = [{"id": "error",
                               "note": f"{type(exc).__name__}: {exc}"}]

    # Real vendored-engine pass: run the actual v48 field_validators +
    # consistency + dedup screens when pandas and the modules are available.
    # Guarded end-to-end — any failure just leaves res.advanced None and the
    # stdlib results stand on their own.
    cb("Running the v49 deterministic engine (repairs · screens · issues)", 0.82)
    try:
        from . import vendor_adapter
        adv = vendor_adapter.run(data, overrides)
        if adv:
            # The full companion can be large — keep it out of the JSON the
            # browser polls; retain it for the CSV/workbook downloads and
            # expose only a small preview inline.
            res.suggestions_records = adv.pop("suggestions_records", []) or []
            adv["suggestions_sample"] = res.suggestions_records[:25]
        res.advanced = adv
    except Exception:  # noqa: BLE001
        res.advanced = None

    cb("Writing cleaned file", 0.90)
    res.out_name = _out_name(src_name)
    _write_output(res, headers, cleaned)
    cb("Done", 1.0)
    return res


def _enrich_via_nppes(cleaned, npi_idx, billing_idx, name_idx, state_idx):
    """Run NPPES verify + recover over the cleaned rows via nppes_bridge.

    Returns the combined ``{"verify": ..., "recover": ...}`` payload, or a
    ``{"note": ...}`` when the bridge is unavailable.
    """
    from . import nppes_bridge
    if not nppes_bridge.available():
        return ({"note": "NPPES connection unavailable in this deployment."}, {})

    # Distinct NPIs across every detected NPI column, for verification.
    all_npis: List[str] = []
    for row in cleaned:
        for i in npi_idx:
            if i < len(row):
                all_npis.append(row[i])
    verify = nppes_bridge.verify_npis(all_npis)

    # Recovery queries: rows whose billing NPI is not valid but which carry a
    # provider name (+ state) we can search on. Track which rows each query
    # covers so a resolved candidate can be written back to every matching row.
    recover: Dict[str, object] = {"note": "No provider-name column to recover from."}
    recovered_rows: Dict[int, str] = {}
    if billing_idx is not None and name_idx is not None:
        queries: List[Dict[str, str]] = []
        key_to_rows: Dict[tuple, List[int]] = {}
        for ridx, row in enumerate(cleaned):
            if billing_idx >= len(row):
                continue
            if classify_npi(row[billing_idx]) == "valid":
                continue
            name = row[name_idx] if name_idx < len(row) else ""
            if not name.strip():
                continue
            state = row[state_idx] if (state_idx is not None
                                       and state_idx < len(row)) else ""
            queries.append({"row": str(ridx + 1), "name": name, "state": state})
            key = (name.strip().lower(), (state or "").strip().upper()[:2])
            key_to_rows.setdefault(key, []).append(ridx + 1)
        if queries:
            recover = nppes_bridge.recover_candidates(queries)
            # A match with exactly one candidate is confident enough to write
            # back to every row that shared that provider name + state.
            for m in recover.get("matches", []):
                cands = m.get("candidates") or []
                if len(cands) != 1:
                    continue
                key = ((m.get("query") or "").strip().lower(),
                       (m.get("state") or "").strip().upper()[:2])
                for rownum in key_to_rows.get(key, []):
                    recovered_rows[rownum] = cands[0]["npi"]
        else:
            recover = {"note": "No rows needed NPI recovery."}

    payload = {"verify": verify, "recover": recover,
               "recovered_written": len(recovered_rows),
               "source": "NPPES via rcm_mc.data_public.nppes_api_client"}
    return payload, recovered_rows


def sample_csv() -> str:
    """A small illustrative claims file exercising every check: a clean row, a
    duplicate, a blank billing NPI, a malformed NPI, a checksum failure, a
    whitespace case, a future service date and a money-ordering violation.
    NPIs here are Luhn-valid synthetic examples — not real providers.
    """
    return (
        "ClaimID,BillingProviderNPI,RenderingNPI,OrganizationName,"
        "ProviderState,ChargeAmt,AllowedAmt,PaidAmt,DateOfService,HCPCS\n"
        "1001,1679576722,1234567893,Mercy General Hospital,OH,420,300,240,2024-02-11,99213\n"
        "1001, 1679576722 ,1234567893,Mercy General Hospital,OH,420,300,240,2024-02-11,99213\n"
        "1003,,1245319599,Riverbend Clinic,TX,180,140,110,2024-03-02,99214\n"
        "1004,99999,1245319599,Riverbend Clinic,TX,180,140,110,2024-03-02,99214\n"
        "1005,1234567890,1679576722,Summit Surgical Center,CA,900,700,760,2024-04-19,ABCDE\n"
        "1006,1699999984,1234567893,Lakeside Imaging,FL,250,200,150,2099-01-01,70450\n"
    )


def _out_name(src_name: str) -> str:
    stem = Path(src_name or "claims").stem.replace(" ", "_") or "claims"
    return f"{stem}_cleaned.csv"


def _write_output(res: CleanResult, headers: List[str],
                  rows: List[List[str]]) -> None:
    # When NPPES recovery filled in NPIs, append a non-destructive column so
    # the original billing-NPI column is preserved and the recovery is visible.
    out_headers = list(headers)
    out_rows = [list(r) for r in rows]
    if res.recovered_rows and headers:
        out_headers = out_headers + ["recovered_billing_npi"]
        for i, r in enumerate(out_rows):
            r.append(res.recovered_rows.get(i + 1, ""))

    token = uuid.uuid4().hex
    out_path = WORKDIR / f"{token}_{res.out_name}"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if out_headers:
            writer.writerow([_defang_cell(h) for h in out_headers])
        for r in out_rows:
            writer.writerow([_defang_cell(c) for c in r])
    res.out_path = str(out_path)

    # Corrections companion (v49 suggested_fixes) as its own CSV download.
    if res.suggestions_records:
        cols = list(res.suggestions_records[0].keys())
        stem = res.out_name[:-len("_cleaned.csv")] if res.out_name.endswith(
            "_cleaned.csv") else res.out_name.rsplit(".", 1)[0]
        res.companion_name = f"{stem or 'claims'}_corrections.csv"
        comp_path = WORKDIR / f"{token}_{res.companion_name}"
        with open(comp_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([_defang_cell(c) for c in cols])
            for rec in res.suggestions_records:
                writer.writerow([_defang_cell(str(rec.get(c, ""))) for c in cols])
        res.companion_path = str(comp_path)

    # A styled multi-tab .xlsx workbook (Cleaned · issues · scorecard) via the
    # app's stdlib xlsx writer — no new dependency. Guarded: a workbook build
    # failure never blocks the CSV download.
    try:
        from . import report
        stem = res.out_name[:-len("_cleaned.csv")] if res.out_name.endswith(
            "_cleaned.csv") else res.out_name.rsplit(".", 1)[0]
        res.workbook_name = f"{stem or 'claims'}_report.xlsx"
        wb_bytes = report.build_workbook(res, out_headers, out_rows)
        wb_path = WORKDIR / f"{token}_{res.workbook_name}"
        with open(wb_path, "wb") as fh:
            fh.write(wb_bytes)
        res.workbook_path = str(wb_path)
    except Exception:  # noqa: BLE001
        res.workbook_path = None


# ------------------------------------------------------------- job management --
@dataclass
class Job:
    job_id: str
    name: str
    frac: float = 0.0
    msg: str = "Queued"
    done: bool = False
    error: Optional[str] = None
    result: Optional[CleanResult] = None
    created: float = 0.0

    def status_dict(self) -> Dict[str, object]:
        d: Dict[str, object] = {
            "job_id": self.job_id, "frac": round(self.frac, 3),
            "msg": self.msg, "done": self.done, "error": self.error,
        }
        if self.result is not None:
            d["scorecard"] = self.result.as_scorecard()
            d["download"] = f"/npi-cleaner/download/{self.job_id}"
        return d


class JobManager:
    """Thread-safe registry of cleaning jobs. One instance per server."""

    def __init__(self, max_jobs: int = 200) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max = max_jobs

    def _evict(self) -> None:
        if len(self._jobs) <= self._max:
            return
        # Drop the oldest completed jobs first.
        finished = sorted(
            (j for j in self._jobs.values() if j.done),
            key=lambda j: j.created)
        for j in finished[: len(self._jobs) - self._max]:
            self._jobs.pop(j.job_id, None)

    def submit(self, data: bytes, name: str, *,
               drop_duplicates: bool = True, enrich: bool = False,
               overrides: Optional[Dict[str, str]] = None) -> str:
        job_id = uuid.uuid4().hex
        job = Job(job_id=job_id, name=name, created=time.time())
        with self._lock:
            self._jobs[job_id] = job
            self._evict()

        def _run() -> None:
            def cb(msg: str, frac: float) -> None:
                job.msg, job.frac = msg, float(frac)
            try:
                job.result = clean_bytes(
                    data, name, drop_duplicates=drop_duplicates,
                    enrich=enrich, overrides=overrides, progress=cb)
                job.frac, job.msg, job.done = 1.0, "Done", True
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                job.error = f"{type(exc).__name__}: {exc}"
                job.done = True

        threading.Thread(target=_run, daemon=True).start()
        return job_id

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)


# One process-wide manager, created lazily so importing this module is cheap.
_MANAGER: Optional[JobManager] = None
_MANAGER_LOCK = threading.Lock()


def manager() -> JobManager:
    global _MANAGER
    if _MANAGER is None:
        with _MANAGER_LOCK:
            if _MANAGER is None:
                _MANAGER = JobManager()
    return _MANAGER

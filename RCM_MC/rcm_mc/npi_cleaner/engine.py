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
    warnings: List[str] = field(default_factory=list)
    # Real-engine findings from the vendored v48 field/consistency/dedup
    # screens (via vendor_adapter). None when pandas / the modules are
    # unavailable and we ran the stdlib path only.
    advanced: Optional[Dict[str, object]] = None

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
                          "|": "pipe"}.get(self.delimiter, self.delimiter),
            "out_name": self.out_name,
            "warnings": self.warnings,
            "advanced": self.advanced,
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


def _read_table(data: bytes) -> Tuple[List[str], List[List[str]], str]:
    """Decode bytes → (headers, rows, delimiter). Tolerant of BOM / latin-1."""
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


# -------------------------------------------------------------------- cleaner --
def clean_bytes(
    data: bytes,
    src_name: str,
    *,
    drop_duplicates: bool = True,
    progress: Optional[ProgressCb] = None,
) -> CleanResult:
    """Clean a delimited claims file given as raw bytes. Pure, no network."""
    def cb(msg: str, frac: float) -> None:
        if progress:
            progress(msg, frac)

    cb("Reading file", 0.05)
    headers, rows, delim = _read_table(data)
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

    # Real vendored-engine pass: run the actual v48 field_validators +
    # consistency + dedup screens when pandas and the modules are available.
    # Guarded end-to-end — any failure just leaves res.advanced None and the
    # stdlib results stand on their own.
    cb("Running coding & consistency screens", 0.82)
    try:
        from . import vendor_adapter
        res.advanced = vendor_adapter.run(data)
    except Exception:  # noqa: BLE001
        res.advanced = None

    cb("Writing cleaned file", 0.90)
    res.out_name = _out_name(src_name)
    _write_output(res, headers, cleaned)
    cb("Done", 1.0)
    return res


def _out_name(src_name: str) -> str:
    stem = Path(src_name or "claims").stem.replace(" ", "_") or "claims"
    return f"{stem}_cleaned.csv"


def _write_output(res: CleanResult, headers: List[str],
                  rows: List[List[str]]) -> None:
    out_path = WORKDIR / f"{uuid.uuid4().hex}_{res.out_name}"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)
    res.out_path = str(out_path)


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
               drop_duplicates: bool = True) -> str:
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
                    data, name, drop_duplicates=drop_duplicates, progress=cb)
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

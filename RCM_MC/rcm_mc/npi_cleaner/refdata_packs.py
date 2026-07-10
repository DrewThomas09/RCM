"""Reference-data packs — pull the REAL public code sets and use them.

The hand-curated catalogs in ``refdata.py`` cover the high-frequency
subset of every domain (enough to grade files out of the box, zero
setup). The authoritative sets are public downloads; this module turns
each one into a one-click / one-command pack:

  * ``taxonomy`` — the full NUCC provider-taxonomy CSV (~870 codes).
    Upgrades the specialty-mix display names from ~80 to all of them.
  * ``icd10cm``  — the CMS/CDC ICD-10-CM code file (~74k codes).
    Activates the ``icd10-unknown-code`` flag: a diagnosis that is
    SHAPED right but does not exist in the code set.
  * ``hcpcs``    — the CMS HCPCS Level II quarterly file (~8k codes).
    Activates ``hcpcs-unknown-code`` for letter-led (Level II) codes.
    Numeric CPT-4 codes are AMA-licensed and deliberately NOT vendored
    or validated beyond shape.
  * ``leie``     — the OIG List of Excluded Individuals/Entities
    (monthly CSV). Activates the automatic, offline
    ``leie-excluded-npi`` screen on EVERY run — no env var, no manual
    download, no online mode needed.

Pulls run on the deployment host (they need outbound HTTPS to nucc.org,
cms.gov and oig.hhs.gov); each pack records its source URL, fetch time,
row count and SHA-256 so a compliance reviewer can reproduce it. URLs
carry year/version patterns that roll — each pack lists candidates
newest-first and takes the first that answers, and every pack accepts an
environment override (``NPI_REFPACK_URL_<ID>``) for mirrors or pinned
versions. Everything is stdlib; storage is one SQLite file in WORKDIR.

Licensing notes, deliberately explicit: NUCC taxonomy and the OIG LEIE
are public; ICD-10-CM is public domain (CDC/NCHS); HCPCS Level II is a
CMS public file. CPT (HCPCS Level I) and the X12 CARC/RARC full lists
are licensed — they stay curated subsets in refdata.py.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import sqlite3
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .engine import WORKDIR

_DB_PATH = Path(WORKDIR) / "npi_cleaner_refpacks.sqlite3"
_LOCK = threading.Lock()
_DOWNLOAD_CAP_BYTES = 300 * 1024 * 1024   # LEIE is ~70 MB; headroom, not ∞
_FETCH_TIMEOUT_S = 120

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pack_meta (
    pack    TEXT PRIMARY KEY,
    source  TEXT NOT NULL,
    fetched REAL NOT NULL,
    rows    INTEGER NOT NULL,
    sha256  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pack_taxonomy (
    code    TEXT PRIMARY KEY,
    display TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pack_icd10cm (
    code    TEXT PRIMARY KEY,
    descr   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pack_hcpcs (
    code    TEXT PRIMARY KEY,
    descr   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pack_leie (
    npi     TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS pack_zip_cbsa (
    zip5    TEXT PRIMARY KEY,
    cbsa    TEXT NOT NULL,
    name    TEXT NOT NULL DEFAULT ''
);
"""


def _conn() -> sqlite3.Connection:
    Path(WORKDIR).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_DB_PATH)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    return con


# ------------------------------------------------------------------ parsers --
def _parse_taxonomy(raw: bytes) -> Iterable[Tuple[str, str]]:
    """NUCC taxonomy CSV: Code, Grouping, Classification, Specialization,
    Definition, … — display name = Classification (— Specialization)."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = [h.strip().lower() for h in next(reader, [])]
    try:
        c_i = header.index("code")
        cls_i = header.index("classification")
    except ValueError:
        raise ValueError("not a NUCC taxonomy CSV (no Code/Classification)")
    spec_i = header.index("specialization") if "specialization" in header \
        else None
    for row in reader:
        if c_i >= len(row):
            continue
        code = row[c_i].strip().upper()
        if len(code) != 10:
            continue
        cls = row[cls_i].strip() if cls_i < len(row) else ""
        spec = (row[spec_i].strip()
                if spec_i is not None and spec_i < len(row) else "")
        display = f"{cls} — {spec}" if spec else cls
        if display:
            yield code, display[:120]


def _parse_icd10cm(raw: bytes) -> Iterable[Tuple[str, str]]:
    """CMS 'codes file' zip (icd10cm_codes_*.txt: CODE<spaces>DESC per
    line) or the same .txt uploaded directly."""
    texts: List[str] = []
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist()
                     if n.lower().endswith(".txt") and "code" in n.lower()]
            names = names or [n for n in z.namelist()
                              if n.lower().endswith(".txt")]
            for n in names[:1]:
                texts.append(z.read(n).decode("utf-8", errors="replace"))
    else:
        texts.append(raw.decode("utf-8", errors="replace"))
    n_yielded = 0
    for text in texts:
        for line in text.splitlines():
            parts = line.strip().split(None, 1)
            if not parts:
                continue
            code = parts[0].strip().upper()
            # ICD-10-CM: letter + 2 alnum + up to 4 more (dot removed).
            if (3 <= len(code) <= 7 and code[0].isalpha()
                    and code[1:].isalnum()):
                n_yielded += 1
                yield code, (parts[1].strip()[:200] if len(parts) > 1 else "")
    if not n_yielded:
        raise ValueError("no ICD-10-CM codes found in the file")


def _parse_hcpcs(raw: bytes) -> Iterable[Tuple[str, str]]:
    """CMS HCPCS Level II release: a zip holding a fixed-width .txt
    (code in cols 1–5) and/or CSV/XLSX variants; also accepts a bare
    txt/csv. Only letter-led Level II codes are kept — numeric CPT-4
    codes are AMA-licensed and never stored."""
    def _lines(blob: bytes) -> List[str]:
        return blob.decode("utf-8", errors="replace").splitlines()

    candidates: List[List[str]] = []
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for n in z.namelist():
                if n.lower().endswith((".txt", ".csv")):
                    candidates.append(_lines(z.read(n)))
    else:
        candidates.append(_lines(raw))
    n_yielded = 0
    for lines in candidates:
        for line in lines:
            if len(line) < 5:
                continue
            code = line[:5].strip().strip('",').upper()
            if not (len(code) == 5 and code[0].isalpha()
                    and code[1:].isdigit()):
                continue
            desc = line[5:].strip().strip('",')[:200]
            # Fixed-width layouts put a sequence field first; CSVs put a
            # comma. Either way the description is best-effort display
            # text — validity only needs the code.
            n_yielded += 1
            yield code, desc
        if n_yielded:
            break
    if not n_yielded:
        raise ValueError("no HCPCS Level II codes found in the file")


def _parse_leie(raw: bytes) -> Iterable[Tuple[str]]:
    """OIG LEIE UPDATED.csv — keep the 10-digit NPIs only (the exclusion
    list carries names/addresses; the offline screen needs just NPIs,
    and storing less PHI-adjacent data is the point)."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = [h.strip().upper() for h in next(reader, [])]
    try:
        npi_i = header.index("NPI")
    except ValueError:
        raise ValueError("not a LEIE CSV (no NPI column)")
    n_yielded = 0
    for row in reader:
        if npi_i >= len(row):
            continue
        d = "".join(ch for ch in row[npi_i] if ch.isdigit())
        if len(d) == 10 and d != "0000000000":
            n_yielded += 1
            yield (d,)
    if not n_yielded:
        raise ValueError("no NPIs found in the LEIE file")


# ------------------------------------------------------------------- packs --
def _parse_zip_cbsa(raw: bytes) -> Iterable[Tuple[str, str, str]]:
    """ZIP/ZCTA → CBSA (metro/micro area) crosswalk.

    Primary source is the Census ZCTA↔CBSA relationship file
    (``tab20_zcta520_cbsa20_natl.txt``): pipe-delimited, one row per
    ZCTA×CBSA overlap. A ZCTA can straddle CBSAs, so the winner per ZIP is
    the overlap with the largest land area — the same tie-break HUD's
    crosswalk applies by address weight. Also accepts any simple delimited
    file with zip/cbsa(/name) columns (a downloaded HUD ZIP-CBSA crosswalk
    export works), so no-egress deployments can install from a file."""
    text = raw.decode("utf-8-sig", errors="replace")
    first = text.split("\n", 1)[0]
    delim = "|" if first.count("|") >= first.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    header = [h.strip().lower() for h in next(reader, [])]

    def _find(*cands: str) -> Optional[int]:
        for c in cands:
            for i, h in enumerate(header):
                if h == c or h.startswith(c):
                    return i
        return None

    z_i = _find("geoid_zcta5", "zcta5", "zip", "zcta")
    c_i = _find("geoid_cbsa", "cbsa")
    n_i = _find("namelsad_cbsa", "cbsaname", "cbsa_name", "name_cbsa",
                "cbsatitle", "cbsa_title")
    a_i = _find("arealand_part", "arealand")
    if z_i is None or c_i is None or z_i == c_i:
        raise ValueError("not a ZIP/ZCTA↔CBSA crosswalk (no zip + cbsa "
                         "columns found)")
    best: Dict[str, Tuple[float, str, str]] = {}
    for row in reader:
        if z_i >= len(row) or c_i >= len(row):
            continue
        z = "".join(ch for ch in row[z_i].strip() if ch.isdigit())
        c = row[c_i].strip()
        if len(z) != 5 or not c or not c.isdigit():
            continue
        name = (row[n_i].strip() if n_i is not None and n_i < len(row)
                else "")
        area = 0.0
        if a_i is not None and a_i < len(row):
            try:
                area = float(row[a_i])
            except ValueError:
                area = 0.0
        cur = best.get(z)
        if cur is None or area > cur[0]:
            best[z] = (area, c, name[:120])
    for z, (_area, c, name) in best.items():
        yield z, c, name


def _year_urls(pattern: str, back: int = 3) -> List[str]:
    y = datetime.now(timezone.utc).year
    return [pattern.format(year=y - i) for i in range(back)]


def _nucc_urls() -> List[str]:
    # NUCC releases version X.0 each January and X.1 each July, named
    # nucc_taxonomy_<major><minor>.csv with major = (year - 2000).
    now = datetime.now(timezone.utc)
    major = now.year - 2000
    out = []
    for m in (major, major - 1, major - 2):
        for minor in ("1", "0"):
            out.append("https://nucc.org/images/stories/CSV/"
                       f"nucc_taxonomy_{m}{minor}.csv")
    return out


# ``cadence_days`` is each pack's honest refresh cadence (how often the
# publisher revises the set): past it, status() marks the pack stale so a
# compliance screen run on a 9-month-old exclusions list SAYS so instead
# of silently passing. LEIE is monthly (35d with slack); HCPCS quarterly
# (100d); NUCC semiannual (200d); ICD-10-CM annual (400d).
PACKS: Dict[str, Dict[str, object]] = {
    "taxonomy": {
        "title": "NUCC provider taxonomy (full)",
        "table": "pack_taxonomy",
        "columns": 2,
        "parse": _parse_taxonomy,
        "urls": _nucc_urls,
        "cadence_days": 200,
        "license": "Public (NUCC); attribution appreciated.",
        "enables": "Full specialty display names in the specialty mix.",
    },
    "icd10cm": {
        "title": "ICD-10-CM code set (CMS/CDC)",
        "table": "pack_icd10cm",
        "columns": 2,
        "parse": _parse_icd10cm,
        "urls": lambda: (
            _year_urls("https://www.cms.gov/files/zip/"
                       "{year}-icd-10-cm-codes-file.zip")
            + _year_urls("https://www.cms.gov/files/zip/"
                         "{year}-code-descriptions-tabular-order.zip")
            + _year_urls("https://ftp.cdc.gov/pub/Health_Statistics/NCHS/"
                         "Publications/ICD10CM/{year}/"
                         "icd10cm-codes-{year}.txt")),
        "cadence_days": 400,
        "license": "Public domain (US Government work).",
        "enables": "icd10-unknown-code — shaped-but-nonexistent diagnoses.",
    },
    "hcpcs": {
        "title": "HCPCS Level II (CMS quarterly)",
        "table": "pack_hcpcs",
        "columns": 2,
        "parse": _parse_hcpcs,
        "urls": lambda: (
            _year_urls("https://www.cms.gov/files/zip/"
                       "{year}-hcpcs-alpha-numeric-hcpc-file.zip")
            + _year_urls("https://www.cms.gov/files/zip/"
                         "january-{year}-alpha-numeric-hcpcs-file.zip")),
        "cadence_days": 100,
        "license": "CMS public file (Level II only; CPT-4 excluded).",
        "enables": "hcpcs-unknown-code — letter-led codes not in the set.",
    },
    "zip_cbsa": {
        "title": "ZIP → CBSA/MSA crosswalk (Census)",
        "table": "pack_zip_cbsa",
        "columns": 3,
        "parse": _parse_zip_cbsa,
        "urls": lambda: [
            "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
            "cbsa/tab20_zcta520_cbsa20_natl.txt"],
        "cadence_days": 800,
        "license": "Public domain (US Census Bureau).",
        "enables": "geo_msa enrichment — cbsa_code / cbsa_name columns and "
                   "the metro-area mix, so claims pivot by MSA.",
    },
    "leie": {
        "title": "OIG exclusions list (LEIE)",
        "table": "pack_leie",
        "columns": 1,
        "parse": _parse_leie,
        "urls": lambda: ["https://oig.hhs.gov/exclusions/downloadables/"
                         "UPDATED.csv"],
        "cadence_days": 35,
        "license": "Public (HHS OIG). Refresh monthly.",
        "enables": "leie-excluded-npi — automatic offline exclusion "
                   "screening on every run.",
    },
}

# In-flight pull state, per pack: {"state": "pulling"|"done"|"error",
# "note": str}. Module-level so the API can report progress.
_PULLS: Dict[str, Dict[str, str]] = {}


def _fetch(url: str, opener: Callable = urllib.request.urlopen) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "rcm-mc-npi-cleaner/1.0 (reference-data pull)"})
    chunks: List[bytes] = []
    got = 0
    with opener(req, timeout=_FETCH_TIMEOUT_S) as resp:
        while True:
            block = resp.read(4 * 1024 * 1024)
            if not block:
                break
            got += len(block)
            if got > _DOWNLOAD_CAP_BYTES:
                raise ValueError(f"download exceeded "
                                 f"{_DOWNLOAD_CAP_BYTES // (1024*1024)} MB")
            chunks.append(block)
    return b"".join(chunks)


def _install_rows(pack_id: str, spec: Dict[str, object], rows: list, *,
                  source: str, digest: str) -> Dict[str, object]:
    """Replace one pack's table + provenance row. Shared by the HTTPS
    pull, the install-from-file path and the vendored bootstrap so every
    install records the same source/fetched/rows/sha256 provenance."""
    table = str(spec["table"])
    ncols = int(spec["columns"])  # type: ignore[arg-type]
    ph = ",".join("?" * ncols)
    with _LOCK, _conn() as con:
        con.execute(f"DELETE FROM {table}")  # noqa: S608 — fixed name
        con.executemany(
            f"INSERT OR REPLACE INTO {table} VALUES ({ph})",  # noqa: S608
            rows)
        con.execute(
            "INSERT INTO pack_meta (pack, source, fetched, rows,"
            " sha256) VALUES (?,?,?,?,?) ON CONFLICT(pack) DO UPDATE"
            " SET source=excluded.source, fetched=excluded.fetched,"
            " rows=excluded.rows, sha256=excluded.sha256",
            (pack_id, source, time.time(), len(rows), digest))
    _invalidate_cache(pack_id)
    return {"pack": pack_id, "source": source, "rows": len(rows),
            "sha256": digest}


def pull(pack_id: str, *, opener: Callable = urllib.request.urlopen,
         url: Optional[str] = None) -> Dict[str, object]:
    """Download, parse and install one pack. Tries the pack's candidate
    URLs newest-first (or exactly ``url``/the env override). Raises
    ValueError with a readable message when nothing worked."""
    spec = PACKS.get(pack_id)
    if spec is None:
        raise ValueError(f"unknown pack: {pack_id!r} "
                         f"(known: {', '.join(sorted(PACKS))})")
    env_url = os.environ.get(f"NPI_REFPACK_URL_{pack_id.upper()}")
    candidates = ([url] if url else [env_url] if env_url
                  else list(spec["urls"]()))  # type: ignore[operator]
    last_err: Optional[Exception] = None
    for cand in candidates:
        try:
            raw = _fetch(cand, opener)
            rows = list(spec["parse"](raw))  # type: ignore[operator]
            if not rows:
                raise ValueError("file parsed to zero rows")
            return _install_rows(pack_id, spec, rows, source=cand,
                                 digest=hashlib.sha256(raw).hexdigest())
        except Exception as exc:  # noqa: BLE001 — try the next candidate
            last_err = exc
    raise ValueError(
        f"could not pull {pack_id!r}: {type(last_err).__name__}: {last_err}. "
        "The host needs outbound HTTPS to the source (or set "
        f"NPI_REFPACK_URL_{pack_id.upper()} to a mirror). On a no-egress "
        "host, install from a downloaded file instead "
        "(install_from_file / rcm-mc npi-clean --refdata-install).")


def install_from_bytes(pack_id: str, raw: bytes, *,
                       source: str = "local file") -> Dict[str, object]:
    """Install one pack from an already-downloaded payload — the offline
    path for no-egress deployments, where pull() can never succeed. Same
    parsers, same provenance row (source recorded as ``file: …``), same
    cache invalidation. Raises ValueError on an unparseable payload."""
    spec = PACKS.get(pack_id)
    if spec is None:
        raise ValueError(f"unknown pack: {pack_id!r} "
                         f"(known: {', '.join(sorted(PACKS))})")
    if not raw:
        raise ValueError("empty payload")
    rows = list(spec["parse"](raw))  # type: ignore[operator]
    if not rows:
        raise ValueError("file parsed to zero rows")
    return _install_rows(pack_id, spec, rows, source=f"file: {source}",
                         digest=hashlib.sha256(raw).hexdigest())


def install_from_file(pack_id: str, path: str) -> Dict[str, object]:
    """``install_from_bytes`` from a path on disk (CLI/API convenience)."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"file not found: {path}")
    return install_from_bytes(pack_id, p.read_bytes(), source=p.name)


def bootstrap_icd10cm_from_vendored() -> Dict[str, object]:
    """Seed the icd10cm pack from the vendored v49 validity table.

    A no-egress deployment can never pull() a pack, yet a complete
    148,980-row ICD-10-CM validity set (FY2025 + FY2026) already ships
    inside vendor_v49 for the pandas path — the stdlib-grade
    ``icd10-unknown-code`` check stayed dark for no reason. This
    installs that table as the icd10cm pack, provenance recorded as the
    vendored file, so the flag fires with zero network."""
    seed = (Path(__file__).parent / "vendor_v49" / "npi_recovery" /
            "reference" / "icd10cm_validity_seed.csv")
    if not seed.exists():
        raise ValueError("vendored icd10cm_validity_seed.csv not shipped "
                         "in this build")
    raw = seed.read_bytes()
    reader = csv.reader(io.StringIO(raw.decode("utf-8", errors="replace")))
    header = [h.strip().lower() for h in next(reader, [])]
    try:
        c_i = header.index("code")
    except ValueError:
        raise ValueError("unexpected validity-seed format (no code column)")
    f_i = header.index("fy") if "fy" in header else None
    best_fy: Dict[str, str] = {}
    for row in reader:
        if c_i >= len(row):
            continue
        code = row[c_i].strip().upper()
        if not (3 <= len(code) <= 7 and code[0].isalpha()
                and code[1:].isalnum()):
            continue
        fy = (row[f_i].strip() if f_i is not None and f_i < len(row)
              else "")
        if fy >= best_fy.get(code, ""):
            best_fy[code] = fy
    if not best_fy:
        raise ValueError("no ICD-10-CM codes parsed from the vendored seed")
    rows = [(code, f"FY{fy}" if fy else "")
            for code, fy in best_fy.items()]
    return _install_rows(
        "icd10cm", PACKS["icd10cm"], rows,
        source="vendored icd10cm_validity_seed FY2025-FY2026 (vendor_v49)",
        digest=hashlib.sha256(raw).hexdigest())


def pull_async(pack_id: str) -> bool:
    """Kick a pull in a background thread; progress via status()."""
    if pack_id not in PACKS:
        return False
    cur = _PULLS.get(pack_id)
    if cur and cur.get("state") == "pulling":
        return True
    _PULLS[pack_id] = {"state": "pulling", "note": "downloading…"}

    def _run() -> None:
        try:
            info = pull(pack_id)
            _PULLS[pack_id] = {"state": "done",
                               "note": f"{info['rows']:,} rows"}
        except Exception as exc:  # noqa: BLE001
            _PULLS[pack_id] = {"state": "error", "note": str(exc)[:300]}

    threading.Thread(target=_run, daemon=True).start()
    return True


def status() -> List[Dict[str, object]]:
    """One entry per pack: installed?, rows, fetched, source, licensing,
    what installing it enables, and any in-flight pull state. Installed
    packs also carry their vintage (``fetched_iso``), ``age_days`` and a
    ``stale`` flag against the pack's refresh cadence — a screen run on
    a nine-month-old exclusions list must be able to say so."""
    meta: Dict[str, tuple] = {}
    try:
        with _LOCK, _conn() as con:
            for pack, source, fetched, rows, sha in con.execute(
                    "SELECT pack, source, fetched, rows, sha256 "
                    "FROM pack_meta"):
                meta[pack] = (source, fetched, rows, sha)
    except Exception:  # noqa: BLE001 — a broken store reads as "none"
        pass
    out = []
    for pid, spec in PACKS.items():
        m = meta.get(pid)
        cadence = int(spec.get("cadence_days") or 0)
        d: Dict[str, object] = {
            "id": pid, "title": spec["title"], "license": spec["license"],
            "enables": spec["enables"], "installed": m is not None,
            "cadence_days": cadence,
        }
        if m:
            try:
                fetched_s = float(m[1])
            except (TypeError, ValueError):
                fetched_s = 0.0
            age_days = max(0.0, (time.time() - fetched_s) / 86400.0)
            d.update({
                "source": m[0], "fetched": m[1], "rows": m[2],
                "sha256": m[3],
                "fetched_iso": (datetime.fromtimestamp(
                    fetched_s, tz=timezone.utc).strftime("%Y-%m-%d")
                    if fetched_s else ""),
                "age_days": round(age_days, 1),
                "stale": bool(cadence and age_days > cadence),
            })
        p = _PULLS.get(pid)
        if p:
            d["pull"] = dict(p)
        out.append(d)
    return out


# ------------------------------------------------------ engine-facing reads --
# Loaded once per process and invalidated on a fresh pull. The sets are
# small relative to a cleaning run (ICD-10-CM ≈ 74k short strings).
_CACHE: Dict[str, object] = {}
_CACHE_LOCK = threading.Lock()


def _invalidate_cache(pack_id: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(pack_id, None)
        if pack_id == "taxonomy":
            _CACHE.pop("taxonomy_codes", None)
        if pack_id == "hcpcs":
            _CACHE.pop("hcpcs_descr", None)


def _load_set(pack_id: str, table: str) -> Optional[frozenset]:
    with _CACHE_LOCK:
        if pack_id in _CACHE:
            return _CACHE[pack_id]  # type: ignore[return-value]
    if not _DB_PATH.exists():
        return None
    try:
        with _LOCK, _conn() as con:
            has = con.execute("SELECT 1 FROM pack_meta WHERE pack = ?",
                              (pack_id,)).fetchone()
            if not has:
                return None
            vals = frozenset(
                r[0] for r in con.execute(
                    f"SELECT code FROM {table}"  # noqa: S608 — fixed name
                    if table != "pack_leie" else "SELECT npi FROM pack_leie"))
    except Exception:  # noqa: BLE001
        return None
    with _CACHE_LOCK:
        _CACHE[pack_id] = vals
    return vals


def icd10_codes() -> Optional[frozenset]:
    return _load_set("icd10cm", "pack_icd10cm")


def hcpcs_codes() -> Optional[frozenset]:
    return _load_set("hcpcs", "pack_hcpcs")


def leie_npis() -> Optional[frozenset]:
    return _load_set("leie", "pack_leie")


def taxonomy_codes() -> Optional[frozenset]:
    """The full NUCC taxonomy code set (for the taxonomy-unknown-code
    membership check), or None when the pack isn't installed."""
    with _CACHE_LOCK:
        if "taxonomy_codes" in _CACHE:
            return _CACHE["taxonomy_codes"]  # type: ignore[return-value]
    if not _DB_PATH.exists():
        return None
    try:
        with _LOCK, _conn() as con:
            has = con.execute(
                "SELECT 1 FROM pack_meta WHERE pack = 'taxonomy'").fetchone()
            if not has:
                return None
            vals = frozenset(
                r[0] for r in con.execute("SELECT code FROM pack_taxonomy"))
    except Exception:  # noqa: BLE001
        return None
    with _CACHE_LOCK:
        _CACHE["taxonomy_codes"] = vals
    return vals


def hcpcs_display(code: str) -> Optional[str]:
    """Long description for a HCPCS Level II code from the installed pack,
    or None (pack absent / code unknown). Powers the top-codes enrichment
    labels — same lazy whole-table cache pattern as taxonomy_display."""
    with _CACHE_LOCK:
        table = _CACHE.get("hcpcs_descr")
    if table is None:
        if not _DB_PATH.exists():
            return None
        try:
            with _LOCK, _conn() as con:
                has = con.execute(
                    "SELECT 1 FROM pack_meta WHERE pack = 'hcpcs'").fetchone()
                if not has:
                    return None
                table = dict(con.execute(
                    "SELECT code, descr FROM pack_hcpcs"))
        except Exception:  # noqa: BLE001
            return None
        with _CACHE_LOCK:
            _CACHE["hcpcs_descr"] = table
    return table.get(code.strip().upper()) or None  # type: ignore[union-attr]


def zip_cbsa_lookup() -> Optional[Dict[str, Tuple[str, str]]]:
    """zip5 → (cbsa_code, cbsa_name) for the geo_msa enrichment, or None
    when the pack isn't installed. ~33k small tuples — cached once per
    process like the code sets."""
    with _CACHE_LOCK:
        if "zip_cbsa" in _CACHE:
            return _CACHE["zip_cbsa"]  # type: ignore[return-value]
    if not _DB_PATH.exists():
        return None
    try:
        with _LOCK, _conn() as con:
            has = con.execute(
                "SELECT 1 FROM pack_meta WHERE pack = 'zip_cbsa'").fetchone()
            if not has:
                return None
            table = {z: (c, n) for z, c, n in con.execute(
                "SELECT zip5, cbsa, name FROM pack_zip_cbsa")}
    except Exception:  # noqa: BLE001
        return None
    with _CACHE_LOCK:
        _CACHE["zip_cbsa"] = table
    return table


def taxonomy_display(code: str) -> Optional[str]:
    """Full-catalog specialty name; None when the pack isn't installed
    or the code isn't in it (caller falls back to the curated subset)."""
    with _CACHE_LOCK:
        table = _CACHE.get("taxonomy")
    if table is None:
        if not _DB_PATH.exists():
            return None
        try:
            with _LOCK, _conn() as con:
                has = con.execute(
                    "SELECT 1 FROM pack_meta WHERE pack = 'taxonomy'"
                ).fetchone()
                if not has:
                    return None
                table = dict(con.execute(
                    "SELECT code, display FROM pack_taxonomy"))
        except Exception:  # noqa: BLE001
            return None
        with _CACHE_LOCK:
            _CACHE["taxonomy"] = table
    return table.get(code.strip().upper())  # type: ignore[union-attr]

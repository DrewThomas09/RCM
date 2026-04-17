"""CMS HCRIS (Hospital Cost Report) public-data layer.

Every Medicare-participating hospital files an annual Cost Report with CMS;
the data is public. This module extracts the ~15 fields a diligence analyst
would want to pre-populate from a target hospital's filing — NPSR, bed
count, payer-day mix, operating expenses, net income, address — and stores
them as a compact parquet that ships with the package.

Refresh pipeline (developer operation, ~once per CMS release)::

    python -m rcm_mc.hcris refresh --year 2022

downloads the CMS HOSP10FY{year}.zip bundle, parses the three constituent
CSVs, applies status-rank dedup (prefer audited > settled > submitted), and
writes the merged parquet.

Runtime API::

    from rcm_mc.data.hcris import load_hcris
    df = load_hcris()         # pandas DataFrame, one row per hospital

No runtime network access — the parquet is the cached view. If a user
wants newer data they can re-run ``refresh``.
"""
from __future__ import annotations

import argparse
import difflib
import logging
import os
import re
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────

HCRIS_URL_TEMPLATE = "https://downloads.cms.gov/Files/hcris/HOSP10FY{year}.zip"

_PACKAGE_DIR = Path(__file__).resolve().parent
# Post-refactor: hcris.py moved into rcm_mc/data/, and the csv lives
# alongside it. _PACKAGE_DIR is already rcm_mc/data/, so no extra
# "data" segment.
DEFAULT_DATA_PATH = _PACKAGE_DIR / "hcris.csv.gz"

# CMS flat-file column schemas (undocumented in the CSVs themselves).
RPT_COLS = [
    "rpt_rec_num", "prvdr_ctrl_type_cd", "prvdr_num", "npi", "rpt_stus_cd",
    "fy_bgn_dt", "fy_end_dt", "proc_dt", "initl_rpt_sw", "last_rpt_sw",
    "trnsmtl_num", "fi_num", "adr_vndr_cd", "fi_creat_dt", "util_cd",
    "npr_dt", "spec_ind", "fi_rcpt_dt",
]
NMRC_COLS = ["rpt_rec_num", "wksht_cd", "line_num", "col_num", "value"]
ALPHA_COLS = NMRC_COLS  # identical shape

# Status-code preference: pick the most authoritative filing per provider.
#   3 = Settled with Audit   (highest authority)
#   2 = Settled w/o Audit
#   4 = Reopened
#   5 = Amended
#   1 = As Submitted         (lowest — not yet reviewed by CMS)
STATUS_RANK = {"3": 0, "2": 1, "4": 2, "5": 3, "1": 4}


# Field coordinate map — verified empirically against 7 known hospitals
# (Cedars-Sinai, Cleveland Clinic, Mass General, Mount Sinai, Northwestern,
# NYU Langone, Penn Medicine) in Step 0 feasibility work.
#
# (worksheet_code, line_num, col_num) — all codes 5-char / 5-digit padded.
NUMERIC_FIELDS: dict[str, tuple[str, str, str]] = {
    "beds":                     ("S300001", "01400", "00200"),  # S-3 Pt I Ln 14 Col 2
    "bed_days_available":       ("S300001", "01400", "00300"),  # Col 3: beds × 365
    "medicare_days":            ("S300001", "01400", "00600"),  # Col 6: Title XVIII
    "medicaid_days":            ("S300001", "01400", "00700"),  # Col 7: Title XIX
    "total_patient_days":       ("S300001", "01400", "00800"),  # Col 8: total
    "gross_patient_revenue":    ("G300000", "00100", "00100"),  # G-3 Ln 1
    "contractual_allowances":   ("G300000", "00200", "00100"),  # G-3 Ln 2
    "net_patient_revenue":      ("G300000", "00300", "00100"),  # G-3 Ln 3: NPSR
    "operating_expenses":       ("G300000", "00400", "00100"),  # G-3 Ln 4
    "net_income":               ("G300000", "00500", "00100"),  # G-3 Ln 5
}

ALPHA_FIELDS: dict[str, tuple[str, str, str]] = {
    "name":    ("S200001", "00300", "00100"),  # S-2 Pt I Ln 3 Col 1: hospital name
    "street":  ("S200001", "00100", "00100"),  # S-2 Pt I Ln 1 Col 1
    "city":    ("S200001", "00200", "00100"),  # S-2 Pt I Ln 2 Col 1
    "state":   ("S200001", "00200", "00200"),  # Col 2
    "zip":     ("S200001", "00200", "00300"),  # Col 3
    "county":  ("S200001", "00200", "00400"),  # Col 4
}


# ── Raw file handling ──────────────────────────────────────────────────────

def _download_archive(year: int, dest: Path) -> Path:
    url = HCRIS_URL_TEMPLATE.format(year=year)
    logger.info("Downloading %s → %s", url, dest)
    urllib.request.urlretrieve(url, dest)
    return dest


def _extract_archive(zip_path: Path, dest_dir: Path) -> dict[str, Path]:
    """Unzip into ``dest_dir`` and return ``{"rpt": Path, "nmrc": Path, "alpha": Path}``."""
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest_dir)
    names = os.listdir(dest_dir)
    def _pick(suffix: str) -> Path:
        hits = [n for n in names if n.endswith(suffix)]
        if not hits:
            raise FileNotFoundError(f"{suffix} not found in {zip_path}")
        return dest_dir / hits[0]
    return {
        "rpt":   _pick("_rpt.csv"),
        "nmrc":  _pick("_nmrc.csv"),
        "alpha": _pick("_alpha.csv"),
    }


def _load_rpt_dedup(path: Path) -> pd.DataFrame:
    """Load RPT; keep the single most authoritative filing per provider."""
    df = pd.read_csv(path, names=RPT_COLS, dtype=str)
    df["_rank"] = df["rpt_stus_cd"].map(STATUS_RANK).fillna(9).astype(int)
    df = df.sort_values(
        ["prvdr_num", "_rank", "fy_end_dt"],
        ascending=[True, True, False],
    )
    return df.drop_duplicates(subset=["prvdr_num"], keep="first").drop(columns="_rank")


def _pivot_long_csv(
    path: Path,
    target_recs: set,
    field_map: dict,
    chunksize: int = 500_000,
    numeric: bool = True,
) -> pd.DataFrame:
    """Stream a long-format HCRIS CSV and pivot selected coordinates to wide.

    ``field_map`` is ``{field_name: (wksht_cd, line_num, col_num)}``.
    """
    target_coords = set(field_map.values())
    coord_to_field = {v: k for k, v in field_map.items()}
    frames: list[pd.DataFrame] = []
    cols = NMRC_COLS  # same shape for NMRC + ALPHA
    for chunk in pd.read_csv(path, names=cols, dtype=str, chunksize=chunksize):
        sel = chunk[chunk["rpt_rec_num"].isin(target_recs)]
        if sel.empty:
            continue
        # Per-row coordinate filter — vectorized tuple lookup
        keys = list(zip(sel["wksht_cd"], sel["line_num"], sel["col_num"]))
        mask = [k in target_coords for k in keys]
        sel = sel[mask]
        if not sel.empty:
            frames.append(sel)

    if not frames:
        return pd.DataFrame(columns=["rpt_rec_num", *field_map])

    raw = pd.concat(frames, ignore_index=True)
    raw["field"] = [coord_to_field[k] for k in zip(raw["wksht_cd"], raw["line_num"], raw["col_num"])]
    if numeric:
        raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    wide = raw.pivot_table(
        index="rpt_rec_num", columns="field", values="value", aggfunc="first",
    )
    return wide.reset_index()


# ── Public API ──────────────────────────────────────────────────────────────

def _refresh_single_year(
    year: int,
    source_zip: Optional[Path] = None,
) -> pd.DataFrame:
    """Parse one CMS HCRIS fiscal-year bundle into a normalized DataFrame.

    Returns the same column set the shipped dataset uses. Caller writes the
    file. Kept as a helper so :func:`refresh_hcris` can iterate multiple
    years and concat.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        zip_path = Path(source_zip) if source_zip else tmp_dir / f"HOSP10FY{year}.zip"
        if not source_zip:
            _download_archive(year, zip_path)
        files = _extract_archive(zip_path, tmp_dir)

        logger.info("FY%d: loading RPT…", year)
        rpt = _load_rpt_dedup(files["rpt"])
        target_recs = set(rpt["rpt_rec_num"])
        logger.info("FY%d: RPT deduplicated: %d providers", year, len(rpt))

        logger.info("FY%d: pivoting NMRC…", year)
        numeric = _pivot_long_csv(files["nmrc"], target_recs, NUMERIC_FIELDS, numeric=True)
        logger.info("FY%d: pivoting ALPHA…", year)
        alpha = _pivot_long_csv(files["alpha"], target_recs, ALPHA_FIELDS, numeric=False)

    # Merge: RPT → ALPHA → NUMERIC
    core = rpt[["rpt_rec_num", "prvdr_num", "rpt_stus_cd", "fy_bgn_dt", "fy_end_dt"]].rename(
        columns={"prvdr_num": "ccn"},
    )
    merged = core.merge(alpha, on="rpt_rec_num", how="left").merge(numeric, on="rpt_rec_num", how="left")

    merged["medicare_day_pct"] = merged["medicare_days"] / merged["total_patient_days"]
    merged["medicaid_day_pct"] = merged["medicaid_days"] / merged["total_patient_days"]
    merged["fiscal_year"] = int(year) if not source_zip else _year_from_zip_name(zip_path, year)
    return merged


def refresh_hcris(
    year: Optional[int] = None,
    out_path: Optional[Path] = None,
    source_zip: Optional[Path] = None,
    *,
    years: Optional[List[int]] = None,
    source_zips: Optional[List[Path]] = None,
) -> Path:
    """Build the shipped gzipped CSV from one or more CMS HCRIS fiscal-year bundles.

    Back-compat single-year call:
        ``refresh_hcris(year=2022)`` — same as pre-multi-year signature.

    Multi-year call (Brick 16+):
        ``refresh_hcris(years=[2020, 2021, 2022])``

    Parameters
    ----------
    year
        Single fiscal year (back-compat). Ignored if ``years`` is set.
    years
        List of fiscal years to fetch + concat into a single output file.
    out_path
        Destination gzipped CSV. Defaults to the shipped location.
    source_zip / source_zips
        Optional pre-downloaded ``HOSP10FY{year}.zip`` paths to skip the
        network step. ``source_zip`` pairs with ``year``; ``source_zips``
        is a list matching ``years`` positionally.
    """
    # Normalize inputs
    if years is None:
        years = [year if year is not None else 2022]
    if source_zip and not source_zips:
        source_zips = [source_zip]
    if source_zips and len(source_zips) != len(years):
        raise ValueError(
            f"source_zips length ({len(source_zips)}) must match years length ({len(years)})"
        )

    out_path = Path(out_path) if out_path else DEFAULT_DATA_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    frames: List[pd.DataFrame] = []
    for i, y in enumerate(years):
        zp = source_zips[i] if source_zips else None
        frames.append(_refresh_single_year(int(y), source_zip=zp))

    combined = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

    # Tight column order for readability (same as single-year)
    col_order = [
        "ccn", "name", "city", "state", "zip", "county",
        "fiscal_year", "fy_bgn_dt", "fy_end_dt", "rpt_stus_cd", "rpt_rec_num",
        "beds", "bed_days_available",
        "medicare_days", "medicaid_days", "total_patient_days",
        "medicare_day_pct", "medicaid_day_pct",
        "gross_patient_revenue", "contractual_allowances",
        "net_patient_revenue", "operating_expenses", "net_income",
        "street",
    ]
    combined = combined[[c for c in col_order if c in combined.columns]]

    combined.to_csv(out_path, index=False, compression="gzip")
    logger.info(
        "Wrote %s (%d rows, %d year(s), %.1f KB)",
        out_path, len(combined), len(years), out_path.stat().st_size / 1024,
    )
    return out_path


def _year_from_zip_name(zip_path: Path, default_year: int) -> int:
    """Best-effort FY parse from an explicit ``source_zip`` filename."""
    name = zip_path.name.upper()
    for y in range(2011, 2040):
        if f"FY{y}" in name:
            return y
    return int(default_year)


def load_hcris(path: Optional[Path] = None) -> pd.DataFrame:
    """Load the shipped HCRIS dataset. Raises ``FileNotFoundError`` if missing."""
    path = Path(path) if path else DEFAULT_DATA_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"HCRIS data not found at {path}. "
            "Build it with `python -m rcm_mc.hcris refresh --year 2022`."
        )
    # dtype enforcement: CCN / state / ZIP must stay strings (leading zeros matter)
    str_cols = {"ccn", "name", "city", "state", "zip", "county", "rpt_rec_num",
                "rpt_stus_cd", "fy_bgn_dt", "fy_end_dt", "street"}
    return pd.read_csv(path, dtype={c: str for c in str_cols}, compression="gzip")


def tag_hcris_row(registry, row, *, metric_map: Optional[dict] = None) -> None:
    """Provenance helper: record every value in an HCRIS row as a
    HCRIS DataPoint on ``registry``.

    Parameters
    ----------
    registry
        A :class:`rcm_mc.provenance.ProvenanceRegistry`.
    row
        A pandas Series or dict-like representing one HCRIS row.
        Must contain at minimum ``ccn``; ``fiscal_year`` is looked
        up if present else defaults to current year.
    metric_map
        Optional ``{column_name: metric_name}``. When None, record
        every numeric column with its original name. Use this to
        rename ``net_patient_revenue`` → ``npsr`` for consistency
        with the rest of the platform.

    Silently skips non-numeric columns and NaN values. Never raises.
    """
    from datetime import date as _date
    try:
        ccn = str(row.get("ccn", "")).strip()
        fy_raw = row.get("fiscal_year")
        fy = int(fy_raw) if fy_raw is not None and fy_raw == fy_raw else _date.today().year
    except Exception:  # noqa: BLE001
        return
    mapping = metric_map or {}
    for col, val in (row.items() if hasattr(row, "items") else []):
        if col in ("ccn", "name", "city", "state", "zip", "county",
                   "fiscal_year", "street", "rpt_rec_num",
                   "rpt_stus_cd", "fy_bgn_dt", "fy_end_dt"):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        metric_name = mapping.get(col, col)
        try:
            registry.record_hcris(
                value=v, metric_name=metric_name,
                ccn=ccn, fiscal_year=fy,
            )
        except Exception:  # noqa: BLE001
            continue


# ── Lookup helpers ──────────────────────────────────────────────────────────

# Module-level cache so repeated lookups don't re-read the CSV. None = not yet
# loaded; set lazily on first lookup call.
_HCRIS_CACHE: Optional[pd.DataFrame] = None


def hcris_cache_age_days() -> Optional[float]:
    """Return the age of the HCRIS data file in days, or None if missing."""
    import time
    path = DEFAULT_DATA_PATH
    if not path.is_file():
        return None
    mtime = path.stat().st_mtime
    return (time.time() - mtime) / 86400.0


def _get_hcris_cached() -> pd.DataFrame:
    """Return the cached HCRIS DataFrame, loading it on first call.

    With multi-year data the DataFrame has one row per (CCN, fiscal_year).
    Callers that want a single row per hospital should go through
    :func:`_get_latest_per_ccn` instead.
    """
    global _HCRIS_CACHE
    if _HCRIS_CACHE is None:
        age = hcris_cache_age_days()
        if age is not None and age > 90:
            logger.warning(
                "HCRIS data is %.0f days old — consider refreshing "
                "with `rcm-mc data refresh hcris`",
                age,
            )
        _HCRIS_CACHE = load_hcris()
    return _HCRIS_CACHE


def _get_latest_per_ccn() -> pd.DataFrame:
    """Cached DataFrame collapsed to one row per CCN (most recent fiscal year).

    Used by name search, state browse, and peer matching so multi-year data
    doesn't surface the same hospital multiple times.
    """
    return _latest_row_per_ccn(_get_hcris_cached())


def _clear_cache() -> None:
    """Drop the module-level cache (test helper)."""
    global _HCRIS_CACHE
    _HCRIS_CACHE = None


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    """Convert a DataFrame row to a plain dict; NaN → None."""
    return {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}


def _latest_row_per_ccn(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the most-recent fiscal_year row per CCN (for default lookups)."""
    if "fiscal_year" not in df.columns or df.empty:
        return df
    return (
        df.sort_values(["ccn", "fiscal_year"], ascending=[True, False])
          .drop_duplicates(subset=["ccn"], keep="first")
          .reset_index(drop=True)
    )


def lookup_by_ccn(ccn: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return a single hospital's record by 6-digit Medicare CCN, or ``None``.

    With multi-year HCRIS data in the shipped file, ``year=None`` (default)
    returns the most-recent fiscal year on file. Pass ``year=2020`` to pin
    to a specific filing.

    Input is left-padded with zeros to 6 chars so ``"50108"`` → ``"050108"``.
    Strips leading/trailing whitespace. Non-string inputs return None
    rather than raise — the caller is usually prompt input.
    """
    if not isinstance(ccn, str):
        return None
    normalized = ccn.strip()
    if not normalized:
        return None
    normalized = normalized.zfill(6)
    df = _get_hcris_cached()
    hits = df[df["ccn"] == normalized]
    if year is not None:
        hits = hits[hits["fiscal_year"] == int(year)]
    if hits.empty:
        return None
    if "fiscal_year" in hits.columns and len(hits) > 1:
        hits = hits.sort_values("fiscal_year", ascending=False)
    return _row_to_dict(hits.iloc[0])


def get_trend(
    ccn: str,
    metrics: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Return a per-fiscal-year DataFrame for ``ccn`` with selected metrics.

    Useful for "how has this target trended?" diligence questions. Columns
    are always ``ccn``, ``name``, ``fiscal_year`` + requested metrics. If
    ``metrics`` is None, a sensible default set is returned (financial +
    volume + payer mix).

    Returns an empty DataFrame if the CCN has no filings in the shipped
    dataset or if the shipped dataset only has one fiscal year.
    """
    if not isinstance(ccn, str):
        return pd.DataFrame()
    normalized = ccn.strip().zfill(6) if ccn.strip() else ""
    if not normalized:
        return pd.DataFrame()
    default_metrics = [
        "beds",
        "total_patient_days",
        "medicare_day_pct",
        "medicaid_day_pct",
        "net_patient_revenue",
        "operating_expenses",
        "net_income",
    ]
    metrics = metrics or default_metrics

    df = _get_hcris_cached()
    hits = df[df["ccn"] == normalized]
    if hits.empty:
        return pd.DataFrame()

    keep = ["ccn", "name", "fiscal_year"] + [m for m in metrics if m in hits.columns]
    hits = hits[keep].copy()
    if "fiscal_year" in hits.columns:
        hits = hits.sort_values("fiscal_year")
    return hits.reset_index(drop=True)


# Metric-specific classification rules for trend_signals. Each rule answers:
# "For this metric, does a rise / fall signal concerning, favorable, or neutral?"
# Thresholds are deliberately conservative — a 1 pt move in operating margin
# isn't material; a 3 pt move is.
#
# Format: metric -> (good_direction, magnitude_threshold, threshold_unit)
#   good_direction: "up" | "down" | None (neutral — always classified as neutral)
#   magnitude_threshold: minimum absolute delta to classify non-neutral
#   threshold_unit: "pct" (for pct_change) or "pts" (for pts_change)
_SEVERITY_RULES: Dict[str, Tuple[Optional[str], float, str]] = {
    "net_income":              ("up",   0.10, "pct"),
    "operating_margin":        ("up",   2.0,  "pts"),
    "net_patient_revenue":     ("up",   0.05, "pct"),
    "operating_expenses":      ("down", 0.05, "pct"),
    "cost_per_patient_day":    ("down", 0.05, "pct"),
    "payer_mix_hhi":           ("down", 0.03, "pts"),
    # Payer-mix ratios are direction-neutral — a shift in either direction
    # just reflects business-model change, not inherently good or bad.
    "medicare_day_pct":        (None,   0.0,  "pts"),
    "medicaid_day_pct":        (None,   0.0,  "pts"),
    "non_government_day_pct":  (None,   0.0,  "pts"),
}


def _classify_severity(
    metric: str,
    direction: str,
    pct_change: Optional[float],
    pts_change: Optional[float],
) -> str:
    """Return ``concerning`` | ``favorable`` | ``neutral`` for one signal row."""
    rule = _SEVERITY_RULES.get(metric)
    if rule is None:
        return "neutral"
    good_dir, threshold, unit = rule
    if good_dir is None:
        return "neutral"
    # Magnitude check: classify only if the move is large enough to matter.
    magnitude = abs(pct_change) if unit == "pct" else (
        abs(pts_change / 100.0) if pts_change is not None else 0.0
    )
    if pct_change is None and pts_change is None:
        return "neutral"
    if unit == "pct":
        if pct_change is None or abs(pct_change) < threshold:
            return "neutral"
    else:  # pts
        if pts_change is None or abs(pts_change) < threshold:
            return "neutral"
    return "favorable" if direction == good_dir else "concerning"


def trend_signals(ccn: str) -> pd.DataFrame:
    """Compute first→last fiscal-year deltas for diligence-relevant metrics.

    Returns one row per metric with ``start_year``, ``end_year``,
    ``start_value``, ``end_value``, ``pct_change`` (for money/counts) or
    ``pts_change`` (for ratios), and a ``direction`` hint in
    ``{"up", "down", "flat"}``. Empty DataFrame if the CCN has < 2 fiscal
    years on file.

    Built on :func:`get_trend` so it shares the same default metric set +
    CCN normalization. Consumed by the CLI ``--trend`` block and the bundle.
    """
    df = get_trend(ccn)
    if df.empty or len(df) < 2 or "fiscal_year" not in df.columns:
        return pd.DataFrame()

    first = df.iloc[0]
    last = df.iloc[-1]
    start_year = int(first["fiscal_year"])
    end_year = int(last["fiscal_year"])

    # Metrics split by delta type: ratios reported in percentage-points; raw
    # dollar/count metrics reported as percent change.
    ratio_metrics = {"medicare_day_pct", "medicaid_day_pct",
                     "operating_margin", "non_government_day_pct"}
    # Derive the on-the-fly ratios so they're available for signal computation
    enriched = _add_derived_kpis(df)
    first_enriched = enriched.iloc[0]
    last_enriched = enriched.iloc[-1]

    candidate_metrics = [
        "net_patient_revenue",
        "operating_expenses",
        "net_income",
        "total_patient_days",
        "medicare_day_pct",
        "medicaid_day_pct",
        "non_government_day_pct",
        "operating_margin",
    ]

    rows: List[Dict[str, Any]] = []
    for metric in candidate_metrics:
        if metric not in enriched.columns:
            continue
        s = first_enriched.get(metric)
        e = last_enriched.get(metric)
        if pd.isna(s) or pd.isna(e):
            continue
        s = float(s)
        e = float(e)

        if metric in ratio_metrics:
            pts = (e - s) * 100.0
            pct_change = None
            if abs(pts) < 0.5:
                direction = "flat"
            else:
                direction = "up" if pts > 0 else "down"
        else:
            pts = None
            if s == 0:
                pct_change = None
                direction = "flat"
            else:
                pct_change = (e - s) / abs(s)
                if abs(pct_change) < 0.01:
                    direction = "flat"
                else:
                    direction = "up" if pct_change > 0 else "down"

        severity = _classify_severity(metric, direction, pct_change, pts)
        rows.append({
            "metric": metric,
            "start_year": start_year,
            "end_year": end_year,
            "start_value": s,
            "end_value": e,
            "pct_change": pct_change,
            "pts_change": pts,
            "direction": direction,
            "severity": severity,
        })
    return pd.DataFrame(rows)


def available_fiscal_years() -> List[int]:
    """Return the sorted list of fiscal years present in the shipped dataset."""
    df = _get_hcris_cached()
    if "fiscal_year" not in df.columns or df.empty:
        return []
    return sorted(int(y) for y in df["fiscal_year"].dropna().unique())


def lookup_by_name(
    query: str,
    state: Optional[str] = None,
    limit: int = 10,
    min_query_length: int = 3,
) -> List[Dict[str, Any]]:
    """Fuzzy hospital-name search.

    Two-stage match: case-insensitive substring filter, then rank by
    :class:`difflib.SequenceMatcher` ratio so the best matches come first.
    Optional ``state`` (two-letter USPS code, case-insensitive) scopes the
    result set.

    Returns an empty list if ``query`` is shorter than ``min_query_length``
    or no hospitals match. Result count is capped at ``limit``.
    """
    if not isinstance(query, str):
        return []
    q = query.strip()
    if len(q) < min_query_length:
        return []
    q_up = q.upper()
    # Latest-year-per-CCN so multi-year data doesn't show the same hospital 5 times
    df = _get_latest_per_ccn()
    if state:
        state_up = str(state).strip().upper()
        df = df[df["state"].astype(str).str.upper() == state_up]
    if df.empty:
        return []
    name_up = df["name"].astype(str).str.upper()
    mask = name_up.str.contains(q_up, na=False, regex=False)
    sel = df[mask].copy()
    if sel.empty:
        return []
    # Rank by SequenceMatcher ratio so closer matches sort first.
    sel["_score"] = sel["name"].astype(str).str.upper().apply(
        lambda n: difflib.SequenceMatcher(None, q_up, n).ratio()
    )
    sel = sel.sort_values("_score", ascending=False).drop(columns="_score")
    return [_row_to_dict(r) for _, r in sel.head(int(limit)).iterrows()]


def browse_by_state(
    state: str,
    beds_range: Optional[tuple] = None,
    limit: int = 25,
    sort_by: str = "beds",
) -> List[Dict[str, Any]]:
    """List hospitals in ``state`` (two-letter USPS), optionally filtered by bed size.

    Default sort is by bed count descending so the largest hospitals surface
    first — matches how analysts actually browse when scoping peer sets.
    """
    if not isinstance(state, str) or not state.strip():
        return []
    state_up = state.strip().upper()
    df = _get_latest_per_ccn()
    sel = df[df["state"].astype(str).str.upper() == state_up].copy()
    if beds_range is not None:
        lo, hi = beds_range
        sel = sel[(sel["beds"] >= float(lo)) & (sel["beds"] <= float(hi))]
    if sort_by in sel.columns:
        sel = sel.sort_values(sort_by, ascending=False, na_position="last")
    return [_row_to_dict(r) for _, r in sel.head(int(limit)).iterrows()]


# ── Facility-type classification ───────────────────────────────────────────

# CMS encodes facility type in the *last 4 digits* of the 6-digit CCN.
# Ranges per the CMS Provider Number table; see SSA §1861 / 42 CFR 413.65.
# We bucket for peer filtering — full-fidelity mapping has ~15 sub-types.
_CCN_TYPE_RANGES: List[tuple[int, int, str]] = [
    (   1,  879, "general"),
    (1300, 1399, "critical_access"),
    (2000, 2299, "ltach"),
    (3025, 3099, "rehab"),
    (3300, 3399, "children"),
    (4000, 4499, "psychiatric"),
]

# Name-keyword fallback for cases where the CCN range is ambiguous (e.g.,
# rebranded facilities, absorbed CCNs). Order matters: first match wins.
_NAME_TYPE_HINTS: List[tuple[tuple[str, ...], str]] = [
    (("CHILDREN", "PEDIATRIC"),       "children"),
    (("PSYCHIATRIC", "BEHAVIORAL"),   "psychiatric"),
    (("REHAB",),                      "rehab"),
    (("LTACH", "LONG TERM", "LONG-TERM"), "ltach"),
    (("CRITICAL ACCESS",),            "critical_access"),
]


def classify_hospital_type(ccn: Optional[str], name: Optional[str] = None) -> str:
    """Classify a hospital into a facility-type bucket for peer filtering.

    CCN last-4-digit range is the primary signal (deterministic per CMS).
    Name heuristics are a fallback for CCNs outside documented ranges.

    Returns one of: ``general``, ``children``, ``psychiatric``, ``rehab``,
    ``ltach``, ``critical_access``, ``other``.
    """
    digits = re.sub(r"\D", "", str(ccn or ""))
    if len(digits) >= 4:
        try:
            last4 = int(digits[-4:])
            for lo, hi, label in _CCN_TYPE_RANGES:
                if lo <= last4 <= hi:
                    return label
        except ValueError:
            pass
    if name:
        name_up = str(name).upper()
        for keywords, label in _NAME_TYPE_HINTS:
            if any(k in name_up for k in keywords):
                return label
    return "other"


def _classify_series(ccns: pd.Series, names: pd.Series) -> pd.Series:
    """Vectorized CCN+name classifier. Same output domain as :func:`classify_hospital_type`."""
    ccn_str = ccns.astype(str)
    last4 = pd.to_numeric(ccn_str.str.extract(r"(\d{4})$", expand=False), errors="coerce")
    out = pd.Series(["other"] * len(ccns), index=ccns.index, dtype=object)
    for lo, hi, label in _CCN_TYPE_RANGES:
        out = out.mask((last4 >= lo) & (last4 <= hi), label)
    # Name fallback only where CCN classification fell through to "other"
    still_other = out == "other"
    if still_other.any() and names is not None:
        name_up = names.astype(str).str.upper()
        for keywords, label in _NAME_TYPE_HINTS:
            pattern = "|".join(re.escape(k) for k in keywords)
            hit = name_up.str.contains(pattern, na=False, regex=True)
            out = out.mask(still_other & hit, label)
            still_other = out == "other"
    return out


# ── Peer matching ──────────────────────────────────────────────────────────

# Weights on the composite similarity score. Hand-picked to balance the three
# dimensions of hospital "similarity" that matter in diligence context:
# size (beds), financial scale (NPSR), and payer mix (Medicare share).
_PEER_WEIGHT_BEDS = 0.5
_PEER_WEIGHT_NPSR = 0.3
_PEER_WEIGHT_MEDICARE_MIX = 0.2


def _log_ratio_distance(series: pd.Series, target: Optional[float]) -> pd.Series:
    """Dimensionless ``|log(series / target)|``, NaN-safe.

    Handles the three-orders-of-magnitude spread of hospital NPSR ($50M rural
    CAH vs $20B academic medical center) by working in log space.
    """
    if target is None or target <= 0:
        return pd.Series([float("nan")] * len(series), index=series.index)
    positive = series.where(series > 0, other=np.nan)
    return (np.log(positive) - np.log(target)).abs()


def find_peers(
    ccn: str,
    n: int = 15,
    same_state_preferred: bool = True,
    exclude_specialty_mismatch: bool = True,
) -> pd.DataFrame:
    """Return the ``n`` HCRIS peers most similar to the target hospital.

    Similarity is a weighted, dimensionless sum of three distances:

    - **beds** (``|peer - target| / target``) — size mismatch as relative %
    - **NPSR** (``|log(peer/target)|``) — scale mismatch on log scale
    - **Medicare day %** (``|peer - target|``) — payer-mix mismatch

    Selection strategy:

    1. Candidate pool = all hospitals except the target, with a reported
       bed count (rows without beds can't be ranked on size).
    2. If ``exclude_specialty_mismatch`` (default), drop candidates whose
       facility type (children's, psychiatric, rehab, LTACH, critical-access)
       differs from the target's. Children's hospitals distort peer stats
       for adult AMCs; applied symmetrically in either direction.
    3. If ``same_state_preferred`` and the target's state has ≥ ``n``
       candidates, scope to that state.
    4. Rank by ascending ``similarity_score`` (lower = closer peer).
    5. Return top ``n``. Result includes a ``similarity_score`` column so
       callers can show or cap on it.

    Raises :class:`ValueError` if the target CCN is absent or has no beds.
    """
    df = _get_latest_per_ccn()
    target_rows = df[df["ccn"] == ccn]
    if target_rows.empty:
        raise ValueError(f"CCN {ccn!r} not found in HCRIS data")
    t = target_rows.iloc[0]

    t_beds = t.get("beds")
    if pd.isna(t_beds) or t_beds <= 0:
        raise ValueError(f"Target CCN {ccn!r} has no bed count; cannot match peers")
    t_beds = float(t_beds)
    t_npsr = float(t["net_patient_revenue"]) if pd.notna(t.get("net_patient_revenue")) else None
    t_mcr = float(t["medicare_day_pct"]) if pd.notna(t.get("medicare_day_pct")) else None
    t_state = t.get("state")
    t_type = classify_hospital_type(ccn, t.get("name"))

    # Candidate pool: exclude target, require valid bed count for ranking
    candidates = df[df["ccn"] != ccn].copy()
    candidates = candidates[candidates["beds"].notna() & (candidates["beds"] > 0)]

    # Specialty-type filter: match the target's facility type so children's /
    # psychiatric / rehab / LTACH / CAH don't pollute an adult-AMC peer set.
    if exclude_specialty_mismatch and not candidates.empty:
        cand_types = _classify_series(candidates["ccn"], candidates.get("name", pd.Series(dtype=object)))
        candidates = candidates[cand_types == t_type]

    # Tier 1: same-state preference, if the pool is big enough
    if same_state_preferred and isinstance(t_state, str) and t_state:
        in_state = candidates[candidates["state"] == t_state]
        if len(in_state) >= n:
            candidates = in_state

    if candidates.empty:
        return candidates.assign(similarity_score=pd.Series(dtype=float))

    # Three dimensionless distances; NaNs get a "distant but not infinite" fill
    # so partial-data peers aren't ranked above complete-data ones.
    bed_dist = (candidates["beds"] - t_beds).abs() / t_beds
    npsr_dist = _log_ratio_distance(candidates["net_patient_revenue"], t_npsr)
    mcr_dist = (candidates["medicare_day_pct"] - t_mcr).abs() if t_mcr is not None else pd.Series(
        [0.0] * len(candidates), index=candidates.index,
    )

    candidates["similarity_score"] = (
        _PEER_WEIGHT_BEDS * bed_dist.fillna(2.0)
        + _PEER_WEIGHT_NPSR * (npsr_dist.fillna(2.0) if t_npsr else 0.0)
        + _PEER_WEIGHT_MEDICARE_MIX * mcr_dist.fillna(0.3)
    )
    return candidates.nsmallest(int(n), "similarity_score").reset_index(drop=True)


# KPIs we score the target against peers for. Ordered by partner-interest:
# raw scale first, then mix, then the derived ratios that actually drive
# diligence (operating margin is the headline metric for a buy-side IC).
PEER_PERCENTILE_KPIS: List[str] = [
    "net_patient_revenue",
    "beds",
    "total_patient_days",
    "medicare_day_pct",
    "medicaid_day_pct",
    "non_government_day_pct",
    "payer_mix_hhi",
    "operating_expenses",
    "net_income",
    "operating_margin",
    "cost_per_patient_day",
    "npsr_per_bed",
]

# Derived KPIs computed as ratios of shipped HCRIS fields. Kept out of the
# parquet so the base schema stays small; materialized on demand inside
# peer-percentile computation.
DERIVED_KPI_FORMULAS: Dict[str, tuple] = {
    "operating_margin":       ("net_income",          "net_patient_revenue"),
    "cost_per_patient_day":   ("operating_expenses",  "total_patient_days"),
    "npsr_per_bed":           ("net_patient_revenue", "beds"),
}


def _add_derived_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with derived-KPI columns added.

    Division-by-zero and NaN-in-denominator both yield NaN (not Inf) so the
    downstream ``pd.to_numeric(...).dropna()`` filter drops them cleanly.
    """
    out = df.copy()
    for kpi, (num, den) in DERIVED_KPI_FORMULAS.items():
        if num in out.columns and den in out.columns:
            n = pd.to_numeric(out[num], errors="coerce")
            d = pd.to_numeric(out[den], errors="coerce")
            # Replace zero denominators with NaN so division yields NaN
            out[kpi] = n / d.where(d != 0)
    # Non-government (commercial + self-pay + other) day share.
    # Residual of Medicare + Medicaid; clipped to [0, 1] because some HCRIS
    # filings have allocation quirks that push the residual slightly negative.
    if "medicare_day_pct" in out.columns and "medicaid_day_pct" in out.columns:
        mcr = pd.to_numeric(out["medicare_day_pct"], errors="coerce")
        mcd = pd.to_numeric(out["medicaid_day_pct"], errors="coerce")
        out["non_government_day_pct"] = (1.0 - mcr - mcd).clip(lower=0.0, upper=1.0)
        # Herfindahl on the three-bucket payer mix. 1/3 ≈ perfectly diversified,
        # 1.0 = one bucket dominates all days. >0.5 flags concentration risk.
        non_gov = out["non_government_day_pct"]
        out["payer_mix_hhi"] = (mcr ** 2) + (mcd ** 2) + (non_gov ** 2)
    return out


def compute_peer_percentiles(
    target_ccn: str,
    peers: pd.DataFrame,
    kpis: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Return a small DataFrame of ``{kpi, target, peer_median, peer_p10, peer_p90,
    target_percentile}`` — one row per KPI.

    ``target_percentile`` is the target's percent-rank among the peer set on
    each KPI (0-100). NaN if the target or all peers lack the field.

    Derived KPIs (``operating_margin``, ``cost_per_patient_day``,
    ``npsr_per_bed``) are materialized on the fly from the base HCRIS fields.
    """
    df = _get_latest_per_ccn()
    target_rows = df[df["ccn"] == target_ccn]
    if target_rows.empty:
        raise ValueError(f"CCN {target_ccn!r} not found in HCRIS data")
    # Materialize derived KPIs on both sides so target + peer rows line up
    t = _add_derived_kpis(target_rows).iloc[0]
    peers = _add_derived_kpis(peers)
    kpis = kpis or PEER_PERCENTILE_KPIS

    rows = []
    for kpi in kpis:
        if kpi not in peers.columns:
            continue
        peer_vals = pd.to_numeric(peers[kpi], errors="coerce").dropna()
        target_val = pd.to_numeric(pd.Series([t.get(kpi)]), errors="coerce").iloc[0]
        if peer_vals.empty or pd.isna(target_val):
            pct = float("nan")
            p10 = p50 = p90 = float("nan")
        else:
            # Target's percentile rank among peers: share of peers below target.
            pct = (peer_vals < target_val).mean() * 100.0
            p10 = float(peer_vals.quantile(0.10))
            p50 = float(peer_vals.quantile(0.50))
            p90 = float(peer_vals.quantile(0.90))
        rows.append({
            "kpi": kpi,
            "target": float(target_val) if pd.notna(target_val) else float("nan"),
            "peer_p10": p10,
            "peer_median": p50,
            "peer_p90": p90,
            "target_percentile": pct,
        })
    return pd.DataFrame(rows)


# ── Dataset diagnostics ────────────────────────────────────────────────────

def dataset_info(path: Optional[Path] = None) -> Dict[str, Any]:
    """Return a summary of the shipped HCRIS dataset for audit-defensibility.

    Keys: ``path``, ``exists``, ``size_bytes``, ``modified_iso``, ``rows``,
    ``unique_ccns``, ``fiscal_years``, ``top_states``. Every value is
    JSON-serializable; missing file returns ``exists=False`` with zero/empty
    values so partners can diff across environments safely.
    """
    from datetime import datetime, timezone

    p = Path(path) if path else DEFAULT_DATA_PATH
    info: Dict[str, Any] = {
        "path": str(p),
        "exists": p.is_file(),
        "size_bytes": 0,
        "modified_iso": None,
        "rows": 0,
        "unique_ccns": 0,
        "fiscal_years": [],
        "top_states": [],
    }
    if not p.is_file():
        return info

    stat = p.stat()
    info["size_bytes"] = int(stat.st_size)
    info["modified_iso"] = datetime.fromtimestamp(
        stat.st_mtime, tz=timezone.utc
    ).isoformat(timespec="seconds")

    df = load_hcris(p)
    info["rows"] = int(len(df))
    info["unique_ccns"] = int(df["ccn"].nunique()) if "ccn" in df.columns else 0
    if "fiscal_year" in df.columns:
        years = sorted({int(y) for y in df["fiscal_year"].dropna().unique()})
        info["fiscal_years"] = years
    if "state" in df.columns:
        # Latest row per CCN so a hospital with 3 years of data counts once
        latest = _latest_row_per_ccn(df)
        counts = latest["state"].dropna().astype(str).str.upper().value_counts().head(5)
        info["top_states"] = [(s, int(c)) for s, c in counts.items()]
    return info


def _format_dataset_info(info: Dict[str, Any]) -> str:
    """Render :func:`dataset_info` output as a terminal-friendly block."""
    if not info.get("exists"):
        return f"HCRIS dataset NOT FOUND at {info['path']}\nRun `rcm-mc hcris refresh` to build it."

    size_mb = info["size_bytes"] / (1024 * 1024)
    years = info["fiscal_years"]
    years_span = (
        f"{years[0]}–{years[-1]} ({len(years)} year{'s' if len(years) != 1 else ''})"
        if years else "none"
    )
    lines = [
        f"HCRIS dataset — {info['path']}",
        "─" * 60,
        f"  Size:           {size_mb:.2f} MB",
        f"  Last modified:  {info['modified_iso']}",
        f"  Rows:           {info['rows']:,}",
        f"  Unique CCNs:    {info['unique_ccns']:,}",
        f"  Fiscal years:   {years_span}",
    ]
    if info["top_states"]:
        top = ", ".join(f"{s} ({c})" for s, c in info["top_states"])
        lines.append(f"  Top 5 states:   {top}")
    return "\n".join(lines)


# ── CLI entry: `python -m rcm_mc.hcris refresh --year 2022` ─────────────────

def _main(argv: Optional[list[str]] = None, prog: str = "rcm_mc.hcris") -> int:
    ap = argparse.ArgumentParser(prog=prog)
    sub = ap.add_subparsers(dest="cmd", required=True)

    refresh = sub.add_parser("refresh", help="Download + parse CMS HCRIS → parquet")
    refresh.add_argument("--year", type=int, default=2022, help="CMS fiscal year (default 2022)")
    refresh.add_argument("--out", type=Path, default=None, help="Output parquet path")
    refresh.add_argument("--source-zip", type=Path, default=None,
                         help="Pre-downloaded HOSP10FY{Y}.zip (skip network)")

    info_p = sub.add_parser("info", help="Show shipped HCRIS dataset diagnostics")
    info_p.add_argument("--path", type=Path, default=None,
                        help="Alternate HCRIS CSV path (defaults to shipped bundle)")
    info_p.add_argument("--json", action="store_true",
                        help="Emit the info payload as JSON")

    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "refresh":
        path = refresh_hcris(year=args.year, out_path=args.out, source_zip=args.source_zip)
        print(f"Wrote {path}")
        return 0

    if args.cmd == "info":
        import json as _json
        info = dataset_info(args.path)
        if args.json:
            print(_json.dumps(info, indent=2, default=str))
        else:
            print(_format_dataset_info(info))
        return 0 if info.get("exists") else 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(_main())

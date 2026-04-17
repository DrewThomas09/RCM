from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml

from ._calib_schema import (
    _classify_denial_reason,
    _clean_currency,
    _enhanced_payer_name,
    _first_matching_col,
    _map_stage,
    _to_datetime_safe,
)
from ._calib_stats import (
    _beta_posterior_mean_sd,
    _smooth_shares,
    _top_n_with_other,
)
from ..infra.logger import logger
from ..data.sources import mark_observed


class CalibrationError(ValueError):
    pass


# ── Step 16: Data quality report on ingestion ──────────────────────────────

@dataclass
class DataQualityReport:
    """Audit trail of what data was loaded and its quality."""
    files_loaded: Dict[str, str] = field(default_factory=dict)
    row_counts: Dict[str, int] = field(default_factory=dict)
    null_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    duplicate_counts: Dict[str, int] = field(default_factory=dict)
    payer_names_found: Dict[str, List[str]] = field(default_factory=dict)
    date_ranges: Dict[str, Dict[str, str]] = field(default_factory=dict)
    schema_match_scores: Dict[str, float] = field(default_factory=dict)
    encoding_used: Dict[str, str] = field(default_factory=dict)
    delimiter_used: Dict[str, str] = field(default_factory=dict)
    rejected_row_counts: Dict[str, int] = field(default_factory=dict)
    column_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)
    payer_alias_mappings: Dict[str, str] = field(default_factory=dict)
    calibrated_parameters: Dict[str, List[str]] = field(default_factory=dict)
    uncalibrated_parameters: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_loaded": self.files_loaded,
            "row_counts": self.row_counts,
            "null_counts": self.null_counts,
            "duplicate_counts": self.duplicate_counts,
            "payer_names_found": self.payer_names_found,
            "date_ranges": self.date_ranges,
            "schema_match_scores": self.schema_match_scores,
            "encoding_used": self.encoding_used,
            "delimiter_used": self.delimiter_used,
            "rejected_row_counts": self.rejected_row_counts,
            "column_mappings": self.column_mappings,
            "payer_alias_mappings": self.payer_alias_mappings,
            "calibrated_parameters": self.calibrated_parameters,
            "uncalibrated_parameters": self.uncalibrated_parameters,
        }

    def write_json(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


# ── Step 30: Data dictionary generation ────────────────────────────────────

@dataclass
class DataDictionary:
    """Self-documenting dictionary of loaded data."""
    columns: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"columns": self.columns}

    def write_json(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


def _build_data_dictionary(dfs: Dict[str, pd.DataFrame]) -> DataDictionary:
    """Generate a data dictionary from loaded DataFrames."""
    dd = DataDictionary()
    for source_name, df in dfs.items():
        if df is None or df.empty:
            continue
        for col in df.columns:
            entry: Dict[str, Any] = {
                "source": source_name,
                "name": col,
                "dtype": str(df[col].dtype),
                "null_rate": float(df[col].isna().mean()),
                "unique_count": int(df[col].nunique()),
            }
            if pd.api.types.is_numeric_dtype(df[col]):
                vals = df[col].dropna()
                if len(vals) > 0:
                    entry["min"] = float(vals.min())
                    entry["max"] = float(vals.max())
                    entry["mean"] = float(vals.mean())
                    entry["sample_values"] = [float(v) for v in vals.head(3).tolist()]
            else:
                vals = df[col].dropna().astype(str)
                if len(vals) > 0:
                    entry["sample_values"] = vals.head(5).tolist()
            dd.columns.append(entry)
    return dd


# ── CSV encoding detection (Step 21) ───────────────────────────────────────

_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

def _detect_encoding(path: str) -> str:
    """Try multiple encodings and return the first that works."""
    for enc in _ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(8192)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


# ── Step 27: Delimiter detection ───────────────────────────────────────────

def _detect_delimiter(path: str, encoding: str = "utf-8") -> str:
    """Detect delimiter by reading first 5 lines."""
    try:
        with open(path, "r", encoding=encoding) as f:
            lines = [f.readline() for _ in range(5)]
        sample = "".join(lines)
        counts = {"|": sample.count("|"), "\t": sample.count("\t"), ",": sample.count(",")}
        best = max(counts, key=counts.get)
        if counts[best] > 0:
            return best
    except Exception:
        pass
    return ","


@dataclass
class DataPackage:
    claims_summary: Optional[pd.DataFrame] = None
    denials: Optional[pd.DataFrame] = None
    ar_aging: Optional[pd.DataFrame] = None
    quality: Optional[DataQualityReport] = None
    dictionary: Optional[DataDictionary] = None


def _read_file(path: str, quality: DataQualityReport) -> Optional[pd.DataFrame]:
    """Read CSV or Excel with encoding/delimiter detection (Steps 20, 21, 27)."""
    if not os.path.exists(path):
        return None

    fname = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()

    if ext in (".xlsx", ".xls"):
        try:
            df = pd.read_excel(path)
            quality.files_loaded[fname] = path
            logger.info("Loaded Excel file: %s (%d rows)", fname, len(df))
            return df
        except Exception as e:
            logger.warning("Failed to read Excel file %s: %s", path, e)
            return None

    encoding = _detect_encoding(path)
    quality.encoding_used[fname] = encoding
    delimiter = _detect_delimiter(path, encoding)
    quality.delimiter_used[fname] = delimiter
    logger.info("Reading %s with encoding=%s, delimiter=%r", fname, encoding, delimiter)

    try:
        df = pd.read_csv(path, encoding=encoding, sep=delimiter)
        quality.files_loaded[fname] = path
        return df
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None


def _find_data_file(data_dir: str, base_names: List[str]) -> Optional[str]:
    """Find a data file by trying multiple base names and extensions."""
    extensions = [".csv", ".xlsx", ".xls", ".tsv", ".txt"]
    for base in base_names:
        for ext in extensions:
            path = os.path.join(data_dir, base + ext)
            if os.path.exists(path):
                return path
    return None


def load_data_package(
    data_dir: str,
    quality: Optional[DataQualityReport] = None,
) -> DataPackage:
    """Load a diligence data package from a directory.

    Supports CSV, Excel, pipe/tab-delimited files with auto-detection.
    """
    if not data_dir:
        raise CalibrationError("data_dir is required")
    if not os.path.isdir(data_dir):
        raise CalibrationError(f"Data package directory not found: {data_dir}")

    if quality is None:
        quality = DataQualityReport()

    claims_path = _find_data_file(data_dir, ["claims_summary", "claims", "revenue_summary"])
    denials_path = _find_data_file(data_dir, ["denials", "denial_detail", "denial_data", "denial_export"])
    ar_path = _find_data_file(data_dir, ["ar_aging", "aging", "ar_summary", "ar_detail"])

    claims_df = _read_file(claims_path, quality) if claims_path else None
    denials_df = _read_file(denials_path, quality) if denials_path else None
    ar_df = _read_file(ar_path, quality) if ar_path else None

    for name, df in [("claims_summary", claims_df), ("denials", denials_df), ("ar_aging", ar_df)]:
        if df is not None:
            quality.row_counts[name] = len(df)
            quality.null_counts[name] = {c: int(df[c].isna().sum()) for c in df.columns}

    dfs = {}
    if claims_df is not None:
        dfs["claims_summary"] = claims_df
    if denials_df is not None:
        dfs["denials"] = denials_df
    if ar_df is not None:
        dfs["ar_aging"] = ar_df
    dictionary = _build_data_dictionary(dfs)

    return DataPackage(
        claims_summary=claims_df,
        denials=denials_df,
        ar_aging=ar_df,
        quality=quality,
        dictionary=dictionary,
    )


def load_multiple_data_dirs(
    data_dirs: Sequence[str],
) -> DataPackage:
    """Load and merge data from multiple directories (Step 29)."""
    quality = DataQualityReport()
    merged_claims: List[pd.DataFrame] = []
    merged_denials: List[pd.DataFrame] = []
    merged_ar: List[pd.DataFrame] = []

    for d in data_dirs:
        pkg = load_data_package(d.strip(), quality=quality)
        if pkg.claims_summary is not None:
            merged_claims.append(pkg.claims_summary)
        if pkg.denials is not None:
            merged_denials.append(pkg.denials)
        if pkg.ar_aging is not None:
            merged_ar.append(pkg.ar_aging)

    claims = pd.concat(merged_claims, ignore_index=True) if merged_claims else None
    denials = pd.concat(merged_denials, ignore_index=True) if merged_denials else None
    ar = pd.concat(merged_ar, ignore_index=True) if merged_ar else None

    dfs = {}
    if claims is not None:
        dfs["claims_summary"] = claims
    if denials is not None:
        dfs["denials"] = denials
    if ar is not None:
        dfs["ar_aging"] = ar

    return DataPackage(
        claims_summary=claims,
        denials=denials,
        ar_aging=ar,
        quality=quality,
        dictionary=_build_data_dictionary(dfs),
    )


def _standardize_claims_summary(
    df: pd.DataFrame,
    quality: Optional[DataQualityReport] = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["payer", "net_revenue", "claim_count"])

    payer_col = _first_matching_col(df, ["payer", "payor", "payer_name", "payor_name", "financial_class", "fin_class"])
    rev_col = _first_matching_col(df, ["net_revenue", "revenue", "netpatientrevenue", "paid_amount", "payments", "allowed_amount"])
    cnt_col = _first_matching_col(df, ["claim_count", "claims", "num_claims", "count", "claimcnt"])

    if payer_col is None or rev_col is None:
        raise CalibrationError("claims_summary must include payer and net_revenue (or equivalent) columns")

    if quality:
        quality.column_mappings["claims_summary"] = {"payer": payer_col, "net_revenue": rev_col}
        if cnt_col:
            quality.column_mappings["claims_summary"]["claim_count"] = cnt_col

    out = pd.DataFrame({
        "payer": df[payer_col].map(_enhanced_payer_name),
        "net_revenue": _clean_currency(df[rev_col]),
    })
    if cnt_col is not None:
        out["claim_count"] = _clean_currency(df[cnt_col])
    else:
        out["claim_count"] = np.nan

    if quality:
        raw_payers = df[payer_col].dropna().unique().tolist()
        mapped_payers = out["payer"].dropna().unique().tolist()
        quality.payer_names_found["claims_summary"] = [str(p) for p in raw_payers]
        for raw, mapped in zip(raw_payers, df[payer_col].map(_enhanced_payer_name).tolist()):
            if str(raw) != str(mapped):
                quality.payer_alias_mappings[str(raw)] = str(mapped)

    out = out.dropna(subset=["payer", "net_revenue"])
    out = out.groupby("payer", as_index=False).agg({"net_revenue": "sum", "claim_count": "sum"})
    return out


def _standardize_denials(
    df: pd.DataFrame,
    quality: Optional[DataQualityReport] = None,
) -> pd.DataFrame:
    empty_cols = [
        "payer", "claim_id", "denial_amount", "writeoff_amount", "stage", "denial_reason", "denial_category",
        "denial_date", "resolved_date", "days_to_resolve", "final_status",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=empty_cols)

    payer_col = _first_matching_col(df, ["payer", "payor", "payer_name", "payor_name", "financial_class", "fin_class"])
    claim_col = _first_matching_col(df, ["claim_id", "claim", "encounter", "account", "patient_account", "visit_id"])
    denial_amt_col = _first_matching_col(df, ["denial_amount", "denied_amount", "amount_denied", "denial_dollars", "denied_amt", "amt_denied"])
    wo_amt_col = _first_matching_col(df, ["writeoff_amount", "write_off", "writeoff", "payer_writeoff", "denial_writeoff", "wo_amount"])
    paid_amt_col = _first_matching_col(df, ["paid_amount", "reimbursement", "payments", "allowed_amount"])
    stage_col = _first_matching_col(df, ["appeal_level", "appeal_stage", "stage", "level", "denial_stage"])
    reason_col = _first_matching_col(df, ["denial_reason", "reason", "denial_reason_desc", "reason_desc", "remark", "carc_rarc"])
    category_col = _first_matching_col(df, ["denial_category", "category", "denial_type", "type"])
    status_col = _first_matching_col(df, ["final_status", "status", "resolution", "outcome"])
    denial_date_col = _first_matching_col(df, ["denial_date", "date_denied", "denied_date", "created_date", "create_date"])
    resolved_date_col = _first_matching_col(df, ["resolved_date", "close_date", "date_resolved", "finalized_date", "resolution_date"])
    days_col = _first_matching_col(df, ["days_to_resolve", "resolution_days", "days", "age_days"])

    if payer_col is None:
        raise CalibrationError("denials data must include payer (or equivalent) column")
    if denial_amt_col is None:
        raise CalibrationError("denials data must include denial_amount (or equivalent) column")

    if quality:
        quality.column_mappings["denials"] = {"payer": payer_col, "denial_amount": denial_amt_col}
        if wo_amt_col:
            quality.column_mappings["denials"]["writeoff_amount"] = wo_amt_col
        if claim_col:
            quality.column_mappings["denials"]["claim_id"] = claim_col

    out = pd.DataFrame({
        "payer": df[payer_col].map(_enhanced_payer_name),
        "denial_amount": _clean_currency(df[denial_amt_col]),
    })
    out["claim_id"] = df[claim_col] if claim_col is not None else pd.Series([np.nan] * len(df))
    out["stage"] = df[stage_col].map(_map_stage) if stage_col is not None else "L1"
    out["denial_reason"] = df[reason_col] if reason_col is not None else ""
    out["denial_category"] = df[category_col] if category_col is not None else ""
    out["final_status"] = df[status_col] if status_col is not None else ""

    # Step 19: Multiple fallback strategies for writeoff_amount
    if wo_amt_col is not None:
        out["writeoff_amount"] = _clean_currency(df[wo_amt_col])
        logger.info("Using explicit writeoff_amount column: %s", wo_amt_col)
    else:
        status = out["final_status"].astype(str).str.lower()
        is_wo_status = (
            status.str.contains("write", na=False) |
            status.str.contains("denied", na=False) |
            status.str.contains("noncover", na=False) |
            status.str.contains("closed", na=False)
        )

        resolution_col = _first_matching_col(df, ["resolution", "outcome", "resolution_status"])
        if resolution_col is not None:
            res = df[resolution_col].astype(str).str.lower()
            is_wo_resolution = (
                res.str.contains("write", na=False) |
                res.str.contains("denied", na=False) |
                res.str.contains("closed no pay", na=False)
            )
            is_wo_status = is_wo_status | is_wo_resolution

        if paid_amt_col is not None:
            paid = _clean_currency(df[paid_amt_col]).fillna(0)
            inferred = out["denial_amount"] - paid
            inferred = inferred.clip(lower=0)
            wo_from_paid = inferred.where(paid < out["denial_amount"], 0.0)
            out["writeoff_amount"] = np.where(
                is_wo_status,
                out["denial_amount"],
                wo_from_paid,
            )
            logger.info("Inferred writeoff from paid_amount column: %s", paid_amt_col)
        else:
            out["writeoff_amount"] = np.where(is_wo_status, out["denial_amount"], 0.0)
            logger.info("Inferred writeoff from status keywords only (no paid_amount column)")

    # Date handling (Step 24)
    if days_col is not None:
        out["days_to_resolve"] = pd.to_numeric(df[days_col], errors="coerce")
    else:
        out["days_to_resolve"] = np.nan
        if denial_date_col is not None and resolved_date_col is not None:
            dd = _to_datetime_safe(df[denial_date_col])
            rd = _to_datetime_safe(df[resolved_date_col])
            out["denial_date"] = dd
            out["resolved_date"] = rd
            out["days_to_resolve"] = (rd - dd).dt.days
            if quality:
                valid_dates = dd.dropna()
                if len(valid_dates) > 0:
                    quality.date_ranges["denials"] = {
                        "min": str(valid_dates.min()),
                        "max": str(valid_dates.max()),
                    }
        else:
            out["denial_date"] = pd.NaT
            out["resolved_date"] = pd.NaT

    # Category: use explicit if present, else classify from reason
    cat = out["denial_category"].astype(str).str.strip()
    cat = cat.where(cat != "", other=pd.NA)
    out["denial_category"] = cat
    out["denial_category"] = out["denial_category"].fillna(out["denial_reason"].map(_classify_denial_reason))
    out["denial_category"] = out["denial_category"].map(lambda x: str(x).strip().lower() if x is not None else "other")
    out.loc[out["denial_category"].eq(""), "denial_category"] = "other"

    if quality:
        raw_payers = df[payer_col].dropna().unique().tolist()
        quality.payer_names_found["denials"] = [str(p) for p in raw_payers]
        for raw in raw_payers:
            mapped = _enhanced_payer_name(str(raw))
            if str(raw) != mapped:
                quality.payer_alias_mappings[str(raw)] = mapped

    # Step 22: Handle duplicates
    n_before = len(out)
    if claim_col is not None and out["claim_id"].notna().any():
        out = out.drop_duplicates(subset=["payer", "claim_id", "denial_amount", "stage", "denial_category"], keep="first")
        n_deduped = n_before - len(out)
        if n_deduped > 0:
            logger.info("Removed %d duplicate denial rows (by claim_id)", n_deduped)
            if quality:
                quality.duplicate_counts["denials"] = n_deduped
    else:
        logger.info("No claim_id column found; skipping deduplication to avoid data loss")

    # Step 28: Row-level validation
    valid_mask = (
        out["payer"].notna() &
        out["denial_amount"].notna() &
        (out["denial_amount"] > 0)
    )
    n_rejected = int((~valid_mask).sum())
    if n_rejected > 0:
        logger.warning("Rejected %d denial rows with null payer or non-positive amount", n_rejected)
        if quality:
            quality.rejected_row_counts["denials"] = n_rejected
    out = out[valid_mask].reset_index(drop=True)

    return out


def _standardize_ar_aging(
    df: pd.DataFrame,
    quality: Optional[DataQualityReport] = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["payer", "ar_amount"])

    payer_col = _first_matching_col(df, ["payer", "payor", "payer_name", "payor_name", "financial_class", "fin_class"])
    amt_col = _first_matching_col(df, ["ar_amount", "amount", "balance", "ar_balance", "ending_ar"])

    if payer_col is None or amt_col is None:
        raise CalibrationError("ar_aging data must include payer and ar_amount (or equivalent) columns")

    if quality:
        quality.column_mappings["ar_aging"] = {"payer": payer_col, "ar_amount": amt_col}

    out = pd.DataFrame({
        "payer": df[payer_col].map(_enhanced_payer_name),
        "ar_amount": _clean_currency(df[amt_col]),
    }).dropna(subset=["payer", "ar_amount"])
    out = out.groupby("payer", as_index=False).agg({"ar_amount": "sum"})
    return out


def calibrate_config(
    base_cfg: Dict[str, Any],
    data_dir: str,
    *,
    max_denial_types: int = 6,
    stage_prior_strength: float = 200.0,
    denial_type_prior_strength: float = 300.0,
    overdispersion: float = 1.15,
    data_dirs: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Calibrate a config using a diligence data package.

    This function is intentionally conservative:
    - If a dataset is missing, it updates nothing for that component.
    - It smooths observations toward the existing config priors.
    - It clamps rates into the min/max already present in the config.

    Supports multiple data directories via data_dirs parameter (Step 29).
    """
    quality = DataQualityReport()

    if data_dirs and len(data_dirs) > 0:
        pkg = load_multiple_data_dirs(data_dirs)
        quality = pkg.quality or quality
    else:
        pkg = load_data_package(data_dir, quality=quality)

    claims = _standardize_claims_summary(pkg.claims_summary, quality) if pkg.claims_summary is not None else pd.DataFrame()
    denials = _standardize_denials(pkg.denials, quality) if pkg.denials is not None else pd.DataFrame()
    ar = _standardize_ar_aging(pkg.ar_aging, quality) if pkg.ar_aging is not None else pd.DataFrame()

    cfg = yaml.safe_load(yaml.safe_dump(base_cfg))  # deep copy, YAML-safe

    # Claims summary -> payer mix + avg claim
    claims_by_payer = {}
    if not claims.empty:
        total_rev = float(claims["net_revenue"].sum())
        for _, r in claims.iterrows():
            payer = str(r["payer"])
            rev = float(r["net_revenue"])
            cnt = float(r["claim_count"]) if pd.notna(r["claim_count"]) and float(r["claim_count"]) > 0 else np.nan
            claims_by_payer[payer] = {"net_revenue": rev, "claim_count": cnt}
        # Step 26: Revenue share auto-inference with 3pp threshold
        if total_rev > 0:
            for payer, pconf in cfg.get("payers", {}).items():
                if payer in claims_by_payer:
                    observed_share = float(claims_by_payer[payer]["net_revenue"] / total_rev)
                    config_share = float(pconf.get("revenue_share", 0.0))
                    delta = abs(observed_share - config_share)
                    if delta > 0.03:
                        logger.info("Payer %s revenue_share: config=%.3f, observed=%.3f (delta=%.3f > 3pp, updating)",
                                    payer, config_share, observed_share, delta)
                        cfg["payers"][payer]["revenue_share"] = observed_share
                        mark_observed(cfg, f"payers.{payer}.revenue_share",
                                      note=f"from claims_summary (observed share {observed_share:.3f})")
                    if pd.notna(claims_by_payer[payer]["claim_count"]):
                        cfg["payers"][payer]["avg_claim_dollars"] = float(
                            claims_by_payer[payer]["net_revenue"] / max(claims_by_payer[payer]["claim_count"], 1.0)
                        )
                        mark_observed(cfg, f"payers.{payer}.avg_claim_dollars",
                                      note=f"from claims_summary (n_claims={int(claims_by_payer[payer]['claim_count'])})")
            share_sum = sum(float(cfg["payers"][p]["revenue_share"]) for p in cfg["payers"])
            if share_sum > 1e-9:
                for p in cfg["payers"]:
                    cfg["payers"][p]["revenue_share"] = float(cfg["payers"][p]["revenue_share"] / share_sum)

    # Denials -> IDR, FWR, stage mix, denial type mix, and stage days
    denials_by_payer = {}
    if not denials.empty:
        # Optional dedup by claim_id
        d = denials.copy()
        if "claim_id" in d.columns and d["claim_id"].notna().any():
            d = d.drop_duplicates(subset=["payer", "claim_id", "denial_amount", "stage", "denial_category"], keep="first")

        for payer, g in d.groupby("payer"):
            denied_dollars = float(g["denial_amount"].sum())
            writeoff_dollars = float(pd.to_numeric(g["writeoff_amount"], errors="coerce").fillna(0.0).sum())
            denial_cases = int(len(g))

            stage_counts = g["stage"].value_counts().to_dict()
            stage_counts = {str(k): float(v) for k, v in stage_counts.items()}
            # Ensure keys
            for k in ("L1", "L2", "L3"):
                stage_counts.setdefault(k, 0.0)

            # Category counts
            cat_counts = g["denial_category"].astype(str).str.lower().value_counts().to_dict()
            cat_counts = {str(k): float(v) for k, v in cat_counts.items()}

            # Days to resolve (by stage)
            days = g[["stage", "days_to_resolve"]].copy()
            days["days_to_resolve"] = pd.to_numeric(days["days_to_resolve"], errors="coerce")

            denials_by_payer[payer] = {
                "denied_dollars": denied_dollars,
                "writeoff_dollars": writeoff_dollars,
                "denial_cases": denial_cases,
                "stage_counts": stage_counts,
                "cat_counts": cat_counts,
                "days": days,
            }

    # AR aging -> total AR
    ar_by_payer = {}
    if not ar.empty:
        for _, r in ar.iterrows():
            ar_by_payer[str(r["payer"])] = float(r["ar_amount"])

    report_rows: List[Dict[str, Any]] = []

    for payer, pconf in cfg.get("payers", {}).items():
        row: Dict[str, Any] = {"payer": payer}

        # Claims metrics
        payer_rev = float(pconf.get("revenue_share", 0.0)) * float(cfg.get("hospital", {}).get("annual_revenue", 0.0))
        claims_cnt = np.nan
        if payer in claims_by_payer:
            row["claims_net_revenue_observed"] = claims_by_payer[payer]["net_revenue"]
            row["claims_count_observed"] = claims_by_payer[payer]["claim_count"]
            claims_cnt = claims_by_payer[payer]["claim_count"]
        row["revenue_modeled"] = payer_rev
        row["avg_claim_modeled"] = float(pconf.get("avg_claim_dollars", np.nan))

        # Denials metrics (only if payer has denials)
        if bool(pconf.get("include_denials", False)) and payer in denials_by_payer:
            dstat = denials_by_payer[payer]
            denied_dollars = float(dstat["denied_dollars"])
            writeoff_dollars = float(dstat["writeoff_dollars"])
            denial_cases = int(dstat["denial_cases"])

            row["denied_dollars_observed"] = denied_dollars
            row["writeoff_dollars_observed"] = writeoff_dollars
            row["denial_cases_observed"] = denial_cases

            # IDR (dollar-based if we have revenue proxy)
            denom_rev = claims_by_payer[payer]["net_revenue"] if payer in claims_by_payer else payer_rev
            obs_idr = (denied_dollars / denom_rev) if denom_rev and denom_rev > 0 else np.nan
            row["idr_observed"] = obs_idr

            # FWR
            obs_fwr = (writeoff_dollars / denied_dollars) if denied_dollars and denied_dollars > 0 else np.nan
            row["fwr_observed"] = obs_fwr

            # Stage mix
            stage_counts = dstat["stage_counts"]
            tot = sum(stage_counts.values())
            obs_stage_mix = {k: (float(stage_counts.get(k, 0.0)) / tot if tot > 0 else 0.0) for k in ("L1", "L2", "L3")}
            row.update({f"stage_{k}_share_observed": obs_stage_mix[k] for k in ("L1", "L2", "L3")})

            # --- Apply calibration updates to config ---
            den_conf = pconf.get("denials", {})

            # IDR distribution update
            if pd.notna(obs_idr) and 0 < obs_idr < 1:
                prior = den_conf.get("idr", {})
                prior_mean = float(prior.get("mean", obs_idr))
                prior_sd = float(prior.get("sd", 0.02))
                n_eff = float(claims_cnt) if pd.notna(claims_cnt) else float(max(denial_cases, 50))

                mean_u, sd_u = _beta_posterior_mean_sd(prior_mean, prior_sd, float(obs_idr), n_eff=n_eff)
                sd_u = float(max(sd_u * overdispersion, 0.003))
                # Respect existing clamps
                if "min" in prior:
                    mean_u = float(max(mean_u, float(prior["min"])))
                if "max" in prior:
                    mean_u = float(min(mean_u, float(prior["max"])))
                den_conf["idr"]["mean"] = float(mean_u)
                den_conf["idr"]["sd"] = float(sd_u)
                row["idr_calibrated_mean"] = float(mean_u)
                row["idr_calibrated_sd"] = float(sd_u)
                mark_observed(cfg, f"payers.{payer}.denials.idr",
                              note=f"from denials data (n_denial_cases={denial_cases}, n_eff={n_eff:.0f})")

            # FWR distribution update
            if pd.notna(obs_fwr) and 0 < obs_fwr < 1:
                prior = den_conf.get("fwr", {})
                prior_mean = float(prior.get("mean", obs_fwr))
                prior_sd = float(prior.get("sd", 0.05))
                n_eff = float(max(denial_cases, 1))
                mean_u, sd_u = _beta_posterior_mean_sd(prior_mean, prior_sd, float(obs_fwr), n_eff=n_eff)
                sd_u = float(max(sd_u * overdispersion, 0.01))
                if "min" in prior:
                    mean_u = float(max(mean_u, float(prior["min"])))
                if "max" in prior:
                    mean_u = float(min(mean_u, float(prior["max"])))
                den_conf["fwr"]["mean"] = float(mean_u)
                den_conf["fwr"]["sd"] = float(sd_u)
                row["fwr_calibrated_mean"] = float(mean_u)
                row["fwr_calibrated_sd"] = float(sd_u)
                mark_observed(cfg, f"payers.{payer}.denials.fwr",
                              note=f"from denials data (n_denial_cases={denial_cases})")

            # Stage mix smoothing
            prior_stage = {k: float(v) for k, v in den_conf.get("stage_mix", {}).items()}
            if prior_stage:
                obs_counts = {k: float(stage_counts.get(k, 0.0)) for k in ("L1", "L2", "L3")}
                stage_new = _smooth_shares(prior_stage, obs_counts, prior_strength=stage_prior_strength)
                # enforce only L1/L2/L3 keys
                den_conf["stage_mix"] = {k: float(stage_new.get(k, 0.0)) for k in ("L1", "L2", "L3")}
                row.update({f"stage_{k}_share_calibrated": den_conf["stage_mix"][k] for k in ("L1", "L2", "L3")})
                mark_observed(cfg, f"payers.{payer}.denials.stage_mix",
                              note=f"from denials data stage counts (n={int(sum(obs_counts.values()))})")

            # Denial types: shares + odds multipliers + stage bias
            cat_counts = dstat["cat_counts"]
            if cat_counts:
                obs_shares = {k: float(v) for k, v in cat_counts.items()}
                s = sum(obs_shares.values())
                if s > 0:
                    obs_shares = {k: v / s for k, v in obs_shares.items()}

                # Collapse to top N + other
                obs_shares = _top_n_with_other(obs_shares, n=max_denial_types)

                # Smooth to prior shares if present
                prior_types = den_conf.get("denial_types", {}) or {}
                prior_shares = {k: float(v.get("share", 0.0)) for k, v in prior_types.items()}
                if prior_shares and sum(prior_shares.values()) > 0:
                    # convert shares to pseudo-counts to smooth
                    obs_counts2 = {k: float(obs_shares.get(k, 0.0)) * float(denial_cases) for k in obs_shares.keys()}
                    type_new = _smooth_shares(prior_shares, obs_counts2, prior_strength=denial_type_prior_strength)
                    type_new = _top_n_with_other(type_new, n=max_denial_types)
                else:
                    type_new = obs_shares

                # Compute fwr odds multiplier + stage bias by type (if data is granular enough)
                denom_fwr = float(obs_fwr) if pd.notna(obs_fwr) and 0 < obs_fwr < 1 else None
                base_odds = (denom_fwr / (1 - denom_fwr)) if denom_fwr is not None else None

                new_types: Dict[str, Any] = {}
                for tname, share in type_new.items():
                    tname = str(tname).strip().lower() or "other"
                    t_rows = denials[(denials["payer"] == payer) & (denials["denial_category"].astype(str).str.lower() == tname)]
                    t_cases = int(len(t_rows))
                    # Default odds multiplier = 1
                    odds_mult = 1.0
                    stage_bias: Dict[str, float] = {}

                    if base_odds is not None and t_cases >= 25:
                        t_denied = float(t_rows["denial_amount"].sum())
                        t_wo = float(pd.to_numeric(t_rows["writeoff_amount"], errors="coerce").fillna(0.0).sum())
                        t_fwr = (t_wo / t_denied) if t_denied > 0 else None
                        if t_fwr is not None and 0 < t_fwr < 1:
                            t_odds = t_fwr / (1 - t_fwr)
                            raw = t_odds / base_odds if base_odds > 0 else 1.0
                            # shrink toward 1.0 based on cases
                            w = t_cases / (t_cases + 200.0)
                            odds_mult = (1.0 - w) * 1.0 + w * raw
                            odds_mult = float(np.clip(odds_mult, 0.50, 3.00))

                    if t_cases >= 50:
                        t_stage_counts = t_rows["stage"].value_counts().to_dict()
                        t_tot = sum(t_stage_counts.values())
                        if t_tot > 0:
                            p_l2 = float(t_stage_counts.get("L2", 0.0) / t_tot)
                            p_l3 = float(t_stage_counts.get("L3", 0.0) / t_tot)
                            # relative to overall payer stage mix
                            p2_base = float(obs_stage_mix.get("L2", 0.0))
                            p3_base = float(obs_stage_mix.get("L3", 0.0))
                            diff2 = float(np.clip(p_l2 - p2_base, -0.10, 0.10))
                            diff3 = float(np.clip(p_l3 - p3_base, -0.10, 0.10))
                            # shrink
                            w = t_cases / (t_cases + 300.0)
                            if abs(diff2) > 1e-6:
                                stage_bias["L2"] = float(w * diff2)
                            if abs(diff3) > 1e-6:
                                stage_bias["L3"] = float(w * diff3)

                    new_types[tname] = {
                        "share": float(share),
                        "fwr_odds_mult": float(odds_mult),
                    }
                    if stage_bias:
                        new_types[tname]["stage_bias"] = stage_bias

                # Ensure shares sum exactly to 1
                s2 = sum(float(v.get("share", 0.0)) for v in new_types.values())
                if s2 > 0:
                    for k in list(new_types.keys()):
                        new_types[k]["share"] = float(new_types[k]["share"] / s2)

                den_conf["denial_types"] = new_types

            # Persist updates
            cfg["payers"][payer]["denials"] = den_conf

            # Stage days: update global appeals.days distributions if we have enough observations
            days = dstat.get("days")
            if isinstance(days, pd.DataFrame) and not days.empty:
                for stage in ("L1", "L2", "L3"):
                    sdays = days.loc[days["stage"] == stage, "days_to_resolve"].dropna()
                    sdays = sdays[sdays >= 0]
                    if len(sdays) < 80:
                        continue
                    obs_mean = float(sdays.mean())
                    obs_sd = float(sdays.std(ddof=1)) if len(sdays) > 1 else 0.0
                    if obs_mean <= 0 or obs_sd <= 0:
                        continue
                    prior_spec = cfg["appeals"]["stages"][stage]["days"]
                    prior_mean = float(prior_spec.get("mean", obs_mean))
                    prior_sd = float(prior_spec.get("sd", obs_sd))
                    w = float(len(sdays) / (len(sdays) + 250.0))
                    new_mean = (1 - w) * prior_mean + w * obs_mean
                    new_sd = (1 - w) * prior_sd + w * obs_sd
                    new_mean = float(np.clip(new_mean, 3.0, 365.0))
                    new_sd = float(np.clip(new_sd, 1.0, 365.0))
                    cfg["appeals"]["stages"][stage]["days"]["mean"] = new_mean
                    cfg["appeals"]["stages"][stage]["days"]["sd"] = new_sd
                    row[f"appeal_days_{stage}_mean_calibrated"] = new_mean
                    row[f"appeal_days_{stage}_sd_calibrated"] = new_sd

        # Derive dar_clean from AR aging if possible
        if payer in ar_by_payer and payer in denials_by_payer:
            ar_total = float(ar_by_payer[payer])
            dstat = denials_by_payer[payer]
            denied = float(dstat["denied_dollars"])
            wo = float(dstat["writeoff_dollars"])
            collectible = max(denied - wo, 0.0)
            # Use mean days-to-resolve across denials as incremental days
            days = dstat.get("days")
            addl_days = np.nan
            if isinstance(days, pd.DataFrame) and not days.empty:
                sdays = pd.to_numeric(days["days_to_resolve"], errors="coerce").dropna()
                sdays = sdays[sdays >= 0]
                if len(sdays) >= 80:
                    addl_days = float(sdays.mean())
            if pd.notna(addl_days) and payer_rev > 0:
                ar_denials_addl = (collectible / 365.0) * float(addl_days)
                dar_clean = (ar_total - ar_denials_addl) / (payer_rev / 365.0)
                if np.isfinite(dar_clean) and 5.0 <= dar_clean <= 200.0:
                    # Update payer dar_clean_days mean/sd conservatively
                    spec = cfg["payers"][payer].get("dar_clean_days", {})
                    prior_mean = float(spec.get("mean", dar_clean))
                    prior_sd = float(spec.get("sd", 5.0))
                    w = 0.65  # treat AR-derived number as useful but noisy
                    new_mean = (1 - w) * prior_mean + w * float(dar_clean)
                    new_sd = max(prior_sd, 3.0)
                    cfg["payers"][payer]["dar_clean_days"]["mean"] = float(new_mean)
                    cfg["payers"][payer]["dar_clean_days"]["sd"] = float(new_sd)
                    row["dar_clean_derived"] = float(dar_clean)
                    row["dar_clean_calibrated_mean"] = float(new_mean)
                    mark_observed(cfg, f"payers.{payer}.dar_clean_days",
                                  note=f"derived from AR aging + denials days-to-resolve")

        # Step 25: Track what was and was not calibrated
        calibrated = []
        uncalibrated = []
        for param in ["idr", "fwr", "stage_mix", "denial_types", "dar_clean_days"]:
            key_found = f"{param}_calibrated_mean" in row or f"{param}_calibrated_sd" in row
            stage_found = any(f"stage_{k}_share_calibrated" in row for k in ("L1", "L2", "L3"))
            if param == "stage_mix":
                key_found = stage_found
            if param == "dar_clean_days":
                key_found = "dar_clean_calibrated_mean" in row
            if param == "denial_types":
                key_found = bool(pconf.get("include_denials", False)) and payer in denials_by_payer and denials_by_payer[payer].get("cat_counts")
            if key_found:
                calibrated.append(param)
            else:
                uncalibrated.append(param)
        quality.calibrated_parameters[payer] = calibrated
        quality.uncalibrated_parameters[payer] = uncalibrated

        report_rows.append(row)

    report = pd.DataFrame(report_rows)

    # Write quality and dictionary outputs
    logger.info("Calibration complete: %d payers processed", len(report_rows))
    for payer, params in quality.calibrated_parameters.items():
        logger.info("  %s calibrated: %s", payer, ", ".join(params) if params else "(none)")
    for payer, params in quality.uncalibrated_parameters.items():
        if params:
            logger.info("  %s left at defaults: %s", payer, ", ".join(params))

    return cfg, report, quality


def write_yaml(cfg: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

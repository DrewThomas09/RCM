"""Column/value normalization helpers used by the calibration pipeline."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..infra.config import canonical_payer_name


def _norm_col(s: str) -> str:
    return "".join(ch for ch in str(s).strip().lower() if ch.isalnum())


_EXTENDED_ALIASES: Dict[str, List[str]] = {
    "denialamount": ["deniedamount", "denialdollars", "denamt", "amountdenied", "deniedamt"],
    "writeoffamount": ["writeoff", "payerwriteoff", "denialwriteoff", "woamount", "writtenoff", "writeoffamt"],
    "paidamount": ["payments", "allowedamount", "paidamt", "reimbursement"],
    "netrevenue": ["revenue", "netpatientrevenue", "payments", "allowedamount", "totalrevenue"],
    "claimcount": ["claims", "numclaims", "count", "claimcnt", "totalclaims"],
    "aramount": ["amount", "balance", "arbalance", "endingar", "outstandingar"],
    "payer": ["payor", "payername", "payorname", "financialclass", "finclass", "insurancename"],
    "claimid": ["claim", "encounter", "account", "patientaccount", "visitid", "accountnumber"],
}


def _first_matching_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return first column in df matching candidates (case/format insensitive)."""
    if df is None or df.empty:
        return None
    norm_to_col = {_norm_col(c): c for c in df.columns}

    all_candidates = list(candidates)
    for cand in candidates:
        key = _norm_col(cand)
        if key in _EXTENDED_ALIASES:
            all_candidates.extend(_EXTENDED_ALIASES[key])

    for cand in all_candidates:
        key = _norm_col(cand)
        if key in norm_to_col:
            return norm_to_col[key]

    norm_cols = list(norm_to_col.keys())
    for cand in all_candidates:
        key = _norm_col(cand)
        for nc in norm_cols:
            if key and len(key) >= 3 and key in nc:
                return norm_to_col[nc]
    return None


def _clean_currency(series: pd.Series) -> pd.Series:
    """Strip $, commas, parentheses and convert to float."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    s = series.astype(str)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace(",", "", regex=False)
    is_negative = s.str.startswith("(") & s.str.endswith(")")
    s = s.str.replace("(", "", regex=False).str.replace(")", "", regex=False)
    result = pd.to_numeric(s, errors="coerce")
    result = result.where(~is_negative, -result)
    return result


_DATE_FORMATS = [
    "%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%b-%Y", "%d/%m/%Y",
    "%Y%m%d", "%m-%d-%Y", "%b %d, %Y", "%B %d, %Y",
]


def _parse_dates(series: pd.Series) -> pd.Series:
    """Try multiple date formats to parse a date column."""
    result = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    if result.notna().sum() > 0.5 * len(series):
        return result
    for fmt in _DATE_FORMATS:
        attempt = pd.to_datetime(series, format=fmt, errors="coerce")
        if attempt.notna().sum() > result.notna().sum():
            result = attempt
            if result.notna().sum() > 0.7 * len(series):
                break
    return result


def _to_datetime_safe(s: pd.Series) -> pd.Series:
    result = _parse_dates(s)
    try:
        if hasattr(result.dt, "tz") and result.dt.tz is not None:
            result = result.dt.tz_convert(None)
    except Exception:
        pass
    return result


_PAYER_ALIASES: List[Tuple[str, str]] = [
    ("medicare advantage", "Medicare"), ("medicare ffs", "Medicare"), ("medicare ma", "Medicare"),
    ("medi-cal", "Medicaid"), ("medi cal", "Medicaid"), ("tenncare", "Medicaid"),
    ("state medicaid", "Medicaid"),
    ("blue cross", "Commercial"), ("blue shield", "Commercial"),
    ("bluecross", "Commercial"), ("blueshield", "Commercial"), ("bcbs", "Commercial"),
    ("unitedhealthcare", "Commercial"), ("unitedhealth", "Commercial"), ("uhc", "Commercial"),
    ("aetna", "Commercial"), ("cigna", "Commercial"), ("humana", "Commercial"),
    ("anthem", "Commercial"), ("kaiser", "Commercial"),
    ("tricare", "Commercial"), ("champus", "Commercial"),
    ("veterans affairs", "Commercial"), ("veterans", "Commercial"),
    ("workers comp", "Commercial"), ("workerscomp", "Commercial"), ("work comp", "Commercial"),
]


def _enhanced_payer_name(raw_name: str) -> str:
    """Resolve payer names through alias table then canonical mapping."""
    cleaned = str(raw_name).strip()
    lower = cleaned.lower().replace("-", " ").replace("_", " ")
    lower_nospace = lower.replace(" ", "")
    for alias, canonical in _PAYER_ALIASES:
        alias_nospace = alias.replace(" ", "").replace("-", "")
        if alias in lower or alias_nospace in lower_nospace:
            return canonical
    return canonical_payer_name(cleaned)


def _map_stage(x: Any) -> str:
    """Map arbitrary appeal level/stage text to L1/L2/L3."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "L1"
    t = str(x).strip().lower()
    if t in ("l1", "level1", "level 1", "1", "first", "initial", "appeal1"):
        return "L1"
    if t in ("l2", "level2", "level 2", "2", "second", "appeal2"):
        return "L2"
    if t in ("l3", "level3", "level 3", "3", "third", "alj", "judge", "hearing", "appeal3"):
        return "L3"
    if "alj" in t or "hearing" in t or "judge" in t:
        return "L3"
    if "level" in t and "3" in t:
        return "L3"
    if "level" in t and "2" in t:
        return "L2"
    if "level" in t and "1" in t:
        return "L1"
    return "L1"


def _classify_denial_reason(text: Any) -> str:
    """Lightweight keyword classifier for denial reasons."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return "other"
    t = str(text).strip().lower()
    t = t.replace("/", " ").replace("-", " ")

    if any(k in t for k in ["eligib", "coverage terminated", "member not", "cob", "coordination", "inactive", "not covered", "no coverage"]):
        return "eligibility"

    if any(k in t for k in ["prior auth", "pre auth", "precert", "authorization", "referral", "out of network", "oon", "network", "nonpar"]):
        return "auth_admin"

    if any(k in t for k in ["coding", "code", "cpt", "icd", "modifier", "drg", "dx", "px", "invalid", "bundl", "edit"]):
        return "coding"

    if any(k in t for k in ["medical necessity", "necessity", "clinical", "not medically", "experimental", "investigational", "no indication"]):
        return "clinical"

    if any(k in t for k in ["timely", "late filing", "missing", "documentation", "doc", "incomplete", "format", "npi", "taxonomy", "claim form"]):
        return "admin"

    return "other"

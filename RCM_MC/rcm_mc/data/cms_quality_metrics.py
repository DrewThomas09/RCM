"""Numeric Hospital Compare quality metrics — predictive features
for RCM performance.

The existing ``cms_hospital_general`` captures the overall
star rating + categorical compare flags ("above national" /
"below national") for mortality / readmission / safety. CMS
also publishes the underlying NUMERIC rates per condition / per
dimension. Those numeric rates are what regression / ML models
need — categorical flags lose the gradient information.

This module ingests four numeric quality datasets:

  • Readmission rates per condition (AMI, COPD, HF, PNE, CABG,
    THA/TKA — the HRRP-tracked conditions). Excess Readmission
    Ratio (ERR) per condition.
  • Mortality rates per condition (same six + COPD/HF/PNE
    mortality measures).
  • HCAHPS patient-satisfaction top-box scores (cleanliness,
    communication, pain mgmt, discharge info, overall rating).
  • Healthcare-Associated Infection (HAI) rates: CAUTI, CLABSI,
    SSI, MRSA, C.diff — Standardized Infection Ratio (SIR) per
    type.

These join to the existing pricing_nppes / cms_hospital_general
tables on CCN. Downstream consumers (the screening dashboard's
``has_pe_history`` / risk-factor predictor, the comparable-
outcomes match scorer) get a continuous-value feature surface
instead of a 3-level categorical.

Public API::

    from rcm_mc.data.cms_quality_metrics import (
        QualityMetric,
        load_readmission_rates,
        load_mortality_rates,
        load_hcahps_scores,
        load_hai_rates,
        get_quality_features,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# ── Schema ─────────────────────────────────────────────────────

def _ensure_quality_table(con: Any) -> None:
    """One row per (CCN, metric_id, period) — wide enough to
    hold any of the four metric families without per-family
    schema churn."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_quality_metrics (
            ccn TEXT NOT NULL,
            metric_family TEXT NOT NULL,
            metric_id TEXT NOT NULL,
            metric_label TEXT,
            period TEXT,
            value REAL,
            denominator INTEGER,
            comparison_to_national TEXT,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (ccn, metric_family, metric_id, period)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_quality_ccn ON cms_quality_metrics(ccn)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_quality_family "
        "ON cms_quality_metrics(metric_family)"
    )


@dataclass
class QualityMetric:
    """One numeric metric row."""
    ccn: str
    metric_family: str   # readmission / mortality / hcahps / hai
    metric_id: str       # e.g. "ERR_AMI", "MORT_HF", "HCAHPS_OVR",
                         # "HAI_CAUTI"
    metric_label: str = ""
    period: str = ""
    value: Optional[float] = None
    denominator: Optional[int] = None
    comparison_to_national: str = ""


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.lower() in ("not available", "n/a", "na",
                     "not applicable", "—"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    f = _safe_float(v)
    return int(f) if f is not None else None


def _ingest_metrics(
    store: Any,
    metrics: Iterable[QualityMetric],
) -> int:
    """Common storage pipeline. Returns count loaded."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_quality_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for m in metrics:
                if not m.ccn or not m.metric_id:
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO cms_quality_metrics "
                    "(ccn, metric_family, metric_id, metric_label,"
                    " period, value, denominator, "
                    " comparison_to_national, loaded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (m.ccn, m.metric_family, m.metric_id,
                     m.metric_label, m.period, m.value,
                     m.denominator, m.comparison_to_national,
                     now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Per-family loaders ────────────────────────────────────────

# Six HRRP-tracked conditions
_READMISSION_CONDITIONS = {
    "READM_30_AMI": "AMI 30-day readmission",
    "READM_30_COPD": "COPD 30-day readmission",
    "READM_30_HF": "Heart failure 30-day readmission",
    "READM_30_PNE": "Pneumonia 30-day readmission",
    "READM_30_CABG": "CABG 30-day readmission",
    "READM_30_HK": "Hip/knee 30-day readmission",
}
_MORTALITY_CONDITIONS = {
    "MORT_30_AMI": "AMI 30-day mortality",
    "MORT_30_COPD": "COPD 30-day mortality",
    "MORT_30_HF": "Heart failure 30-day mortality",
    "MORT_30_PNE": "Pneumonia 30-day mortality",
    "MORT_30_STK": "Stroke 30-day mortality",
    "MORT_30_CABG": "CABG 30-day mortality",
}
_HCAHPS_DIMS = {
    "HCAHPS_NURSE": "Nurse communication top-box",
    "HCAHPS_DOC": "Doctor communication top-box",
    "HCAHPS_RESP": "Staff responsiveness top-box",
    "HCAHPS_PAIN": "Pain management top-box",
    "HCAHPS_MEDS": "Medication communication top-box",
    "HCAHPS_DISCH": "Discharge information top-box",
    "HCAHPS_TRANS": "Care transition top-box",
    "HCAHPS_CLEAN": "Cleanliness top-box",
    "HCAHPS_QUIET": "Quietness top-box",
    "HCAHPS_OVERALL": "Overall rating 9-10",
    "HCAHPS_RECOMMEND": "Would recommend",
}
_HAI_TYPES = {
    "HAI_CAUTI": "Catheter-associated UTI SIR",
    "HAI_CLABSI": "Central-line bloodstream infection SIR",
    "HAI_SSI_COLON": "Colon SSI SIR",
    "HAI_SSI_HYS": "Abdominal hysterectomy SSI SIR",
    "HAI_MRSA": "MRSA bacteremia SIR",
    "HAI_CDIFF": "C. diff infection SIR",
}


def load_readmission_rates(
    store: Any,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """Ingest condition-level readmission rates.

    Each input row should include: ccn, condition_id (one of the
    keys above OR the Hospital Compare measure ID), value
    (excess readmission ratio, where 1.0 = exactly national
    average), denominator (cases), period.
    """
    metrics: List[QualityMetric] = []
    for r in rows:
        ccn = str(r.get("ccn") or "").strip()
        cid = str(r.get("metric_id") or
                  r.get("condition_id") or "").strip()
        if not (ccn and cid):
            continue
        label = (r.get("metric_label")
                 or _READMISSION_CONDITIONS.get(cid, cid))
        metrics.append(QualityMetric(
            ccn=ccn,
            metric_family="readmission",
            metric_id=cid,
            metric_label=label,
            period=str(r.get("period") or ""),
            value=_safe_float(r.get("value")),
            denominator=_safe_int(r.get("denominator")),
            comparison_to_national=str(
                r.get("comparison_to_national") or ""),
        ))
    return _ingest_metrics(store, metrics)


def load_mortality_rates(
    store: Any,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """Ingest condition-level mortality rates."""
    metrics: List[QualityMetric] = []
    for r in rows:
        ccn = str(r.get("ccn") or "").strip()
        cid = str(r.get("metric_id") or
                  r.get("condition_id") or "").strip()
        if not (ccn and cid):
            continue
        label = (r.get("metric_label")
                 or _MORTALITY_CONDITIONS.get(cid, cid))
        metrics.append(QualityMetric(
            ccn=ccn,
            metric_family="mortality",
            metric_id=cid,
            metric_label=label,
            period=str(r.get("period") or ""),
            value=_safe_float(r.get("value")),
            denominator=_safe_int(r.get("denominator")),
            comparison_to_national=str(
                r.get("comparison_to_national") or ""),
        ))
    return _ingest_metrics(store, metrics)


def load_hcahps_scores(
    store: Any,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """Ingest HCAHPS top-box scores per dimension."""
    metrics: List[QualityMetric] = []
    for r in rows:
        ccn = str(r.get("ccn") or "").strip()
        did = str(r.get("metric_id") or
                  r.get("dimension") or "").strip()
        if not (ccn and did):
            continue
        label = (r.get("metric_label")
                 or _HCAHPS_DIMS.get(did, did))
        metrics.append(QualityMetric(
            ccn=ccn,
            metric_family="hcahps",
            metric_id=did,
            metric_label=label,
            period=str(r.get("period") or ""),
            value=_safe_float(r.get("value")),
            denominator=_safe_int(
                r.get("survey_response_count")
                or r.get("denominator")),
        ))
    return _ingest_metrics(store, metrics)


def load_hai_rates(
    store: Any,
    rows: Iterable[Dict[str, Any]],
) -> int:
    """Ingest Healthcare-Associated Infection SIRs."""
    metrics: List[QualityMetric] = []
    for r in rows:
        ccn = str(r.get("ccn") or "").strip()
        hid = str(r.get("metric_id") or
                  r.get("hai_type") or "").strip()
        if not (ccn and hid):
            continue
        label = (r.get("metric_label")
                 or _HAI_TYPES.get(hid, hid))
        metrics.append(QualityMetric(
            ccn=ccn,
            metric_family="hai",
            metric_id=hid,
            metric_label=label,
            period=str(r.get("period") or ""),
            value=_safe_float(r.get("value")),
            denominator=_safe_int(r.get("denominator")),
            comparison_to_national=str(
                r.get("comparison_to_national") or ""),
        ))
    return _ingest_metrics(store, metrics)


# ── Read helpers ──────────────────────────────────────────────

def get_quality_features(
    store: Any,
    ccn: str,
) -> Dict[str, float]:
    """Return a flat {metric_id → value} dict for a single CCN.

    Output is the partner-facing feature vector for downstream
    ML / regression — null values omitted so consumers can
    reason about coverage explicitly.
    """
    if not ccn:
        return {}
    with store.connect() as con:
        _ensure_quality_table(con)
        rows = con.execute(
            "SELECT metric_id, value FROM cms_quality_metrics "
            "WHERE ccn = ? AND value IS NOT NULL",
            (str(ccn).strip(),),
        ).fetchall()
    return {r["metric_id"]: float(r["value"]) for r in rows}


def get_quality_summary(
    store: Any,
    ccn: str,
) -> Dict[str, Any]:
    """Multi-family summary: readmission / mortality / hcahps /
    hai medians for a single CCN."""
    if not ccn:
        return {}
    with store.connect() as con:
        _ensure_quality_table(con)
        rows = con.execute(
            "SELECT metric_family, AVG(value) as mean_value, "
            "       COUNT(*) as n_metrics "
            "FROM cms_quality_metrics "
            "WHERE ccn = ? AND value IS NOT NULL "
            "GROUP BY metric_family",
            (str(ccn).strip(),),
        ).fetchall()
    out: Dict[str, Any] = {"ccn": ccn, "by_family": {}}
    for r in rows:
        out["by_family"][r["metric_family"]] = {
            "mean": round(float(r["mean_value"]), 4),
            "n_metrics": int(r["n_metrics"]),
        }
    return out

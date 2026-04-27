"""SeekingChartis Provenance System — source attribution for every number.

Every metric in the platform has a source: HCRIS public filing, ML
prediction, seller data room, Bayesian calibration, benchmark default,
or computed derivation. This module generates visual provenance tags
and data freshness indicators.

The provenance system is the trust layer. A PE partner who sees
"Source: HCRIS FY2022 (n=5,808)" trusts the number. A partner who
sees a bare "12%" does not.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple


# ── Source definitions ──

class Source:
    HCRIS = "hcris"
    ML_PREDICTION = "ml"
    SELLER = "seller"
    CALIBRATED = "calibrated"
    BENCHMARK = "benchmark"
    COMPUTED = "computed"
    DEFAULT = "default"


_SOURCE_META = {
    Source.HCRIS: {
        "label": "HCRIS",
        "color": "#2d6ba4",
        "bg": "rgba(45,107,164,0.15)",
        "description": "CMS Cost Report public filing",
        "trust": "high",
    },
    Source.ML_PREDICTION: {
        "label": "ML",
        "color": "#8b5cf6",
        "bg": "rgba(139,92,246,0.15)",
        "description": "Machine learning prediction from HCRIS features",
        "trust": "medium",
    },
    Source.SELLER: {
        "label": "SELLER",
        "color": "#e67e22",
        "bg": "rgba(230,126,34,0.15)",
        "description": "Seller-provided data from diligence data room",
        "trust": "high",
    },
    Source.CALIBRATED: {
        "label": "CALIBRATED",
        "color": "#2ecc71",
        "bg": "rgba(46,204,113,0.15)",
        "description": "Bayesian posterior blending ML prediction with seller data",
        "trust": "high",
    },
    Source.BENCHMARK: {
        "label": "BENCHMARK",
        "color": "#718096",
        "bg": "rgba(113,128,150,0.15)",
        "description": "Industry benchmark (P50 for hospital type/size)",
        "trust": "low",
    },
    Source.COMPUTED: {
        "label": "COMPUTED",
        "color": "#5b9bd5",
        "bg": "rgba(91,155,213,0.15)",
        "description": "Derived from other observed values",
        "trust": "high",
    },
    Source.DEFAULT: {
        "label": "DEFAULT",
        "color": "#4a5568",
        "bg": "rgba(74,85,104,0.15)",
        "description": "Model default assumption — no hospital-specific data",
        "trust": "low",
    },
}


def source_tag(source: str, detail: str = "") -> str:
    """Render a small inline provenance badge.

    Usage in any page:
        f'{value} {source_tag(Source.HCRIS, "FY2022")}'
    """
    meta = _SOURCE_META.get(source, _SOURCE_META[Source.DEFAULT])
    title = _html.escape(meta["description"])
    if detail:
        title += f" — {_html.escape(detail)}"
    return (
        f'<span style="display:inline-block;font-size:8.5px;padding:1px 5px;'
        f'border-radius:2px;font-weight:700;letter-spacing:0.04em;'
        f'background:{meta["bg"]};color:{meta["color"]};'
        f'vertical-align:middle;margin-left:4px;cursor:help;" '
        f'title="{title}">{meta["label"]}</span>'
    )


def source_tag_with_n(source: str, n: int = 0, period: str = "") -> str:
    """Provenance badge with sample size and period."""
    detail_parts = []
    if period:
        detail_parts.append(period)
    if n > 0:
        detail_parts.append(f"n={n:,}")
    return source_tag(source, " | ".join(detail_parts))


def data_freshness_footer(
    hcris_year: int = 2022,
    n_hospitals: int = 0,
    has_seller_data: bool = False,
    n_seller_metrics: int = 0,
) -> str:
    """Render a data freshness footer for any page."""
    parts = [f"HCRIS FY{hcris_year}"]
    if n_hospitals > 0:
        parts.append(f"{n_hospitals:,} hospitals")
    if has_seller_data:
        parts.append(f"{n_seller_metrics} seller data points")

    sources_used = [source_tag(Source.HCRIS, f"FY{hcris_year}")]
    if has_seller_data:
        sources_used.append(source_tag(Source.SELLER))
        sources_used.append(source_tag(Source.CALIBRATED))
    else:
        sources_used.append(source_tag(Source.ML_PREDICTION))

    return (
        f'<div style="margin-top:12px;padding:10px 16px;background:var(--cad-bg2);'
        f'border-top:1px solid var(--cad-border);font-size:11px;color:var(--cad-text3);'
        f'display:flex;justify-content:space-between;align-items:center;">'
        f'<span>Data: {_html.escape(" | ".join(parts))}</span>'
        f'<span>Sources: {"".join(sources_used)}</span>'
        f'</div>'
    )


def provenance_legend() -> str:
    """Render a legend explaining all source badges."""
    items = ""
    for src, meta in _SOURCE_META.items():
        items += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
            f'{source_tag(src)}'
            f'<span style="font-size:11px;color:var(--cad-text2);">{meta["description"]}</span>'
            f'<span style="font-size:10px;color:var(--cad-text3);">Trust: {meta["trust"]}</span>'
            f'</div>'
        )
    return (
        f'<div class="cad-card" style="padding:12px 16px;">'
        f'<div style="font-size:11px;font-weight:600;color:var(--cad-text3);'
        f'margin-bottom:6px;">DATA SOURCE LEGEND</div>'
        f'{items}</div>'
    )


def classify_metric_source(
    metric: str,
    hcris_value: Optional[float] = None,
    ml_predicted: Optional[float] = None,
    seller_value: Optional[float] = None,
    calibrated_value: Optional[float] = None,
) -> Tuple[str, float, str]:
    """Determine the best source for a metric.

    Returns (source_type, value, detail_string).
    Priority: calibrated > seller > hcris > ml > default.
    """
    if calibrated_value is not None:
        return Source.CALIBRATED, calibrated_value, "Bayesian posterior"
    if seller_value is not None:
        return Source.SELLER, seller_value, "Data room"
    if hcris_value is not None:
        return Source.HCRIS, hcris_value, "CMS Cost Report"
    if ml_predicted is not None:
        return Source.ML_PREDICTION, ml_predicted, "Model prediction"
    return Source.DEFAULT, 0, "No data"


def build_provenance_profile(
    ccn: str,
    hcris_profile: Dict[str, Any],
    ml_predictions: Dict[str, float],
    db_path: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Build a complete provenance-tagged profile for a hospital.

    Returns {metric: {value, source, tag_html, detail}} for every metric.
    """
    result: Dict[str, Dict[str, Any]] = {}

    # Load seller data if available
    seller_data: Dict[str, float] = {}
    calibrations: Dict[str, float] = {}
    if db_path:
        try:
            # Late local import keeps the bypass cleanup contained
            # (campaign target 4E) — the module top doesn't need
            # PortfolioStore otherwise. Routes the read through
            # the canonical seam so it inherits busy_timeout=5000,
            # foreign_keys=ON, and Row factory.
            from ..portfolio.store import PortfolioStore
            with PortfolioStore(db_path).connect() as con:
                # Raw entries
                rows = con.execute(
                    "SELECT metric, value FROM data_room_entries "
                    "WHERE hospital_ccn = ? AND superseded_by IS NULL",
                    (ccn,),
                ).fetchall()
                for m, v in rows:
                    if m not in seller_data:
                        seller_data[m] = v
                # Calibrations
                rows = con.execute(
                    "SELECT metric, bayesian_posterior FROM data_room_calibrations "
                    "WHERE hospital_ccn = ? ORDER BY computed_at DESC",
                    (ccn,),
                ).fetchall()
                for m, v in rows:
                    if m not in calibrations:
                        calibrations[m] = v
        except Exception:
            pass

    # HCRIS financial metrics
    hcris_metrics = {
        "net_patient_revenue": ("Net Patient Revenue", "dollars"),
        "operating_expenses": ("Operating Expenses", "dollars"),
        "net_income": ("Net Income", "dollars"),
        "beds": ("Beds", "count"),
        "medicare_day_pct": ("Medicare Day %", "pct"),
        "medicaid_day_pct": ("Medicaid Day %", "pct"),
        "total_patient_days": ("Total Patient Days", "count"),
        "occupancy_rate": ("Occupancy Rate", "pct"),
        "operating_margin": ("Operating Margin", "pct"),
        "revenue_per_bed": ("Revenue per Bed", "dollars"),
        "net_to_gross_ratio": ("Net-to-Gross Ratio", "pct"),
    }

    for metric, (label, fmt) in hcris_metrics.items():
        hcris_val = hcris_profile.get(metric)
        if hcris_val is not None:
            try:
                hcris_val = float(hcris_val)
                if hcris_val != hcris_val:
                    hcris_val = None
            except (TypeError, ValueError):
                hcris_val = None

        src, val, detail = classify_metric_source(
            metric,
            hcris_value=hcris_val,
            ml_predicted=ml_predictions.get(metric),
            seller_value=seller_data.get(metric),
            calibrated_value=calibrations.get(metric),
        )

        result[metric] = {
            "label": label,
            "value": val,
            "source": src,
            "detail": detail,
            "fmt": fmt,
            "tag": source_tag(src, detail),
        }

    # ML-predicted RCM metrics
    rcm_metrics = {
        "denial_rate": "Denial Rate",
        "days_in_ar": "Days in AR",
        "clean_claim_rate": "Clean Claim Rate",
        "collection_rate": "Net Collection Rate",
    }

    for metric, label in rcm_metrics.items():
        src, val, detail = classify_metric_source(
            metric,
            ml_predicted=ml_predictions.get(metric),
            seller_value=seller_data.get(metric),
            calibrated_value=calibrations.get(metric),
        )
        result[metric] = {
            "label": label,
            "value": val,
            "source": src,
            "detail": detail,
            "fmt": "pct" if "rate" in metric or "pct" in metric else "days",
            "tag": source_tag(src, detail),
        }

    return result

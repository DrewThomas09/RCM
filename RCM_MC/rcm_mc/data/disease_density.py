"""CMS Medicare Chronic Conditions by county — disease density loader.

Fetches county-level chronic condition prevalence from data.cms.gov.
Falls back to national averages when API is unavailable.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)

# National average prevalence rates (Medicare beneficiaries, 2022)
NATIONAL_PREVALENCE: Dict[str, float] = {
    "Hypertension": 58.2,
    "Hyperlipidemia": 49.3,
    "Diabetes": 27.8,
    "Ischemic Heart Disease": 27.1,
    "Chronic Kidney Disease": 25.4,
    "Depression": 19.8,
    "Heart Failure": 14.2,
    "COPD": 11.4,
    "Alzheimer's/Dementia": 11.2,
    "Atrial Fibrillation": 9.1,
    "Cancer": 8.7,
    "Stroke": 4.1,
    "Osteoporosis": 6.8,
    "Rheumatoid Arthritis": 6.2,
    "Asthma": 5.1,
}


@dataclass
class CountyPrevalence:
    county_name: str
    state: str
    condition: str
    prevalence_pct: float
    national_avg_pct: float
    delta_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_county(name: str) -> str:
    """Normalize county name for matching."""
    if not name:
        return ""
    n = name.lower().strip()
    for suffix in [" county", " parish", " borough", " census area",
                   " municipality", " city and borough"]:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
    n = n.replace("saint ", "st ").replace("st. ", "st ")
    return n.strip()


def fetch_chronic_conditions_api(state: str = "", limit: int = 5000) -> List[Dict[str, Any]]:
    """Fetch from CMS SODA API. Returns raw records or empty list on failure."""
    try:
        base = "https://data.cms.gov/data-api/v1/dataset/9767cb68-8ea9-4f0b-8179-9431abc89f11/data"
        params = f"?size={limit}"
        if state:
            params += f"&filter[Bene_Geo_Lvl]=County&filter[Bene_Geo_Desc]={state}"
        url = base + params
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            if isinstance(data, list):
                return data
    except Exception as exc:
        logger.warning("CMS Chronic Conditions API unavailable: %s", exc)
    return []


def get_county_prevalence(
    county: str,
    state: str,
    store: Any = None,
) -> List[CountyPrevalence]:
    """Get disease prevalence for a county. Falls back to state/national averages."""
    norm_county = _normalize_county(county)
    norm_state = state.upper().strip() if state else ""

    # Try database first
    if store:
        try:
            with store.connect() as con:
                rows = con.execute(
                    "SELECT condition, prevalence_pct FROM county_disease_prevalence "
                    "WHERE state = ? AND county_name_norm = ? ORDER BY prevalence_pct DESC",
                    (norm_state, norm_county),
                ).fetchall()
                if rows:
                    return [
                        CountyPrevalence(
                            county_name=county, state=norm_state,
                            condition=r["condition"],
                            prevalence_pct=r["prevalence_pct"],
                            national_avg_pct=NATIONAL_PREVALENCE.get(r["condition"], 0),
                            delta_pct=r["prevalence_pct"] - NATIONAL_PREVALENCE.get(r["condition"], 0),
                        )
                        for r in rows
                    ]
        except Exception:
            pass

    # Try API
    api_data = fetch_chronic_conditions_api(state=norm_state, limit=500)
    if api_data:
        county_records = []
        for rec in api_data:
            geo = str(rec.get("Bene_Geo_Desc", ""))
            if _normalize_county(geo) == norm_county:
                for cond, nat_avg in NATIONAL_PREVALENCE.items():
                    key = _condition_to_api_key(cond)
                    val = rec.get(key)
                    if val is not None:
                        try:
                            pct = float(val)
                            county_records.append(CountyPrevalence(
                                county_name=county, state=norm_state,
                                condition=cond, prevalence_pct=pct,
                                national_avg_pct=nat_avg, delta_pct=pct - nat_avg,
                            ))
                        except (TypeError, ValueError):
                            pass
        if county_records:
            return sorted(county_records, key=lambda x: -x.prevalence_pct)

    # Fallback: use national averages with regional adjustments
    return _generate_estimated_prevalence(county, norm_state)


def _condition_to_api_key(condition: str) -> str:
    """Map condition name to CMS API column name."""
    mapping = {
        "Hypertension": "Prvlnc_Hypertension",
        "Hyperlipidemia": "Prvlnc_Hyperlipidemia",
        "Diabetes": "Prvlnc_Diabetes",
        "Ischemic Heart Disease": "Prvlnc_Ischemic_Heart_Disease",
        "Chronic Kidney Disease": "Prvlnc_CKD",
        "Depression": "Prvlnc_Depression",
        "Heart Failure": "Prvlnc_Heart_Failure",
        "COPD": "Prvlnc_COPD",
        "Alzheimer's/Dementia": "Prvlnc_Alzheimers",
        "Atrial Fibrillation": "Prvlnc_Atrial_Fibrillation",
        "Cancer": "Prvlnc_Cancer",
        "Stroke": "Prvlnc_Stroke",
        "Osteoporosis": "Prvlnc_Osteoporosis",
        "Rheumatoid Arthritis": "Prvlnc_RA_OA",
        "Asthma": "Prvlnc_Asthma",
    }
    return mapping.get(condition, "")


# Regional adjustment factors (Southern/Appalachian states have higher chronic disease)
_STATE_ADJUSTMENTS: Dict[str, float] = {
    "MS": 1.25, "AL": 1.20, "LA": 1.18, "AR": 1.15, "WV": 1.22,
    "KY": 1.15, "TN": 1.12, "SC": 1.10, "GA": 1.08, "OK": 1.12,
    "TX": 1.05, "NC": 1.05, "MO": 1.05, "IN": 1.03,
    "CO": 0.88, "UT": 0.85, "MN": 0.90, "HI": 0.82, "CT": 0.92,
    "MA": 0.93, "NH": 0.91, "VT": 0.90, "WA": 0.92, "OR": 0.93,
}


def _generate_estimated_prevalence(county: str, state: str) -> List[CountyPrevalence]:
    """Generate estimated prevalence using national averages + state adjustment."""
    adj = _STATE_ADJUSTMENTS.get(state, 1.0)
    results = []
    for cond, nat_avg in sorted(NATIONAL_PREVALENCE.items(), key=lambda x: -x[1]):
        est = nat_avg * adj
        results.append(CountyPrevalence(
            county_name=county, state=state,
            condition=cond, prevalence_pct=round(est, 1),
            national_avg_pct=nat_avg,
            delta_pct=round(est - nat_avg, 1),
        ))
    return results


def ensure_disease_table(store: Any) -> None:
    """Create the county_disease_prevalence table if needed."""
    try:
        with store.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS county_disease_prevalence (
                    id INTEGER PRIMARY KEY,
                    county_fips TEXT,
                    state TEXT NOT NULL,
                    county_name TEXT NOT NULL,
                    county_name_norm TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    prevalence_pct REAL,
                    year INTEGER,
                    loaded_at TEXT NOT NULL,
                    UNIQUE(state, county_name_norm, condition, year)
                )
            """)
    except Exception:
        pass

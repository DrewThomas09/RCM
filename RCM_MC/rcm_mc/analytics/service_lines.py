"""Service line profitability analysis (Prompt 82).

Maps DRG codes to service lines, computes per-service-line P&L
from claim-level data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SERVICE_LINE_DEFINITIONS: Dict[str, List[str]] = {
    "Cardiology": ["216", "217", "218", "219", "220", "221", "222",
                   "246", "247", "280", "281", "282"],
    "Orthopedics": ["453", "454", "455", "456", "470", "480", "481"],
    "Oncology": ["820", "821", "822", "823", "824", "825"],
    "Women's Health": ["765", "766", "767", "768", "774", "775"],
    "General Medicine": ["175", "176", "177", "178", "190", "191",
                         "192", "193", "194", "195"],
    "Neurology": ["023", "024", "025", "026", "027", "028"],
    "Pulmonary": ["163", "164", "165", "166", "167"],
}


@dataclass
class ServiceLinePnL:
    service_line: str
    revenue: float = 0.0
    claim_count: int = 0
    top_drgs: List[str] = field(default_factory=list)
    contribution_margin: float = 0.0
    pct_of_total_revenue: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_line": self.service_line,
            "revenue": float(self.revenue),
            "claim_count": int(self.claim_count),
            "top_drgs": list(self.top_drgs),
            "contribution_margin": float(self.contribution_margin),
            "pct_of_total_revenue": float(self.pct_of_total_revenue),
        }


def _drg_to_service_line(drg_code: str) -> str:
    """Map a DRG code to its service line. Unknown → 'Other'."""
    for sl, codes in SERVICE_LINE_DEFINITIONS.items():
        if drg_code in codes:
            return sl
    return "Other"


def compute_service_line_pnl(
    claims: List[Dict[str, Any]],
) -> List[ServiceLinePnL]:
    """Aggregate claim-level data into per-service-line P&L.

    ``claims`` is a list of dicts with keys: drg_code, paid_amount,
    total_charge, status.
    """
    by_sl: Dict[str, Dict[str, Any]] = {}
    for claim in claims:
        drg = str(claim.get("drg_code") or "")
        sl = _drg_to_service_line(drg)
        if sl not in by_sl:
            by_sl[sl] = {"revenue": 0.0, "count": 0, "drgs": {}}
        paid = float(claim.get("paid_amount") or 0)
        by_sl[sl]["revenue"] += paid
        by_sl[sl]["count"] += 1
        by_sl[sl]["drgs"][drg] = by_sl[sl]["drgs"].get(drg, 0) + 1

    total_rev = sum(d["revenue"] for d in by_sl.values()) or 1.0
    results: List[ServiceLinePnL] = []
    for sl, data in sorted(by_sl.items(), key=lambda kv: kv[1]["revenue"], reverse=True):
        top = sorted(data["drgs"].items(), key=lambda kv: kv[1], reverse=True)[:5]
        results.append(ServiceLinePnL(
            service_line=sl,
            revenue=data["revenue"],
            claim_count=data["count"],
            top_drgs=[d[0] for d in top],
            pct_of_total_revenue=(data["revenue"] / total_rev) * 100.0,
        ))
    return results

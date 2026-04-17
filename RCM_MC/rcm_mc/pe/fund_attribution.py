"""Fund-level value-creation attribution (Prompt 60).

Decomposes total fund value created into three sources:

- **RCM improvement** — dollar impact from the v2 bridge levers
  (denial-rate reduction, AR acceleration, coding uplift, etc.).
- **Organic growth** — actual EBITDA trajectory *minus* the RCM
  portion, capturing volume/mix/rate tailwinds.
- **Multiple expansion** — placeholder for now; requires entry and
  exit multiples that are often unavailable until exit.

Each source gets a dollar amount and a percentage of total. The
per-deal breakdown lets the GP explain to LPs which deals drove the
most value and through which channel.
"""
from __future__ import annotations

import json
import logging
import zlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class SourceAttribution:
    """Dollar amount and percentage for one value-creation source."""
    dollar_amount: float = 0.0
    pct_of_total: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DealAttribution:
    """Per-deal value-creation breakdown."""
    deal_id: str = ""
    rcm_value: float = 0.0
    organic_growth: float = 0.0
    multiple_expansion: float = 0.0
    total_value_created: float = 0.0
    entry_ebitda: float = 0.0
    latest_ebitda: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundAttribution:
    """Fund-level aggregation of value created across all deals."""
    total_value_created: float = 0.0
    by_source: Dict[str, SourceAttribution] = field(default_factory=lambda: {
        "rcm_improvement": SourceAttribution(),
        "organic_growth": SourceAttribution(),
        "multiple_expansion": SourceAttribution(),
    })
    by_deal: Dict[str, DealAttribution] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_value_created": self.total_value_created,
            "by_source": {k: v.to_dict() for k, v in self.by_source.items()},
            "by_deal": {k: v.to_dict() for k, v in self.by_deal.items()},
        }


# ── Helpers ────────────────────────────────────────────────────────

def _load_v2_bridge_total(store: Any, deal_id: str) -> float:
    """Pull total recurring EBITDA delta from the v2 bridge in analysis_runs."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT packet_json FROM analysis_runs "
                "WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
                (deal_id,),
            ).fetchone()
        if row is None:
            return 0.0
        blob = row["packet_json"]
        if isinstance(blob, (bytes, memoryview)):
            data = json.loads(zlib.decompress(blob).decode())
        else:
            data = json.loads(blob)
        vbr = data.get("value_bridge_result") or {}
        return float(vbr.get("total_recurring_ebitda_delta") or 0)
    except Exception:  # noqa: BLE001
        logger.debug("Could not load v2 bridge for %s", deal_id)
        return 0.0


def _load_ebitda_trajectory(store: Any, deal_id: str) -> List[float]:
    """Pull the EBITDA values from quarterly_actuals, in order."""
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT kpis_json FROM quarterly_actuals "
                "WHERE deal_id = ? ORDER BY quarter",
                (deal_id,),
            ).fetchall()
        result = []
        for r in rows:
            kpis = json.loads(r["kpis_json"] or "{}")
            if "ebitda" in kpis:
                result.append(float(kpis["ebitda"]))
        return result
    except Exception:  # noqa: BLE001
        logger.debug("Could not load EBITDA trajectory for %s", deal_id)
        return []


def _load_entry_ebitda(store: Any, deal_id: str) -> float:
    """Pull entry EBITDA from the plan values in quarterly actuals or snapshot."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT plan_kpis_json FROM quarterly_actuals "
                "WHERE deal_id = ? ORDER BY quarter ASC LIMIT 1",
                (deal_id,),
            ).fetchone()
        if row and row["plan_kpis_json"]:
            plan = json.loads(row["plan_kpis_json"])
            if "ebitda" in plan:
                return float(plan["ebitda"])
    except Exception:  # noqa: BLE001
        logger.debug("Could not load entry EBITDA for %s", deal_id)
    return 0.0


def _all_deal_ids(store: Any) -> List[str]:
    """Return all deal_ids from the deals table."""
    try:
        with store.connect() as con:
            rows = con.execute("SELECT deal_id FROM deals").fetchall()
        return [r["deal_id"] for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _has_hold_actuals(store: Any, deal_id: str) -> bool:
    """True if the deal has at least one quarterly_actuals row."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT 1 FROM quarterly_actuals WHERE deal_id = ? LIMIT 1",
                (deal_id,),
            ).fetchone()
        return row is not None
    except Exception:  # noqa: BLE001
        return False


# ── Public API ─────────────────────────────────────────────────────

def compute_fund_attribution(
    store: Any,
    *,
    deals: Optional[List[str]] = None,
) -> FundAttribution:
    """Compute fund-level value-creation attribution.

    For each deal with hold-period actuals:
    - RCM value = total_recurring_ebitda_delta from the v2 bridge.
    - Organic growth = (latest EBITDA - entry EBITDA) - RCM value.
    - Multiple expansion = placeholder (0 until entry/exit multiples
      are captured in the schema).

    Parameters
    ----------
    store
        PortfolioStore with deals, analysis_runs, and quarterly_actuals.
    deals
        Subset of deal_ids to include. ``None`` means all deals with
        hold-period actuals.
    """
    if deals is None:
        all_ids = _all_deal_ids(store)
        deals = [d for d in all_ids if _has_hold_actuals(store, d)]

    total_rcm = 0.0
    total_organic = 0.0
    total_multiple = 0.0
    deal_attrs: Dict[str, DealAttribution] = {}

    for did in deals:
        rcm_value = _load_v2_bridge_total(store, did)
        trajectory = _load_ebitda_trajectory(store, did)
        entry = _load_entry_ebitda(store, did)

        latest = trajectory[-1] if trajectory else entry
        total_ebitda_change = latest - entry if entry else 0.0

        # Organic = total change minus RCM attribution
        organic = max(0.0, total_ebitda_change - rcm_value)

        # Multiple expansion placeholder
        multiple_exp = 0.0

        deal_total = rcm_value + organic + multiple_exp

        deal_attrs[did] = DealAttribution(
            deal_id=did,
            rcm_value=rcm_value,
            organic_growth=organic,
            multiple_expansion=multiple_exp,
            total_value_created=deal_total,
            entry_ebitda=entry,
            latest_ebitda=latest,
        )

        total_rcm += rcm_value
        total_organic += organic
        total_multiple += multiple_exp

    grand_total = total_rcm + total_organic + total_multiple

    def _pct(part: float) -> float:
        return (part / grand_total * 100) if grand_total else 0.0

    attr = FundAttribution(
        total_value_created=grand_total,
        by_source={
            "rcm_improvement": SourceAttribution(
                dollar_amount=total_rcm,
                pct_of_total=_pct(total_rcm),
            ),
            "organic_growth": SourceAttribution(
                dollar_amount=total_organic,
                pct_of_total=_pct(total_organic),
            ),
            "multiple_expansion": SourceAttribution(
                dollar_amount=total_multiple,
                pct_of_total=_pct(total_multiple),
            ),
        },
        by_deal=deal_attrs,
    )
    return attr


def format_fund_attribution(attr: FundAttribution) -> str:
    """Terminal-friendly summary of fund attribution."""
    lines = []
    lines.append("=" * 60)
    lines.append("FUND VALUE-CREATION ATTRIBUTION")
    lines.append("=" * 60)
    lines.append(f"Total Value Created: ${attr.total_value_created:,.2f}")
    lines.append("")
    lines.append("By Source:")
    lines.append("-" * 40)
    for source, sa in attr.by_source.items():
        label = source.replace("_", " ").title()
        lines.append(f"  {label:<25s} ${sa.dollar_amount:>14,.2f}  ({sa.pct_of_total:5.1f}%)")
    lines.append("")
    if attr.by_deal:
        lines.append("By Deal:")
        lines.append("-" * 40)
        for did, da in attr.by_deal.items():
            lines.append(f"  {did}")
            lines.append(f"    Entry EBITDA:    ${da.entry_ebitda:>14,.2f}")
            lines.append(f"    Latest EBITDA:   ${da.latest_ebitda:>14,.2f}")
            lines.append(f"    RCM Value:       ${da.rcm_value:>14,.2f}")
            lines.append(f"    Organic Growth:  ${da.organic_growth:>14,.2f}")
            lines.append(f"    Total:           ${da.total_value_created:>14,.2f}")
    lines.append("=" * 60)
    return "\n".join(lines)

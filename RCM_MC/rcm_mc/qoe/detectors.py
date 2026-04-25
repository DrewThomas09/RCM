"""Rule-based QoE adjustment detectors.

Each detector takes a ``financial_panel`` dict (the standard QoE
target deal artefact) and returns a list of ``QoEFlag``s where
the rule fires. A single detector can return zero or many flags.

The financial_panel shape (the canonical target-data dict every
detector expects):

    {
      "deal_name": "...",
      "periods": ["2023", "2024", "TTM"],
      "income_statement": {
          "revenue": [180.0, 195.0, 205.0],
          "cogs": [...],
          "gross_profit": [...],
          "opex_compensation": [...],   # owner + officer comp
          "opex_other": [...],
          "ebitda_reported": [...],
          "non_recurring_items": [
              {"period": "2024", "amount": 4.5,
               "description": "Lawsuit settlement"}
          ],
          ...
      },
      "balance_sheet": {
          "ar": [...],
          "inventory": [...],
          "ap": [...],
          ...
      },
      "cash_flow": {
          "cash_receipts": [...],
          "cash_disbursements": [...]
      },
      "related_party": [
          {"counterparty": "...", "period": "2024",
           "amount": 1.2, "type": "lease",
           "market_rate_amount": 0.85}
      ],
      "owner_compensation": {
          "actual": [...],
          "benchmark": [...]   # market-rate comp for the role
      },
      # Healthcare-specific
      "payer_mix": {
          "self_pay_share": [0.05, 0.07, 0.18],   # cash-pay mix
          "out_of_network_share": [...]
      },
      "drug_revenue": {
          "340b_accumulator": [0.0, 1.4, 4.2]    # 340B margin captured
      }
    }

All amounts in $M unless stated otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QoEFlag:
    """One flagged QoE adjustment."""
    flag_id: str               # canonical id (e.g. "NR_001")
    category: str              # category bucket
    title: str
    description: str
    period: str = ""           # period when the issue surfaces
    proposed_adjustment_mm: float = 0.0  # ± to EBITDA
    confidence: float = 0.5    # 0-1
    evidence: List[str] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────

def _periods(panel: Dict[str, Any]) -> List[str]:
    return list(panel.get("periods", []) or [])


def _series(panel: Dict[str, Any], section: str,
            key: str) -> List[float]:
    sec = panel.get(section, {}) or {}
    return list(sec.get(key, []) or [])


# ── 1. Non-recurring items ───────────────────────────────────────

def detect_non_recurring(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag any explicitly listed non-recurring items hitting EBITDA.

    Rule: every item in income_statement.non_recurring_items is a
    candidate adjustment. Confidence = 0.95 if the deal team has
    already labeled it; 0.6 if we're inferring from large unusual
    one-period spikes (handled by the anomaly detector).
    """
    out: List[QoEFlag] = []
    items = (panel.get("income_statement", {}) or {}).get(
        "non_recurring_items", []) or []
    for i, item in enumerate(items):
        amount = float(item.get("amount", 0) or 0)
        if amount == 0:
            continue
        out.append(QoEFlag(
            flag_id=f"NR_{i+1:03d}",
            category="non_recurring",
            title=item.get("description", "Non-recurring item"),
            description=(
                f"Non-recurring item identified by management: "
                f"{item.get('description', 'unspecified')}. "
                f"Removing from EBITDA per QoE convention."),
            period=str(item.get("period", "")),
            proposed_adjustment_mm=-amount,  # remove from EBITDA
            confidence=0.95,
            evidence=[
                f"income_statement.non_recurring_items[{i}]: "
                f"${amount:.2f}M",
            ],
        ))
    return out


# ── 2. Owner compensation ────────────────────────────────────────

def detect_owner_compensation(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag actual owner comp materially above the role benchmark."""
    out: List[QoEFlag] = []
    block = panel.get("owner_compensation", {}) or {}
    actual = list(block.get("actual", []) or [])
    bench = list(block.get("benchmark", []) or [])
    periods = _periods(panel)
    n = min(len(actual), len(bench), len(periods))
    for i in range(n):
        excess = actual[i] - bench[i]
        if excess <= 0.05:        # under $50K excess → ignore
            continue
        # Confidence scales with the magnitude
        conf = min(0.95, 0.5 + (excess / max(0.5, bench[i])) * 0.5)
        out.append(QoEFlag(
            flag_id=f"OC_{i+1:03d}",
            category="owner_compensation",
            title="Owner compensation above market",
            description=(
                f"Owner/officer compensation of ${actual[i]:.2f}M "
                f"exceeds role benchmark ${bench[i]:.2f}M by "
                f"${excess:.2f}M. Add back per QoE convention."),
            period=str(periods[i]),
            proposed_adjustment_mm=excess,
            confidence=round(conf, 3),
            evidence=[
                f"owner_compensation.actual[{i}]: ${actual[i]:.2f}M",
                f"owner_compensation.benchmark[{i}]: ${bench[i]:.2f}M",
            ],
        ))
    return out


# ── 3. Revenue recognition ───────────────────────────────────────

def detect_revenue_recognition(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag periods where revenue grows materially faster than AR
    days receivable would suggest, signaling premature recognition
    or channel stuffing."""
    out: List[QoEFlag] = []
    revenue = _series(panel, "income_statement", "revenue")
    ar = _series(panel, "balance_sheet", "ar")
    periods = _periods(panel)
    if len(revenue) < 2 or len(ar) < 2 or len(periods) < 2:
        return out
    n = min(len(revenue), len(ar), len(periods))
    for i in range(1, n):
        if revenue[i-1] <= 0:
            continue
        rev_growth = (revenue[i] - revenue[i-1]) / revenue[i-1]
        ar_growth = (ar[i] - ar[i-1]) / max(0.01, ar[i-1])
        # Red flag: AR grew >2× faster than revenue (collections
        # falling behind), or shrunk while revenue grew >20%
        if (ar_growth > rev_growth * 2 and rev_growth > 0.05) \
                or (rev_growth > 0.20 and ar_growth < -0.05):
            mag = abs(rev_growth - ar_growth) * revenue[i-1] * 0.5
            out.append(QoEFlag(
                flag_id=f"RR_{i:03d}",
                category="revenue_recognition",
                title="Revenue / AR growth divergence",
                description=(
                    f"Revenue grew {rev_growth*100:.1f}% but AR "
                    f"moved {ar_growth*100:.1f}% — material "
                    f"divergence suggests aggressive recognition or "
                    f"channel stuffing. Reserve for collection risk."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(mag, 2),
                confidence=0.65,
                evidence=[
                    f"revenue: ${revenue[i-1]:.1f}M → ${revenue[i]:.1f}M",
                    f"AR: ${ar[i-1]:.1f}M → ${ar[i]:.1f}M",
                ],
            ))
    return out


# ── 4. NWC manipulation ──────────────────────────────────────────

def detect_nwc_manipulation(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag year-end NWC drops that reverse the next period."""
    out: List[QoEFlag] = []
    bs = panel.get("balance_sheet", {}) or {}
    ar = list(bs.get("ar", []) or [])
    ap = list(bs.get("ap", []) or [])
    inventory = list(bs.get("inventory", []) or [])
    periods = _periods(panel)

    def _nwc(i: int) -> float:
        return ((ar[i] if i < len(ar) else 0)
                + (inventory[i] if i < len(inventory) else 0)
                - (ap[i] if i < len(ap) else 0))

    n = len(periods)
    if n < 3:
        return out
    for i in range(1, n - 1):
        nwc_prev = _nwc(i-1)
        nwc_now = _nwc(i)
        nwc_next = _nwc(i+1)
        # V-shape: down then back up
        if (nwc_now < nwc_prev * 0.85
                and nwc_next > nwc_now * 1.15):
            magnitude = nwc_prev - nwc_now
            out.append(QoEFlag(
                flag_id=f"NWC_{i:03d}",
                category="nwc_manipulation",
                title="V-shaped NWC at period end",
                description=(
                    f"NWC dropped from ${nwc_prev:.1f}M to "
                    f"${nwc_now:.1f}M and rebounded to "
                    f"${nwc_next:.1f}M — classic year-end "
                    f"window-dressing pattern. Normalize NWC peg "
                    f"using TTM average."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(magnitude, 2),
                confidence=0.7,
                evidence=[
                    f"NWC[{periods[i-1]}]={nwc_prev:.1f}M, "
                    f"NWC[{periods[i]}]={nwc_now:.1f}M, "
                    f"NWC[{periods[i+1]}]={nwc_next:.1f}M",
                ],
            ))
    return out


# ── 5. Related-party transactions ────────────────────────────────

def detect_related_party(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag related-party transactions priced off market."""
    out: List[QoEFlag] = []
    rp = panel.get("related_party", []) or []
    for i, item in enumerate(rp):
        amount = float(item.get("amount", 0) or 0)
        market = float(item.get("market_rate_amount", 0) or 0)
        if amount == 0 or market == 0:
            continue
        delta = amount - market
        # If the related-party rate is meaningfully off market,
        # flag — direction depends on whether target is the
        # payer (delta positive = overpayment, EBITDA add-back)
        # or payee (delta negative = underpayment of related
        # party, but for QoE we flag the abnormal level).
        if abs(delta) / max(0.1, market) > 0.10:
            out.append(QoEFlag(
                flag_id=f"RP_{i+1:03d}",
                category="related_party",
                title="Off-market related-party transaction",
                description=(
                    f"{item.get('type', 'transaction').capitalize()} "
                    f"with {item.get('counterparty', 'related party')} "
                    f"at ${amount:.2f}M vs market rate "
                    f"${market:.2f}M — adjust to market "
                    f"per QoE convention."),
                period=str(item.get("period", "")),
                proposed_adjustment_mm=round(delta, 2),
                confidence=0.85,
                evidence=[
                    f"related_party[{i}]: amount=${amount:.2f}M, "
                    f"market=${market:.2f}M",
                ],
            ))
    return out


# ── 6. Proof-of-cash gaps ────────────────────────────────────────

def detect_proof_of_cash(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag periods where reported revenue and cash receipts
    diverge beyond a normal collections lag."""
    out: List[QoEFlag] = []
    rev = _series(panel, "income_statement", "revenue")
    cash = _series(panel, "cash_flow", "cash_receipts")
    periods = _periods(panel)
    n = min(len(rev), len(cash), len(periods))
    for i in range(n):
        if rev[i] <= 0:
            continue
        # Tolerance: within 10% of revenue
        gap_pct = (rev[i] - cash[i]) / rev[i]
        if abs(gap_pct) > 0.10:
            out.append(QoEFlag(
                flag_id=f"PC_{i+1:03d}",
                category="proof_of_cash",
                title="Proof-of-cash gap",
                description=(
                    f"Revenue ${rev[i]:.1f}M vs cash receipts "
                    f"${cash[i]:.1f}M — {gap_pct*100:.1f}% gap "
                    f"exceeds normal collections lag. Investigate."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(
                    (rev[i] - cash[i]) * 0.5, 2),
                confidence=0.7,
                evidence=[
                    f"revenue[{i}]=${rev[i]:.1f}M, "
                    f"cash_receipts[{i}]=${cash[i]:.1f}M",
                ],
            ))
    return out


# ── Healthcare-specific detectors ───────────────────────────────

def detect_340b_accumulator(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag periods where 340B accumulator revenue is large enough
    that the EBITDA depends on a regulatory program with active
    federal litigation. Add back as risk-adjusted."""
    out: List[QoEFlag] = []
    drug = panel.get("drug_revenue", {}) or {}
    accum = list(drug.get("340b_accumulator", []) or [])
    revenue = _series(panel, "income_statement", "revenue")
    periods = _periods(panel)
    n = min(len(accum), len(revenue), len(periods))
    for i in range(n):
        if accum[i] <= 0:
            continue
        share = accum[i] / max(0.1, revenue[i])
        if share > 0.05:
            out.append(QoEFlag(
                flag_id=f"H340_{i+1:03d}",
                category="340b_accumulator",
                title="340B accumulator revenue exposure",
                description=(
                    f"${accum[i]:.2f}M of revenue "
                    f"({share*100:.1f}% of total) flows from 340B "
                    f"accumulator/contract pharmacy program — "
                    f"regulatory exposure justifies a haircut on "
                    f"the run-rate."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(accum[i] * 0.30, 2),
                confidence=0.55,
                evidence=[
                    f"drug_revenue.340b_accumulator[{i}]="
                    f"${accum[i]:.2f}M",
                ],
            ))
    return out


def detect_oon_balance_billing(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag periods where OON share is high — bad-debt risk and
    regulatory exposure under the No Surprises Act."""
    out: List[QoEFlag] = []
    pm = panel.get("payer_mix", {}) or {}
    oon_share = list(pm.get("out_of_network_share", []) or [])
    revenue = _series(panel, "income_statement", "revenue")
    periods = _periods(panel)
    n = min(len(oon_share), len(revenue), len(periods))
    for i in range(n):
        if oon_share[i] > 0.10:
            exposed_rev = oon_share[i] * revenue[i]
            out.append(QoEFlag(
                flag_id=f"OON_{i+1:03d}",
                category="oon_balance_billing",
                title="Out-of-network revenue exposure",
                description=(
                    f"{oon_share[i]*100:.1f}% of revenue is OON. "
                    f"No Surprises Act + bad-debt risk warrant a "
                    f"haircut on the run-rate."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(exposed_rev * 0.20, 2),
                confidence=0.6,
                evidence=[
                    f"payer_mix.out_of_network_share[{i}]="
                    f"{oon_share[i]:.1%}",
                ],
            ))
    return out


def detect_cash_pay_mix(panel: Dict[str, Any]) -> List[QoEFlag]:
    """Flag periods where self-pay (cash-pay) share spikes —
    transient demand that won't repeat post-close."""
    out: List[QoEFlag] = []
    pm = panel.get("payer_mix", {}) or {}
    cash_share = list(pm.get("self_pay_share", []) or [])
    revenue = _series(panel, "income_statement", "revenue")
    periods = _periods(panel)
    if len(cash_share) < 2:
        return out
    n = min(len(cash_share), len(revenue), len(periods))
    for i in range(1, n):
        if cash_share[i] > cash_share[i-1] * 1.5 \
                and cash_share[i] > 0.10:
            spike = (cash_share[i] - cash_share[i-1]) * revenue[i]
            out.append(QoEFlag(
                flag_id=f"CASH_{i:03d}",
                category="cash_pay_mix",
                title="Self-pay mix spike",
                description=(
                    f"Self-pay share jumped from "
                    f"{cash_share[i-1]*100:.1f}% to "
                    f"{cash_share[i]*100:.1f}%. Pandemic-era cash "
                    f"surges typically don't repeat — normalize "
                    f"forward run-rate."),
                period=str(periods[i]),
                proposed_adjustment_mm=-round(spike * 0.5, 2),
                confidence=0.65,
                evidence=[
                    f"self_pay_share: "
                    f"{cash_share[i-1]:.1%} → {cash_share[i]:.1%}",
                ],
            ))
    return out


# ── Composite runner ─────────────────────────────────────────────

_DETECTORS = (
    detect_non_recurring,
    detect_owner_compensation,
    detect_revenue_recognition,
    detect_nwc_manipulation,
    detect_related_party,
    detect_proof_of_cash,
    detect_340b_accumulator,
    detect_oon_balance_billing,
    detect_cash_pay_mix,
)


def run_rule_detectors(panel: Dict[str, Any]) -> List[QoEFlag]:
    flags: List[QoEFlag] = []
    for d in _DETECTORS:
        try:
            flags.extend(d(panel))
        except Exception:  # noqa: BLE001
            # Don't let a single broken input block the rest of
            # the suite — partner gets all detectable signals.
            continue
    flags.sort(
        key=lambda f: abs(f.proposed_adjustment_mm),
        reverse=True,
    )
    return flags

"""Working capital peer bands — DSO / DPO / DIO benchmarks.

Working capital is a cash-generation lever. Healthcare-PE peer
bands (partner-approximated):

- **DSO** (AR days): specialty practices 35-55d; hospitals 45-60d;
  ASC 40-50d; DME 55-85d; home health 50-70d.
- **DPO** (AP days): 30-45d most subsectors; DME 40-60d.
- **DIO** (inventory days): ASC 15-25d; hospital 30-45d; DME
  45-60d; practices 5-15d.

Cash conversion cycle = DSO + DIO - DPO. Negative or low values
indicate working-capital-favorable operations.

This module takes actuals + subsector and returns a peer-band
verdict and estimated cash release from moving each lever to the
favorable end of the band.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


WC_PEER_BANDS: Dict[str, Dict[str, tuple]] = {
    "specialty_practice": {
        "dso": (35.0, 55.0), "dpo": (30.0, 45.0), "dio": (5.0, 15.0),
    },
    "hospital": {
        "dso": (45.0, 60.0), "dpo": (30.0, 45.0), "dio": (30.0, 45.0),
    },
    "outpatient_asc": {
        "dso": (40.0, 50.0), "dpo": (30.0, 45.0), "dio": (15.0, 25.0),
    },
    "dme_supplier": {
        "dso": (55.0, 85.0), "dpo": (40.0, 60.0), "dio": (45.0, 60.0),
    },
    "home_health": {
        "dso": (50.0, 70.0), "dpo": (30.0, 45.0), "dio": (0.0, 5.0),
    },
}


@dataclass
class WCInputs:
    subsector: str
    revenue_m: float
    cogs_m: float
    dso_days: float
    dpo_days: float
    dio_days: float


@dataclass
class WCLever:
    component: str                        # "dso" / "dpo" / "dio"
    actual: float
    band_low: float
    band_high: float
    verdict: str                          # "favorable" / "in_band" / "unfavorable"
    cash_release_m: float                 # $ released moving to favorable end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "actual": self.actual,
            "band_low": self.band_low,
            "band_high": self.band_high,
            "verdict": self.verdict,
            "cash_release_m": self.cash_release_m,
        }


@dataclass
class WCPeerReport:
    subsector: str
    cash_conversion_cycle: float
    levers: List[WCLever] = field(default_factory=list)
    total_cash_opportunity_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "cash_conversion_cycle": self.cash_conversion_cycle,
            "levers": [l.to_dict() for l in self.levers],
            "total_cash_opportunity_m": self.total_cash_opportunity_m,
            "partner_note": self.partner_note,
        }


def _revenue_per_day(rev_m: float) -> float:
    return rev_m / 365.0


def _cogs_per_day(cogs_m: float) -> float:
    return cogs_m / 365.0


def benchmark_working_capital(inputs: WCInputs) -> WCPeerReport:
    bands = WC_PEER_BANDS.get(inputs.subsector)
    if bands is None:
        return WCPeerReport(
            subsector=inputs.subsector,
            cash_conversion_cycle=round(
                inputs.dso_days + inputs.dio_days - inputs.dpo_days, 2),
            partner_note=f"Subsector {inputs.subsector!r} not in WC library.",
        )

    rpd = _revenue_per_day(inputs.revenue_m)
    cpd = _cogs_per_day(inputs.cogs_m)

    levers: List[WCLever] = []

    # DSO: lower is better.
    dso_lo, dso_hi = bands["dso"]
    dso_verdict = ("favorable" if inputs.dso_days <= dso_lo
                   else "in_band" if inputs.dso_days <= dso_hi
                   else "unfavorable")
    dso_release = max(0.0, (inputs.dso_days - dso_lo) * rpd)
    levers.append(WCLever(
        component="dso", actual=inputs.dso_days,
        band_low=dso_lo, band_high=dso_hi,
        verdict=dso_verdict,
        cash_release_m=round(dso_release, 2),
    ))

    # DPO: higher is better.
    dpo_lo, dpo_hi = bands["dpo"]
    dpo_verdict = ("favorable" if inputs.dpo_days >= dpo_hi
                   else "in_band" if inputs.dpo_days >= dpo_lo
                   else "unfavorable")
    dpo_release = max(0.0, (dpo_hi - inputs.dpo_days) * cpd)
    levers.append(WCLever(
        component="dpo", actual=inputs.dpo_days,
        band_low=dpo_lo, band_high=dpo_hi,
        verdict=dpo_verdict,
        cash_release_m=round(dpo_release, 2),
    ))

    # DIO: lower is better.
    dio_lo, dio_hi = bands["dio"]
    dio_verdict = ("favorable" if inputs.dio_days <= dio_lo
                   else "in_band" if inputs.dio_days <= dio_hi
                   else "unfavorable")
    dio_release = max(0.0, (inputs.dio_days - dio_lo) * cpd)
    levers.append(WCLever(
        component="dio", actual=inputs.dio_days,
        band_low=dio_lo, band_high=dio_hi,
        verdict=dio_verdict,
        cash_release_m=round(dio_release, 2),
    ))

    ccc = inputs.dso_days + inputs.dio_days - inputs.dpo_days
    total_release = sum(l.cash_release_m for l in levers)

    unfavorable = [l for l in levers if l.verdict == "unfavorable"]
    if len(unfavorable) >= 2:
        note = (f"WC posture weak on {len(unfavorable)} levers. "
                f"~${total_release:,.1f}M cash release available by "
                "moving to peer-favorable end. CCC "
                f"{ccc:.0f}d — high priority lever.")
    elif unfavorable:
        note = (f"WC weak link: {unfavorable[0].component.upper()} — "
                f"~${unfavorable[0].cash_release_m:,.1f}M release "
                "available.")
    elif total_release >= 5.0:
        note = (f"WC in-band but ~${total_release:,.1f}M residual "
                "opportunity to best-in-class.")
    else:
        note = (f"WC posture strong (CCC {ccc:.0f}d). Preserve, don't "
                "optimize further.")

    return WCPeerReport(
        subsector=inputs.subsector,
        cash_conversion_cycle=round(ccc, 2),
        levers=levers,
        total_cash_opportunity_m=round(total_release, 2),
        partner_note=note,
    )


def render_wc_markdown(r: WCPeerReport) -> str:
    lines = [
        f"# Working capital peer band — {r.subsector}",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Cash conversion cycle: {r.cash_conversion_cycle:.1f} days",
        f"- Total opportunity: ${r.total_cash_opportunity_m:,.1f}M",
        "",
        "| Lever | Actual | Low | High | Verdict | Release |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for l in r.levers:
        lines.append(
            f"| {l.component.upper()} | {l.actual:.1f}d | "
            f"{l.band_low:.1f}d | {l.band_high:.1f}d | {l.verdict} | "
            f"${l.cash_release_m:,.2f}M |"
        )
    return "\n".join(lines)

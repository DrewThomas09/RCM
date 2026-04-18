"""Fund-level vintage impact — what does this deal do to *the fund*.

Partner statement: "Every deal is evaluated on its
own IRR, but that's not how LPs grade us. They grade
us on fund TVPI, DPI by year five, and where we rank
in the vintage. A 22% IRR deal that soaks up 15% of
committed capital and doesn't return cash for seven
years can still drag the fund below its vintage peer
median. Size the deal against the fund, not itself."

Distinct from `fund_model` (fund-level LBO math) and
`vintage_return_curve` (vintage pacing curve). This
module asks a different question: **what does adding
this deal do to the fund's LP-facing metrics vs.
vintage peers** (PME, DPI-by-year-N, net TVPI, and
the concentration risk of a single position).

### 6 fund-impact dimensions

1. **capital_concentration** — equity as % of fund
   committed capital. >15% is single-deal risk; >10%
   requires coinvest to de-risk.
2. **dpi_timing_drag** — years from close to first
   distribution. PE median is 4-5; past 6 years drags
   DPI-by-year-5 below vintage median.
3. **tvpi_contribution** — deal's expected MOIC
   weighted by capital share. Measures how much the
   deal can pull fund TVPI up (or down).
4. **vintage_peer_rank** — implied quartile ranking in
   the fund's vintage based on deal IRR vs. Cambridge /
   Burgiss vintage medians.
5. **pme_delta** — public market equivalent vs. the
   healthcare PE peer benchmark (S&P Healthcare Services
   + leverage-adjusted). Net IRR vs. benchmark.
6. **reserve_consumption** — follow-on / add-on capital
   reserved for this platform as % of remaining fund
   dry powder. >30% is platform-bet territory.

### Partner-voice verdict tiers

- **fund_accretive** — deal lifts fund TVPI and DPI
  timing is on-par. Signal: "good for the fund, not
  just good on its own."
- **fund_neutral** — deal hits vintage median but
  doesn't move the needle. Signal: "size down or pass
  unless you love it."
- **fund_dilutive** — deal's capital weight drags fund
  metrics even if deal IRR is respectable. Signal:
  "right deal, wrong fund — pass or coinvest heavily."

### Output

Per-dimension score, vintage-peer rank band, fund-level
partner note explicit on "this deal's effect on *the
fund*."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FundVintageInputs:
    fund_committed_capital_m: float = 800.0
    fund_dry_powder_remaining_m: float = 400.0
    fund_vintage_year: int = 2026
    deal_equity_check_m: float = 80.0
    follow_on_reserved_m: float = 30.0
    expected_deal_gross_moic: float = 2.5
    expected_deal_gross_irr: float = 0.22
    years_to_first_distribution: float = 4.5
    hold_years: float = 5.5
    vintage_peer_median_net_irr: float = 0.17
    vintage_peer_top_quartile_net_irr: float = 0.22
    vintage_peer_top_decile_net_irr: float = 0.28
    healthcare_sector_benchmark_irr: float = 0.14
    coinvest_committed_m: float = 0.0


@dataclass
class FundDimensionScore:
    name: str
    metric: str
    value: float
    threshold_band: str
    partner_read: str


@dataclass
class FundVintageReport:
    dimensions: List[FundDimensionScore] = field(
        default_factory=list)
    capital_weight_pct: float = 0.0
    reserve_weight_pct: float = 0.0
    implied_fund_tvpi_lift: float = 0.0
    implied_vintage_quartile: int = 3
    pme_delta_bps: int = 0
    verdict: str = "fund_neutral"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": [
                {"name": d.name,
                 "metric": d.metric,
                 "value": d.value,
                 "threshold_band": d.threshold_band,
                 "partner_read": d.partner_read}
                for d in self.dimensions
            ],
            "capital_weight_pct": self.capital_weight_pct,
            "reserve_weight_pct": self.reserve_weight_pct,
            "implied_fund_tvpi_lift":
                self.implied_fund_tvpi_lift,
            "implied_vintage_quartile":
                self.implied_vintage_quartile,
            "pme_delta_bps": self.pme_delta_bps,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def _quartile_from_irr(
    irr: float,
    median: float,
    top_quartile: float,
    top_decile: float,
) -> int:
    if irr >= top_decile:
        return 1
    if irr >= top_quartile:
        return 1
    if irr >= median:
        return 2
    if irr >= median * 0.75:
        return 3
    return 4


def _quartile_label(q: int) -> str:
    return {
        1: "top quartile",
        2: "second quartile",
        3: "third quartile",
        4: "bottom quartile",
    }.get(q, "unranked")


def score_fund_vintage_impact(
    inputs: FundVintageInputs,
) -> FundVintageReport:
    committed = max(1.0, inputs.fund_committed_capital_m)
    dry_powder = max(1.0, inputs.fund_dry_powder_remaining_m)
    # net-of-coinvest check from the main fund
    net_check = max(
        0.0,
        inputs.deal_equity_check_m -
        inputs.coinvest_committed_m,
    )
    capital_weight = net_check / committed
    reserve_weight = inputs.follow_on_reserved_m / dry_powder

    # net IRR rough proxy: gross IRR minus 200bps fees/carry drag
    # (post-fee LP IRR; the coarse standard partner uses when
    # glancing at vintage peer tables).
    net_irr = inputs.expected_deal_gross_irr - 0.02

    # capital concentration
    if capital_weight > 0.15:
        cap_band = "single-deal concentration risk"
        cap_read = (
            "Deal equity > 15% of fund committed. "
            "Single-deal blow-up threatens the fund; "
            "size down or bring coinvest to cap fund "
            "exposure at 10%."
        )
    elif capital_weight > 0.10:
        cap_band = "platform-sized"
        cap_read = (
            "10-15% weight — platform territory. "
            "Acceptable only if thesis is platform / "
            "roll-up and add-ons will absorb the "
            "outsize position."
        )
    elif capital_weight > 0.05:
        cap_band = "portfolio-balanced"
        cap_read = (
            "5-10% weight — standard portfolio sizing. "
            "Fund can absorb a mark-down without "
            "derailing vintage metrics."
        )
    else:
        cap_band = "small position"
        cap_read = (
            "<5% weight — small enough that even full "
            "write-off is absorbed. But also small "
            "enough that outperformance is muted."
        )

    # DPI timing
    dpi_years = inputs.years_to_first_distribution
    if dpi_years > 6.0:
        dpi_band = "DPI drag"
        dpi_read = (
            f"{dpi_years:.1f} yr to first distribution — "
            "drags fund DPI-by-year-5 below vintage "
            "median. LPs will notice."
        )
    elif dpi_years > 5.0:
        dpi_band = "slow"
        dpi_read = (
            f"{dpi_years:.1f} yr — slow but within "
            "vintage norm. Dividend recap in year 3-4 "
            "would rehabilitate DPI pacing."
        )
    elif dpi_years >= 3.0:
        dpi_band = "on-pace"
        dpi_read = (
            f"{dpi_years:.1f} yr — standard PE timing. "
            "DPI-by-year-5 tracks vintage median."
        )
    else:
        dpi_band = "fast-DPI"
        dpi_read = (
            f"{dpi_years:.1f} yr — fast return of "
            "capital; LP-friendly pacing."
        )

    # TVPI contribution: capital-weighted MOIC lift
    tvpi_lift = capital_weight * (
        inputs.expected_deal_gross_moic - 1.0)
    if tvpi_lift > 0.15:
        tvpi_band = "accretive"
        tvpi_read = (
            f"Contributes +{tvpi_lift:.2f} to fund TVPI "
            "— meaningful lift to aggregate fund mark."
        )
    elif tvpi_lift > 0.05:
        tvpi_band = "modest-lift"
        tvpi_read = (
            f"Contributes +{tvpi_lift:.2f} to fund "
            "TVPI — positive but doesn't move the "
            "needle."
        )
    elif tvpi_lift > 0:
        tvpi_band = "marginal"
        tvpi_read = (
            f"+{tvpi_lift:.2f} TVPI contribution — "
            "barely distinguishable from cash yield. "
            "Opportunity cost is real."
        )
    else:
        tvpi_band = "dilutive"
        tvpi_read = (
            f"TVPI contribution {tvpi_lift:.2f} — "
            "deal actively dilutes fund mark. Pass."
        )

    # Vintage quartile
    quartile = _quartile_from_irr(
        net_irr,
        inputs.vintage_peer_median_net_irr,
        inputs.vintage_peer_top_quartile_net_irr,
        inputs.vintage_peer_top_decile_net_irr,
    )
    peer_band = _quartile_label(quartile)
    peer_read = (
        f"Net IRR {net_irr:.1%} vs. vintage median "
        f"{inputs.vintage_peer_median_net_irr:.1%} → "
        f"{peer_band}. "
    )
    if quartile == 1:
        peer_read += (
            "Top-quartile deal lifts fund's vintage rank."
        )
    elif quartile == 2:
        peer_read += (
            "Median-performing — neutral to vintage rank."
        )
    else:
        peer_read += (
            "Below vintage median — drags fund rank."
        )

    # PME delta (net IRR vs. sector benchmark)
    pme_delta = int(round(
        (net_irr - inputs.healthcare_sector_benchmark_irr)
        * 10000
    ))
    if pme_delta >= 500:
        pme_band = "strong-PME"
        pme_read = (
            f"Net IRR beats healthcare public benchmark "
            f"by {pme_delta} bps. LP story: 'we're "
            "earning the illiquidity premium.'"
        )
    elif pme_delta >= 200:
        pme_band = "modest-PME"
        pme_read = (
            f"Beats benchmark by {pme_delta} bps — "
            "earns the illiquidity premium but not "
            "dramatically."
        )
    elif pme_delta >= 0:
        pme_band = "at-PME"
        pme_read = (
            f"{pme_delta} bps over benchmark — barely "
            "earns the illiquidity premium. LP push-"
            "back expected."
        )
    else:
        pme_band = "sub-PME"
        pme_read = (
            f"{pme_delta} bps — underperforms the "
            "healthcare public benchmark. Fails the "
            "LP illiquidity-premium test."
        )

    # Reserve consumption
    if reserve_weight > 0.30:
        rsv_band = "platform-bet"
        rsv_read = (
            f"Follow-on reserve = "
            f"{reserve_weight:.0%} of dry powder. "
            "Platform-bet territory; other platforms "
            "in the fund will be starved."
        )
    elif reserve_weight > 0.15:
        rsv_band = "heavy"
        rsv_read = (
            f"{reserve_weight:.0%} of dry powder "
            "reserved — heavy but defensible for a "
            "roll-up platform."
        )
    elif reserve_weight > 0.05:
        rsv_band = "standard"
        rsv_read = (
            f"{reserve_weight:.0%} of dry powder "
            "reserved — standard platform reserve."
        )
    else:
        rsv_band = "thin"
        rsv_read = (
            f"{reserve_weight:.0%} of dry powder — "
            "thin reserve; platform M&A will need "
            "new-fund capital."
        )

    dims = [
        FundDimensionScore(
            name="capital_concentration",
            metric="net equity / fund committed",
            value=round(capital_weight, 4),
            threshold_band=cap_band,
            partner_read=cap_read,
        ),
        FundDimensionScore(
            name="dpi_timing_drag",
            metric="years to first distribution",
            value=round(dpi_years, 2),
            threshold_band=dpi_band,
            partner_read=dpi_read,
        ),
        FundDimensionScore(
            name="tvpi_contribution",
            metric="capital-weighted MOIC lift",
            value=round(tvpi_lift, 4),
            threshold_band=tvpi_band,
            partner_read=tvpi_read,
        ),
        FundDimensionScore(
            name="vintage_peer_rank",
            metric="implied quartile",
            value=float(quartile),
            threshold_band=peer_band,
            partner_read=peer_read,
        ),
        FundDimensionScore(
            name="pme_delta",
            metric="bps over healthcare benchmark",
            value=float(pme_delta),
            threshold_band=pme_band,
            partner_read=pme_read,
        ),
        FundDimensionScore(
            name="reserve_consumption",
            metric="follow-on / dry powder",
            value=round(reserve_weight, 4),
            threshold_band=rsv_band,
            partner_read=rsv_read,
        ),
    ]

    # Verdict: triangulate across dims
    accretive_hits = sum(
        1 for b in (cap_band, dpi_band, tvpi_band,
                    peer_band, pme_band, rsv_band)
        if b in {"portfolio-balanced", "fast-DPI",
                 "accretive", "top quartile",
                 "strong-PME", "standard",
                 "on-pace", "modest-lift", "modest-PME"}
    )
    dilutive_hits = sum(
        1 for b in (cap_band, dpi_band, tvpi_band,
                    peer_band, pme_band, rsv_band)
        if b in {"single-deal concentration risk",
                 "DPI drag", "dilutive",
                 "third quartile", "bottom quartile",
                 "sub-PME", "platform-bet"}
    )

    if dilutive_hits >= 3:
        verdict = "fund_dilutive"
        note = (
            f"{dilutive_hits} fund-dilutive signals "
            f"(capital={capital_weight:.0%}, "
            f"net IRR={net_irr:.1%}, "
            f"TVPI lift={tvpi_lift:+.2f}). "
            "Right deal, wrong fund — pass or restructure "
            "with heavy coinvest to right-size fund "
            "exposure."
        )
    elif accretive_hits >= 4 and dilutive_hits == 0:
        verdict = "fund_accretive"
        note = (
            f"{accretive_hits} fund-accretive signals; "
            f"TVPI lift {tvpi_lift:+.2f}, "
            f"{peer_band} vintage, {pme_delta} bps over "
            "benchmark. Good for the fund, not just "
            "good on its own — proceed."
        )
    else:
        verdict = "fund_neutral"
        note = (
            f"Mixed fund impact — "
            f"accretive={accretive_hits}, "
            f"dilutive={dilutive_hits}. Deal hits vintage "
            "median but doesn't move fund metrics "
            "materially. Size down or pass unless IC "
            "loves the thesis on its own."
        )

    return FundVintageReport(
        dimensions=dims,
        capital_weight_pct=round(capital_weight, 4),
        reserve_weight_pct=round(reserve_weight, 4),
        implied_fund_tvpi_lift=round(tvpi_lift, 4),
        implied_vintage_quartile=quartile,
        pme_delta_bps=pme_delta,
        verdict=verdict,
        partner_note=note,
    )


def render_fund_vintage_markdown(
    r: FundVintageReport,
) -> str:
    lines = [
        "# Fund-level vintage impact",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Capital weight: {r.capital_weight_pct:.1%} of fund",
        f"- Reserve weight: {r.reserve_weight_pct:.1%} of dry powder",
        f"- Fund TVPI contribution: "
        f"{r.implied_fund_tvpi_lift:+.2f}",
        f"- Vintage quartile: "
        f"{_quartile_label(r.implied_vintage_quartile)}",
        f"- PME delta: {r.pme_delta_bps:+d} bps",
        "",
        "| Dimension | Value | Band | Partner read |",
        "|---|---|---|---|",
    ]
    for d in r.dimensions:
        lines.append(
            f"| {d.name} | {d.value} | "
            f"{d.threshold_band} | {d.partner_read} |"
        )
    return "\n".join(lines)

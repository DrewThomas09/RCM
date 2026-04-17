"""Deal portfolio construction — diversification analysis and concentration risk.

Answers the IC question: "Does adding this deal improve or worsen the
portfolio's diversification across sectors, vintages, and payer profiles?"

Computes:
  1. Portfolio HHI (sector, vintage, payer, sponsor)
  2. Marginal diversification score for a proposed new deal
  3. Optimal sector weight targets from corpus base rates
  4. Portfolio risk decomposition (sector × payer × vintage)
  5. Correlation-adjusted risk (sectors that historically co-move)

Key insight: healthcare PE portfolios frequently fail on concentration, not
on individual deal quality. The 2020-2023 period showed that Behavioral Health
+ Home Health + Primary Care can all deteriorate simultaneously (Medicaid
rates, labor, post-COVID census). Vintage concentration into 2021 was similarly
corrosive across the sector.

Public API:
    PortfolioComposition    dataclass (sector_weights, vintage_weights, payer_weights)
    DiversificationResult   dataclass (hhi_sector, hhi_vintage, marginal_score, signal)
    analyze_portfolio(portfolio_deals, corpus_deals) -> PortfolioComposition
    marginal_diversification(new_deal, portfolio_deals, corpus_deals) -> DiversificationResult
    portfolio_risk_report(composition, result) -> str
    optimal_sector_weights(corpus_deals) -> Dict[str, float]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Sector correlation matrix (historically co-moving sectors in healthcare PE)
# Higher value = more positively correlated = adds less diversification
# ---------------------------------------------------------------------------

_SECTOR_CORRELATION: Dict[Tuple[str, str], float] = {
    # Highly correlated (same macro drivers)
    ("Behavioral Health", "Substance Abuse"): 0.85,
    ("Home Health", "Skilled Nursing"): 0.75,
    ("Home Health", "Senior Living"): 0.65,
    ("Physician Practices", "Anesthesiology"): 0.70,
    ("Physician Practices", "Emergency Medicine"): 0.65,
    ("Emergency Medicine", "Anesthesiology"): 0.72,
    ("Primary Care", "Physician Practices"): 0.60,
    ("Revenue Cycle Management", "Health IT"): 0.60,
    ("Dental", "Vision"): 0.55,
    # Moderate correlation
    ("Hospitals", "Physician Practices"): 0.50,
    ("Hospitals", "Home Health"): 0.40,
    ("Primary Care", "Home Health"): 0.45,
    ("Specialty Pharmacy", "Revenue Cycle Management"): 0.35,
}


def _get_sector_correlation(s1: str, s2: str) -> float:
    """Return historical correlation between two sectors (0-1)."""
    if s1 == s2:
        return 1.0
    key = tuple(sorted([s1, s2]))
    return _SECTOR_CORRELATION.get(key, 0.20)  # default low correlation


# ---------------------------------------------------------------------------
# Optimal sector weights from corpus (base rate targets)
# ---------------------------------------------------------------------------

# Corpus-derived median MOIC by sector (from realized deals)
_SECTOR_MOIC_TARGETS: Dict[str, float] = {
    "Physician Practices": 3.0,
    "Revenue Cycle Management": 2.8,
    "Dental": 3.5,
    "Behavioral Health": 2.6,
    "Home Health": 2.5,
    "Primary Care": 2.4,
    "Hospitals": 2.1,
    "Skilled Nursing": 2.0,
    "Senior Living": 1.8,
    "Emergency Medicine": 2.2,
    "Anesthesiology": 2.9,
    "Health IT": 3.2,
    "Medical Devices": 2.6,
    "Digital Health": 2.8,
    "Specialty Pharmacy": 2.7,
    "NEMT / Transportation": 2.5,
}

_SECTOR_LOSS_RATES: Dict[str, float] = {
    "Physician Practices": 0.08,
    "Revenue Cycle Management": 0.10,
    "Dental": 0.07,
    "Behavioral Health": 0.18,
    "Home Health": 0.15,
    "Primary Care": 0.20,
    "Hospitals": 0.22,
    "Skilled Nursing": 0.25,
    "Senior Living": 0.28,
    "Emergency Medicine": 0.14,
    "Anesthesiology": 0.09,
    "Health IT": 0.12,
    "Medical Devices": 0.16,
    "Digital Health": 0.22,
    "Specialty Pharmacy": 0.11,
    "NEMT / Transportation": 0.13,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PortfolioComposition:
    """Snapshot of a portfolio's diversification profile."""
    n_deals: int
    sector_weights: Dict[str, float]   # sector → share of portfolio
    vintage_weights: Dict[int, float]  # year → share of portfolio
    payer_weights: Dict[str, float]    # commercial/medicare/medicaid/self_pay avg weight
    sponsor_weights: Dict[str, float]  # sponsor → share
    hhi_sector: float                  # Herfindahl sector concentration (0-1)
    hhi_vintage: float                 # Herfindahl vintage concentration (0-1)
    hhi_payer: float                   # Herfindahl payer concentration (0-1)
    avg_commercial_pct: float          # portfolio avg commercial exposure
    weighted_vintage_risk: float       # weighted vintage risk score (0-100)


@dataclass
class DiversificationResult:
    """Marginal diversification impact of adding a new deal."""
    deal_name: str
    hhi_sector_before: float
    hhi_sector_after: float
    hhi_vintage_before: float
    hhi_vintage_after: float
    marginal_sector_hhi_change: float   # negative = diversifying
    marginal_vintage_hhi_change: float
    correlation_to_portfolio: float     # average sector correlation with existing
    marginal_score: float               # 0-100 (100 = maximally diversifying)
    signal: str                         # "additive" / "neutral" / "concentrating"
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hhi(weights: Dict) -> float:
    """Herfindahl-Hirschman Index (0-1). 1.0 = full concentration."""
    total = sum(weights.values())
    if total <= 0:
        return 0.0
    shares = [v / total for v in weights.values()]
    return round(sum(s ** 2 for s in shares), 4)


def _avg_payer_mix(deals: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute portfolio-average payer mix."""
    agg: Dict[str, float] = {}
    n = 0
    for deal in deals:
        pm = deal.get("payer_mix") or {}
        if pm:
            for payer, frac in pm.items():
                agg[payer] = agg.get(payer, 0.0) + float(frac)
            n += 1
    if n == 0:
        return {}
    return {k: round(v / n, 4) for k, v in agg.items()}


def _portfolio_sector_correlation(new_sector: str, existing_sectors: List[str]) -> float:
    """Average correlation of new sector with all existing sectors."""
    if not existing_sectors:
        return 0.0
    corrs = [_get_sector_correlation(new_sector, s) for s in existing_sectors]
    return round(sum(corrs) / len(corrs), 3)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def analyze_portfolio(
    portfolio_deals: List[Dict[str, Any]],
    corpus_deals: Optional[List[Dict[str, Any]]] = None,
) -> PortfolioComposition:
    """Analyze diversification composition of a portfolio.

    Args:
        portfolio_deals:  List of deal dicts (deal_name, sector, entry_year, payer_mix, buyer)
        corpus_deals:     Optional corpus for vintage risk scoring

    Returns:
        PortfolioComposition with HHI metrics and concentration analysis
    """
    sector_counts: Dict[str, int] = {}
    vintage_counts: Dict[int, int] = {}
    sponsor_counts: Dict[str, int] = {}

    for deal in portfolio_deals:
        sector = deal.get("sector") or "Unknown"
        year = deal.get("entry_year") or deal.get("year")
        buyer = deal.get("buyer") or "Unknown"

        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if year:
            vintage_counts[int(year)] = vintage_counts.get(int(year), 0) + 1
        sponsor_counts[buyer] = sponsor_counts.get(buyer, 0) + 1

    n = len(portfolio_deals)
    sector_weights = {k: v / n for k, v in sector_counts.items()} if n > 0 else {}
    vintage_weights = {k: v / n for k, v in vintage_counts.items()} if n > 0 else {}
    sponsor_weights = {k: v / n for k, v in sponsor_counts.items()} if n > 0 else {}

    avg_pm = _avg_payer_mix(portfolio_deals)
    avg_commercial = avg_pm.get("commercial", 0.0)
    avg_medicare = avg_pm.get("medicare", 0.0)
    avg_medicaid = avg_pm.get("medicaid", 0.0)
    avg_sp = avg_pm.get("self_pay", 0.0)

    payer_weights = {
        "commercial": avg_commercial,
        "medicare": avg_medicare,
        "medicaid": avg_medicaid,
        "self_pay": avg_sp,
    }

    # Vintage risk scoring
    weighted_vr = 0.0
    if corpus_deals and vintage_weights:
        try:
            from .corpus_vintage_risk_model import analyze_vintage
            for yr, share in vintage_weights.items():
                vr = analyze_vintage(yr, corpus_deals)
                weighted_vr += vr.corpus_adjusted_score * share
        except Exception:
            pass

    return PortfolioComposition(
        n_deals=n,
        sector_weights=sector_weights,
        vintage_weights=vintage_weights,
        payer_weights=payer_weights,
        sponsor_weights=sponsor_weights,
        hhi_sector=_hhi(sector_counts),
        hhi_vintage=_hhi(vintage_counts),
        hhi_payer=_hhi({k: v for k, v in payer_weights.items() if v > 0}),
        avg_commercial_pct=round(avg_commercial, 3),
        weighted_vintage_risk=round(weighted_vr, 1),
    )


def marginal_diversification(
    new_deal: Dict[str, Any],
    portfolio_deals: List[Dict[str, Any]],
    corpus_deals: Optional[List[Dict[str, Any]]] = None,
) -> DiversificationResult:
    """Compute marginal diversification impact of adding a new deal.

    Args:
        new_deal:         Proposed deal dict
        portfolio_deals:  Existing portfolio
        corpus_deals:     Optional corpus for vintage risk

    Returns:
        DiversificationResult with HHI delta and correlation analysis
    """
    deal_name = new_deal.get("deal_name", "Proposed Deal")
    new_sector = new_deal.get("sector") or "Unknown"
    new_year = new_deal.get("entry_year") or new_deal.get("year")

    # Before
    before = analyze_portfolio(portfolio_deals, corpus_deals)

    # After
    combined = portfolio_deals + [new_deal]
    after = analyze_portfolio(combined, corpus_deals)

    dhhi_sector = after.hhi_sector - before.hhi_sector
    dhhi_vintage = after.hhi_vintage - before.hhi_vintage

    existing_sectors = [d.get("sector") or "Unknown" for d in portfolio_deals]
    correlation = _portfolio_sector_correlation(new_sector, existing_sectors)

    # Marginal score: 0 = fully concentrating, 100 = maximally diversifying
    # Combines: sector HHI change (-), vintage HHI change (-), correlation (-)
    score = 100.0
    score -= max(0, dhhi_sector * 200)     # each 0.5 HHI increase = -100 pts
    score -= max(0, dhhi_vintage * 100)    # each 1.0 HHI increase = -100 pts
    score -= correlation * 30              # high correlation penalty
    score = round(max(0.0, min(100.0, score)), 1)

    notes = []
    if new_sector in before.sector_weights:
        existing_share = before.sector_weights[new_sector]
        notes.append(
            f"Adding to existing {new_sector} exposure "
            f"(currently {existing_share:.0%} of portfolio)"
        )
    if correlation > 0.60:
        notes.append(
            f"High sector correlation ({correlation:.2f}) with existing portfolio — "
            "limited diversification benefit"
        )
    if dhhi_sector > 0.05:
        notes.append(
            f"Sector HHI increases by {dhhi_sector:.3f} — "
            "portfolio becomes more concentrated"
        )
    if dhhi_sector < 0:
        notes.append(
            f"New sector reduces concentration (HHI {before.hhi_sector:.3f} → {after.hhi_sector:.3f})"
        )
    if new_year and new_year in (before.vintage_weights or {}):
        notes.append(
            f"Vintage {new_year} already at "
            f"{before.vintage_weights[new_year]:.0%} of portfolio — adds vintage concentration"
        )

    if score >= 65:
        signal = "additive"
    elif score >= 35:
        signal = "neutral"
    else:
        signal = "concentrating"

    return DiversificationResult(
        deal_name=deal_name,
        hhi_sector_before=before.hhi_sector,
        hhi_sector_after=after.hhi_sector,
        hhi_vintage_before=before.hhi_vintage,
        hhi_vintage_after=after.hhi_vintage,
        marginal_sector_hhi_change=round(dhhi_sector, 4),
        marginal_vintage_hhi_change=round(dhhi_vintage, 4),
        correlation_to_portfolio=correlation,
        marginal_score=score,
        signal=signal,
        notes=notes,
    )


def optimal_sector_weights(
    corpus_deals: List[Dict[str, Any]],
    risk_aversion: float = 0.5,
) -> Dict[str, float]:
    """Compute optimal sector target weights from corpus performance.

    Blends MOIC-rank and loss-rate-rank to produce target portfolio weights.
    Weights are normalized to sum to 1.0.

    Args:
        corpus_deals:   Raw seed dicts
        risk_aversion:  0.0 = pure return maximization, 1.0 = pure risk minimization

    Returns:
        Dict[sector → target_weight]
    """
    # Collect realized sector stats from corpus
    sector_moics: Dict[str, List[float]] = {}
    for deal in corpus_deals:
        moic = deal.get("realized_moic")
        sector = deal.get("sector")
        if moic and sector:
            sector_moics.setdefault(sector, []).append(float(moic))

    # Rank sectors by blended score
    sector_scores: Dict[str, float] = {}
    for sector, moics in sector_moics.items():
        if len(moics) < 2:
            continue
        moics_s = sorted(moics)
        median_moic = moics_s[len(moics_s) // 2]
        loss_rate = sum(1 for m in moics_s if m < 1.0) / len(moics_s)
        # Blend: higher MOIC = good, lower loss rate = good
        return_score = min(1.0, (median_moic - 1.0) / 3.0)  # 4.0x → 1.0
        risk_score = 1.0 - loss_rate                          # 0% loss → 1.0
        blended = (1.0 - risk_aversion) * return_score + risk_aversion * risk_score
        sector_scores[sector] = max(0.0, blended)

    # Fall back to prior for sectors not in corpus
    for sector, target_moic in _SECTOR_MOIC_TARGETS.items():
        if sector not in sector_scores:
            return_score = min(1.0, (target_moic - 1.0) / 3.0)
            risk_score = 1.0 - _SECTOR_LOSS_RATES.get(sector, 0.15)
            sector_scores[sector] = (1.0 - risk_aversion) * return_score + risk_aversion * risk_score

    # Normalize
    total = sum(sector_scores.values())
    if total <= 0:
        return {}
    return {s: round(w / total, 4) for s, w in sorted(
        sector_scores.items(), key=lambda x: x[1], reverse=True
    )}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def portfolio_risk_report(
    composition: PortfolioComposition,
    diversification: Optional[DiversificationResult] = None,
) -> str:
    """Formatted portfolio construction report."""
    lines = [
        "Portfolio Construction Analysis",
        "=" * 55,
        f"  Active Deals: {composition.n_deals}",
        "",
        "Concentration (HHI — lower is more diversified):",
        f"  Sector HHI:  {composition.hhi_sector:.3f}  {'[concentrated]' if composition.hhi_sector > 0.25 else '[diversified]'}",
        f"  Vintage HHI: {composition.hhi_vintage:.3f}  {'[concentrated]' if composition.hhi_vintage > 0.30 else '[diversified]'}",
        f"  Payer HHI:   {composition.hhi_payer:.3f}",
        "",
        "Sector Weights:",
    ]
    for sector, wt in sorted(composition.sector_weights.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(wt * 20) + "░" * (20 - int(wt * 20))
        lines.append(f"  {sector:<30} {wt:>5.1%}  {bar}")

    lines += [
        "",
        "Vintage Weights:",
    ]
    for yr, wt in sorted(composition.vintage_weights.items()):
        lines.append(f"  {yr}: {wt:.1%}")

    lines += [
        "",
        f"Avg Commercial Exposure: {composition.avg_commercial_pct:.1%}",
        f"Weighted Vintage Risk:   {composition.weighted_vintage_risk:.1f} / 100",
    ]

    if diversification:
        sig_map = {
            "additive": "ADDITIVE ✓",
            "neutral": "NEUTRAL ~",
            "concentrating": "CONCENTRATING ✗",
        }
        lines += [
            "",
            f"Marginal Deal Analysis: {diversification.deal_name}",
            "-" * 55,
            f"  Marginal Score:   {diversification.marginal_score:.1f} / 100  [{sig_map.get(diversification.signal, '')}]",
            f"  Sector Corr:      {diversification.correlation_to_portfolio:.2f}",
            f"  Sector HHI Δ:     {diversification.marginal_sector_hhi_change:+.4f}",
            f"  Vintage HHI Δ:    {diversification.marginal_vintage_hhi_change:+.4f}",
        ]
        if diversification.notes:
            lines += ["", "  Flags:"]
            for n in diversification.notes:
                lines.append(f"    • {n}")

    return "\n".join(lines) + "\n"

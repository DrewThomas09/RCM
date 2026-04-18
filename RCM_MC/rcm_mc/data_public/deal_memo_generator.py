"""Deal memo generator — synthesizes all corpus analytics into a partner memo.

One-call entry point that runs:
  1. Heuristic assessment (entry band, traps, hold flags)
  2. Enhanced comparables (5 closest corpus deals)
  3. Peer-group percentile ranking
  4. Portfolio analytics (return distribution, loss rate)
  5. Sector timing / momentum signal
  6. Base-rate benchmarks (P25/P50/P75)
  7. CMS calibration (if cms_df provided)

Returns a PartnerMemo object and a formatted markdown/text memo.

Public API:
    PartnerMemo                                  dataclass
    generate_deal_memo(deal, corpus_deals, ...)  -> PartnerMemo
    memo_text(memo)                              -> str
    memo_markdown(memo)                          -> str
    quick_deal_memo(deal, db_path)               -> str  (one-call shortcut)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PartnerMemo:
    """Container for all analytics synthesized into a deal memo."""

    deal: Dict[str, Any]

    # Heuristic
    heuristic_signal: str = "green"
    multiple_flags: List[str] = field(default_factory=list)
    hold_flags: List[str] = field(default_factory=list)
    traps: List[Dict[str, Any]] = field(default_factory=list)
    plausibility: Dict[str, Any] = field(default_factory=dict)
    entry_band: Dict[str, Any] = field(default_factory=dict)

    # Comparables
    comps: List[Dict[str, Any]] = field(default_factory=list)
    peer_percentiles: Dict[str, Any] = field(default_factory=dict)

    # Portfolio benchmarks
    corpus_distribution: Dict[str, Any] = field(default_factory=dict)
    base_rate_benchmarks: Optional[Dict[str, Any]] = None

    # Sector timing
    sector: str = "other"
    timing: Dict[str, Any] = field(default_factory=dict)

    # CMS calibration
    calibration: Optional[Dict[str, Any]] = None

    errors: List[str] = field(default_factory=list)


def generate_deal_memo(
    deal: Dict[str, Any],
    corpus_deals: List[Dict[str, Any]],
    base_rate_benchmarks: Optional[Dict[str, Any]] = None,
    cms_df=None,
    cms_year: int = 2021,
) -> PartnerMemo:
    """Generate a PartnerMemo by running all analytics.

    Parameters
    ----------
    deal :
        The target deal dict (canonical schema).
    corpus_deals :
        Full list of corpus deals for comparables + benchmarks.
    base_rate_benchmarks :
        Optional pre-computed benchmarks dict from base_rates module.
    cms_df :
        Optional pandas DataFrame for CMS calibration (avoids HTTP).
    cms_year :
        Year for CMS calibration (default 2021).
    """
    memo = PartnerMemo(deal=deal)
    errors: List[str] = []

    # 1. Heuristic assessment
    try:
        from .senior_partner_heuristics import (
            full_heuristic_assessment, _classify_sector_simple
        )
        assessment = full_heuristic_assessment(deal)
        memo.heuristic_signal = assessment["overall_signal"]
        memo.multiple_flags = assessment.get("multiple_flags", [])
        memo.hold_flags = assessment.get("hold_flags", [])
        memo.traps = assessment.get("traps", [])
        memo.plausibility = assessment.get("plausibility", {})
        memo.entry_band = assessment.get("entry_band", {})
        memo.sector = assessment.get("sector", "other")
    except Exception as e:
        errors.append(f"heuristics: {e}")

    # 2. Enhanced comparables
    try:
        from .deal_comparables_enhanced import (
            find_enhanced_comps, peer_group_percentiles
        )
        memo.comps = find_enhanced_comps(deal, corpus_deals, n=5)
        memo.peer_percentiles = peer_group_percentiles(deal, memo.comps)
    except Exception as e:
        errors.append(f"comparables: {e}")

    # 3. Portfolio return distribution
    try:
        from .portfolio_analytics import return_distribution, corpus_scorecard
        memo.corpus_distribution = corpus_scorecard(corpus_deals)
    except Exception as e:
        errors.append(f"portfolio_analytics: {e}")

    # 4. Base-rate benchmarks
    memo.base_rate_benchmarks = base_rate_benchmarks

    # 5. Sector timing
    try:
        from .deal_momentum import timing_assessment
        memo.timing = timing_assessment(corpus_deals, memo.sector)
    except Exception as e:
        errors.append(f"momentum: {e}")

    # 6. CMS calibration (optional)
    if cms_df is not None:
        try:
            from .cms_benchmark_calibration import calibrate_from_cms, apply_calibration
            cal = calibrate_from_cms(year=cms_year, df=cms_df)
            if base_rate_benchmarks:
                memo.base_rate_benchmarks = apply_calibration(base_rate_benchmarks, cal)
            memo.calibration = {
                "year": cal.year,
                "moic_uplift_factor": cal.moic_uplift_factor,
                "confidence": cal.confidence,
                "regime_ratio": cal.regime_ratio,
                "median_hhi": cal.median_hhi,
            }
        except Exception as e:
            errors.append(f"calibration: {e}")

    memo.errors = errors
    return memo


# ---------------------------------------------------------------------------
# Text / markdown output
# ---------------------------------------------------------------------------

def _fmt(v: Any, fmt: str = ".2f", suffix: str = "") -> str:
    if v is None:
        return "N/A"
    try:
        return format(float(v), fmt) + suffix
    except (TypeError, ValueError):
        return str(v)


def _signal_icon(sig: str) -> str:
    return {"red": "[RED]", "amber": "[AMBER]", "yellow": "[YELLOW]", "green": "[GREEN]"}.get(sig, "")


def memo_text(memo: PartnerMemo) -> str:
    """Formatted text deal memo (terminal/email-friendly)."""
    deal = memo.deal
    lines = [
        "PARTNER DEAL MEMO",
        "=" * 72,
        f"  Deal       : {deal.get('deal_name', 'N/A')}",
        f"  Year       : {deal.get('year', 'N/A')}",
        f"  Buyer      : {deal.get('buyer', 'N/A')}",
        f"  EV         : ${_fmt(deal.get('ev_mm'), ',.0f')}M",
        f"  EBITDA     : ${_fmt(deal.get('ebitda_at_entry_mm'), ',.0f')}M",
        f"  EV/EBITDA  : {_ev_ebitda(deal)}",
        f"  Sector     : {memo.sector}",
        f"  Signal     : {_signal_icon(memo.heuristic_signal)} {memo.heuristic_signal.upper()}",
        "-" * 72,
    ]

    # Entry band
    band = memo.entry_band
    if band:
        lines.append(
            f"  Entry band : {_fmt(band.get('low'))}x – {_fmt(band.get('fair_low'))}x / "
            f"{_fmt(band.get('fair_high'))}x – {_fmt(band.get('high'))}x"
        )

    # Flags
    for f in memo.multiple_flags:
        lines.append(f"  ⚑ Multiple : {f}")
    for f in memo.hold_flags:
        lines.append(f"  ⚑ Hold     : {f}")

    # Traps
    if memo.traps:
        lines.append("")
        lines.append("  Healthcare Traps:")
        for t in memo.traps:
            lines.append(f"    [{t['severity'].upper()}] {t['trap']}")

    # Plausibility
    plaus = memo.plausibility
    if plaus.get("warnings"):
        lines.append("")
        lines.append("  Return Plausibility:")
        for w in plaus["warnings"]:
            lines.append(f"    • {w}")

    # Sector timing
    timing = memo.timing
    if timing:
        lines.append("")
        lines.append(f"  Sector timing: {timing.get('entry_risk', 'N/A')} "
                     f"(momentum={_fmt(timing.get('momentum_score'), '.2f')})")
        if timing.get("recommendation"):
            lines.append(f"    → {timing['recommendation']}")

    # Comps
    if memo.comps:
        lines.append("")
        lines.append(f"  Top {len(memo.comps)} Comparable Deals:")
        lines.append(
            f"    {'Deal':<38} {'MOIC':>7} {'Sim':>6}"
        )
        for c in memo.comps[:5]:
            name = str(c.get("deal_name") or "")[:37]
            moic = _fmt(c.get("realized_moic"), ".2f", "x") if c.get("realized_moic") else "N/A "
            sim = _fmt(c.get("similarity_score"), ".3f")
            lines.append(f"    {name:<38} {moic:>7} {sim:>6}")

    # Peer percentiles
    pp = memo.peer_percentiles
    if pp.get("moic_percentile") is not None:
        lines.append("")
        lines.append(
            f"  Peer percentile (MOIC): {pp['moic_percentile']:.0f}th "
            f"vs {pp.get('comp_count', 0)} comps "
            f"(peer median: {_fmt(pp.get('moic_comp_median'), '.2f')}x)"
        )

    # Corpus distribution
    dist = memo.corpus_distribution
    if dist:
        lines.append("")
        lines.append(
            f"  Corpus benchmarks (n={dist.get('realized_deals', 0)} realized): "
            f"P25={_fmt(dist.get('moic_p25'), '.2f')}x  "
            f"P50={_fmt(dist.get('moic_p50'), '.2f')}x  "
            f"P75={_fmt(dist.get('moic_p75'), '.2f')}x"
        )
        lines.append(
            f"  Loss rate={_fmt(dist.get('loss_rate'), '.1%')}  "
            f"Home-run rate={_fmt(dist.get('home_run_rate'), '.1%')}"
        )

    # CMS calibration
    cal = memo.calibration
    if cal:
        lines.append("")
        lines.append(
            f"  CMS calibration ({cal.get('year')}): "
            f"uplift={_fmt(cal.get('moic_uplift_factor'), '.4f')}  "
            f"confidence={cal.get('confidence', 'N/A')}"
        )

    if memo.errors:
        lines.append("")
        lines.append(f"  Errors: {'; '.join(memo.errors[:3])}")

    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


def memo_markdown(memo: PartnerMemo) -> str:
    """Markdown deal memo (suitable for display in doc or web)."""
    deal = memo.deal
    signal = memo.heuristic_signal.upper()
    lines = [
        f"# Partner Deal Memo",
        f"",
        f"**Deal:** {deal.get('deal_name', 'N/A')}  ",
        f"**Year:** {deal.get('year', 'N/A')}  "
        f"**Sector:** {memo.sector}  "
        f"**Signal:** `{signal}`",
        f"",
        f"## Deal Metrics",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| EV | ${_fmt(deal.get('ev_mm'), ',.0f')}M |",
        f"| EBITDA | ${_fmt(deal.get('ebitda_at_entry_mm'), ',.0f')}M |",
        f"| EV/EBITDA | {_ev_ebitda(deal)} |",
        f"| Buyer | {deal.get('buyer', 'N/A')} |",
        f"",
    ]

    if memo.multiple_flags or memo.hold_flags or memo.traps:
        lines += ["## Flags & Traps", ""]
        for f in memo.multiple_flags:
            lines.append(f"- **Multiple:** {f}")
        for f in memo.hold_flags:
            lines.append(f"- **Hold:** {f}")
        for t in memo.traps:
            lines.append(f"- **[{t['severity'].upper()}] {t['trap']}:** {t['detail']}")
        lines.append("")

    if memo.comps:
        lines += ["## Comparable Deals", "", "| Deal | MOIC | Similarity |", "|------|------|------------|"]
        for c in memo.comps[:5]:
            name = str(c.get("deal_name") or "")
            moic = f"{c['realized_moic']:.2f}x" if c.get("realized_moic") is not None else "N/A"
            sim = f"{c.get('similarity_score', 0):.3f}"
            lines.append(f"| {name} | {moic} | {sim} |")
        lines.append("")

    if memo.corpus_distribution:
        dist = memo.corpus_distribution
        lines += [
            "## Corpus Benchmarks",
            f"P25={_fmt(dist.get('moic_p25'), '.2f')}x | "
            f"P50={_fmt(dist.get('moic_p50'), '.2f')}x | "
            f"P75={_fmt(dist.get('moic_p75'), '.2f')}x",
            f"Loss rate: {_fmt(dist.get('loss_rate'), '.1%')} | "
            f"Home-run rate: {_fmt(dist.get('home_run_rate'), '.1%')}",
            "",
        ]

    return "\n".join(lines)


def _ev_ebitda(deal: Dict) -> str:
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    if ev and ebitda:
        try:
            eb = float(ebitda)
            if eb > 0:
                return f"{float(ev)/eb:.1f}x"
        except (TypeError, ValueError):
            pass
    return "N/A"


# ---------------------------------------------------------------------------
# One-call shortcut
# ---------------------------------------------------------------------------

def quick_deal_memo(
    deal: Dict[str, Any],
    db_path: str = "corpus.db",
) -> str:
    """One-call deal memo from a deal dict + corpus DB path.

    Opens corpus DB, loads all deals, runs full pipeline, returns text memo.
    """
    try:
        from .deals_corpus import DealsCorpus
        corpus = DealsCorpus(db_path)
        corpus.seed()
        all_deals = corpus.list()
    except Exception as e:
        return f"Error loading corpus: {e}\n"

    memo = generate_deal_memo(deal, all_deals)
    return memo_text(memo)

"""Deal Pipeline Tracker — live sourcing pipeline, stage conversion, velocity.

Models the healthcare PE deal funnel:
- Sourced → Triage → Active → LOI → DD → Close
- Stage conversion rates
- Deal velocity (days in stage)
- Sector concentration in pipeline
- Sourcing channel ROI (proprietary / banker / corporate dev)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Pipeline stage definitions with typical conversion rates
# ---------------------------------------------------------------------------

_STAGES = [
    ("Sourced", 1.00, 14),        # 100% by definition, 14 days to triage
    ("Triaged / NDA", 0.35, 21),
    ("Initial Meeting", 0.60, 28),
    ("IOI Submitted", 0.45, 21),
    ("Management Meeting", 0.55, 35),
    ("LOI / Exclusivity", 0.40, 14),
    ("Due Diligence", 0.88, 60),
    ("Definitive Agreement", 0.75, 45),
    ("Closed", 0.95, 30),
]


# ---------------------------------------------------------------------------
# Sourcing channel ROI
# ---------------------------------------------------------------------------

_CHANNELS = [
    {"channel": "Proprietary Outreach", "close_rate": 0.28, "avg_moic": 2.9, "cost_per_close_k": 180},
    {"channel": "Banker / Limited Auction", "close_rate": 0.18, "avg_moic": 2.4, "cost_per_close_k": 95},
    {"channel": "Broad Auction", "close_rate": 0.08, "avg_moic": 2.1, "cost_per_close_k": 60},
    {"channel": "Inbound / Referral", "close_rate": 0.22, "avg_moic": 2.6, "cost_per_close_k": 40},
    {"channel": "Corporate Development", "close_rate": 0.35, "avg_moic": 3.1, "cost_per_close_k": 220},
    {"channel": "Portfolio Follow-on", "close_rate": 0.55, "avg_moic": 2.8, "cost_per_close_k": 55},
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PipelineStage:
    stage: str
    count: int
    conversion_from_prior: float
    cumulative_conversion: float
    avg_days_in_stage: int
    total_ev_mm: float
    avg_ev_mm: float


@dataclass
class PipelineDeal:
    company: str
    sector: str
    stage: str
    ev_mm: float
    ev_ebitda: float
    days_in_pipeline: int
    probability: float
    source_channel: str


@dataclass
class SourceChannel:
    channel: str
    deals_sourced: int
    close_rate: float
    closed_deals: int
    avg_moic: float
    cost_per_close_k: float
    total_cost_mm: float
    roi: float


@dataclass
class SectorPipelineRow:
    sector: str
    pipeline_count: int
    pipeline_ev_mm: float
    median_ebitda_mult: float
    avg_days_in_pipeline: int
    pct_of_pipeline: float


@dataclass
class PipelineResult:
    total_active_deals: int
    total_pipeline_ev_mm: float
    weighted_closed_ev_mm: float
    end_to_end_conversion_pct: float
    avg_days_source_to_close: int
    stages: List[PipelineStage]
    pipeline_deals: List[PipelineDeal]
    channels: List[SourceChannel]
    sector_breakdown: List[SectorPipelineRow]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 64):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_stages(sourced_count: int) -> List[PipelineStage]:
    rows = []
    prior_count = sourced_count
    cumulative = 1.0
    for i, (stage, conv, days) in enumerate(_STAGES):
        if i == 0:
            count = sourced_count
        else:
            count = int(prior_count * conv)
        cumulative *= conv if i > 0 else 1.0

        # Average EV in stage: scales up as deals progress
        avg_ev = 180 + i * 20
        total_ev = count * avg_ev

        rows.append(PipelineStage(
            stage=stage,
            count=count,
            conversion_from_prior=round(conv if i > 0 else 1.0, 3),
            cumulative_conversion=round(cumulative, 4),
            avg_days_in_stage=days,
            total_ev_mm=round(total_ev, 1),
            avg_ev_mm=round(avg_ev, 1),
        ))
        prior_count = count
    return rows


def _synthesize_pipeline_deals(corpus: List[dict], n: int = 50) -> List[PipelineDeal]:
    """Pick representative deals from corpus, place them in pipeline stages."""
    import hashlib
    stages = [s[0] for s in _STAGES[1:]]   # skip "Sourced"
    channels = [c["channel"] for c in _CHANNELS]

    rows = []
    # Stride through corpus for sector diversity
    stride = max(1, len(corpus) // n)
    sample = [corpus[i * stride] for i in range(n) if i * stride < len(corpus)]
    if not sample:
        sample = corpus[:n]
    for i, d in enumerate(sample):
        # Deterministic stage / channel assignment
        h = int(hashlib.md5((d.get("company_name", f"x{i}")).encode()).hexdigest()[:6], 16)
        stage = stages[h % len(stages)]
        channel = channels[(h // 7) % len(channels)]
        ev = d.get("ev_mm") or 150.0
        em = d.get("ev_ebitda") or 12.0
        days = 30 + (h % 180)
        # Probability: higher stage = higher probability
        stage_idx = stages.index(stage) + 1
        prob = stage_idx / len(stages)

        rows.append(PipelineDeal(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            stage=stage,
            ev_mm=round(ev, 1),
            ev_ebitda=round(em, 1),
            days_in_pipeline=days,
            probability=round(prob, 3),
            source_channel=channel,
        ))
    return rows


def _build_channels(pipeline_deals: List[PipelineDeal]) -> List[SourceChannel]:
    rows = []
    for c in _CHANNELS:
        deals = [d for d in pipeline_deals if d.source_channel == c["channel"]]
        sourced = len(deals)
        closed = int(sourced * c["close_rate"])
        total_cost = closed * c["cost_per_close_k"] / 1000
        # ROI = closed MOIC contribution / cost
        avg_equity = 150 * 0.45
        expected_value = closed * avg_equity * (c["avg_moic"] - 1) / 1000  # net gain $M
        roi = expected_value / total_cost if total_cost else 0
        rows.append(SourceChannel(
            channel=c["channel"],
            deals_sourced=sourced,
            close_rate=round(c["close_rate"], 3),
            closed_deals=closed,
            avg_moic=round(c["avg_moic"], 2),
            cost_per_close_k=round(c["cost_per_close_k"], 0),
            total_cost_mm=round(total_cost, 2),
            roi=round(roi, 1),
        ))
    return rows


def _build_sector_breakdown(pipeline_deals: List[PipelineDeal], total_ev: float) -> List[SectorPipelineRow]:
    by_sector: Dict[str, List[PipelineDeal]] = {}
    for d in pipeline_deals:
        by_sector.setdefault(d.sector, []).append(d)

    rows = []
    for sector, ds in sorted(by_sector.items(), key=lambda x: -len(x[1])):
        evs = [d.ev_mm for d in ds]
        ems = [d.ev_ebitda for d in ds]
        days = [d.days_in_pipeline for d in ds]
        sorted_ems = sorted(ems)
        median_em = sorted_ems[len(sorted_ems) // 2] if sorted_ems else 0
        rows.append(SectorPipelineRow(
            sector=sector,
            pipeline_count=len(ds),
            pipeline_ev_mm=round(sum(evs), 1),
            median_ebitda_mult=round(median_em, 2),
            avg_days_in_pipeline=int(sum(days) / len(days)) if days else 0,
            pct_of_pipeline=round(sum(evs) / total_ev if total_ev else 0, 3),
        ))
    return rows[:15]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_deal_pipeline(
    sourced_count: int = 800,
) -> PipelineResult:
    corpus = _load_corpus()

    stages = _build_stages(sourced_count)
    pipeline_deals = _synthesize_pipeline_deals(corpus, n=60)
    channels = _build_channels(pipeline_deals)

    active_stages = stages[1:-1]   # exclude Sourced and Closed
    total_active = sum(s.count for s in active_stages)
    total_pipeline_ev = sum(d.ev_mm for d in pipeline_deals)
    sector_breakdown = _build_sector_breakdown(pipeline_deals, total_pipeline_ev)

    # Weighted closed EV
    closed_ev = sum(d.ev_mm * d.probability for d in pipeline_deals)

    end_to_end = stages[-1].cumulative_conversion if stages else 0
    avg_days = sum(s.avg_days_in_stage for s in stages)

    return PipelineResult(
        total_active_deals=total_active,
        total_pipeline_ev_mm=round(total_pipeline_ev, 1),
        weighted_closed_ev_mm=round(closed_ev, 1),
        end_to_end_conversion_pct=round(end_to_end * 100, 2),
        avg_days_source_to_close=avg_days,
        stages=stages,
        pipeline_deals=pipeline_deals,
        channels=channels,
        sector_breakdown=sector_breakdown,
        corpus_deal_count=len(corpus),
    )

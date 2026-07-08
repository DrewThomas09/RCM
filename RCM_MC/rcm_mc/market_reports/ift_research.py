"""IFT market-level research brief — the deep, MARKET-focused research layer.

This is the "answer the 20-section research brief" content: market definition,
taxonomy, patient journeys, health-system operating models, procurement, pain
points, performance metrics, reimbursement, unit economics, competitive
landscape (by TYPE, not company), technology, regulatory, growth, segmentation,
sizing methodology, and evidence quality — all at the MARKET level (no
company-specific analysis).

It reuses the quantitative IFT spine (ift_geo / ift_analytics / ift_clinical_
demand / ift_insourcing / ift_tracking / ift_study) for the numeric anchors, and
adds authored market frameworks for the sections the sized pages don't cover.
Every table/figure carries an honesty basis: GOV (published government), ACADEMIC
(published study / the IBISWorld industry report), ILLUSTRATIVE (modeled with a
named basis), or FRAMEWORK (an analytic framework/definition, not a figure).

Design contract mirrors the other IFT modules: frozen dataclasses, pure functions
that DEGRADE and never raise, honesty labels throughout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Industry-report context (IBISWorld "Ambulance Services in the US")
# ─────────────────────────────────────────────────────────────────────────────
# Honestly-extracted QUALITATIVE frame only. The report's numeric series render as
# chart images and were not text-extractable, so NO specific $/% figures are taken
# from it — for numbers we use our GOV/market-research anchors. Cited as ACADEMIC.
_INDUSTRY_SOURCE = ("IBISWorld, \"Ambulance Services in the US\" industry report "
                    "(NAICS 62191) — qualitative market-structure frame; numeric "
                    "series not extracted (chart images), so figures use our "
                    "GOV/market-research anchors")

_INDUSTRY_CONTEXT: Tuple[Tuple[str, str], ...] = (
    ("Service tiers", "The industry is organized around BLS (Basic Life Support), "
     "ALS (Advanced Life Support), and the emerging TIP (Treatment in Place) "
     "'treat, don't transport' model — the same acuity ladder the Medicare AFS "
     "prices, with SCT (critical care) at the top."),
    ("Ownership segmentation", "A primary axis is Government vs Non-government "
     "providers (municipal/fire-based/public-utility vs private and hospital-owned) "
     "— the split that shapes 911 vs interfacility supply."),
    ("Operations & technology", "AVL (Automatic Vehicle Location), CAD "
     "(Computer-Aided Dispatch), ambulance diversion, and public-private "
     "partnerships are the industry's recurring operational levers — the same "
     "dispatch/visibility capabilities that separate reliable IFT from spot-market "
     "vendors."),
    ("Geographic concentration", "The largest state ambulance markets are "
     "California, Texas, Florida, New York, Pennsylvania, Ohio, Illinois, Georgia, "
     "New Jersey, and Arizona — population-weighted, consistent with where IFT "
     "demand concentrates."),
    ("Competitive structure", "The market includes large integrated ground + air "
     "networks (e.g. Global Medical Response), regional and local private "
     "operators, municipal/fire-based EMS, and hospital-owned programs — a "
     "fragmented field where federal contracts (e.g. FEMA) and scale matter for "
     "the 911 side but IFT competes on facility relationships and density."),
    ("Analytic frames", "The report tracks Key External Drivers (with directional "
     "impact) and a SWOT (Strengths / Weaknesses / Opportunities / Threats) — the "
     "same driver/headwind structure carried in the growth section here."),
)


@dataclass(frozen=True)
class IndustryContext:
    available: bool
    items: Tuple[Tuple[str, str], ...] = ()
    source_label: str = ""


def industry_context() -> IndustryContext:
    """The IBISWorld qualitative market-structure frame (ACADEMIC). No numeric
    figures are taken from the report (its series are chart images)."""
    return IndustryContext(available=True, items=_INDUSTRY_CONTEXT,
                           source_label=_INDUSTRY_SOURCE)


# ─────────────────────────────────────────────────────────────────────────────
# Authored market-research sections (KPIs, unit economics, technology, regulatory,
# segmentation, sizing, reimbursement, growth, evidence). Each section is a dict:
#   {id, title, intro, subsections:[{heading, kind:'table'|'bullets', basis,
#    source, columns?, rows?, bullets?}]}
# Authored offline as market frameworks; every subsection carries a basis chip.
# ─────────────────────────────────────────────────────────────────────────────
try:
    from .ift_research_data import AUTHORED_SECTIONS as _AUTHORED_SECTIONS
except Exception:  # noqa: BLE001 — degrade to no authored sections, never raise
    _AUTHORED_SECTIONS: List[Dict[str, Any]] = []


@dataclass(frozen=True)
class ResearchBrief:
    available: bool
    industry: IndustryContext
    sections: List[Dict[str, Any]] = field(default_factory=list)
    n_sections: int = 0
    source_label: str = ""
    note: str = ""


def research_sections() -> List[Dict[str, Any]]:
    """The ordered authored market-research sections. Never raises."""
    return list(_AUTHORED_SECTIONS)


def research_brief() -> ResearchBrief:
    """The full market-level research brief — industry context + authored sections.
    Degrades to available=False only if there is no content at all."""
    secs = research_sections()
    return ResearchBrief(
        available=bool(secs),
        industry=industry_context(),
        sections=secs,
        n_sections=len(secs),
        source_label=("Authored market-level IFT research; quantitative anchors "
                      "reused from the IFT module spine; industry frame from "
                      "IBISWorld (ACADEMIC)"),
        note=("Market-level research only — no company-specific positioning. Every "
              "table carries an honesty basis (GOV / ACADEMIC / ILLUSTRATIVE / "
              "FRAMEWORK); numeric anchors are GOV/market-research, not invented."))

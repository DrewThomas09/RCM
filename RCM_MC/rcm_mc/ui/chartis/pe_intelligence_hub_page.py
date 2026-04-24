"""PE Intelligence Brain hub — /pe-intelligence.

Landing page for the rcm_mc.pe_intelligence package (278 modules).
Surfaces the seven partner reflexes from the brain's README, links
to the archetype library, reasonableness matrix, red-flag catalog,
and bear book. This is the "what can the brain do" page — per-deal
output lives at /deal/<id>/partner-review and /deal/<id>/red-flags.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import P, chartis_shell, ck_kpi_block, ck_section_header
from ._helpers import render_page_explainer


_SEVEN_REFLEXES: List[Dict[str, str]] = [
    {
        "n": "1",
        "title": "Sniff test before math",
        "body": (
            "Knows what's unrealistic on the teaser — 400M rural CAH at 28% IRR, "
            "dental DSO at 4× revenue, MA-will-cover-FFS without a named contract. "
            "14-pattern pre-math triage returning stop_work / senior_partner_review / "
            "proceed_with_diligence."
        ),
        "module": "unrealistic_on_face_check",
    },
    {
        "n": "2",
        "title": "Archetype on sight",
        "body": (
            "Recognizes seven healthcare thesis shapes — payer-mix shift, back-office "
            "consolidation, outpatient migration, CMI uplift, roll-up platform, "
            "cost-basis compression, capacity expansion — and applies the right "
            "lever stack + named risks per shape."
        ),
        "module": "healthcare_thesis_archetype_recognizer",
    },
    {
        "n": "3",
        "title": "Named-failure pattern match",
        "body": (
            "Fingerprint-matches signals against 20+ dated historical failures (MA "
            "startup unwind 2023, NSA platform rate shock 2022, PDGM transition 2020) "
            "and cites the specific lesson — not a generic 'watch out for churn.'"
        ),
        "module": "deal_to_historical_failure_matcher",
    },
    {
        "n": "4",
        "title": "Dot-connect packet signals",
        "body": (
            "Traces packet-level signals through six causal chains: denial fix → CMI "
            "reversal → Medicare bridge; payer-mix shift → case-mix → IP margin; "
            "wage step → physician comp → EBITDA → add-back risk; and three others."
        ),
        "module": "connect_the_dots_packet_reader",
    },
    {
        "n": "5",
        "title": "Recurring vs one-time discipline",
        "body": (
            "Religiously separates recurring EBITDA from one-time cash releases at "
            "the line-item level. 20-pattern catalog (CARES, ERC, settlements, gain-"
            "on-sale vs owner comp, synergy, restructuring). Exit multiple only "
            "applies to recurring."
        ),
        "module": "recurring_ebitda_line_scrubber",
    },
    {
        "n": "6",
        "title": "Specific regulatory $-impact",
        "body": (
            "OBBBA / site-neutral / sequestration / state Medicaid / PAMA translated "
            "into service-line dollar exposure over the hold — not hand-waved. "
            "Reimbursement cliff calendar 2026–2029 with 12 named CMS/payer events."
        ),
        "module": "site_neutral_specific_impact_calculator",
    },
    {
        "n": "7",
        "title": "Partner voice",
        "body": (
            "Direct, numbers-first, willing to say pass when the math doesn't work. "
            "Every module exposes a partner_note — short, blunt, IC-ready — and "
            "every report serializes to dict for LP digests and IC memo exports."
        ),
        "module": "partner_voice_variants",
    },
]

_PER_DEAL_ROUTES: List[Dict[str, str]] = [
    {
        "suffix": "partner-review",
        "module": "partner_review.partner_review",
        "desc": "Full IC verdict: recommendation, partner-voice narrative, "
                "reasonableness bands, heuristic hits, supplemental healthcare "
                "checks, Claude look, and secondary analytics.",
    },
    {
        "suffix": "red-flags",
        "module": "red_flags + reasonableness",
        "desc": "Focused view: critical/high severity heuristic hits plus "
                "band violations (OUT_OF_BAND + IMPLAUSIBLE), supplemental "
                "healthcare signals, and Claude status.",
    },
    {
        "suffix": "archetype",
        "module": "deal_archetype + regime_classifier",
        "desc": "Sponsor-structure archetype match (playbook + risks + IC "
                "questions) plus time-series regime classification.",
    },
    {
        "suffix": "investability",
        "module": "investability_scorer + exit_readiness",
        "desc": "Composite 0-100 score + grade + sub-scores plus 12-dimension "
                "exit readiness report and top-3 change-my-mind items.",
    },
    {
        "suffix": "market-structure",
        "module": "market_structure",
        "desc": "HHI / CR3 / CR5 + fragmentation verdict + consolidation-"
                "play score + thesis hint (buy_and_build / platform_entry).",
    },
    {
        "suffix": "white-space",
        "module": "white_space",
        "desc": "Geographic / segment / channel adjacency opportunities "
                "with per-opportunity scores, rationales, and barriers.",
    },
    {
        "suffix": "stress",
        "module": "stress_test.run_stress_grid",
        "desc": "Scenario grid: rate / volume / multiple / lever / labor "
                "shocks with pass-rate, covenant breaches, EBITDA delta.",
    },
    {
        "suffix": "ic-packet",
        "module": "master_bundle.build_master_bundle",
        "desc": "Composed IC packet: memo + cheatsheet + 100-day plan + "
                "bear patterns + regulatory items + partner discussion.",
    },
]


_QUICK_LINKS: List[Dict[str, str]] = [
    {
        "label": "Archetype Library",
        "href": "/methodology#archetypes",
        "desc": (
            "Seven healthcare thesis shapes + sponsor-structure archetypes "
            "(platform rollup, take-private, carve-out, turnaround, buy-and-build, "
            "continuation, GP-led secondary, PIPE, operating lift, growth equity)."
        ),
        "module_count": "10 archetype modules",
    },
    {
        "label": "Reasonableness Matrix",
        "href": "/methodology#reasonableness",
        "desc": (
            "Band-check library for IRR, EBITDA margin, exit multiple, lever "
            "realizability, EBITDA quality. Verdicts: IN_BAND / STRETCH / "
            "OUT_OF_BAND / IMPLAUSIBLE."
        ),
        "module_count": "reasonableness.py — 40+ bands",
    },
    {
        "label": "Red Flag Catalog",
        "href": "/methodology#red-flags",
        "desc": (
            "Codified red flags scanned per deal: MA bridge traps, payer "
            "renegotiation timing, denial-fix pace, physician retention, "
            "covenant headroom, leverage limits."
        ),
        "module_count": "red_flags.py + 9 deal-smell detectors",
    },
    {
        "label": "Bear Book",
        "href": "/methodology#bear-book",
        "desc": (
            "Pattern library of specific bear cases. Each pattern: named "
            "breakage, EBITDA hit, recovery posture, early-warning indicator. "
            "Cross-pattern digest unifies failure + bear + trap libraries."
        ),
        "module_count": "bear_book.py + cross_pattern_digest",
    },
    {
        "label": "IC Decision Synthesizer",
        "href": "/methodology#ic-decision",
        "desc": (
            "Single recommendation + three flip signals. 3-round IC dialog "
            "simulator with five voices (skeptic, optimist, MD numbers, "
            "operating partner, LP-facing) + chair synthesis."
        ),
        "module_count": "ic_decision_synthesizer + ic_dialog_simulator",
    },
    {
        "label": "Stress Grid & Regime",
        "href": "/methodology#stress",
        "desc": (
            "Scenario sweep with base / bear / bull outcomes. Regime "
            "classifier tags the deal as expansion / normalization / peak / "
            "correction / contraction."
        ),
        "module_count": "stress_test + regime_classifier",
    },
]


def _reflex_card(reflex: Dict[str, str]) -> str:
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px;">'
        f'<div style="display:flex;gap:10px;align-items:baseline;margin-bottom:6px;">'
        f'<span style="font-family:var(--ck-mono);font-size:24px;font-weight:700;'
        f'color:{P["accent"]};line-height:1;">{_html.escape(reflex["n"])}</span>'
        f'<span style="font-family:var(--ck-mono);font-size:12px;font-weight:700;'
        f'letter-spacing:0.04em;color:{P["text"]};text-transform:uppercase;">'
        f'{_html.escape(reflex["title"])}</span>'
        f'</div>'
        f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;'
        f'margin-bottom:8px;">{_html.escape(reflex["body"])}</p>'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["text_faint"]};letter-spacing:0.08em;">'
        f'&rarr; {_html.escape(reflex["module"])}.py</div>'
        f'</div>'
    )


def _link_card(link: Dict[str, str]) -> str:
    return (
        f'<a href="{_html.escape(link["href"])}" '
        f'style="display:block;background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:12px;text-decoration:none;transition:border-color 0.1s;">'
        f'<div style="font-family:var(--ck-mono);font-size:12px;font-weight:700;'
        f'color:{P["accent"]};letter-spacing:0.04em;text-transform:uppercase;'
        f'margin-bottom:6px;">{_html.escape(link["label"])} &rarr;</div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;line-height:1.5;'
        f'margin-bottom:6px;">{_html.escape(link["desc"])}</div>'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["text_faint"]};letter-spacing:0.08em;">'
        f'{_html.escape(link["module_count"])}</div>'
        f'</a>'
    )


def render_pe_intelligence_hub(
    store: Any = None,
    deal_id: Optional[str] = None,
    current_user: Optional[str] = None,
) -> str:
    """Render the PE Intelligence Brain landing page."""
    explainer = render_page_explainer(
        what=(
            "Entry point into the codified PE-partner judgment layer "
            "— 278 modules organised around 7 partner reflexes, plus a "
            "catalog of per-deal routes that exercise the brain on a "
            "specific packet."
        ),
        scale=(
            "The 7 reflexes: sniff test before math; archetype on "
            "sight; named-failure pattern match; dot-connect packet "
            "signals; recurring vs one-time discipline; specific "
            "regulatory dollar-impact; partner voice."
        ),
        use=(
            "Open a deal and follow the Partner Review link on the "
            "deal dashboard to run the full brain. Use this hub to "
            "jump to an inventory (reasonableness matrix, bear book, "
            "archetype library) when you want context before a specific "
            "per-deal read."
        ),
        source="pe_intelligence/README.md (seven reflex definitions).",
        page_key="pe-intelligence",
    )
    kpis = (
        ck_kpi_block("Modules", "278", "partner reflexes codified")
        + ck_kpi_block("Tests", "2,970", "unit tests passing")
        + ck_kpi_block("Reflexes", "7", "senior-partner judgment layers")
        + ck_kpi_block("Exports", "1,455+", "public symbols")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    intro = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px;margin-bottom:14px;">'
        f'<p style="color:{P["text_dim"]};font-size:12px;line-height:1.6;">'
        f'A senior-PE-healthcare-partner judgment layer. Reads a '
        f'<code style="color:{P["accent"]};font-family:var(--ck-mono);">'
        f'DealAnalysisPacket</code> and answers the questions a partner actually '
        f'asks in IC — not a taxonomy of features but a library of partner '
        f'reflexes. Partner Review now also surfaces supplemental healthcare '
        f'checks and a Claude second-look confirmation card. Open any deal and click '
        f'<a href="#" style="color:{P["accent"]};">Partner Review</a> on the '
        f'deal dashboard to exercise the brain against that packet.'
        f'</p></div>'
    )

    # Seven reflexes grid (2 columns)
    reflex_header = ck_section_header(
        "SEVEN PARTNER REFLEXES",
        "what the brain does on every packet",
        count=7,
    )
    reflex_grid = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;'
        f'margin-bottom:14px;">'
        + "".join(_reflex_card(r) for r in _SEVEN_REFLEXES)
        + f'</div>'
    )

    # Quick links
    links_header = ck_section_header(
        "BRAIN INVENTORIES",
        "click into the catalog you need",
        count=len(_QUICK_LINKS),
    )
    links_grid = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;'
        f'margin-bottom:14px;">'
        + "".join(_link_card(l) for l in _QUICK_LINKS)
        + f'</div>'
    )

    # Per-deal module catalog
    catalog_header = ck_section_header(
        "PER-DEAL ROUTES",
        "which brain module drives each page",
        count=len(_PER_DEAL_ROUTES),
    )
    catalog_rows = []
    for row in _PER_DEAL_ROUTES:
        catalog_rows.append(
            f'<div style="display:grid;grid-template-columns:180px 260px 1fr;'
            f'gap:14px;padding:8px 10px;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11.5px;align-items:baseline;">'
            f'<div style="font-family:var(--ck-mono);color:{P["accent"]};'
            f'font-size:11px;">/deal/&lt;id&gt;/{_html.escape(row["suffix"])}</div>'
            f'<div style="font-family:var(--ck-mono);color:{P["text_dim"]};'
            f'font-size:10.5px;">{_html.escape(row["module"])}</div>'
            f'<div style="color:{P["text"]};line-height:1.55;">'
            f'{_html.escape(row["desc"])}</div></div>'
        )
    catalog = (
        f'<div class="ck-panel"><div class="ck-panel-title">Per-deal routes · '
        f'pick any deal and append one of these suffixes</div>'
        f'<div style="padding:6px 10px;">{"".join(catalog_rows)}</div></div>'
    )

    cta = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px;margin-bottom:14px;margin-top:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;margin-bottom:6px;">'
        f'GET STARTED</div>'
        f'<div style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;">'
        f'The brain runs per packet. Open a deal and follow '
        f'<span style="color:{P["accent"]};">Partner Review</span> '
        f'from the deal dashboard — that page links into every drill-down '
        f'below. Need historical comps first? Browse '
        f'<a href="/library" style="color:{P["accent"]};">the corpus</a> '
        f'(655 deals).'
        f'</div></div>'
    )

    body = (
        explainer + kpi_strip + intro + reflex_header + reflex_grid
        + links_header + links_grid
        + catalog_header + catalog + cta
    )

    subtitle = (
        f"Signed in as {_html.escape(current_user)} · 278 modules · 7 reflexes"
        if current_user else "278 modules · 2,970 tests · the senior-PE judgment layer"
    )
    return chartis_shell(
        body,
        title="PE Intelligence",
        active_nav="/pe-intelligence",
        subtitle=subtitle,
    )

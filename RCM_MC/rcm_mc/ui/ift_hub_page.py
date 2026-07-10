"""IFT suite hub (``/ift``) — the one page that says what lives where.

The 2026-07-10 audit found the nine IFT surfaces had no index: a reader met
nine dense pages with overlapping names and no reading order. This hub gives
each surface ONE job description, a reading order, and the dedup state —
so the suite reads as one study, not nine competing documents.

Degrades — never raises.
"""
from __future__ import annotations

import html as _html
from typing import List, Tuple

from ._chartis_kit import (
    chartis_shell, ck_page_actions, ck_page_title, ck_panel,
    ck_section_header,
)


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


# (route, title, one job, what NOT to look for here)
_SURFACES: Tuple[Tuple[str, str, str, str], ...] = (
    ("/ift-mmt", "1 · MMT — the company",
     "Who MMT actually is: the NPPES-verified 13-state estate, ownership/PE "
     "trail, hospital-system customers, registry-computed competitive field, "
     "litigation record, and the legacy-core 22-county model with the "
     "derived demand band + volume-increase scenarios.",
     "National market sizing (that's the markets page)."),
    ("/ift-demand", "2 · Demand — the volume",
     "The demand story end to end: the sourced national transport-volume "
     "funnel, CMS acuity-code analysis, the growth-evidence registry "
     "(consolidation, REH conversions, transfer trends — all cited), and "
     "the regional/county roll-down.",
     "Company positioning or diligence questions."),
    ("/ift-markets", "3 · Markets — the geography",
     "Metro-by-metro market structure from the vendored CMS estate "
     "(hospitals, post-acute, density) with the MMT-presence "
     "reconciliation: NPI-verified metros vs the roll-up screen.",
     "The demand growth thesis (that's demand)."),
    ("/ift-study", "4 · Study — the synthesis",
     "The four-dimension investor study, and the SINGLE HOME of the shared "
     "frameworks: transport taxonomy, patient journey + ecosystem, "
     "operating-model bands, and MMT positioning pillars.",
     "Raw data tables — the study synthesizes."),
    ("/ift-research", "5 · Research — the market brief",
     "The 20-topic market-level research brief (reimbursement, unit "
     "economics, KPIs, technology, regulatory, segmentation, sizing) — "
     "market-level only, digests + links where the study owns content.",
     "Company-specific analysis."),
    ("/ift-clinical", "6 · Clinical — the demand engine",
     "Condition-level acute-transfer scenarios mapped to ICD-10 and "
     "post-acute destinations — the clinical WHY under the demand model.",
     "Dollar sizing."),
    ("/ift-hs-demand", "7 · Health systems — the buyers",
     "Demand sized from the health systems' own HCRIS filings, county by "
     "county — the account-level view of the demand base.",
     "The national funnel (that's demand)."),
    ("/ift-diligence", "8 · Diligence — the workplan",
     "The question architecture with inline digests linking to each "
     "answer's single home, plus the evidence-request list.",
     "Full framework tables (they live on the study)."),
    ("/ift-sourcing", "9 · Sourcing — the prompts",
     "The scope-bounded research prompts that generated the corpus — the "
     "meta layer for reproducing or extending the research.",
     "Findings — this is process, not results."),
)

_DATA_ASSETS: Tuple[Tuple[str, str], ...] = (
    ("/api/ift/markets.xlsx", "Market-study workbook (.xlsx) — every sourced "
     "figure by market"),
    ("/api/ift/demand.xlsx", "Demand workbook (.xlsx) — volume-first, "
     "GOV/SOURCED/ACADEMIC/DERIVED only"),
    ("/api/ift/mmt.json", "MMT model JSON API"),
    ("/connector-estate", "Live data-connector estate (network-gated "
     "county datasets: Census ACS, CDC PLACES, CMS geographic variation)"),
)


def render_ift_hub(qs=None) -> str:
    """Render the IFT hub. Degrades — never raises."""
    head = ck_page_title(
        "Interfacility Transport — The Study",
        eyebrow="IFT SUITE · START HERE",
        meta=("9 surfaces · 1 reading order · subject operator: Midwest "
              "Medical Transport (MMT Ambulance)"))
    intro = (
        '<p style="font-family:var(--sc-serif,Georgia,serif);font-size:15px;'
        'line-height:1.65;max-width:88ch;color:var(--sc-text,#1a2332);">'
        "One study, nine surfaces, each with one job. Read top to bottom "
        "for the full picture — company, demand, geography, synthesis — or "
        "jump straight to the surface that answers your question. Shared "
        "frameworks render once (on the study) and are digested elsewhere; "
        "every figure carries an honesty basis, and anything captured from "
        "search excerpts rather than fetched primary text sits in an "
        "explicit re-verification queue.</p>")
    cards: List[str] = []
    for route, title, job, notfor in _SURFACES:
        cards.append(
            '<div style="border:1px solid var(--sc-rule,#d8d0bc);'
            'border-left:3px solid var(--sc-teal,#155752);border-radius:4px;'
            'padding:14px 16px;background:#fff;">'
            f'<a href="{_esc(route)}" style="font-family:var(--sc-serif,'
            'Georgia,serif);font-size:16px;font-weight:600;'
            'color:var(--sc-navy,#0b2341);text-decoration:none;">'
            f"{_esc(title)}</a>"
            f'<p style="font-size:13px;line-height:1.55;margin:6px 0;'
            f'color:var(--sc-text,#2a3340);">{_esc(job)}</p>'
            f'<p style="font-family:var(--sc-mono,Consolas,monospace);'
            f'font-size:10.5px;color:var(--sc-muted,#6b6357);margin:0;">'
            f"NOT here: {_esc(notfor)}</p></div>")
    grid = ('<div style="display:grid;grid-template-columns:repeat(auto-fit,'
            'minmax(340px,1fr));gap:14px;margin:14px 0 20px;">'
            + "".join(cards) + "</div>")
    assets = "".join(
        f'<li style="margin:5px 0;"><a href="{_esc(r)}" '
        f'style="color:var(--sc-teal,#155752);">{_esc(label)}</a></li>'
        for r, label in _DATA_ASSETS)
    assets_html = (
        ck_section_header("Data assets", eyebrow="DOWNLOADS & APIS")
        + ck_panel(f'<ul style="font-size:13px;line-height:1.6;'
                   f'padding-left:20px;margin:4px 0;">{assets}</ul>'))
    governance = ""
    try:
        from ..market_reports import ift_growth_evidence as _ge
        from ..market_reports import ift_unit_economics as _ue
        q = len(_ge.reverify_queue())
        total = len(_ge.all_evidence())
        econ_q = sum(1 for b in _ue.all_benchmarks() if b.needs_reverify)
        econ_total = len(_ue.all_benchmarks())
        governance = (
            ck_section_header("Evidence governance",
                              eyebrow="HONESTY, TRACKED")
            + ck_panel(
                '<p style="font-size:13.5px;line-height:1.6;max-width:88ch;">'
                f"Growth registry: <strong>{total - q} of {total}</strong> "
                "entries carry verbatim-verified quotes (fetched primary "
                f"text); <strong>{q}</strong> were captured from search "
                "excerpts of the cited page and sit in the explicit "
                "re-verification queue. Unit-economics benchmarks: "
                f"<strong>{econ_q} of {econ_total}</strong> queued for "
                "re-verification against the blocked CMS/MedPAC PDFs. "
                "Nothing in a queue is presented as verified — the flag "
                "travels with each figure on every page and workbook "
                "sheet.</p>"))
    except Exception:  # noqa: BLE001
        governance = ""
    return chartis_shell(
        head + intro + grid + assets_html + governance + ck_page_actions(),
        "IFT — The Study", active_nav="/market",
        subtitle="Interfacility transport study hub — what lives where")

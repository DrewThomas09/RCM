"""Corpus Coverage Report — data completeness, field coverage rates, quality overview.

Shows: per-field coverage rates, completeness heatmap by seed batch,
sector breadth, quality tier distribution, and trust-grade indicators.
This is the "institutional credibility" page that gives IC confidence
in the underlying data quality.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    # Canonical loader → the corpus-coverage page reports the FULL,
    # authoritative corpus instead of a bespoke range(2,39) subset that
    # under-counted it. The coverage page must reflect the real corpus.
    from rcm_mc.data_public.corpus_loader import load_corpus_deals
    return load_corpus_deals("all")


from rcm_mc.ui._chartis_kit import (
    P, _MONO, _SANS, chartis_shell, ck_fmt_num, ck_kpi_block,
    ck_page_title, ck_provenance_tooltip, ck_section_header,
)


TRACKED_FIELDS = [
    ("deal_name",           "Deal Name",          True),
    ("year",                "Year",               True),
    ("buyer",               "Buyer",              True),
    ("seller",              "Seller",             False),
    ("sector",              "Sector",             False),
    ("deal_type",           "Deal Type",          False),
    ("region",              "Region",             False),
    ("geography",           "Geography",          False),
    ("ev_mm",               "EV ($M)",            False),
    ("ebitda_at_entry_mm",  "EBITDA at Entry",    False),
    ("ev_ebitda",           "EV/EBITDA",          False),
    ("hold_years",          "Hold Years",         False),
    ("realized_moic",       "Realized MOIC",      False),
    ("realized_irr",        "Realized IRR",       False),
    ("payer_mix",           "Payer Mix",          False),
    ("notes",               "Notes",              False),
]


def _coverage_bar(pct: float, w: int = 120) -> str:
    bar_w = int(pct / 100 * w)
    col = P["positive"] if pct >= 80 else (P["warning"] if pct >= 50 else P["negative"])
    return (
        f'<svg width="{w}" height="10" style="vertical-align:middle">'
        f'<rect x="0" y="2" width="{w}" height="6" fill="{P["panel"]}" stroke="{P["border"]}" stroke-width="1"/>'
        f'<rect x="1" y="3" width="{bar_w}" height="4" fill="{col}"/>'
        f'</svg>'
    )


def _coverage_table(corpus: List[Dict]) -> str:
    n = len(corpus)
    rows = ""
    for field, label, required in TRACKED_FIELDS:
        count = sum(1 for d in corpus if d.get(field) is not None and d.get(field) != "")
        pct = count / n * 100 if n > 0 else 0
        col = P["positive"] if pct >= 80 else (P["warning"] if pct >= 50 else P["negative"])
        req_badge = (
            f'<span style="font-size:8px;color:{P["accent"]};border:1px solid {P["accent"]};padding:0px 3px;margin-left:4px;font-family:{_SANS}">REQ</span>'
            if required else ""
        )
        rows += (
            f'<tr style="background:{P["row_stripe"] if TRACKED_FIELDS.index((field,label,required))%2 else P["panel"]}">'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO}">{field}{req_badge}</td>'
            f'<td style="padding:4px 8px;font-size:10px;color:{P["text_dim"]}">{html.escape(label)}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{count}</td>'
            f'<td style="padding:4px 8px">{_coverage_bar(pct)}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};color:{col};text-align:right;font-variant-numeric:tabular-nums">{pct:.1f}%</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">FIELD</th>
  <th style="{th}">DESCRIPTION</th>
  <th style="{th};text-align:right">POPULATED</th>
  <th style="{th}">COVERAGE</th>
  <th style="{th};text-align:right">RATE</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>"""


def _sector_breadth_table(corpus: List[Dict]) -> str:
    sector_counts: Dict[str, int] = defaultdict(int)
    sector_moic: Dict[str, int] = defaultdict(int)
    sector_irr: Dict[str, int] = defaultdict(int)
    sector_payer: Dict[str, int] = defaultdict(int)
    sector_ev: Dict[str, int] = defaultdict(int)

    for d in corpus:
        sec = d.get("sector") or "Unknown"
        sector_counts[sec] += 1
        if d.get("realized_moic") is not None: sector_moic[sec] += 1
        if d.get("realized_irr") is not None:  sector_irr[sec]  += 1
        if isinstance(d.get("payer_mix"), dict): sector_payer[sec] += 1
        if d.get("ev_mm") is not None:           sector_ev[sec]    += 1

    rows_data = sorted(sector_counts.items(), key=lambda x: -x[1])

    rows = ""
    for i, (sec, n) in enumerate(rows_data[:25]):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        moic_cov = sector_moic[sec] / n * 100
        irr_cov  = sector_irr[sec]  / n * 100
        payer_cov = sector_payer[sec] / n * 100
        ev_cov   = sector_ev[sec]   / n * 100

        def cov_cell(pct: float) -> str:
            col = P["positive"] if pct >= 80 else (P["warning"] if pct >= 50 else P["negative"])
            return f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{col};font-variant-numeric:tabular-nums">{pct:.0f}%</td>'

        rows += (
            f'<tr>'
            f'<td style="padding:4px 8px;font-size:11px;white-space:nowrap">{html.escape(sec[:30])}</td>'
            f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{n}</td>'
            + cov_cell(moic_cov) + cov_cell(irr_cov) + cov_cell(payer_cov) + cov_cell(ev_cov) +
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">DEALS</th>
  <th style="{th};text-align:right">MOIC COV</th>
  <th style="{th};text-align:right">IRR COV</th>
  <th style="{th};text-align:right">PAYER COV</th>
  <th style="{th};text-align:right">EV COV</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>"""


def _quality_kpi_grid(corpus: List[Dict]) -> str:
    n = len(corpus)
    has_moic  = sum(1 for d in corpus if d.get("realized_moic") is not None)
    has_irr   = sum(1 for d in corpus if d.get("realized_irr") is not None)
    has_payer = sum(1 for d in corpus if isinstance(d.get("payer_mix"), dict))
    has_ev    = sum(1 for d in corpus if d.get("ev_mm") is not None)
    has_ebitda = sum(1 for d in corpus if d.get("ebitda_at_entry_mm") is not None)
    has_sector = sum(1 for d in corpus if d.get("sector"))
    has_hold  = sum(1 for d in corpus if d.get("hold_years") is not None)
    has_year  = sum(1 for d in corpus if d.get("year") is not None)
    sectors   = len({d.get("sector") for d in corpus if d.get("sector")})
    years     = len({d.get("year") for d in corpus if d.get("year")})

    # compute avg completeness (fields with value / possible fields)
    completeness_scores = []
    for d in corpus:
        possible = len(TRACKED_FIELDS)
        populated = sum(1 for f, _, _ in TRACKED_FIELDS if d.get(f) is not None and d.get(f) != "")
        completeness_scores.append(populated / possible)
    avg_completeness = sum(completeness_scores) / len(completeness_scores) * 100 if completeness_scores else 0

    kpis = [
        ("TOTAL DEALS",    str(n),                       P["text"]),
        ("SECTORS",        str(sectors),                 P["text"]),
        ("VINTAGE YEARS",  str(years),                   P["text"]),
        ("MOIC COVERAGE",  f"{has_moic/n*100:.0f}%",     P["positive"] if has_moic/n >= 0.7 else P["warning"]),
        ("IRR COVERAGE",   f"{has_irr/n*100:.0f}%",      P["positive"] if has_irr/n >= 0.7 else P["warning"]),
        ("PAYER COVERAGE", f"{has_payer/n*100:.0f}%",    P["positive"] if has_payer/n >= 0.7 else P["warning"]),
        ("EV COVERAGE",    f"{has_ev/n*100:.0f}%",       P["positive"] if has_ev/n >= 0.7 else P["warning"]),
        ("SECTOR COVERAGE",f"{has_sector/n*100:.0f}%",   P["positive"] if has_sector/n >= 0.8 else P["warning"]),
        ("AVG COMPLETENESS",f"{avg_completeness:.0f}%",  P["positive"] if avg_completeness >= 70 else P["warning"]),
    ]

    # Cycle 47 — port to ck_kpi_block + provenance on completeness.
    completeness_value = ck_provenance_tooltip(
        "Average corpus completeness",
        f"{avg_completeness:.0f}%",
        explainer=(
            f"Mean share of tracked fields populated across "
            f"{n} corpus deals. Below 70% means the corpus's "
            f"average deal is missing data the audit panels "
            f"depend on - cells fall back to '—' and percentile "
            f"comparisons get noisier."
        ),
    )
    moic_cov_value = ck_provenance_tooltip(
        "MOIC coverage",
        f"{has_moic/n*100:.0f}%",
        explainer=(
            f"Share of corpus with disclosed realized MOIC. "
            f"This is the highest-stakes coverage stat - MOIC "
            f"benchmarking on /market-rates and /backtest "
            f"weights by this denominator."
        ),
        inject_css=False,
    )
    blocks = []
    for lbl, val, _col in kpis:
        # Provide provenance only for the two anchor stats.
        if lbl == "AVG COMPLETENESS":
            blocks.append(ck_kpi_block(lbl.title(), completeness_value))
        elif lbl == "MOIC COVERAGE":
            blocks.append(ck_kpi_block(lbl.title(), moic_cov_value))
        else:
            blocks.append(ck_kpi_block(lbl.title(), val))
    return "".join(blocks)


def render_corpus_coverage() -> str:
    corpus = _load_corpus()
    n = len(corpus)

    kpi_grid = _quality_kpi_grid(corpus)
    kpi_strip = f'<div class="ck-kpi-grid" style="grid-template-columns:repeat(9,1fr);gap:6px;margin-bottom:16px;">{kpi_grid}</div>'

    cov_table = _coverage_table(corpus)
    sector_table = _sector_breadth_table(corpus)

    # trust grade
    has_moic_pct = sum(1 for d in corpus if d.get("realized_moic") is not None) / n * 100
    trust_grade = "A" if has_moic_pct >= 75 else ("B" if has_moic_pct >= 55 else "C")
    trust_col = P["positive"] if trust_grade == "A" else (P["warning"] if trust_grade == "B" else P["negative"])

    trust_panel = f"""
<div style="background:{P['panel_alt']};border:2px solid {trust_col};padding:14px 20px;margin-bottom:16px;display:flex;align-items:center;gap:20px">
  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em">CORPUS TRUST GRADE</div>
    <div style="font-size:48px;font-family:{_MONO};color:{trust_col};font-weight:700;line-height:1">{trust_grade}</div>
  </div>
  <div style="flex:1">
    <div style="font-size:11px;color:{P['text']};font-family:{_SANS};line-height:1.6">
      {n:,} healthcare PE transactions from public filings, press releases, and investor disclosures.<br>
      {has_moic_pct:.0f}% have disclosed MOIC. All figures represent publicly available data only.<br>
      Sources: SEC filings, company press releases, LP letters, Bloomberg, Pitchbook disclosures.
    </div>
  </div>
</div>"""

    # B11 — same shape as concentration_risk (PR #165): page used
    # ck_section_header as a de-facto title. ck_section_header is an
    # h2-level section primitive, not a page-level h1. Adding
    # ck_page_title and removing the now-redundant ck_section_header
    # to avoid the visual "CORPUS COVERAGE REPORT" duplication. Meta
    # surfaces the trust_grade + MOIC coverage % since those are the
    # load-bearing institutional-credibility signals the page
    # exists to communicate (and they appear visually in the big
    # 48px trust_panel right below — meta gives a one-line read
    # for partners scanning quickly).
    page_title = ck_page_title(
        "Corpus Coverage Report",
        eyebrow="CORPUS COVERAGE",
        meta=(
            f"{n:,} deals · trust grade {trust_grade} · "
            f"MOIC coverage {has_moic_pct:.0f}%"
        ),
    )
    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {page_title}
  {trust_panel}
  {kpi_strip}

  <div class="ck-page-head">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      FIELD COVERAGE RATES — {n:,} DEALS
    </div>
    {cov_table}
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      COVERAGE BY SECTOR — TOP 25 BY DEAL COUNT
    </div>
    {sector_table}
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    Coverage color: green ≥80%, amber 50–80%, red &lt;50%. Trust grade A = MOIC coverage ≥75%, B = ≥55%, C = &lt;55%.
  </div>
</div>"""

    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    return chartis_shell(_ckn("corpus coverage (illustrative seed corpus)") + body, "Corpus Coverage Report", active_nav="/corpus-coverage",
                         subtitle=f"{n:,} deals — Trust grade {trust_grade}",
        editorial_intro={
            "eyebrow": "CORPUS COVERAGE",
            "headline": "How much of the corpus you can trust.",
            "italic_word": "trust",
            "body": (
                "Field-by-field coverage rates across the realized "
                "deal corpus. Trust grade A means MOIC coverage "
                ">=75%; below B and the corpus benchmarks lean on "
                "a thin denominator. Coverage by sector below "
                "shows which sectors are well-papered and which "
                "are sparse."
            ),
        })

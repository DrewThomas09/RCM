"""Clinical Verticals Reference — 13 US healthcare specialty verticals.

Renders the CY2026 clinical-specialty deep-dive reference
(:mod:`rcm_mc.data_public.clinical_verticals_2026`) as a chart-ready
editorial page: cross-cutting 2026 policy drivers, a volume-anchor
leaderboard, and a per-vertical card grid (codes, epidemiology,
workforce, access, sources, the chart each fact supports).

This is the *clinical-specialty* companion to the existing /verticals
page (which covers the facility verticals: acute care, ASC, BH, MSO).
"""
from __future__ import annotations

import html

from ._chartis_kit import (
    chartis_shell, ck_editorial_head, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_actions, ck_signal_badge,
)
from ..data_public.clinical_verticals_2026 import (
    ASC_CF_2026, CLINICAL_VERTICALS_2026, OPPS_CF_2026, PFS_CF_NONQP_2026,
    POLICY_DRIVERS_2026, Stat, list_verticals, verticals_with_asc_cpl_2026,
    volume_anchors,
)
from .brand import PALETTE


def _fmt_stat_value(s: Stat) -> str:
    """Human chart label for a Stat — handles big counts, pct, ranges."""
    if s.value is None:
        return "—"
    unit = s.unit.lower()
    if "pct" in unit:
        body = f"{s.value:.1f}%"
    elif s.value >= 1e9:
        body = f"{s.value / 1e9:.2f}B"
    elif s.value >= 1e6:
        body = f"{s.value / 1e6:.1f}M"
    elif s.value >= 1e3:
        body = f"{s.value:,.0f}"
    else:
        body = (f"{s.value:.2f}".rstrip("0").rstrip("."))
    if "usd" in unit and not body.startswith("$"):
        body = "$" + body
    if "x " in unit or unit.startswith("x"):
        body = body + "x"
    if s.low is not None and s.high is not None and s.low != s.high:
        return f"{body} <span style='color:{PALETTE['text_muted']};'>(range)</span>"
    return body


def render_clinical_verticals() -> str:
    """Render the clinical-specialty verticals reference page."""

    verts = list_verticals()
    n_asc = len(verticals_with_asc_cpl_2026())

    # --- KPI strip ---------------------------------------------------
    kpi_strip = (
        '<div class="ck-kpi-grid" '
        'style="grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Clinical Verticals", ck_fmt_num(len(verts)), "profiled")
        + ck_kpi_block("ASC Site-Shift Exposed", ck_fmt_num(n_asc),
                       "verticals (2026 ASC-CPL)")
        + ck_kpi_block("PFS CF (non-QP)", f"${PFS_CF_NONQP_2026:.4f}",
                       "per total RVU · CMS-1832-F")
        + ck_kpi_block("OPPS / ASC CF",
                       f"${OPPS_CF_2026:.3f} / ${ASC_CF_2026:.3f}",
                       "+2.6% · CMS-1834-FC")
        + '</div>'
    )

    # --- Cross-cutting 2026 policy drivers ---------------------------
    driver_rows = ""
    for key, text in POLICY_DRIVERS_2026.items():
        label = key.replace("_", " ").title()
        driver_rows += (
            f'<tr>'
            f'<td style="font-weight:600;white-space:nowrap;">'
            f'{html.escape(label)}</td>'
            f'<td style="font-size:12px;color:{PALETTE["text_secondary"]};">'
            f'{html.escape(text)}</td>'
            f'</tr>'
        )
    drivers_card = (
        f'<div class="cad-card">'
        f'<h2>Cross-cutting 2026 policy drivers</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'The forces reshaping site-of-care and revenue cycle across the '
        f'procedural verticals. Each per-vertical card flags which apply.</p>'
        f'<table class="cad-table"><tbody>{driver_rows}</tbody></table>'
        f'</div>'
    )

    # --- Volume anchors leaderboard ----------------------------------
    anchor_rows = ""
    for s in volume_anchors()[:10]:
        anchor_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{html.escape(s.label)}</td>'
            f'<td class="num">{_fmt_stat_value(s)}</td>'
            f'<td style="font-size:11px;color:{PALETTE["text_muted"]};">'
            f'{html.escape(s.source)}'
            f'{(" · " + str(s.year)) if s.year else ""}</td>'
            f'</tr>'
        )
    anchors_card = (
        f'<div class="cad-card">'
        f'<h2>Volume anchors</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'The "how big is each vertical" headline counts, sorted descending.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Anchor</th><th class="num">Value</th><th>Source</th>'
        f'</tr></thead><tbody>{anchor_rows}</tbody></table>'
        f'</div>'
    )

    # --- Per-vertical cards ------------------------------------------
    cards = ""
    for v in verts:
        # Badges: ASC exposure + policy drivers.
        badges = ""
        if v.asc_cpl_2026:
            badges += ck_signal_badge("ASC site-shift", tone="warning") + " "
        for pk in v.policy_2026:
            badges += (
                f'<span class="cad-badge cad-badge-muted" '
                f'style="font-size:10px;margin:1px;">'
                f'{html.escape(pk.replace("_", " "))}</span>'
            )

        # Top epidemiology / access stats (max 4 for the card).
        stat_pool = (v.epidemiology + v.access + v.benchmarks)[:4]
        stat_rows = ""
        for s in stat_pool:
            note = (f'<div style="font-size:10.5px;color:{PALETTE["text_muted"]};">'
                    f'{html.escape(s.note)}</div>') if s.note else ""
            stat_rows += (
                f'<tr>'
                f'<td style="font-size:11.5px;">{html.escape(s.label)}{note}</td>'
                f'<td class="num" style="font-size:11.5px;white-space:nowrap;">'
                f'{_fmt_stat_value(s)}</td>'
                f'</tr>'
            )
        stat_table = (
            f'<table class="cad-table" style="margin:6px 0;">'
            f'<tbody>{stat_rows}</tbody></table>'
        ) if stat_rows else ""

        # Code chips (first 8 of each system that has codes).
        code_bits = []
        for sys_label, codes in (
            ("CPT", v.codes.cpt), ("HCPCS/J", v.codes.hcpcs),
            ("ICD-10", v.codes.icd10), ("DRG", v.codes.drg),
            ("Taxonomy", v.codes.taxonomy),
        ):
            if codes:
                shown = ", ".join(codes[:8])
                code_bits.append(
                    f'<strong>{sys_label}:</strong> {html.escape(shown)}'
                )
        code_html = (
            f'<div style="font-size:10.5px;color:{PALETTE["text_muted"]};'
            f'line-height:1.7;margin-bottom:6px;">'
            + " &nbsp;·&nbsp; ".join(code_bits) + '</div>'
        ) if code_bits else ""

        # Viz chips.
        viz_html = " ".join(
            f'<span class="cad-badge cad-badge-muted" '
            f'style="font-size:9.5px;margin:1px;" title="{html.escape(z.description)}">'
            f'{html.escape(z.chart_type)}</span>'
            for z in v.viz
        )

        sources = " · ".join(html.escape(s) for s in v.sources[:4])
        caveat_html = ""
        if v.caveats:
            caveat_html = (
                f'<div style="font-size:10px;color:{PALETTE["warning"]};'
                f'margin-top:4px;">&#9888; {html.escape(v.caveats[0])}</div>'
            )

        cards += (
            f'<div class="cad-card" '
            f'style="border-left:3px solid {PALETTE["brand_accent"]};">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:start;margin-bottom:6px;">'
            f'<h2 style="margin:0;font-size:16px;">{html.escape(v.name)}</h2>'
            f'<div>{badges}</div>'
            f'</div>'
            f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};'
            f'line-height:1.5;margin-bottom:6px;">{html.escape(v.summary)}</p>'
            f'{code_html}'
            f'{stat_table}'
            f'<div style="font-size:11px;color:{PALETTE["text_secondary"]};'
            f'margin-bottom:4px;"><strong>Reimbursement:</strong> '
            f'{html.escape(v.reimbursement)}</div>'
            f'<div style="margin:4px 0;">{viz_html}</div>'
            f'<div style="font-size:10px;color:{PALETTE["text_muted"]};">'
            f'<strong>Sources:</strong> {sources}</div>'
            f'{caveat_html}'
            f'</div>'
        )

    head = ck_editorial_head(
        eyebrow="RESEARCH · CLINICAL VERTICALS",
        title="Clinical Verticals Reference",
        meta=(
            f"{len(verts)} VERTICALS · {n_asc} ASC-EXPOSED · CY2026"
        ),
        lede_italic_phrase=(
            "Thirteen US healthcare specialty verticals, profiled across "
            "codes, epidemiology, workforce, access, and reimbursement."
        ),
        lede_body=(
            "The clinical-specialty companion to the facility verticals. "
            "Every figure is sourced and chart-ready; the 2026 ASC site-shift "
            "and No-Surprises-Act IDR drivers are flagged per vertical."
        ),
    )

    next_up = ck_next_section(
        "See the facility verticals (ASC / BH / MSO)",
        "/verticals",
        eyebrow="Up next",
        italic_word="facility",
    )

    body = (
        head
        + kpi_strip
        + drivers_card
        + anchors_card
        + f'<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        f'minmax(420px,1fr));gap:12px;">{cards}</div>'
        + next_up
        + ck_page_actions()
    )

    return chartis_shell(
        body, "Clinical Verticals Reference",
        subtitle="13 US healthcare specialty verticals · CY2026",
    )

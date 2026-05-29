"""Hospital provider directory — /hospital/<ccn>/providers.

Commercial-DD-grade view of the provider roster at a hospital, sourced
from the NPPES live cache (rcm_mc.data_public.nppes_cache). Used during
Phase-1 diligence to read:

  - Specialty mix (top taxonomies → count)
  - Provider concentration (top-N producers as share of total)
  - Cache freshness (when was this last refreshed?)
  - Cross-link to the in-platform PPAM physician-attrition view

When the cache is empty or stale, the page renders an "empty / refresh"
CTA pointing partners to the CLI command + the /data/refresh surface.
"""
from __future__ import annotations

import html as _html
import sqlite3
from collections import Counter
from typing import Any, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_bar_row, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_panel, ck_provenance_tooltip, ck_section_intro,
    ck_signal_badge,
)
from ..data_public.nppes_cache import (
    cache_age_days, get_cached_org_roster, list_providers,
)


def _freshness_tone(age_days: Optional[int]) -> str:
    """Map cache age to severity tone for the freshness chip."""
    if age_days is None:
        return "negative"
    if age_days <= 30:
        return "positive"
    if age_days <= 90:
        return "warning"
    return "negative"


def _freshness_label(age_days: Optional[int]) -> str:
    if age_days is None:
        return "No cached data"
    if age_days <= 1:
        return f"Refreshed {age_days}d ago · fresh"
    return f"Refreshed {age_days}d ago"


def render_hospital_providers(
    con: sqlite3.Connection,
    ccn: str,
    *,
    hospital_name: str = "",
    state: str = "",
) -> str:
    """Render the provider-directory page for one CCN.

    Reads the NPPES live cache; renders an empty state with refresh
    instructions if nothing is cached.
    """
    ccn_safe = _html.escape(str(ccn))
    name_safe = _html.escape(hospital_name) if hospital_name else f"CCN {ccn_safe}"

    summary = get_cached_org_roster(con, ccn)
    providers = list_providers(con, ccn)
    age = cache_age_days(con, ccn)

    # 2026-05-28 batch 22 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow=f"PROVIDER DIRECTORY · {ccn_safe}",
        title=f"Who actually practices at {name_safe}.",
        meta=(
            f"{len(providers)} NPI"
            f"{'S' if len(providers) != 1 else ''} · "
            f"NPPES LIVE CACHE · "
            + (f"AGE {age}d" if age is not None else "FRESH")
        ),
        lede_italic_phrase=(
            "Who actually practices at this hospital."
        ),
        lede_body=(
            "NPPES live-cache view of every Type-1 individual and "
            "Type-2 organization NPI registered to this hospital's "
            "practice address. Used during commercial DD to read "
            "specialty mix, provider concentration, and recruiting-"
            "market depth — none of which HCRIS cost-report data "
            "captures."
        ),
    )

    # Freshness chip — surfaces when this data was last refreshed.
    freshness_chip = ck_signal_badge(
        _freshness_label(age),
        tone=_freshness_tone(age),
    )
    fetched_iso = (summary or {}).get("fetched_at_iso", "")
    freshness_panel = (
        f'<div style="margin-bottom:12px;display:flex;align-items:center;'
        f'gap:10px;font-size:11px;color:var(--cad-text2);">'
        f'{freshness_chip}'
        f'<span>Source: NPPES NPI Registry (CMS, live).'
        + (f' Last fetch: {_html.escape(fetched_iso[:19])}' if fetched_iso else "")
        + '</span>'
        f'</div>'
    )

    if not summary or not providers:
        empty = ck_panel(
            '<p class="ck-section-body">'
            '<strong>No NPPES data cached for this CCN.</strong> The '
            'provider directory pulls from a live CMS feed via an explicit '
            'CLI refresh, not on every page load (NPPES is rate-limited; '
            'inline calls would slow every render).'
            '</p>'
            '<p class="ck-section-body" style="margin-top:8px;">'
            'Run from the project root:</p>'
            # 2026-05-28 batch 31 · Tier-4 trope removal — drops
            # decorative 3px accent stripe; caps radius at 2px.
            f'<pre style="background:var(--cad-panel-alt);padding:12px;'
            f'font-family:var(--cad-mono);font-size:12px;border-radius:2px;'
            f'border:1px solid var(--cad-border);overflow-x:auto;">'
            f'rcm-mc data refresh-nppes --ccn {ccn_safe} '
            f'--name "{_html.escape(hospital_name or "Hospital")}" '
            f'--state {_html.escape(state or "—")}'
            f'</pre>'
            '<p class="ck-section-body" style="margin-top:8px;">'
            'Or trigger from <a class="ck-link" href="/data/refresh">'
            '/data/refresh</a>. Cache TTL is 30 days; a fresh pull '
            'typically takes ~5 seconds for a community hospital and '
            '~15 seconds for an urban academic.</p>',
            title="No cached data",
        )
        body = intro + freshness_panel + empty
        return chartis_shell(
            body,
            title=f"Providers — {name_safe}",
            active_nav="/diligence/deal",
            subtitle=(
                f"NPPES live cache — empty for CCN {ccn_safe}"
            ),
        )

    # ── KPI strip ───────────────────────────────────────────────
    spec_mix = summary["specialty_mix"]
    top_spec = ""
    if spec_mix:
        top_label, top_count = max(spec_mix.items(), key=lambda kv: kv[1])
        top_spec = f"{top_label} ({top_count})"

    providers_value = ck_provenance_tooltip(
        "Provider roster",
        ck_fmt_num(summary["n_providers"]),
        explainer=(
            f"Distinct NPIs cached for this CCN as of "
            f"{(fetched_iso or '')[:10]}. Counts Type-1 individuals + "
            f"Type-2 organizations at the practice address(es) "
            f"resolved from NPPES."
        ),
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Total providers", providers_value, "Type-1 + Type-2",
            help={
                "definition": (
                    "All distinct NPIs cached for the hospital's "
                    "practice address. Bigger doesn't always mean "
                    "better — large physician rosters at low-margin "
                    "hospitals signal labor-cost overhang."
                ),
            },
        )
        + ck_kpi_block(
            "Individuals", ck_fmt_num(summary["n_individuals"]),
            "Type-1 NPI-1 individual practitioners",
            help={
                "definition": (
                    "Individual provider NPIs (Type-1). The recruiting "
                    "pool + concentration risk lives here — a single "
                    "specialty with 1-2 producers is structurally "
                    "fragile."
                ),
            },
        )
        + ck_kpi_block(
            "Organizations", ck_fmt_num(summary["n_organizations"]),
            "Type-2 NPI-2 group practices",
            help={
                "definition": (
                    "Group / organizational NPIs at this address. "
                    "Includes the hospital itself plus affiliated "
                    "physician groups; useful for identifying "
                    "structural relationships (employed vs PSA vs "
                    "independent)."
                ),
            },
        )
        + ck_kpi_block(
            "Specialty mix", str(len(spec_mix)),
            "distinct taxonomies",
            help={
                "definition": (
                    "Count of distinct NPPES taxonomy codes across "
                    "the roster. Diverse mix (>20) = full-service "
                    "facility; narrow mix (<8) = specialty platform."
                ),
            },
        )
        + ck_kpi_block(
            "Top specialty", top_spec or "—",
            "largest cohort",
        )
        + '</div>'
    )

    # ── Specialty mix table ──────────────────────────────────────
    mix_rows = ""
    sorted_specs = sorted(
        spec_mix.items(), key=lambda kv: kv[1], reverse=True
    )
    for label, count in sorted_specs[:20]:
        share_pct = (count / summary["n_providers"] * 100) if summary["n_providers"] else 0
        # Concentration callout: any single specialty > 50% = flag
        flag = (
            ' <span class="ck-badge tone-warning">CONCENTRATION</span>'
            if share_pct >= 50 else ""
        )
        mix_rows += (
            f'<tr>'
            f'<td>{_html.escape(label)}{flag}</td>'
            f'<td class="num">{count}</td>'
            f'<td class="num">{share_pct:.1f}%</td>'
            f'</tr>'
        )

    # Lead concentration chart — share of roster by taxonomy, so the
    # structural-fragility read (one specialty dominating) lands before
    # the table. Bars flag red ≥50% (the CONCENTRATION threshold), amber
    # ≥30%, teal otherwise.
    n_prov = summary["n_providers"] or 1
    mix_bars = ""
    for label, count in sorted_specs[:10]:
        share = count / n_prov * 100
        tone = "negative" if share >= 50 else "warning" if share >= 30 else "teal"
        mix_bars += ck_bar_row(label, str(count), share, tone=tone)
    mix_chart = (
        '<div style="margin-bottom:12px;">' + mix_bars + '</div>'
        if mix_bars else ""
    )

    mix_section = ck_panel(
        mix_chart
        + '<table class="cad-table"><thead><tr>'
        '<th>Taxonomy</th><th>Count</th><th>Share</th>'
        f'</tr></thead><tbody>{mix_rows}</tbody></table>'
        + (
            '<p class="ck-section-body" style="margin-top:10px;'
            'font-style:italic;color:var(--cad-text-faint);">'
            'CONCENTRATION flags single specialties above 50% of the '
            'roster — a structural-fragility signal worth understanding '
            'before LOI.'
            '</p>'
            if any(
                count / summary["n_providers"] * 100 >= 50
                for count in spec_mix.values()
            ) else ""
        ),
        title=f"Specialty mix · top {min(20, len(sorted_specs))} taxonomies",
    )

    # ── Provider list (top 50) ───────────────────────────────────
    p_rows = ""
    for p in providers[:50]:
        entity_chip = (
            '<span class="ck-badge tone-neutral">ORG</span>'
            if p.is_organization
            else '<span class="ck-badge tone-neutral">IND</span>'
        )
        p_rows += (
            f'<tr>'
            f'<td>{_html.escape(p.name)}</td>'
            f'<td>{entity_chip}</td>'
            f'<td class="num" style="font-family:var(--cad-mono);font-size:11px;">'
            f'{_html.escape(p.npi)}</td>'
            f'<td>{_html.escape(p.primary_specialty or "—")}</td>'
            f'<td>{_html.escape(p.city or "—")}, {_html.escape(p.state or "—")}</td>'
            f'</tr>'
        )
    list_section = ck_panel(
        '<table class="cad-table"><thead><tr>'
        '<th>Name</th><th>Type</th><th>NPI</th>'
        '<th>Specialty</th><th>Location</th>'
        f'</tr></thead><tbody>{p_rows}</tbody></table>'
        + (
            f'<p class="ck-section-body" style="margin-top:10px;'
            f'font-size:11px;color:var(--cad-text-faint);">'
            f'Showing first 50 of {summary["n_providers"]} providers. '
            f'Full roster available via the CLI export '
            f'<code>rcm-mc data export nppes --ccn {ccn_safe}</code>.</p>'
            if summary["n_providers"] > 50 else ""
        ),
        title=f"Provider roster · top 50 by name",
    )

    next_up = ck_next_section(
        "Cross-check against PPAM attrition predictions",
        "/diligence/physician-attrition",
        eyebrow="Continue —",
        italic_word="attrition",
    )

    body = (
        intro
        + freshness_panel
        + kpis
        + mix_section
        + list_section
        + next_up
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title=f"Providers — {name_safe}",
        active_nav="/diligence/deal",
        subtitle=(
            f"{summary['n_providers']} NPIs · "
            f"{summary['n_organizations']} orgs · "
            f"{summary['n_individuals']} individuals · "
            f"refreshed {age}d ago"
        ),
    )

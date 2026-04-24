"""Per-deal IC Packet — /deal/<id>/ic-packet.

The "give me everything in one document" view. Combines the outputs
of ``pe_intelligence.ic_memo`` and ``pe_intelligence.master_bundle``
into a single page a partner can skim before an IC meeting.

What master_bundle(packet) gives us (top-level keys):

  review, ic_memo, lp_pitch, memo_formats, analyst_cheatsheet,
  board_memo, hundred_day_plan_markdown, narrative_styles,
  extra_heuristics, extra_red_flags, deepdive_heuristics,
  bear_patterns, regulatory_items, scenario_narrative,
  partner_discussion, audit_trail.

We render a compact table-of-contents, the IC memo (via
ic_memo.render_html which already returns institutional HTML), the
analyst cheat-sheet, the 100-day plan, bear patterns, regulatory
items, and a partner discussion section. Each section collapses to
an empty-state placeholder when the bundle lacks that key.
"""
from __future__ import annotations

import html as _html
import json as _json
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import (
    bullet_list,
    deal_header_nav,
    empty_note,
    insufficient_data_banner,
    render_page_explainer,
    safe_dict,
    small_panel,
    verdict_badge,
)


_SECTION_DEFS: List[tuple[str, str, str]] = [
    # (bundle_key, anchor, display_title)
    ("ic_memo",                  "ic-memo",         "IC Memo"),
    ("analyst_cheatsheet",       "cheatsheet",      "Analyst Cheat-Sheet"),
    ("bear_patterns",            "bear-patterns",   "Bear Patterns"),
    ("regulatory_items",         "regulatory",      "Regulatory Items"),
    ("hundred_day_plan_markdown","hundred-day",     "100-Day Plan"),
    ("partner_discussion",       "discussion",      "Partner Discussion"),
    ("scenario_narrative",       "scenario",        "Scenario Narrative"),
    ("board_memo",               "board-memo",      "Board Memo"),
    ("lp_pitch",                 "lp-pitch",        "LP Pitch"),
    ("audit_trail",              "audit",           "Audit Trail"),
]

_CLAUDE_STATUS_COLORS = {
    "confirmed": P["positive"],
    "needs_attention": P["warning"],
    "insufficient_support": P["negative"],
    "not_configured": P["text_faint"],
    "call_failed": P["negative"],
    "failed": P["negative"],
}


def _toc(bundle: Dict[str, Any], review: Any = None) -> str:
    """Links strip at the top — one entry per populated section."""
    items = []
    if review is not None:
        items.append(
            f'<a href="#supplemental-review" '
            f'style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-radius:2px;padding:4px 8px;font-family:var(--ck-mono);'
            f'font-size:10px;color:{P["accent"]};text-decoration:none;'
            f'letter-spacing:0.04em;">Supplemental Review &rarr;</a>'
        )
    for key, anchor, title in _SECTION_DEFS:
        if not bundle.get(key):
            continue
        items.append(
            f'<a href="#{anchor}" '
            f'style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-radius:2px;padding:4px 8px;font-family:var(--ck-mono);'
            f'font-size:10px;color:{P["accent"]};text-decoration:none;'
            f'letter-spacing:0.04em;">{_html.escape(title)} &rarr;</a>'
        )
    if not items:
        return ""
    return (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;">'
        f'{"".join(items)}</div>'
    )


def _ic_memo_section(html_body: str, anchor: str) -> str:
    """Wrap the ic_memo HTML (which is a full styled block) in our
    standard chartis panel so it reads at parity with the other sections.
    """
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">IC Memo <span style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.12em;color:{P["text_faint"]};'
        f'margin-left:8px;">MEM</span></div>'
        f'<div style="padding:14px 18px;">{html_body}</div>'
        f'</div>'
    )


def _supplemental_healthcare_panel(review: Any) -> str:
    checks = getattr(review, "healthcare_checks", None) or {}
    sev = checks.get("severity_counts") or {}
    total_hits = int(checks.get("total_hits") or len(checks.get("hits") or []))
    summary = str(checks.get("summary") or "No supplemental healthcare checks available.")
    focus_areas = list(checks.get("focus_areas") or [])
    focus = "".join(
        f'<span class="ck-sig" style="margin-right:6px;margin-bottom:6px;">'
        f'{_html.escape(str(area.get("category", "OTHER")))} '
        f'{int(area.get("count", 0))}</span>'
        for area in focus_areas[:6]
    )
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">Supplemental Healthcare Checks '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'HCX</span></div>'
        f'<div style="padding:14px 18px;">'
        f'<div class="ck-kpi-grid" style="margin-bottom:12px;">'
        f'{ck_kpi_block("Supplemental Hits", str(total_hits), "additive")}'
        f'{ck_kpi_block("Critical", str(sev.get("CRITICAL", 0)), "extra checks")}'
        f'{ck_kpi_block("High", str(sev.get("HIGH", 0)), "extra checks")}'
        f'{ck_kpi_block("Medium", str(sev.get("MEDIUM", 0)), "extra checks")}'
        f'</div>'
        f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;'
        f'margin:0 0 10px;">{_html.escape(summary)} These checks are additive '
        f'and do not override the core IC verdict.</p>'
        + (
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;">{focus}</div>'
            if focus else ""
        )
        + f'</div></div>'
    )


def _claude_review_panel(review: Any) -> str:
    claude = getattr(review, "claude_review", None) or {}
    status = str(claude.get("status") or "not_configured")
    color = _CLAUDE_STATUS_COLORS.get(status, P["text_faint"])
    status_label = status.replace("_", " ").upper()
    summary = str(claude.get("summary") or "Claude review not available.").strip()
    model = str(claude.get("model") or "fallback")
    confirmed = [str(x) for x in list(claude.get("confirmed_points") or []) if str(x).strip()]
    concerns = [str(x) for x in list(claude.get("concerns") or []) if str(x).strip()]

    def _bullets(items: List[str], label: str, tone: str) -> str:
        if not items:
            return ""
        lis = "".join(
            f'<li style="padding:4px 0;color:{P["text"]};font-size:11.5px;line-height:1.5;">'
            f'{_html.escape(item)}</li>'
            for item in items[:4]
        )
        return (
            f'<div style="margin-top:10px;">'
            f'<div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;'
            f'color:{tone};margin-bottom:4px;">{_html.escape(label)}</div>'
            f'<ul style="margin:0;padding-left:18px;">{lis}</ul>'
            f'</div>'
        )

    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">Claude Look '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'CLD</span></div>'
        f'<div style="padding:14px 18px;">'
        f'<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;">'
        f'<span class="ck-sig" style="color:{color};border:1px solid {color};'
        f'background:rgba(255,255,255,0.02);">{_html.escape(status_label)}</span>'
        f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);font-size:10px;">'
        f'{_html.escape(model)}</span>'
        f'</div>'
        f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.6;margin:10px 0 0;">'
        f'{_html.escape(summary)}</p>'
        + _bullets(confirmed, "CONFIRMED POINTS", P["positive"])
        + _bullets(concerns, "WATCH ITEMS", P["warning"])
        + f'</div></div>'
    )


def _supplemental_review_section(review: Any) -> str:
    if review is None:
        return ""
    checks = getattr(review, "healthcare_checks", None) or {}
    total_hits = int(checks.get("total_hits") or len(checks.get("hits") or []))
    return (
        f'<div id="supplemental-review">'
        + ck_section_header(
            "SUPPLEMENTAL REVIEW SIGNALS",
            "additive healthcare checks + Claude confirmation",
            count=total_hits,
        )
        + f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));'
        f'gap:12px;margin-bottom:14px;">'
        f'{_supplemental_healthcare_panel(review)}'
        f'{_claude_review_panel(review)}'
        f'</div></div>'
    )


def _cheatsheet_section(data: Dict[str, Any], anchor: str) -> str:
    if not isinstance(data, dict) or not data:
        return small_panel("Analyst Cheat-Sheet", empty_note("No cheat-sheet."), code="CHT")
    # The cheat-sheet is a dict of named subsections — render as
    # definition list, each value might be list of strings or string.
    rows = []
    for k, v in data.items():
        key_label = str(k).replace("_", " ").title()
        if isinstance(v, list):
            body = bullet_list(v, color=P["text"])
        elif isinstance(v, dict):
            body = "".join(
                f'<div style="padding:3px 0;font-size:11px;">'
                f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
                f'font-size:10px;width:140px;display:inline-block;">'
                f'{_html.escape(str(kk))}</span>'
                f'<span style="color:{P["text"]};">{_html.escape(str(vv))}</span>'
                f'</div>'
                for kk, vv in v.items()
            ) or empty_note("—")
        else:
            body = (
                f'<p style="color:{P["text"]};font-size:11.5px;line-height:1.55;">'
                f'{_html.escape(str(v))}</p>'
            )
        rows.append(
            f'<div style="margin-bottom:10px;">'
            f'<div style="font-family:var(--ck-mono);font-size:10px;'
            f'letter-spacing:0.12em;color:{P["accent"]};margin-bottom:4px;">'
            f'{_html.escape(key_label)}</div>'
            f'{body}</div>'
        )
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">Analyst Cheat-Sheet '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">CHT</span>'
        f'</div><div style="padding:14px 18px;">{"".join(rows)}</div></div>'
    )


def _bear_patterns_section(items: List[Any], anchor: str) -> str:
    if not items:
        return small_panel("Bear Patterns", empty_note("No bear patterns matched."), code="BER")
    rows = []
    for hit in items:
        d = safe_dict(hit) if not isinstance(hit, dict) else hit
        title = _html.escape(str(d.get("title") or d.get("pattern_name") or d.get("name") or "—"))
        confidence = d.get("confidence", d.get("score"))
        conf_str = (
            f'{float(confidence):.2f}' if isinstance(confidence, (int, float)) else "—"
        )
        note = _html.escape(str(d.get("partner_note") or d.get("finding") or "")[:400])
        rows.append(
            f'<div style="padding:8px 0;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11.5px;">'
            f'<div style="display:flex;gap:10px;align-items:baseline;">'
            f'<span style="color:{P["negative"]};font-family:var(--ck-mono);'
            f'font-size:9px;letter-spacing:0.12em;">BEAR</span>'
            f'<span style="color:{P["text"]};font-weight:600;">{title}</span>'
            f'<span style="margin-left:auto;color:{P["text_faint"]};'
            f'font-family:var(--ck-mono);font-size:10px;">'
            f'conf {conf_str}</span></div>'
            + (
                f'<div style="color:{P["text_dim"]};margin-top:4px;line-height:1.5;">'
                f'{note}</div>' if note else ""
            )
            + f'</div>'
        )
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">Bear Patterns ({len(items)}) '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">BER</span>'
        f'</div><div style="padding:14px 18px;">{"".join(rows)}</div></div>'
    )


def _regulatory_section(items: List[Any], anchor: str) -> str:
    if not items:
        return small_panel("Regulatory Items", empty_note("No regulatory hits."), code="REG")
    rows = []
    for it in items:
        d = safe_dict(it) if not isinstance(it, dict) else it
        name = _html.escape(str(d.get("name") or d.get("title") or "—"))
        impact = d.get("dollar_impact") or d.get("impact")
        impact_str = ""
        if isinstance(impact, (int, float)):
            impact_str = f"${impact/1e6:.1f}M"
        elif impact is not None:
            impact_str = _html.escape(str(impact))
        desc = _html.escape(str(d.get("description") or d.get("note") or "")[:400])
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-weight:600;font-size:11.5px;">{name}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);color:{P["warning"]};'
            f'font-variant-numeric:tabular-nums;">{impact_str or "—"}</td>'
            f'<td style="color:{P["text_dim"]};font-size:11px;line-height:1.4;'
            f'white-space:normal;">{desc or "—"}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">Regulatory Items ({len(items)}) '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">REG</span>'
        f'</div>'
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr><th>Item</th><th class="num">Impact</th>'
        f'<th>Description</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></div>'
    )


def _markdown_section(title: str, md_text: str, anchor: str, code: str) -> str:
    if not md_text:
        return small_panel(title, empty_note("Not generated."), code=code)
    # We preserve the markdown as-is — partners read it verbatim for
    # export parity with the other brain renderers.
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">{_html.escape(title)} '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'{code}</span></div>'
        f'<pre style="padding:14px 18px;color:{P["text"]};'
        f'font-family:var(--ck-mono);font-size:11px;line-height:1.6;'
        f'white-space:pre-wrap;margin:0;">{_html.escape(md_text)}</pre>'
        f'</div>'
    )


def _discussion_section(items: Any, anchor: str) -> str:
    rows = []
    if items is None:
        items = []
    for it in items or []:
        d = safe_dict(it) if not isinstance(it, dict) else it
        voice = _html.escape(str(d.get("voice") or "—"))
        statement = _html.escape(str(d.get("statement") or d.get("text") or ""))
        rows.append(
            f'<div style="padding:8px 0;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11.5px;">'
            f'<span style="color:{P["accent"]};font-family:var(--ck-mono);'
            f'font-size:9px;letter-spacing:0.12em;">{voice.upper()}</span>'
            f'<p style="color:{P["text"]};margin-top:4px;line-height:1.55;">'
            f'{statement or "—"}</p></div>'
        )
    body = "".join(rows) if rows else empty_note("No partner discussion.")
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">Partner Discussion '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">DSC</span>'
        f'</div><div style="padding:14px 18px;">{body}</div></div>'
    )


def _audit_section(audit: Any, anchor: str) -> str:
    d = safe_dict(audit) if not isinstance(audit, dict) else audit
    if not d:
        return small_panel("Audit Trail", empty_note("No audit trail."), code="AUD")
    # Render as JSON pre for transparency — this section is about
    # traceability, not beauty.
    try:
        pretty = _json.dumps(d, default=str, indent=2)[:8000]
    except Exception:
        pretty = str(d)[:8000]
    return (
        f'<div class="ck-panel" id="{anchor}">'
        f'<div class="ck-panel-title">Audit Trail '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">AUD</span>'
        f'</div>'
        f'<pre style="padding:14px 18px;color:{P["text_dim"]};'
        f'font-family:var(--ck-mono);font-size:10px;line-height:1.5;'
        f'white-space:pre-wrap;overflow-x:auto;margin:0;'
        f'max-height:300px;overflow-y:auto;">{_html.escape(pretty)}</pre>'
        f'</div>'
    )


def render_ic_packet(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    bundle: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="ic-packet")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="IC packet",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"IC Packet · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"IC packet unavailable for {label}",
        )

    b = bundle or {}
    if not b:
        body = header + small_panel(
            "IC Packet — not built",
            empty_note("master_bundle returned nothing for this deal."),
            code="NIL",
        )
        return chartis_shell(
            body, title=f"IC Packet · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"{label} · IC packet unavailable",
        )

    # Banner at the top — IC-verdict pulled from the review's narrative.
    rec = str(getattr(review.narrative, "recommendation", "—") or "—") if review else "—"
    rec_colors = {
        "PASS": P["negative"],
        "PROCEED_WITH_CAVEATS": P["warning"],
        "PROCEED": P["text"],
        "STRONG_PROCEED": P["positive"],
    }
    rec_col = rec_colors.get(rec, P["text_dim"])
    headline = str(getattr(review.narrative, "headline", "") or "") if review else ""
    banner = (
        f'<div style="background:{P["panel"]};border-left:4px solid {rec_col};'
        f'border:1px solid {P["border"]};border-left-width:4px;border-radius:3px;'
        f'padding:14px 18px;margin-bottom:14px;">'
        f'<div style="display:flex;gap:12px;align-items:baseline;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">IC VERDICT</span>'
        f'{verdict_badge(rec, color=rec_col)}'
        f'<span style="margin-left:auto;font-family:var(--ck-mono);'
        f'font-size:10px;color:{P["text_faint"]};">'
        f'built {review.generated_at:%Y-%m-%d %H:%M UTC}</span>'
        f'</div>'
        + (
            f'<div style="color:{P["text"]};font-size:13px;margin-top:8px;'
            f'line-height:1.55;">{_html.escape(headline)}</div>' if headline else ""
        )
        + f'</div>'
    )

    # KPI count of populated sections
    populated = sum(1 for k, _, _ in _SECTION_DEFS if b.get(k))
    healthcare_checks = getattr(review, "healthcare_checks", None) or {}
    supplemental_hits = int(
        healthcare_checks.get("total_hits")
        or len(healthcare_checks.get("hits") or [])
    )
    kpis = (
        ck_kpi_block("Sections", str(populated), f"of {len(_SECTION_DEFS)} bundled")
        + ck_kpi_block("Bear Patterns", str(len(b.get("bear_patterns") or [])), "matches")
        + ck_kpi_block("Regulatory Items",
                        str(len(b.get("regulatory_items") or [])), "in registry")
        + ck_kpi_block("Extra Heuristics",
                        str(len(b.get("extra_heuristics") or [])), "beyond core")
        + ck_kpi_block("Deep-Dive Hits",
                        str(len(b.get("deepdive_heuristics") or [])), "granular checks")
        + ck_kpi_block("Healthcare Checks", str(supplemental_hits), "additive")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    toc = _toc(b, review=review)
    ic_html = str(b.get("ic_memo") or "")
    ic_memo_section = _ic_memo_section(ic_html, "ic-memo") if ic_html else small_panel(
        "IC Memo", empty_note("ic_memo not rendered."), code="MEM",
    )
    cheatsheet_section = _cheatsheet_section(b.get("analyst_cheatsheet") or {}, "cheatsheet")
    bear_section = _bear_patterns_section(b.get("bear_patterns") or [], "bear-patterns")
    regulatory_section = _regulatory_section(b.get("regulatory_items") or [], "regulatory")
    hundred_day_section = _markdown_section(
        "100-Day Plan", str(b.get("hundred_day_plan_markdown") or ""),
        "hundred-day", "100D",
    )
    discussion_section = _discussion_section(b.get("partner_discussion"), "discussion")

    # scenario_narrative is a dict with a 'markdown' or 'summary' field
    sn = safe_dict(b.get("scenario_narrative"))
    scenario_text = (
        sn.get("markdown") or sn.get("summary")
        or sn.get("narrative") or ""
    )
    scenario_section = _markdown_section(
        "Scenario Narrative", str(scenario_text or ""), "scenario", "SCN",
    )

    # board_memo and lp_pitch are dicts with HTML/MD content
    board_dict = safe_dict(b.get("board_memo"))
    board_html = str(board_dict.get("html") or board_dict.get("markdown") or "")
    board_section = _markdown_section(
        "Board Memo", str(board_dict.get("markdown") or ""),
        "board-memo", "BRD",
    )
    lp_dict = safe_dict(b.get("lp_pitch"))
    lp_section = _markdown_section(
        "LP Pitch", str(lp_dict.get("markdown") or lp_dict.get("text") or ""),
        "lp-pitch", "LPP",
    )

    audit_section = _audit_section(b.get("audit_trail"), "audit")

    # TODO(phase-7): split into per-section micro-explainers as part
    # of a later documentation polish pass.
    explainer = render_page_explainer(
        what=(
            "IC-ready packet combining the IC memo, analyst "
            "cheat-sheet, bear patterns, regulatory items, 100-day "
            "plan, and partner discussion into a single view a "
            "partner can skim before the meeting."
        ),
        source=(
            "pe_intelligence/master_bundle.py::build_master_bundle "
            "(top-level composer); ic_memo.render_html (memo body)."
        ),
        page_key="deal-ic-packet",
    )

    body = (
        explainer
        + header
        + banner
        + kpi_strip
        + toc
        + _supplemental_review_section(review)
        + ck_section_header(
            "IC-READY PACKET", "master_bundle(packet) composed",
            count=populated,
        )
        + ic_memo_section
        + cheatsheet_section
        + bear_section
        + regulatory_section
        + hundred_day_section
        + discussion_section
        + scenario_section
        + board_section
        + lp_section
        + audit_section
    )

    return chartis_shell(
        body,
        title=f"IC Packet · {label}",
        active_nav="/pe-intelligence",
        subtitle=f"{label} · {rec} · {populated}/{len(_SECTION_DEFS)} sections",
    )

"""Escalations page — /escalations.

Editorial port of the legacy `_route_escalations` inline renderer.
Surfaces every red alert open ≥ `min_days` (default 30) — the
view a partner reviews before an LP update or weekly check-in:
"anything we've failed to resolve for 30+ days needs a decision."

Reuses the same Insights-style chrome as `/alerts` —
`ck_severity_panel` (red-toned), `ck_affirm_empty` (when zero
matches), `ck_results_header` (count + min-days chip + Clear all).
The threshold picker becomes a filter sidebar group with the
canonical `7 / 14 / 30 / 60 / 90` choices.
"""
from __future__ import annotations

import html as _html
import urllib.parse
from typing import Any, Dict, List


# Canonical day thresholds offered as filter options. 30 is the
# default ("monthly review" cadence); 7 surfaces hot escalations,
# 90 surfaces stale ones the partner has stopped looking at.
_THRESHOLDS = (7, 14, 30, 60, 90)


def _aging_svg(df: Any, min_days: int) -> str:
    """How stale each escalation actually is.

    The list says "47d open" per row; this draws every escalation's
    age as a bar from the threshold line, brick for live alerts and
    gray for acknowledged ones — so "three deals have been red for a
    quarter and nobody silenced them" reads instantly. Capped at the
    20 oldest. Empty frames render nothing.
    """
    if df is None or df.empty:
        return ""
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "deal": str(r.get("deal_id") or "—"),
            "title": str(r.get("title") or ""),
            "days": int(r.get("days_open") or 0),
            "acked": bool(r.get("acked")),
        })
    rows.sort(key=lambda x: -x["days"])
    rows = rows[:20]
    max_days = max(r["days"] for r in rows) or 1

    label_w, bar_w_max, right_w = 230, 360, 70
    row_h, gap, pad_top, pad_bot = 16, 7, 20, 10
    width = label_w + bar_w_max + right_w
    height = pad_top + len(rows) * (row_h + gap) - gap + pad_bot

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Days open per escalated alert">'
        f'<text x="{label_w}" y="{pad_top - 7}" font-size="8.5" '
        f'letter-spacing="1" fill="#7a8699">'
        f'DAYS BEYOND THE {min_days}-DAY THRESHOLD &#8594;</text>'
    ]
    for i, r in enumerate(rows):
        y = pad_top + i * (row_h + gap)
        ty = y + row_h / 2 + 3.5
        label = f'{r["deal"]} · {r["title"]}'
        if len(label) > 34:
            label = label[:33] + "…"
        tone = "#9b9382" if r["acked"] else "#b5321e"
        parts.append(
            f'<text x="{label_w - 8}" y="{ty:.1f}" text-anchor="end" '
            f'font-size="9.5" fill="#465366">{_html.escape(label)}</text>'
        )
        w = max(2.0, bar_w_max * r["days"] / max_days)
        parts.append(
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{row_h}" '
            f'rx="2" fill="{tone}" fill-opacity="0.85"/>'
        )
        suffix = " ACKED" if r["acked"] else ""
        parts.append(
            f'<text x="{label_w + w + 6:.1f}" y="{ty:.1f}" font-size="9.5" '
            f'font-weight="600" fill="{tone}">{r["days"]}d{suffix}</text>'
        )
    parts.append("</svg>")
    note = (
        '<div style="font-size:9px;letter-spacing:0.08em;color:#7a8699;'
        'margin:2px 0 12px;">'
        '<span style="display:inline-block;width:9px;height:9px;'
        'border-radius:2px;background:#b5321e;margin-right:4px;"></span>'
        'LIVE · '
        '<span style="display:inline-block;width:9px;height:9px;'
        'border-radius:2px;background:#9b9382;margin-right:4px;"></span>'
        'ACKNOWLEDGED (KNOWN BUT STILL OPEN) · 20 OLDEST SHOWN</div>'
    )
    return (
        '<div class="ck-escalation-aging">' + "".join(parts) + note + "</div>"
    )


def render_escalations(
    *,
    store: Any,
    min_days: int = 30,
) -> str:
    """Render /escalations with the editorial chrome."""
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_search_hero, ck_filter_sidebar,
        ck_results_header, ck_section_header, ck_section_intro,
        ck_severity_panel, ck_affirm_empty, ck_provenance_tooltip,
        ck_next_section,
    )
    from rcm_mc.alerts.alert_acks import is_acked
    from rcm_mc.alerts.alert_history import days_red

    df = days_red(store, min_days=min_days)

    # Mark each row's ack status so partner sees "known but still
    # open" vs "silenced" — preserved from the legacy renderer.
    if not df.empty:
        ack_flags = []
        for _, r in df.iterrows():
            ack_flags.append(is_acked(
                store,
                kind=str(r["kind"]),
                deal_id=str(r["deal_id"]),
                trigger_key=str(r["trigger_key"]),
            ))
        df = df.assign(acked=ack_flags)

    count = 0 if df is None else len(df)

    # Filter sidebar — single-select radio over the canonical day
    # thresholds. Clicking a threshold submits the form (same UX
    # as the inline ck-sel dropdown the legacy renderer used).
    threshold_opts = [
        {
            "label": f"≥ {t} days",
            "value": str(t),
            "checked": (t == min_days),
        }
        for t in _THRESHOLDS
    ]
    filter_rail = ck_filter_sidebar(
        title="Filter",
        form_action="/escalations",
        groups=[{
            "title": "Days open",
            "name": "min_days",
            "input_type": "radio",
            "options": threshold_opts,
        }],
    )

    # Active-filter chip — one chip naming the threshold; Clear all
    # resets to the default 30-day view (still always shows
    # something so the chip is informational, not "remove this".)
    chips: List[Dict[str, str]] = []
    if min_days != 30:
        chips.append({
            "label": f"≥ {min_days} days",
            "remove_href": "/escalations",
        })

    # Wrap the count value in a provenance hover so the partner sees
    # what "escalation" means without leaving the page. Cycle 34
    # adoption — kit-level ck_provenance_tooltip with explainer text.
    count_display = ck_provenance_tooltip(
        f"Escalations ≥ {min_days}d",
        f"{count:,}",
        explainer=(
            f"Red-severity alerts whose first sighting is older "
            f"than {min_days} days. Threshold tunes the urgency "
            f"window — narrow it to surface hot escalations or "
            f"widen it to find stale items."
        ),
    )
    results_head = ck_results_header(
        count=count_display,
        label="Escalation" if count == 1 else "Escalations",
        chips=chips or None,
        clear_all_href="/escalations" if chips else None,
    )

    section = ck_section_header(
        f"Red alerts open at least {min_days} days",
        eyebrow="PORTFOLIO · ESCALATIONS",
    )

    # Severity panel content — one row per escalated alert. Reuse
    # the alerts-page row shape so partners moving between /alerts
    # and /escalations see the same chrome.
    if df is None or df.empty:
        results_body = ck_affirm_empty(
            headline=f"No red alerts open ≥ {min_days} days.",
            body=(
                "Escalations show red-severity alerts whose first "
                "sighting is older than the threshold. History is "
                "built up on every /alerts call — narrow the "
                "threshold above to look further back."
            ),
            cta_text="View live alerts",
            cta_href="/alerts",
        )
    else:
        rows_html = []
        for _, r in df.iterrows():
            days_open = int(r["days_open"])
            deal_id = str(r["deal_id"])
            deal_q = urllib.parse.quote(deal_id)
            title = _html.escape(str(r.get("title") or ""))
            detail = _html.escape(str(r.get("detail") or ""))
            first_seen = _html.escape(str(r["first_seen_at"])[:10])
            ack_badge = (
                ' <span class="ck-badge tone-neutral">ACKED</span>'
                if r.get("acked") else ""
            )
            rows_html.append(
                "<li>"
                '<div class="ck-severity-row">'
                f'<a class="deal" href="/deal/{deal_q}">'
                f'{_html.escape(deal_id)}</a>'
                f'<span class="title">{title}</span>'
                f'<span class="age">{days_open}d open · {first_seen}</span>'
                "</div>"
                f'<div class="ck-severity-detail">{detail}{ack_badge}</div>'
                "</li>"
            )
        results_body = _aging_svg(df, min_days) + ck_severity_panel(
            tone="red",
            label=f"Aged ≥ {min_days} days",
            count=count,
            rows_html="".join(rows_html),
        )

    # CSV download is preserved — the link below the results header
    # uses the existing /escalations?format=csv branch in server.py.
    csv_link = (
        f'<a class="ck-arrow" '
        f'href="/escalations?min_days={min_days}&amp;format=csv" '
        f'style="margin: 8px 0 16px;">Download CSV</a>'
    )

    rail_layout = (
        '<div class="ck-rail-layout">'
        f'{filter_rail}'
        '<div class="ck-rail-content">'
        f'{section}{results_head}{csv_link}{results_body}'
        '</div>'
        '</div>'
    )

    # Search hero — even though escalations don't have a keyword
    # search, the visual continuity with /library, /notes, /research
    # is worth the cost. Submit-action keeps the partner on the same
    # page; min_days hidden so the search hero acts as a "find" jump
    # without dropping the active threshold.
    search_hero = ck_search_hero(
        action="/escalations",
        name="q",
        initial="",
        label="Search",
        placeholder="(future: filter by deal name, alert title)",
        extra_hidden={"min_days": str(min_days)},
    )

    # 2026-05-28 batch 20 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    n_esc = len(escalated) if 'escalated' in dir() else 0
    intro = ck_editorial_head(
        eyebrow="ESCALATIONS",
        title="Escalations",
        meta=(
            f"RED ALERTS · OPEN > {min_days} DAYS · OLDEST FIRST"
        ),
        lede_italic_phrase=(
            "The red alerts the clock is running on."
        ),
        lede_body=(
            "Red-severity alerts sorted by days-open, oldest first. "
            "Anything still red past the threshold needs a decision "
            "before the next LP update."
        ),
    )

    next_up = ck_next_section(
        "Open the alerts triage view",
        "/alerts",
        eyebrow="Up next",
        italic_word="alerts",
    )
    body = intro + search_hero + rail_layout + next_up
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title="Escalations",
        active_nav="alerts",
        subtitle=(
            f"{count:,} red alert{'s' if count != 1 else ''} open "
            f"at least {min_days} days"
        ),
    )

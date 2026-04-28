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


def render_escalations(
    *,
    store: Any,
    min_days: int = 30,
) -> str:
    """Render /escalations with the editorial chrome."""
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_search_hero, ck_filter_sidebar,
        ck_results_header, ck_section_header, ck_section_intro,
        ck_severity_panel, ck_affirm_empty,
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

    results_head = ck_results_header(
        count=f"{count:,}",
        label="Escalation" if count == 1 else "Escalations",
        chips=chips or None,
        clear_all_href="/escalations" if chips else None,
    )

    section = ck_section_header(
        f"Red alerts open at least {min_days} days",
        eyebrow="ESCALATIONS",
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
        results_body = ck_severity_panel(
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

    intro = ck_section_intro(
        eyebrow="ESCALATIONS",
        headline="What stayed open longer than it should.",
        italic_word="longer",
        body=(
            "Red-severity alerts sorted by days-open, oldest first. "
            "Anything still red past the threshold needs a decision "
            "before the next LP update."
        ),
    )

    body = intro + search_hero + rail_layout
    return chartis_shell(
        body,
        title="Escalations",
        active_nav="alerts",
        subtitle=(
            f"{count:,} red alert{'s' if count != 1 else ''} open "
            f"at least {min_days} days"
        ),
    )

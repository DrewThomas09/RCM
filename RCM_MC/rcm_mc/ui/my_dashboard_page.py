"""Personal analyst dashboard — /my/<owner>.

Editorial port of the legacy `_route_my_dashboard` inline renderer.
Surfaces an analyst's daily work in one read: their owned deals
(with health, stage, covenant, MOIC, IRR), the active alerts on
those deals, the deadlines assigned to them (overdue + upcoming),
and a personalized pulse line up top — "your portfolio in one URL"
so analyst can start Monday on a single page instead of five.

Reuses the editorial primitives from cycles 1-14:
- `ck_section_intro` for the eyebrow + serif-italic headline
- `ck_kpi_block` for the pulse strip
- `ck_severity_panel` (red/amber tones) for alerts + deadlines
- `ck_affirm_empty` for empty states
- `ck_table` for the deals table

Server-side data semantics unchanged from the inline implementation.
"""
from __future__ import annotations

import html as _html
import urllib.parse
from typing import Any, Dict, List, Optional


def _fmt_moic(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):.2f}x"


def _fmt_pct(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v) * 100:.1f}%"


def _health_band_label(score: Optional[int], band: Optional[str]) -> str:
    """Inline health cell — colored score with a band label.

    Renders as a sc-num span tinted by band so the deals table reads
    consistent with the editorial palette.
    """
    if score is None:
        return '<span class="ck-health-cell faint">—</span>'
    tone = {
        "green": "positive",
        "amber": "warning",
        "red": "negative",
    }.get(band or "", "neutral")
    return (
        f'<span class="ck-health-cell tone-{tone} sc-num">'
        f'{int(score)}</span>'
    )


def render_my_dashboard(
    *,
    store: Any,
    owner: str,
) -> str:
    """Render /my/<owner> with the editorial chrome."""
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_editorial_head, ck_kpi_block,
        ck_severity_panel, ck_affirm_empty, ck_arrow_link,
        ck_next_section, ck_provenance_tooltip,
    )
    from rcm_mc.alerts.alerts import evaluate_active
    from rcm_mc.deals.deal_deadlines import overdue, upcoming
    from rcm_mc.deals.deal_owners import deals_by_owner
    from rcm_mc.deals.health_score import compute_health
    from rcm_mc.portfolio.portfolio_snapshots import latest_per_deal

    my_deals = set(deals_by_owner(store, owner))
    my_alerts = [a for a in evaluate_active(store)
                 if a.deal_id in my_deals]
    my_od = overdue(store, owner=owner)
    my_up = upcoming(store, days_ahead=14, owner=owner)

    n_red = sum(1 for a in my_alerts if a.severity == "red")
    n_amber = sum(1 for a in my_alerts if a.severity == "amber")

    # Editorial intro — italic-serif headline naming the analyst.
    # Single-line cadence matching chartis.com ("Where the portfolio
    # *needs* attention" on /alerts).
    safe_owner = _html.escape(owner)
    # 2026-05-28 sweep batch 19 · strict 5-block head via the
    # universal kit helper. Replaces ck_section_intro (h2 deck +
    # shell auto-inject double-h1 risk) with one editorial header.
    n_my_deals = len(my_deals)
    intro = ck_editorial_head(
        eyebrow=f"PARTNER · {safe_owner.upper()}",
        title="Your week, in one read.",
        meta=(
            f"{n_my_deals} DEAL{'S' if n_my_deals != 1 else ''} · "
            f"{len(my_alerts)} ALERT{'S' if len(my_alerts) != 1 else ''}"
            f" · {n_red} RED · {n_amber} AMBER · "
            f"{len(my_od)} OVERDUE · {len(my_up)} UPCOMING (14d)"
        ),
        lede_italic_phrase="Your week, in one read.",
        lede_body=(
            f"Active deals, alerts, and deadlines assigned to "
            f"{safe_owner}, refreshed each request. The pulse strip "
            f"below summarises what needs attention this morning."
        ),
    )

    # Pulse strip — five KPI blocks. Even in the empty case we render
    # all five so the analyst sees zeros not gaps; "0 red" is itself a
    # signal worth surfacing. ``ck_kpi_block`` escapes the value so we
    # pass plain strings; tonal tinting (red/amber on non-zero counts)
    # is applied via .ck-kpi-value selectors in the CSS class set on
    # the kpi block via the ``sub`` line below.
    # Cycle 35 — wrap the two most decision-driving values in
    # explainer hovers. Red Alerts: what triggers + ack flow.
    # Overdue Deadlines: what counts + how to clear.
    red_value = ck_provenance_tooltip(
        "Red alerts on your deals",
        str(n_red),
        explainer=(
            "Severity-red alerts on deals you own that haven't "
            "been acknowledged or snoozed. Red signals partner-"
            "level decision required (covenant breach, EBITDA "
            "miss, stage regress). Click into a deal to ack."
        ),
    )
    overdue_value = ck_provenance_tooltip(
        "Overdue deadlines on your deals",
        str(len(my_od)),
        explainer=(
            "Deadlines tagged with you as owner whose due-date "
            "has passed. Counts every overdue item regardless of "
            "deal stage. Open the deal page's Deadlines panel to "
            "mark complete or reassign."
        ),
        inject_css=False,  # CSS already in the page from Red Alerts call
    )
    pulse = (
        '<div class="ck-kpi-grid ck-pulse-grid">'
        + ck_kpi_block("My Deals", str(len(my_deals)), sub="active")
        + ck_kpi_block("Red Alerts", red_value, sub="severity high")
        + ck_kpi_block("Amber Alerts", str(n_amber), sub="severity medium")
        + ck_kpi_block("Overdue Deadlines", overdue_value, sub="past due")
        + ck_kpi_block("Upcoming Deadlines", str(len(my_up)), sub="next 14 days")
        + '</div>'
    )

    # ── Health mix card ──
    health_html = ""
    if my_deals:
        counts = {"green": 0, "amber": 0, "red": 0}
        for did in my_deals:
            h = compute_health(store, did)
            if h["score"] is None:
                continue
            if h["band"] in counts:
                counts[h["band"]] += 1
        total = sum(counts.values())
        if total > 0:
            def pct(n: int) -> float:
                return (n / total) * 100.0
            green_w = pct(counts["green"])
            amber_w = pct(counts["amber"])
            red_w = pct(counts["red"])
            health_html = (
                '<section class="ck-health-mix">'
                '<header class="ck-health-mix-head">'
                '<h3>Your health mix</h3>'
                '<span class="count">'
                f'{total} graded deal{"" if total == 1 else "s"}</span>'
                '</header>'
                '<div class="ck-health-bar">'
                f'<div class="seg green" style="width:{green_w:.1f}%" '
                f'title="{counts["green"]} green"></div>'
                f'<div class="seg amber" style="width:{amber_w:.1f}%" '
                f'title="{counts["amber"]} amber"></div>'
                f'<div class="seg red" style="width:{red_w:.1f}%" '
                f'title="{counts["red"]} red"></div>'
                '</div>'
                '<div class="ck-health-legend">'
                f'<span class="lg green">● {counts["green"]} green</span>'
                f'<span class="lg amber">● {counts["amber"]} amber</span>'
                f'<span class="lg red">● {counts["red"]} red</span>'
                '</div>'
                '</section>'
            )

    # ── Alerts card ──
    if my_alerts:
        red_alerts = [a for a in my_alerts if a.severity == "red"]
        amber_alerts = [a for a in my_alerts if a.severity == "amber"]

        def _alert_li(a) -> str:
            deal_q = urllib.parse.quote(a.deal_id)
            severity = a.severity
            tone_label = severity.upper()
            return (
                "<li>"
                '<div class="ck-severity-row">'
                f'<span class="ck-badge tone-{"negative" if severity == "red" else "warning"}">'
                f'{tone_label}</span>'
                f'<a class="deal" href="/deal/{deal_q}">'
                f'{_html.escape(a.deal_id)}</a>'
                f'<span class="title">{_html.escape(a.title)}</span>'
                "</div>"
                f'<div class="ck-severity-detail">{_html.escape(a.detail)}</div>'
                "</li>"
            )

        rows_html = "".join(_alert_li(a) for a in red_alerts + amber_alerts)
        # Pick the panel tone by the worst severity present
        panel_tone = "red" if red_alerts else "amber"
        panel_label = (
            f"My alerts — {len(red_alerts)} red"
            + (f" / {len(amber_alerts)} amber" if amber_alerts else "")
        )
        alerts_html = ck_severity_panel(
            tone=panel_tone,
            label=panel_label,
            count=len(my_alerts),
            rows_html=rows_html,
        )
    else:
        alerts_html = ck_affirm_empty(
            headline="No active alerts on your deals.",
            body=(
                "When alerts fire on a deal you own they'll surface here. "
                "Until then, the rest of the portfolio's signal is on "
                "/alerts."
            ),
            cta_text="View portfolio alerts",
            cta_href="/alerts",
        )

    # ── Deadlines card ──
    def _deadline_li(r, *, badge_html: str) -> str:
        did = str(r["deal_id"])
        deal_q = urllib.parse.quote(did)
        return (
            "<li>"
            '<div class="ck-severity-row">'
            f'{badge_html}'
            f'<a class="deal" href="/deal/{deal_q}">'
            f'{_html.escape(did)}</a>'
            f'<span class="title">{_html.escape(str(r["label"]))}</span>'
            f'<span class="age">due {_html.escape(str(r["due_date"]))}</span>'
            "</div>"
            "</li>"
        )

    deadline_rows = []
    for _, r in my_od.iterrows():
        days_overdue = int(r["days_overdue"])
        badge = (
            f'<span class="ck-badge tone-negative">'
            f'{days_overdue}d OVERDUE</span>'
        )
        deadline_rows.append(_deadline_li(r, badge_html=badge))
    for _, r in my_up.iterrows():
        deadline_rows.append(_deadline_li(
            r,
            badge_html='<span class="ck-badge tone-warning">UPCOMING</span>',
        ))

    if deadline_rows:
        deadlines_html = ck_severity_panel(
            tone="red" if not my_od.empty else "amber",
            label=(
                f"My deadlines — {len(my_od)} overdue, "
                f"{len(my_up)} upcoming"
            ),
            count=len(deadline_rows),
            rows_html="".join(deadline_rows),
        )
    else:
        deadlines_html = ck_affirm_empty(
            headline="No deadlines assigned.",
            body=(
                "Open a deal and use the Deadlines panel to add an "
                "owner-tagged due date. Anything assigned to "
                f"{safe_owner} will surface here, oldest first."
            ),
        )

    # ── Deals card ──
    df = latest_per_deal(store)
    df = df[df["deal_id"].isin(my_deals)] if not df.empty else df
    if my_deals and not df.empty:
        deal_rows = []
        for _, r in df.iterrows():
            did = str(r["deal_id"])
            deal_q = urllib.parse.quote(did)
            h = compute_health(store, did)
            health_cell = _health_band_label(h.get("score"), h.get("band"))
            deal_rows.append(
                "<tr>"
                f'<td><a href="/deal/{deal_q}" class="ck-deal-link">'
                f'{_html.escape(did)}</a></td>'
                f'<td>{health_cell}</td>'
                f'<td>{_html.escape(str(r.get("stage") or "—"))}</td>'
                f'<td>{_html.escape(str(r.get("covenant_status") or "—"))}</td>'
                f'<td class="align-right sc-num">'
                f'{_fmt_moic(r.get("moic"))}</td>'
                f'<td class="align-right sc-num">'
                f'{_fmt_pct(r.get("irr"))}</td>'
                "</tr>"
            )
        deals_html = (
            '<section class="ck-panel">'
            '<div class="ck-panel-head">'
            f'<div class="ck-panel-title">'
            f'My deals · {len(my_deals)}</div>'
            '</div>'
            '<div class="ck-panel-body">'
            '<table class="ck-table ck-dense">'
            "<thead><tr>"
            '<th class="align-left">Deal</th>'
            '<th class="align-left">Health</th>'
            '<th class="align-left">Stage</th>'
            '<th class="align-left">Covenant</th>'
            '<th class="align-right">MOIC</th>'
            '<th class="align-right">IRR</th>'
            "</tr></thead>"
            f"<tbody>{''.join(deal_rows)}</tbody>"
            "</table>"
            "</div>"
            "</section>"
        )
    elif my_deals:
        # Owned deals exist but no snapshot rows yet (fresh deals
        # before the first analysis run).
        deals_html = ck_affirm_empty(
            headline=f"{len(my_deals)} deal{'' if len(my_deals) == 1 else 's'} owned, no snapshots yet.",
            body=(
                "Run an analysis on each deal to populate the health "
                "score, stage, covenant, MOIC, and IRR columns."
            ),
            cta_text="Open analysis workbench",
            cta_href="/analysis",
        )
    else:
        deals_html = ck_affirm_empty(
            headline=f"No deals currently assigned to {safe_owner}.",
            body=(
                "Open any deal and use the Owner panel on its page to "
                "assign yourself, then return here for a single-pane "
                "view of your portfolio."
            ),
            cta_text="Browse deal corpus",
            cta_href="/library",
        )

    body = (
        intro
        + pulse
        + health_html
        + alerts_html
        + deadlines_html
        + deals_html
        + ck_next_section(
            "Open the Monday brief",
            "/day-one",
            eyebrow="Continue —",
            italic_word="Monday",
        )
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title=f"My work · {owner}",
        active_nav="alerts",
        # No subtitle= — the editorial head's meta line already carries the
        # deals/alerts/overdue/upcoming summary under the title. A shell
        # subtitle would render orphaned ABOVE the page's own title.
        breadcrumbs=[
            ("Home", "/"),
            ("My Work", None),
        ],
    )

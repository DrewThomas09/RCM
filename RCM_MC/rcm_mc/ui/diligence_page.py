"""PE Desk Diligence Tools — questions, playbook, challenge solver.

Connects analysis/diligence_questions.py, analysis/playbook.py, and
analysis/challenge.py to the browser.

Both renderers accept loose dicts because they sit behind two upstream
shapes: the packet path (``DiligenceQuestion.to_dict()`` emits
P0/P1/P2 priorities + trigger_reason/context;
``PlaybookEntry.to_dict()`` emits lever/pattern/success_rate/
recommendation) and the server's exception-path fallback lists (which
emit high/medium priorities + title/category/ebitda_impact/timeline/
owner). Key normalization lives HERE, in the renderer — never adapt
the analysis dataclasses to the page. Pre-normalization, the primary
data path rendered muted badges, blank rationale columns, and
playbook tables of empty rows.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell, ck_bar_row, ck_editorial_head, ck_empty_state,
    ck_fmt_currency, ck_fmt_percent, ck_kpi_block, ck_next_section,
    ck_page_actions, ck_panel, ck_provenance_tooltip, ck_signal_badge,
    ck_value_anchor,
)
from .models_page import _model_nav


# ── Normalization helpers ──────────────────────────────────────────

#: Hover gloss for every priority badge — the ladder in one line.
_PRI_LADDER_TT = (
    "P0 — IC blocker · P1 — confirm before signing · P2 — nice-to-have"
)

#: rank → (badge label, badge tone, tier subhead)
_TIER_META: Dict[int, Tuple[str, str, str]] = {
    0: ("P0", "negative", "P0 — IC blockers"),
    1: ("P1", "warning", "P1 — confirm before signing"),
    2: ("P2", "neutral", "P2 — nice-to-have"),
}


def _priority_tier(raw: Any) -> int:
    """Map a loose priority value onto the P0/P1/P2 ladder.

    Upstream speaks two dialects — ``DiligenceQuestion`` sends
    "P0"/"P1"/"P2"; the server fallbacks send "high"/"critical"/
    "medium"/"low" in mixed case. Normalizing once means badge tone,
    tier grouping, and masthead counts always agree (a capitalized
    "High" used to be counted as high but badged as muted).
    """
    p = str(raw or "").strip().upper()
    if p in ("P0", "CRITICAL", "HIGH"):
        return 0
    if p in ("P1", "MEDIUM", "MED"):
        return 1
    return 2


def _question_status(raw: Any) -> Tuple[str, str, bool]:
    """(badge label, badge tone, is_answered) from a loose status.

    ``DiligenceQuestion`` carries no status field today, so the
    default reads as one clean OPEN state; answered/resolved values
    arriving from future upstream (or hand-edited dicts) degrade
    gracefully into a positive badge + dimmed row.
    """
    s = str(raw or "open").strip().lower()
    if s in ("answered", "resolved", "closed", "done"):
        return "Answered", "positive", True
    return "Open", "neutral", False


def _to_float(v: Any) -> Optional[float]:
    """Numeric guard — a None/str impact must dash, never 500 the page."""
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _prettify_key(v: Any) -> str:
    """"denial_rate" → "Denial Rate" for lever / pattern keys."""
    return str(v or "").replace("_", " ").strip().title()


# ── Page-scoped CSS (classes, never style= attributes) ─────────────

_DLQ_CSS = (
    "<style>"
    ".dlq-q{font-weight:500;max-width:60ch;}"
    ".dlq-trigger{display:block;font-family:var(--sc-mono);"
    "font-size:10.5px;letter-spacing:0.02em;color:var(--sc-text-faint);"
    "margin-top:3px;}"
    ".dlq-rationale{font-size:12px;color:var(--sc-text-dim);max-width:52ch;}"
    ".dlq-dim{color:var(--sc-text-dim);}"
    "tr.dlq-done .dlq-q,tr.dlq-done .dlq-rationale{"
    "color:var(--sc-text-faint);}"
    "tr.dlq-done .dlq-q{font-weight:400;}"
    "table.ck-table tr.dlq-tier td{background:var(--paper);"
    "border-top:1px solid var(--sc-rule);padding:6px 13px;"
    "font-family:var(--sc-mono);font-size:10.5px;font-weight:600;"
    "letter-spacing:0.08em;text-transform:uppercase;"
    "color:var(--sc-text-dim);}"
    ".dlq-tier-count{color:var(--sc-text-faint);margin-left:8px;}"
    ".dlq-chips{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 0;}"
    "</style>"
)

_PLB_CSS = (
    "<style>"
    ".plb-title{font-weight:500;}"
    ".plb-rec{display:block;font-weight:400;font-size:12px;"
    "color:var(--sc-text-dim);max-width:64ch;margin-top:3px;}"
    ".plb-n{font-family:var(--sc-mono);font-size:10.5px;"
    "color:var(--sc-text-faint);margin-left:4px;}"
    "table.ck-table tr.plb-total td{background:var(--paper);"
    "border-top:2px solid var(--sc-rule);border-bottom:0;font-weight:600;}"
    "</style>"
)


# ── Diligence questions ────────────────────────────────────────────

def render_diligence_questions(deal_id: str, deal_name: str,
                               questions: List[Dict[str, Any]]) -> str:
    """Render auto-generated diligence questions, grouped P0 → P2."""
    did = html.escape(deal_id)
    nav = _model_nav(deal_id, "questions")
    next_sec = ck_next_section(
        "Open the portfolio-wide question ledger",
        "/diligence/questions",
        eyebrow="Up next",
        italic_word="ledger",
    )

    if not questions:
        head = ck_editorial_head(
            eyebrow=f"DILIGENCE QUESTIONS · {deal_id.upper()}",
            title=f"Open questions — {html.escape(deal_name)}",
            meta="0 QUESTIONS",
            lede_italic_phrase="Auto-generated diligence questions.",
            lede_body=(
                "Questions generate from analysis-packet gaps, risk "
                "flags, and benchmark deltas — none are queued for "
                "this deal yet."
            ),
            source_note="deal analysis packet · risk flags · benchmark gaps",
        )
        empty = ck_empty_state(
            "No open questions for this deal.",
            "Diligence questions are generated from packet gaps, "
            "risk flags, and benchmark deltas. Run the full analysis "
            "to populate the data-room request list.",
            eyebrow="NOTHING QUEUED",
            icon="?",
            cta_label="Run full analysis",
            cta_href=f"/analysis/{deal_id}",
        )
        return chartis_shell(
            _DLQ_CSS + head + nav + empty + ck_page_actions() + next_sec,
            f"Diligence Questions — {html.escape(deal_name)}",
            active_nav="/analysis",
            subtitle="0 questions",
        )

    by_category: Dict[str, int] = {}
    for q in questions:
        cat = str(q.get("category", "Other"))
        by_category[cat] = by_category.get(cat, 0) + 1

    # Tier sort — the lede promises IC blockers first, so deliver it.
    # Stable within tier: upstream ordering inside a severity band is
    # already meaningful (generation order tracks the packet walk).
    decorated = sorted(
        ((_priority_tier(q.get("priority", q.get("severity", "medium"))),
          i, q) for i, q in enumerate(questions)),
        key=lambda t: (t[0], t[1]),
    )
    tier_counts: Dict[int, int] = {}
    for rank, _, _ in decorated:
        tier_counts[rank] = tier_counts.get(rank, 0) + 1

    has_status = any("status" in q for q in questions)
    n_answered = 0

    rows: List[str] = []
    seen_tier: Optional[int] = None
    for n, (rank, _, q) in enumerate(decorated, 1):
        if rank != seen_tier:
            _lbl, _tone, tier_head = _TIER_META[rank]
            rows.append(
                '<tr class="dlq-tier"><td colspan="6">'
                f'{html.escape(tier_head)}'
                f'<span class="dlq-tier-count">{tier_counts[rank]}</span>'
                '</td></tr>'
            )
            seen_tier = rank
        label, tone, _head = _TIER_META[rank]
        question = html.escape(str(q.get("question", q.get("text", ""))))
        category = html.escape(str(q.get("category", "")))
        # Why-it-matters text arrives under four possible keys; the
        # packet path uses trigger_reason (narrative) + context
        # (valuation angle). If only context exists it becomes the
        # cell; otherwise context lands on the cell's hover.
        rationale_src = str(
            q.get("rationale") or q.get("reason")
            or q.get("trigger_reason") or "")
        context = str(q.get("context") or "")
        if not rationale_src:
            rationale_src, context = context, ""
        rationale = html.escape(rationale_src)
        context_attr = f' title="{html.escape(context)}"' if context else ""
        # Machine-readable firing pattern ("denial_rate=14.5%") —
        # every question shows what fired it, in mono under the text.
        trigger = str(q.get("trigger") or q.get("trigger_metric") or "")
        trigger_html = (
            f'<span class="dlq-trigger">{html.escape(trigger)}</span>'
            if trigger else "")
        status_label, status_tone, answered = _question_status(
            q.get("status", "open"))
        if answered:
            n_answered += 1
        row_cls = ' class="dlq-done"' if answered else ""
        rows.append(
            f'<tr{row_cls}>'
            f'<td class="num dlq-dim">{n}</td>'
            f'<td><span title="{_PRI_LADDER_TT}">'
            + ck_signal_badge(label, tone=tone)
            + '</span></td>'
            f'<td class="dlq-q">{question}{trigger_html}</td>'
            f'<td class="dlq-dim">{category}</td>'
            f'<td class="dlq-rationale"{context_attr}>{rationale}</td>'
            '<td>' + ck_signal_badge(status_label, tone=status_tone)
            + '</td></tr>'
        )

    # Distribution bars make the question mix scannable — which
    # diligence areas dominate the auto-generated set — with the
    # count chips retained beneath.
    _sorted_cats = sorted(by_category.items(), key=lambda x: -x[1])
    _cat_max = max((n for _, n in _sorted_cats), default=0) or 1
    cat_bars = "".join(
        ck_bar_row(c, str(n), n / _cat_max * 100.0)
        for c, n in _sorted_cats
    )
    cat_chips = "".join(
        f'<span class="cad-badge cad-badge-muted">{html.escape(c)}: {n}</span>'
        for c, n in _sorted_cats
    )
    cat_body = cat_bars + f'<p class="dlq-chips">{cat_chips}</p>'

    n_p0 = tier_counts.get(0, 0)
    n_p1 = tier_counts.get(1, 0)
    n_p2 = tier_counts.get(2, 0)
    n_open = len(questions) - n_answered
    top_cat, top_n = _sorted_cats[0]

    meta_facts = [
        f"{len(questions)} QUESTION{'S' if len(questions) != 1 else ''}",
        f"{n_p0} IC BLOCKER{'S' if n_p0 != 1 else ''}",
        f"{len(by_category)} CATEGOR{'IES' if len(by_category) != 1 else 'Y'}",
    ]
    if has_status:
        meta_facts.append(f"{n_open} OPEN · {n_answered} ANSWERED")

    head = ck_editorial_head(
        eyebrow=f"DILIGENCE QUESTIONS · {deal_id.upper()}",
        title=f"Open questions — {html.escape(deal_name)}",
        meta=" · ".join(meta_facts),
        lede_italic_phrase="Auto-generated diligence questions.",
        lede_body=(
            "Every analytic output that raises a question lands here, "
            "grouped P0 → P2 so IC blockers read first. Push the lot "
            "to the data room with the CSV button, or print this page "
            "for an IC binder appendix."
        ),
        source_note="deal analysis packet · risk flags · benchmark gaps",
        actions_html=(
            f'<a href="/api/analysis/{did}/diligence-questions" '
            'class="cad-btn cad-btn-primary">Download CSV for Data Room</a>'
        ),
    )

    # KPI strip carries facts the masthead meta does not repeat —
    # the P0/P1 split, the dominant category, and (when statuses
    # exist) the open/answered balance.
    p0_value = ck_provenance_tooltip(
        "IC blockers (P0)", str(n_p0),
        explainer=(
            "Count of P0-tier questions. The generator assigns P0 to "
            "questions fired by IC-blocking gaps (missing core "
            "financials, unexplained outlier metrics); legacy "
            "high/critical labels fold into the same tier."
        ),
    )
    status_kpi = (
        ck_kpi_block("Open", str(n_open), f"{n_answered} answered")
        if has_status else
        ck_kpi_block("Nice-to-Have", str(n_p2), "P2 — ask when convenient")
    )
    kpi_strip = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("IC Blockers", p0_value, "P0 — resolve before IC")
        + ck_kpi_block("Confirm Before Signing", str(n_p1),
                       "P1 — pre-signing confirmations")
        + ck_kpi_block("Top Category", html.escape(str(top_cat)),
                       f"{top_n} of {len(questions)} questions")
        + status_kpi
        + "</div>"
    )

    questions_table = (
        '<p class="ck-section-body">Grouped by priority tier — send '
        'the P0 block to the seller first. The mono line under a '
        'question is the data pattern that fired it; hover a '
        'rationale for its valuation context.</p>'
        '<table class="ck-table"><thead><tr>'
        '<th class="num">#</th><th>Priority</th><th>Question</th>'
        '<th>Category</th><th>Rationale</th><th>Status</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
    )

    next_steps = (
        '<p class="ck-section-body">Send the P0 block to the seller '
        'as the initial data-room request; confirm P1 items before '
        'signing. Once answers come back, update the deal profile '
        f'via <a href="/import">Import</a> and re-run the '
        f'<a href="/models/denial/{did}">denial analysis</a> with '
        'actual payer-level data.</p>'
    )

    body = (
        head
        + nav
        + kpi_strip
        + ck_panel(cat_body, title="Category mix")
        + ck_panel(questions_table, title="Diligence Questions")
        + ck_panel(next_steps, title="Next steps")
        + ck_page_actions(extras_html=(
            f'<a href="/models/playbook/{did}" class="cad-btn">'
            'Value Creation Playbook</a>'
            f'<a href="/analysis/{did}" class="cad-btn">Full Analysis</a>'
        ))
        + next_sec
    )

    return chartis_shell(
        _DLQ_CSS + body,
        f"Diligence Questions — {html.escape(deal_name)}",
        active_nav="/analysis",
        subtitle=(f"{len(questions)} questions across "
                  f"{len(by_category)} categories"),
    )


# ── Value-creation playbook ────────────────────────────────────────

def render_playbook(deal_id: str, deal_name: str,
                    entries: List[Dict[str, Any]]) -> str:
    """Render the operational playbook."""
    did = html.escape(deal_id)
    nav = _model_nav(deal_id, "playbook")
    next_sec = ck_next_section(
        "Track execution against the EBITDA bridge",
        f"/models/bridge/{did}",
        eyebrow="Up next",
        italic_word="bridge",
    )

    if not entries:
        head = ck_editorial_head(
            eyebrow=f"OPERATIONAL PLAYBOOK · {deal_id.upper()}",
            title=f"Value creation plan — {html.escape(deal_name)}",
            meta="0 INITIATIVES",
            lede_italic_phrase="The 100-day operating plan.",
            lede_body=(
                "Playbook entries generate when a deal carries "
                "lever-level impacts and at least three "
                "pattern-matched historical deals — none qualify yet."
            ),
            source_note=("deal analysis packet · v2 bridge levers · "
                         "historical deal outcomes"),
        )
        empty = ck_empty_state(
            "No playbook initiatives yet.",
            "Entries require lever-level impact estimates plus at "
            "least three pattern-matched historical deals; thin "
            "history renders nothing rather than a noisy estimate. "
            "Run the denial analysis to attach lever impacts.",
            eyebrow="INSUFFICIENT HISTORY",
            icon="≡",
            cta_label="Run denial analysis",
            cta_href=f"/models/denial/{deal_id}",
        )
        return chartis_shell(
            _PLB_CSS + head + nav + empty + ck_page_actions() + next_sec,
            f"Playbook — {html.escape(deal_name)}",
            active_nav="/analysis",
            subtitle="0 initiatives",
        )

    # Normalize both entry shapes into display rows.
    total_impact = 0.0
    any_impact = False
    any_priority = False
    n_high = 0
    sr_values: List[float] = []
    rows: List[str] = []
    for e in entries:
        title = (str(e.get("title") or e.get("initiative") or "").strip()
                 or _prettify_key(e.get("lever")))
        category = (str(e.get("category") or "").strip()
                    or _prettify_key(e.get("pattern")))
        timeline = str(e.get("timeline") or e.get("timeframe") or "").strip()
        owner = str(e.get("owner") or "").strip()
        recommendation = str(e.get("recommendation") or "").strip()
        impact = _to_float(e.get("ebitda_impact", e.get("impact")))
        if impact is not None:
            total_impact += impact
            any_impact = True
        raw_pri = e.get("priority")
        pri_html = '<span class="dlq-dim">—</span>'
        if raw_pri is not None and str(raw_pri).strip():
            any_priority = True
            rank = _priority_tier(raw_pri)
            if rank == 0:
                n_high += 1
            _lbl, tone, _head = _TIER_META[rank]
            pri_html = ck_signal_badge(
                str(raw_pri).strip().capitalize(), tone=tone)
        sr = _to_float(e.get("success_rate"))
        achievement = _to_float(e.get("avg_achievement_pct"))
        n_match = len(e.get("matching_deals") or [])
        sr_html = '<span class="dlq-dim">—</span>'
        if sr is not None:
            sr_values.append(sr)
            n_html = (f'<span class="plb-n">n={n_match}</span>'
                      if n_match else "")
            ach_attr = ""
            if achievement is not None:
                ach_attr = (
                    ' title="Average achievement vs target: '
                    f'{ck_fmt_percent(achievement)} across pattern-matched '
                    'historical deals"'
                )
            sr_html = f'<span{ach_attr}>{ck_fmt_percent(sr)}{n_html}</span>'
        rec_html = (
            f'<span class="plb-rec">{html.escape(recommendation)}</span>'
            if recommendation else "")
        impact_html = (ck_fmt_currency(impact)
                       if impact is not None else "—")
        rows.append(
            '<tr>'
            f'<td class="plb-title">{html.escape(title)}{rec_html}</td>'
            f'<td class="dlq-dim">{html.escape(category)}</td>'
            f'<td>{pri_html}</td>'
            f'<td class="num">{impact_html}</td>'
            f'<td class="num">{sr_html}</td>'
            f'<td>{html.escape(timeline) if timeline else "—"}</td>'
            f'<td>{html.escape(owner) if owner else "—"}</td>'
            '</tr>'
        )

    has_dollar = total_impact > 0

    # Lead takeaway — the 100-day-plan value (total EBITDA impact +
    # the equity it creates at exit) surfaces before the table. When
    # no entry carries a defensible dollar estimate the band anchors
    # on the initiative count + historical evidence instead of
    # inventing a $0 figure (ck_value_anchor defensibility contract).
    if has_dollar:
        lead_anchor = ck_value_anchor(
            "100-DAY PLAN VALUE",
            f"{ck_fmt_currency(total_impact)} EBITDA impact",
            delta=f"{len(entries)} initiatives",
            opportunity=(f"{ck_fmt_currency(total_impact * 11)} "
                         "equity value at 11x"),
            target="100-day operational plan",
            tone="teal",
        )
    else:
        avg_sr = sum(sr_values) / len(sr_values) if sr_values else None
        lead_anchor = ck_value_anchor(
            "100-DAY PLAN VALUE",
            f"{len(entries)} initiatives",
            delta=(f"{ck_fmt_percent(avg_sr)} avg historical success rate"
                   if avg_sr is not None else ""),
            opportunity="",
            target="100-day operational plan",
            tone="teal",
        )

    meta_facts = [f"{len(entries)} INITIATIVE"
                  f"{'S' if len(entries) != 1 else ''}"]
    if has_dollar:
        meta_facts.append(f"{ck_fmt_currency(total_impact)} EBITDA IMPACT")
    if any_priority:
        meta_facts.append(f"{n_high} HIGH PRIORITY")
    elif sr_values:
        _avg = sum(sr_values) / len(sr_values)
        meta_facts.append(f"{ck_fmt_percent(_avg)} AVG SUCCESS RATE")

    head = ck_editorial_head(
        eyebrow=f"OPERATIONAL PLAYBOOK · {deal_id.upper()}",
        title=f"Value creation plan — {html.escape(deal_name)}",
        meta=" · ".join(meta_facts),
        lede_italic_phrase="The 100-day operating plan.",
        lede_body=(
            "Sequenced value-creation initiatives for year one — what "
            "the operator does, what it earns, and the historical "
            "precedent behind each move. Present it at IC, then track "
            "execution against the EBITDA bridge."
        ),
        source_note=("deal analysis packet · v2 bridge levers · "
                     "historical deal outcomes"),
    )

    tfoot = ""
    if any_impact:
        total_cell = ck_provenance_tooltip(
            "Total EBITDA impact",
            f"<strong>{ck_fmt_currency(total_impact)}</strong>",
            explainer=(
                "Sum of per-initiative annual EBITDA impact "
                "estimates from the deal profile and lever "
                "assumptions. Initiatives without a defensible "
                "dollar estimate show an em dash and are excluded."
            ),
        )
        tfoot = (
            '<tfoot><tr class="plb-total">'
            f'<td colspan="3">Total — {len(entries)} initiatives</td>'
            f'<td class="num">{total_cell}</td>'
            '<td colspan="3"></td></tr></tfoot>'
        )

    playbook_panel = ck_panel(
        '<p class="ck-section-body">Prioritized operational '
        'initiatives with estimated annual EBITDA impact. Where the '
        'corpus holds at least three pattern-matched historical '
        'deals, the success rate shows how often hospitals like this '
        'one landed the move.</p>'
        '<table class="ck-table"><thead><tr>'
        '<th>Initiative</th><th>Category</th><th>Priority</th>'
        '<th class="num" title="Estimated annual EBITDA impact, '
        '$ per year">EBITDA Impact</th>'
        '<th class="num" title="Share of pattern-matched historical '
        'deals that reached at least 80% of target">Success Rate</th>'
        '<th>Timeline</th><th>Owner</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody>'
        + tfoot + '</table>',
        title="Value Creation Playbook",
    )

    if has_dollar:
        equity_val = ck_provenance_tooltip(
            "Equity value at exit",
            f"<strong>{ck_fmt_currency(total_impact * 11)}</strong>",
            explainer=(
                "Annual EBITDA impact × 11 — an illustrative sector "
                "exit multiple, not a deal-specific mark. Open the "
                "Returns model for this deal's own multiple "
                "assumptions."
            ),
            inject_css=False,
        )
        takeaway = (
            f'<p class="ck-section-body">{len(entries)} initiatives '
            f'totaling <strong>{ck_fmt_currency(total_impact)}</strong> '
            'in annual EBITDA improvement. At an 11x exit multiple '
            f'this represents {equity_val} in equity value '
            'creation.</p>'
        )
    else:
        takeaway = (
            f'<p class="ck-section-body">{len(entries)} initiatives '
            'drawn from historical deals that share this '
            'hospital&rsquo;s operating pattern. Dollar impacts are '
            'not yet defensible for this deal — attach lever-level '
            'estimates via the EBITDA bridge before presenting a '
            'plan value at IC.</p>'
        )
    takeaway += (
        '<p class="ck-section-body">Present this as the 100-day plan '
        'at IC. Track execution against the '
        f'<a href="/models/bridge/{did}">EBITDA bridge</a> and '
        'monitor trends via the '
        f'<a href="/models/trends/{did}">trend forecast</a>.</p>'
    )

    body = (
        head
        + nav
        + lead_anchor
        + playbook_panel
        + ck_panel(takeaway, title="What This Means")
        + ck_page_actions(extras_html=(
            f'<a href="/models/bridge/{did}" class="cad-btn">'
            'EBITDA Bridge</a>'
            f'<a href="/models/denial/{did}" class="cad-btn">'
            'Denial Drivers</a>'
            f'<a href="/models/questions/{did}" class="cad-btn">'
            'Diligence Questions</a>'
            f'<a href="/deal/{did}" class="cad-btn cad-btn-primary">'
            'Deal Dashboard</a>'
        ))
        + next_sec
    )

    subtitle = (
        f"{len(entries)} initiatives · "
        f"{ck_fmt_currency(total_impact)} total impact"
        if has_dollar else f"{len(entries)} initiatives"
    )
    return chartis_shell(
        _PLB_CSS + body,
        f"Playbook — {html.escape(deal_name)}",
        active_nav="/analysis",
        subtitle=subtitle,
    )

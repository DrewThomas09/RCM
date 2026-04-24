"""Diligence Checklist dashboard at /diligence/checklist.

The analyst's daily workspace — coverage %, open P0/P1 blockers,
per-phase progress, full item table with auto-status + evidence
links + partner manual overrides.

The page is read/write:
    - ``?mark_done=item_id`` marks the item manually complete
    - ``?mark_blocked=item_id`` marks blocked (external dependency)
    - ``?mark_in_progress=item_id`` marks partial work
    - ``?clear=item_id`` removes any override

All state is encoded in the URL (saved-view friendly; no
server-side persistence yet). A partner can bookmark the URL to
share a specific checklist snapshot with the deal team.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Set

from ..diligence.checklist import (
    CHECKLIST_ITEMS, Category, ChecklistItem, ChecklistStatus,
    DealChecklistState, DealObservations, ItemStatus, Owner,
    Priority, compute_status, open_questions_for_ic_packet,
    summarize_coverage,
)
from ..diligence.checklist.items import build_checklist
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped styles
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.dc-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.dc-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.dc-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.dc-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.dc-callout.alert{{border-left-color:{ne};color:{ne};font-weight:600;font-size:13px;}}
.dc-callout.warn{{border-left-color:{wn};color:{wn};font-weight:600;font-size:13px;}}
.dc-callout.good{{border-left-color:{po};color:{po};font-weight:600;font-size:13px;}}
.dc-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.dc-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-top:18px;}}
.dc-kpi{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 16px;}}
.dc-kpi__label{{font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;font-weight:600;}}
.dc-kpi__val{{font-size:28px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.dc-kpi__band{{font-size:10px;margin-top:4px;font-weight:600;}}
.dc-phase{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 18px;margin-bottom:12px;
transition:border-color 140ms ease;}}
.dc-phase:hover{{border-color:{tf};}}
.dc-phase__head{{display:flex;justify-content:space-between;
align-items:baseline;gap:14px;margin-bottom:8px;}}
.dc-phase__title{{font-size:14px;color:{tx};font-weight:600;}}
.dc-phase__count{{font-size:10px;color:{tf};letter-spacing:1.2px;
text-transform:uppercase;font-weight:600;}}
.dc-progress{{height:5px;background:{bdim};border-radius:3px;
overflow:hidden;margin-top:6px;}}
.dc-progress__fill{{height:100%;background:{po};}}
.dc-progress__partial{{background:{wn};}}
.dc-progress__low{{background:{ne};}}
.dc-item{{display:grid;grid-template-columns:80px 70px 1fr 110px 90px 70px;
gap:10px;align-items:baseline;padding:9px 2px;
border-bottom:1px solid {bdim};font-size:12px;}}
.dc-item:last-child{{border-bottom:0;}}
.dc-item:hover{{background:{pa};}}
.dc-item__status{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
font-weight:700;text-align:center;padding:2px 0;border:1px solid currentColor;
border-radius:3px;}}
.dc-item__prio{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
font-weight:700;text-align:center;padding:2px 0;border:1px solid currentColor;
border-radius:3px;}}
.dc-item__question{{color:{tx};line-height:1.45;}}
.dc-item__owner{{color:{td};font-size:10px;letter-spacing:1px;
text-transform:uppercase;font-weight:600;}}
.dc-item__category{{color:{tf};font-size:10px;letter-spacing:1px;
text-transform:uppercase;}}
.dc-item__action{{text-align:right;}}
.dc-item__action a{{color:{ac};font-size:10px;text-decoration:none;
font-weight:600;margin-left:6px;}}
.dc-item__action a:hover{{text-decoration:underline;}}
.dc-item__note{{grid-column:3 / -1;font-size:11px;color:{tf};
font-style:italic;margin-top:4px;}}
.dc-oq-row{{padding:8px 0;border-bottom:1px solid {bdim};
display:grid;grid-template-columns:40px 1fr 100px;gap:12px;
align-items:baseline;font-size:12.5px;color:{td};line-height:1.5;}}
.dc-oq-row__prio{{font-size:9px;font-weight:700;letter-spacing:1.3px;
text-align:center;padding:2px 0;border:1px solid currentColor;
border-radius:3px;text-transform:uppercase;}}
.dc-oq-row__owner{{color:{tf};font-size:10px;letter-spacing:1px;
text-transform:uppercase;text-align:right;font-weight:600;}}
@media (max-width:720px){{.dc-item{{grid-template-columns:70px 60px 1fr;}}
.dc-item__owner,.dc-item__category,.dc-item__action{{display:none;}}}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], bdim=P["border_dim"],
        ac=P["accent"], po=P["positive"],
        wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Demo observation — an 8-provider-group target mid-diligence
# ────────────────────────────────────────────────────────────────────

def _demo_observations() -> DealObservations:
    """Default state for the landing page — a realistic
    mid-diligence snapshot so the page isn't empty."""
    return DealObservations(
        bankruptcy_scan_run=True,
        deal_autopsy_run=True,
        sector_sentiment_reviewed=True,
        ccd_ingested=True,
        hfma_days_in_ar_computed=True,
        hfma_denial_rate_computed=True,
        hfma_ar_aging_computed=True,
        hfma_nrr_computed=True,
        qor_waterfall_computed=True,
        hfma_cost_to_collect_computed=False,
        cohort_liquidation_computed=True,
        denial_pareto_computed=True,
        denial_prediction_run=True,
        physician_attrition_run=True,
        nsa_run=True,
        steward_run=True,
        cyber_run=True,
        ma_v28_run=True,
        antitrust_run=True,
        physician_comp_fmv_run=True,
        cpom_run=False,
        team_run=False,
        labor_referral_run=False,
        patient_pay_run=False,
        ebitda_bridge_built=True,
        deal_mc_run=True,
        counterfactual_run=True,
        market_intel_run=True,
        working_capital_peg_set=False,
        qoe_memo_generated=False,
        ic_packet_assembled=False,
    )


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

_STATUS_COLOR = {
    ItemStatus.DONE: "positive",
    ItemStatus.IN_PROGRESS: "warning",
    ItemStatus.OPEN: "text_faint",
    ItemStatus.BLOCKED: "negative",
}

_PRIORITY_COLOR = {
    Priority.P0: "negative",
    Priority.P1: "warning",
    Priority.P2: "text_faint",
}


def _status_badge(status: ItemStatus) -> str:
    c = P.get(_STATUS_COLOR[status], P["text_dim"])
    return (
        f'<span class="dc-item__status" style="color:{c};">'
        f'{html.escape(status.value.replace("_", " "))}</span>'
    )


def _priority_badge(p: Priority) -> str:
    c = P.get(_PRIORITY_COLOR[p], P["text_dim"])
    return (
        f'<span class="dc-item__prio" style="color:{c};">'
        f'{p.value}</span>'
    )


_PHASE_TITLES = {
    1: "Phase 1 · Pre-NDA screening",
    2: "Phase 2 · CCD benchmarks + predictive",
    3: "Phase 3 · Risk workbench + manual diligence",
    4: "Phase 4 · Financial synthesis",
    5: "Phase 5 · Partner deliverables",
}


def _parse_id_set(qs: Dict[str, List[str]], key: str) -> Set[str]:
    raw = qs.get(key) or []
    out: Set[str] = set()
    for entry in raw:
        for tok in str(entry).split(","):
            tok = tok.strip()
            if tok:
                out.add(tok)
    return out


def _action_link(item: ChecklistItem, qs: Dict[str, List[str]]) -> str:
    """Produce inline action links: Mark done · Block · In progress · Clear.

    Each link toggles the item into the requested state via a URL
    round-trip (no JS needed).  The other override-sets are
    preserved in the URL so one toggle doesn't blow away other
    state.
    """
    import urllib.parse as _urllib
    # Preserve existing param lists
    def _copy_without(exclude_key: str, exclude_value: str) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for k, vs in qs.items():
            if k in ("mark_done", "mark_blocked", "mark_in_progress", "clear"):
                flat: List[str] = []
                for v in vs:
                    for t in str(v).split(","):
                        t = t.strip()
                        if t and not (k == exclude_key and t == exclude_value):
                            flat.append(t)
                if flat:
                    out[k] = [",".join(flat)]
            else:
                out[k] = list(vs)
        return out

    def _url_for(action: str) -> str:
        # Start from current qs, strip item_id from all overrides,
        # then add it under `action`.
        base = _copy_without(action, item.item_id)
        # Strip from all other override buckets
        other_keys = {"mark_done", "mark_blocked", "mark_in_progress"} - {action}
        for k in other_keys:
            if k in base:
                flat = [t for t in base[k][0].split(",") if t and t != item.item_id]
                if flat:
                    base[k] = [",".join(flat)]
                else:
                    base.pop(k, None)
        if action != "clear":
            existing = base.get(action, [""])[0]
            tokens = [t for t in existing.split(",") if t]
            if item.item_id not in tokens:
                tokens.append(item.item_id)
            base[action] = [",".join(tokens)]
        else:
            # 'clear' removes the id from all override lists
            for k in ("mark_done", "mark_blocked", "mark_in_progress"):
                if k in base:
                    flat = [t for t in base[k][0].split(",") if t and t != item.item_id]
                    if flat:
                        base[k] = [",".join(flat)]
                    else:
                        base.pop(k, None)
        query = _urllib.urlencode(
            {k: vs[0] for k, vs in base.items() if vs and vs[0]},
            doseq=False,
        )
        return f"/diligence/checklist?{query}" if query else "/diligence/checklist"

    return (
        f'<a href="{_url_for("mark_done")}">Mark done</a>'
        f'<a href="{_url_for("mark_blocked")}">Block</a>'
        f'<a href="{_url_for("mark_in_progress")}">WIP</a>'
        f'<a href="{_url_for("clear")}">Clear</a>'
    )


def _hero(state: DealChecklistState) -> str:
    if state.open_p0 > 0:
        banner_class = "alert"
    elif state.open_p1 > 0:
        banner_class = "warn"
    else:
        banner_class = "good"
    banner = summarize_coverage(state)

    # KPI tiles
    p0_color = (
        P["negative"] if state.open_p0 > 0
        else P["positive"]
    )
    p1_color = (
        P["warning"] if state.open_p1 > 0
        else P["positive"]
    )
    cov_color = (
        P["positive"] if state.p0_coverage >= 1.0
        else P["warning"] if state.p0_coverage >= 0.70
        else P["negative"]
    )
    cov_num = provenance(
        f'{state.p0_coverage*100:.0f}%',
        source="compute_status()",
        formula="count(items where priority=P0 AND status=DONE) / count(P0 items)",
        detail=(
            "P0 coverage must be 100% before IC. Partners read this "
            "as the single go/no-go KPI for IC readiness."
        ),
    )
    done_num = provenance(
        f'{state.done}/{state.total}',
        source="compute_status()",
        formula="count(items where status=DONE)",
        detail="Total items covered across all phases and priorities.",
    )
    return (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="dc-eyebrow">Diligence Checklist</div>'
        f'<div class="dc-h1">Coverage + Open Questions</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">Auto-tracked from live analytics · '
        f'partner overrides via URL</div>'
        f'<div class="dc-callout {banner_class}">{html.escape(banner)}</div>'
        f'<div class="dc-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'P0 coverage is the single go/no-go gauge for IC. Items '
        f'tied to analytics auto-mark DONE when the analytic is run. '
        f'Manual items (management references, legal review) need an '
        f'explicit override — "Mark done" link on each row. All '
        f'overrides are URL-encoded so you can share a state snapshot '
        f'by copying the URL.</div>'
        f'<div class="dc-kpi-grid">'
        f'<div class="dc-kpi">'
        f'<div class="dc-kpi__label">P0 coverage</div>'
        f'<div class="dc-kpi__val" style="color:{cov_color};">{cov_num}</div>'
        f'<div class="dc-kpi__band" style="color:{cov_color};">'
        f'{"Ready for IC" if state.p0_coverage >= 1.0 else "Blocking IC"}'
        f'</div></div>'
        f'<div class="dc-kpi">'
        f'<div class="dc-kpi__label">Total done</div>'
        f'<div class="dc-kpi__val" style="color:{P["text"]};">{done_num}</div>'
        f'<div class="dc-kpi__band" style="color:{P["text_faint"]};">'
        f'{state.total_coverage*100:.0f}% of all items</div></div>'
        f'<div class="dc-kpi">'
        f'<div class="dc-kpi__label">Open P0</div>'
        f'<div class="dc-kpi__val" style="color:{p0_color};">'
        f'{state.open_p0}</div>'
        f'<div class="dc-kpi__band" style="color:{p0_color};">'
        f'must close before IC</div></div>'
        f'<div class="dc-kpi">'
        f'<div class="dc-kpi__label">Open P1</div>'
        f'<div class="dc-kpi__val" style="color:{p1_color};">'
        f'{state.open_p1}</div>'
        f'<div class="dc-kpi__band" style="color:{p1_color};">'
        f'assign owners</div></div>'
        f'</div>'
        f'</div>'
    )


def _phase_section(
    phase: int,
    items: List[ChecklistStatus],
    qs: Dict[str, List[str]],
) -> str:
    n_total = len(items)
    n_done = sum(1 for s in items if s.status == ItemStatus.DONE)
    pct = (n_done / n_total * 100) if n_total > 0 else 0.0
    if pct >= 85:
        bar_cls = ""
    elif pct >= 50:
        bar_cls = "dc-progress__partial"
    else:
        bar_cls = "dc-progress__low"
    rows: List[str] = []
    for s in items:
        item = s.item
        evidence = ""
        if item.evidence_url:
            evidence = (
                f'<a href="{html.escape(item.evidence_url)}" '
                f'style="color:{P["accent"]};font-size:10px;'
                f'text-decoration:none;">Open →</a> '
            )
        # Question tooltip: the completion_criteria
        q_tooltip = (
            f' title="{html.escape(item.completion_criteria)}"'
            if item.completion_criteria else ''
        )
        note_html = (
            f'<div class="dc-item__note">{html.escape(s.note)}</div>'
            if s.note else ''
        )
        rows.append(
            f'<div class="dc-item">'
            f'{_status_badge(s.status)}'
            f'{_priority_badge(item.priority)}'
            f'<div class="dc-item__question"{q_tooltip}>'
            f'{html.escape(item.question)}</div>'
            f'<div class="dc-item__category">'
            f'{html.escape(item.category.value.replace("_", " "))}</div>'
            f'<div class="dc-item__owner">'
            f'{html.escape(item.default_owner.value)}</div>'
            f'<div class="dc-item__action">'
            f'{evidence}{_action_link(item, qs)}</div>'
            f'{note_html}'
            f'</div>'
        )
    return (
        f'<div class="dc-phase">'
        f'<div class="dc-phase__head">'
        f'<div class="dc-phase__title">'
        f'{html.escape(_PHASE_TITLES.get(phase, f"Phase {phase}"))}</div>'
        f'<div class="dc-phase__count">{n_done}/{n_total} done · '
        f'{pct:.0f}%</div>'
        f'</div>'
        f'<div class="dc-progress">'
        f'<div class="dc-progress__fill {bar_cls}" '
        f'style="width:{pct:.1f}%;"></div></div>'
        f'<div style="margin-top:8px;">{"".join(rows)}</div>'
        f'</div>'
    )


def _open_questions_block(state: DealChecklistState) -> str:
    qs = open_questions_for_ic_packet(state)
    if not qs:
        return (
            f'<div class="dc-callout good">'
            f'All diligence items covered — no open questions for IC.'
            f'</div>'
        )
    rows: List[str] = []
    for q in qs:
        color = (
            P["negative"] if q.priority == "P0"
            else P["warning"] if q.priority == "P1"
            else P["text_faint"]
        )
        rows.append(
            f'<div class="dc-oq-row">'
            f'<span class="dc-oq-row__prio" style="color:{color};">'
            f'{q.priority}</span>'
            f'<span>{html.escape(q.question)}</span>'
            f'<span class="dc-oq-row__owner">{html.escape(q.owner)}</span>'
            f'</div>'
        )
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:16px 20px;'
        f'margin-bottom:18px;">'
        f'<div class="dc-eyebrow">Open questions for IC '
        f'({len(qs)})</div>'
        f'<div style="font-size:11.5px;color:{P["text_dim"]};'
        f'margin-top:4px;line-height:1.55;max-width:880px;">'
        f'Every P0/P1 item that remains OPEN or BLOCKED. This list '
        f'is what the IC Packet "Open Questions" section prints — '
        f'close the loop on each before the memo ships.</div>'
        f'<div style="margin-top:12px;">{"".join(rows)}</div>'
        f'</div>'
    )


def _flat_checklist_table(state: DealChecklistState) -> str:
    """Sortable/filterable/exportable table of every item."""
    headers = [
        "Item", "Phase", "Category", "Priority", "Status",
        "Owner", "Question",
    ]
    rows: List[List[str]] = []
    sort_keys: List[List[Any]] = []
    status_rank = {
        ItemStatus.BLOCKED: 0, ItemStatus.OPEN: 1,
        ItemStatus.IN_PROGRESS: 2, ItemStatus.DONE: 3,
    }
    priority_rank = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2}
    for s in state.items:
        it = s.item
        status_color = P.get(_STATUS_COLOR[s.status], P["text_dim"])
        prio_color = P.get(_PRIORITY_COLOR[it.priority], P["text_dim"])
        rows.append([
            it.item_id,
            str(it.phase),
            it.category.value.replace("_", " "),
            f'<span style="color:{prio_color};font-weight:600;">'
            f'{it.priority.value}</span>',
            f'<span style="color:{status_color};font-weight:600;">'
            f'{s.status.value.replace("_", " ")}</span>',
            it.default_owner.value,
            it.question,
        ])
        sort_keys.append([
            it.item_id, it.phase, it.category.value,
            priority_rank[it.priority],
            status_rank[s.status],
            it.default_owner.value,
            it.question,
        ])
    return sortable_table(
        headers, rows, name="diligence_checklist", sort_keys=sort_keys,
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_diligence_checklist_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    manual_done = _parse_id_set(qs, "mark_done")
    manual_blocked = _parse_id_set(qs, "mark_blocked")
    manual_in_progress = _parse_id_set(qs, "mark_in_progress")

    # If ?empty=1, start from a fully-empty observation set (useful
    # for demos + tests).
    empty = (qs.get("empty") or [""])[0] == "1"
    obs = DealObservations() if empty else _demo_observations()
    state = compute_status(
        obs,
        manual_completed_ids=manual_done,
        manual_blocked_ids=manual_blocked,
        manual_in_progress_ids=manual_in_progress,
    )

    by_phase = state.by_phase()
    phase_html = "".join(
        _phase_section(phase, by_phase[phase], qs)
        for phase in sorted(by_phase.keys())
    )

    # Wrap the hero + open-questions in an export_json_panel so the
    # partner can download the live state as JSON.
    hero_and_oq = export_json_panel(
        _hero(state) + _open_questions_block(state),
        payload=state.to_dict(),
        name="diligence_checklist_state",
    )

    body = (
        _scoped_styles()
        + '<div class="dc-wrap">'
        + hero_and_oq
        + '<div class="dc-section-label">'
          'Items by phase · click an evidence link to drill in</div>'
        + phase_html
        + '<div class="dc-section-label">'
          'Flat view · sortable · filterable · CSV export</div>'
        + _flat_checklist_table(state)
        + '</div>'
        + bookmark_hint()
    )
    return chartis_shell(
        body, "RCM Diligence — Checklist",
        subtitle="Orchestration layer · auto-tracked from live analytics",
    )

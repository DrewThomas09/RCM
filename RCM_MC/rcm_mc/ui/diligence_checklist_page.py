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
    DealChecklistState, DealObservations, ICReadinessGate, ItemStatus,
    Owner, Priority, compute_ic_readiness, compute_status,
    open_questions_for_ic_packet, summarize_coverage,
)
from ..diligence.checklist.items import build_checklist
from ._chartis_kit import (
    P, chartis_shell, ck_help_tooltip, ck_kpi_block, ck_next_section,
    ck_page_title, ck_panel, ck_section_header, ck_section_intro,
    ck_sticky_toc, ck_page_explainer)
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped styles
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.dc-wrap{{font-family:var(--sc-sans,"Helvetica Neue",Arial,sans-serif);}}
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
.dc-item{{display:grid;grid-template-columns:80px 70px 1fr 110px 90px 240px;
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
.dc-item__action{{text-align:right;white-space:nowrap;
font-size:10px;color:{tf};letter-spacing:0.04em;}}
.dc-item__action a{{color:{ac};font-size:10px;text-decoration:none;
font-weight:600;white-space:nowrap;}}
.dc-item__action a + a{{margin-left:4px;
padding-left:8px;border-left:1px solid {bdim};}}
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
@media (max-width:960px){{.dc-item{{grid-template-columns:70px 60px 1fr;}}
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

# Editorial glosses surfaced via ck_help_tooltip [?] on each phase
# header. Partners encountering an unfamiliar phase label get the
# what-belongs-here + when-this-runs framing inline.
_PHASE_HELP = {
    1: (
        "Pre-NDA screening. Public-data sourcing + size / sub-sector "
        "filters before a signed NDA opens the data room. Predictive "
        "screener + market-intel comp band sit here."
    ),
    2: (
        "CCD benchmarks + predictive. The seller's data room becomes "
        "structured records (CCD ingest); HFMA benchmarks compare "
        "every initiative to industry priors; denial-rate predictor "
        "lands a forward-looking write-off projection."
    ),
    3: (
        "Risk workbench + manual diligence. Tier 1-3 risk panels run "
        "alongside partner-led checklist items (legal reps, payer "
        "contract review, management interviews). Bear case assembles "
        "from this layer."
    ),
    4: (
        "Financial synthesis. The 7-lever EBITDA bridge, the two-"
        "source Monte Carlo, and the public-market overlay turn "
        "diligence findings into investment math. Covenant headroom "
        "math runs against the post-close credit stack."
    ),
    5: (
        "Partner deliverables. IC memo, IC packet, LP digest, "
        "exit memo. Every export caps the chain of citation so the "
        "LP can audit any number back to its source."
    ),
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


_GATE_TONE = {
    "READY": ("#0a8a5f", "CLEARS THE IC GATE"),
    "CONDITIONAL": ("#b8732a", "CONDITIONAL — NAME OPEN P1s IN THE MEMO"),
    "NOT_READY": ("#b5321e", "DO NOT SCHEDULE IC"),
}


def _gate_blocker_row(b) -> str:
    """One punch-list row: the blocker, its completion criterion, the
    evidence link that closes it, and whether the platform can verify
    closure itself."""
    pr_color = P["negative"] if b.priority == "P0" else P["warning"]
    status_label = "BLOCKED" if b.status == "blocked" else "OPEN"
    verify = (
        f'<span style="color:{P["positive"]};font-size:10px;'
        f'font-weight:600;">AUTO-VERIFIABLE</span>'
        if b.auto_verifiable else
        f'<span style="color:{P["text_faint"]};font-size:10px;">'
        f'MANUAL ATTESTATION</span>'
    )
    evidence = (
        f'<a href="{html.escape(b.evidence_url, quote=True)}" '
        f'style="color:{P["accent"]};font-size:11px;'
        f'text-decoration:none;">Produce evidence →</a>'
        if b.evidence_url else
        f'<span style="color:{P["text_faint"]};font-size:11px;">'
        f'manual workstream</span>'
    )
    crit = html.escape(b.completion_criteria or "—")
    return (
        f'<div style="padding:10px 0;border-bottom:1px solid {P["border_dim"]};">'
        f'<div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'font-weight:700;letter-spacing:0.1em;color:{pr_color};">'
        f'{b.priority} · {status_label}</span>'
        f'<span style="font-size:9px;letter-spacing:0.08em;'
        f'color:{P["text_faint"]};text-transform:uppercase;">'
        f'{html.escape(b.category)}</span>'
        f'<span style="margin-left:auto;">{verify}</span>'
        f'</div>'
        f'<div style="font-size:12.5px;color:{P["text"]};font-weight:500;'
        f'margin-top:3px;">{html.escape(b.question)}</div>'
        f'<div style="font-size:11px;color:{P["text_dim"]};margin-top:3px;'
        f'line-height:1.5;"><span style="color:{P["text_faint"]};">'
        f'Closes when: </span>{crit}</div>'
        f'<div style="margin-top:4px;">{evidence}</div>'
        f'</div>'
    )


def _ic_readiness_section(gate: ICReadinessGate) -> str:
    """The auditable IC go/no-go gate — verdict band, verifiability
    split, and the evidence-linked punch-list of every blocker.

    This is the partner's single 'can we go to IC' answer, and it is
    self-justifying: each blocker names the criterion + link that
    closes it, so the gate doubles as the to-do list and the audit
    trail of why the answer is what it is.
    """
    tone, tagline = _GATE_TONE.get(gate.verdict, ("#7a8699", ""))
    # Verifiability mini-bar: how much of the open work the platform
    # can confirm from observations vs. needs a human sign-off.
    total_open = gate.auto_verifiable_open + gate.manual_attestation_open
    auto_pct = (gate.auto_verifiable_open / total_open * 100.0) if total_open else 0.0
    verify_bar = (
        f'<div style="margin-top:10px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:10px;color:{P["text_faint"]};margin-bottom:3px;">'
        f'<span>{gate.auto_verifiable_open} auto-verifiable from data</span>'
        f'<span>{gate.manual_attestation_open} need partner attestation</span>'
        f'</div>'
        f'<div style="height:8px;border-radius:4px;overflow:hidden;'
        f'background:{P["text_faint"]};background-opacity:0.2;display:flex;">'
        f'<div style="width:{auto_pct:.0f}%;background:{P["positive"]};"></div>'
        f'<div style="flex:1;background:{P["text_faint"]};opacity:0.35;"></div>'
        f'</div></div>'
    ) if total_open else ""

    p0_block = ""
    if gate.blocking_p0:
        p0_block = (
            f'<div style="margin-top:14px;">'
            f'<div style="font-family:var(--ck-mono);font-size:10px;'
            f'letter-spacing:0.12em;color:{P["negative"]};font-weight:700;'
            f'margin-bottom:4px;">P0 HARD STOPS · {len(gate.blocking_p0)}</div>'
            + "".join(_gate_blocker_row(b) for b in gate.blocking_p0)
            + '</div>'
        )
    p1_block = ""
    if gate.blocking_p1:
        p1_block = (
            f'<div style="margin-top:14px;">'
            f'<div style="font-family:var(--ck-mono);font-size:10px;'
            f'letter-spacing:0.12em;color:{P["warning"]};font-weight:700;'
            f'margin-bottom:4px;">P1 — NAME IN MEMO · {len(gate.blocking_p1)}</div>'
            + "".join(_gate_blocker_row(b) for b in gate.blocking_p1)
            + '</div>'
        )
    return (
        f'<div class="ck-panel" style="border-left:4px solid {tone};">'
        f'<div style="display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;">'
        f'<span style="font-family:var(--ck-mono);font-size:22px;'
        f'font-weight:700;color:{tone};letter-spacing:0.02em;">'
        f'{html.escape(gate.verdict.replace("_", " "))}</span>'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.14em;color:{P["text_faint"]};">{tagline}</span>'
        f'<span style="margin-left:auto;font-family:var(--ck-mono);'
        f'font-size:11px;color:{P["text_dim"]};">'
        f'P0 {gate.p0_done}/{gate.p0_total} · {gate.p0_coverage*100:.0f}%</span>'
        f'</div>'
        f'<p style="font-size:12.5px;color:{P["text_dim"]};line-height:1.6;'
        f'margin:8px 0 0;">{html.escape(gate.rationale)}</p>'
        f'{verify_bar}{p0_block}{p1_block}'
        f'</div>'
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
    # 2026-05-28 batch 21 · universal strict 5-block head.
    # as_subhead=True (audit 2026-05-29): this page also renders a
    # top-of-body ck_page_title (the H1). The editorial deck is
    # the section head under that H1 — render as H2 so the page
    # satisfies the One-H1 invariant.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow="DILIGENCE · CHECKLIST",
        title="Diligence Checklist",
        meta=(
            f"{state.done}/{state.total} ITEMS DONE · "
            f"AUTO-TRACKED · URL-SHARABLE STATE"
        ),
        lede_italic_phrase="Coverage + open questions for IC.",
        lede_body=(
            f"{html.escape(banner)} Auto-tracked from live analytics; "
            "partner overrides URL-encoded so you can share a state "
            "snapshot by copying the link."
        ),
        as_subhead=True,
    )
    explainer = ck_panel(
        '<p class="ck-section-body">'
        '<strong>How to read:</strong> '
        'P0 coverage is the single go/no-go gauge for IC. Items '
        'tied to analytics auto-mark DONE when the analytic is run. '
        'Manual items (management references, legal review) need an '
        'explicit override — "Mark done" link on each row. All '
        'overrides are URL-encoded so you can share a state snapshot '
        'by copying the URL.</p>',
        title="Coverage rules",
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "P0 coverage", cov_num,
            sub="Ready for IC" if state.p0_coverage >= 1.0 else "Blocking IC",
        )
        + ck_kpi_block(
            "Total done", done_num,
            sub=f"{state.total_coverage*100:.0f}% of all items",
        )
        + ck_kpi_block(
            "Open P0", f"{state.open_p0}",
            sub="must close before IC",
        )
        + ck_kpi_block(
            "Open P1", f"{state.open_p1}",
            sub="assign owners",
        )
        + '</div>'
    )
    return f'{intro}{explainer}{kpis}'


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
    phase_title = _PHASE_TITLES.get(phase, f"Phase {phase}")
    phase_help = _PHASE_HELP.get(phase)
    title_html = (
        ck_help_tooltip(phase_title, phase_help)
        if phase_help else html.escape(phase_title)
    )
    return (
        f'<div class="dc-phase">'
        f'<div class="dc-phase__head">'
        f'<div class="dc-phase__title">'
        f'{title_html}</div>'
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
        return ck_panel(
            '<p class="ck-section-body">'
            'All diligence items covered — no open questions for IC.'
            '</p>',
            title="Open questions for IC",
        )
    rows: List[str] = []
    for q in qs:
        cls = (
            "cad-neg" if q.priority == "P0"
            else "cad-warn" if q.priority == "P1"
            else ""
        )
        rows.append(
            f'<div class="dc-oq-row">'
            f'<span class="dc-oq-row__prio {cls}">'
            f'{q.priority}</span>'
            f'<span>{html.escape(q.question)}</span>'
            f'<span class="dc-oq-row__owner">{html.escape(q.owner)}</span>'
            f'</div>'
        )
    return ck_panel(
        '<p class="ck-section-body">'
        'Every P0/P1 item that remains OPEN or BLOCKED. This list '
        'is what the IC Packet "Open Questions" section prints — '
        'close the loop on each before the memo ships.</p>'
        f'{"".join(rows)}',
        title=f"Open questions for IC ({len(qs)})",
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

def _category_progress_svg(state, width: int = 660) -> str:
    """The checklist at a glance: one stacked bar per category — DONE
    green, IN-PROGRESS amber, OPEN gray, BLOCKED red — so the blocked
    category is visible before scrolling the roster."""
    cats = state.by_category()
    if not cats:
        return ""
    tone = {"DONE": "#0a8a5f", "IN_PROGRESS": "#b8732a",
            "OPEN": "#9aa3ad", "BLOCKED": "#b5321e"}
    order = ["DONE", "IN_PROGRESS", "OPEN", "BLOCKED"]
    row_h, pad_l, pad_r = 24, 170, 86
    pw = width - pad_l - pad_r
    rows = list(cats.items())
    h = len(rows) * row_h + 6
    parts = [f'<svg width="{width}" height="{h}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Checklist progress by category">']
    for i, (cat, items) in enumerate(rows):
        y = i * row_h + 4
        n = len(items) or 1
        counts = {s: 0 for s in order}
        for st in items:
            counts[st.status.value] = counts.get(st.status.value, 0) + 1
        done = counts["DONE"]
        parts.append(
            f'<text x="{pad_l-8}" y="{y+12}" text-anchor="end" '
            'font-family="monospace" font-size="9.5" fill="#465366">'
            f'{html.escape(cat.value.title()[:24])}</text>')
        x = pad_l
        for s in order:
            c = counts[s]
            if not c:
                continue
            w = c / n * pw
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{max(w,1):.1f}" '
                f'height="14" fill="{tone[s]}">'
                f'<title>{s.replace("_", " ").title()}: {c}</title>'
                '</rect>')
            x += w
        parts.append(
            f'<text x="{pad_l+pw+8}" y="{y+12}" '
            'font-family="monospace" font-size="9.5" fill="#465366">'
            f'{done}/{len(items)}</text>')
    parts.append('</svg>')
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'margin-right:12px;font-size:10.5px;color:#465366;">'
        f'<span style="width:9px;height:9px;background:{c};'
        f'display:inline-block;"></span>'
        f'{s.replace("_", " ").title()}</span>'
        for s, c in tone.items())
    return ("".join(parts)
            + f'<div style="margin:2px 0 14px;">{legend}</div>')


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

    # Auditable IC go/no-go gate — derived purely from item statuses,
    # so it can never disagree with the checklist below it.
    gate = compute_ic_readiness(state)
    _payload = state.to_dict()
    _payload["ic_readiness_gate"] = gate.to_dict()

    # Wrap the hero + gate + open-questions in an export_json_panel so
    # the partner can download the live state (incl. the gate) as JSON.
    hero_and_oq = export_json_panel(
        _hero(state)
        + _ic_readiness_section(gate)
        + _open_questions_block(state),
        payload=_payload,
        name="diligence_checklist_state",
    )

    # Compute a quick completion ratio for the meta line — done over total.
    _items = getattr(state, "items", []) or []
    _done = sum(
        1 for s in _items
        if getattr(getattr(s, "status", None), "value", None) == "done"
    )
    _pct = (_done / len(_items) * 100.0) if _items else 0.0
    title = (
        ck_page_title(
        "Diligence Checklist",
        eyebrow="RCM DILIGENCE",
        meta=(
            f"Orchestration layer · {_pct:.0f}% complete · "
            "auto-tracked from live analytics"
        ),
    )
        + ck_page_explainer(
            'Diligence orchestration + open-questions tracker.',
            "Tracks every diligence workstream (QoE, IT, HR, regulatory, commercial) by owner and deadline, plus the rolling list of open questions the partner has flagged. Used as the partner's daily standup view during the exclusivity window.",
            source='Per-deal checklist + workflow state (live).',
        )
    )
    # Sticky right-rail TOC — the checklist has three vertical
    # sections (the hero + open questions, the phase-grouped item
    # list, and the flat sortable table). Partners come back to a
    # specific phase mid-diligence; the TOC lets them jump.
    toc = ck_sticky_toc([
        {"id": "dc-hero",   "title": "Open questions"},
        {"id": "dc-phases", "title": "Items by phase"},
        {"id": "dc-flat",   "title": "Flat view · CSV"},
    ])
    body = (
        _scoped_styles()
        + title
        + '<div class="dc-wrap">'
        + '<div class="ck-toc-layout">'
        + toc
        + '<div class="ck-toc-content">'
        + f'<section id="dc-hero">{hero_and_oq}</section>'
        + _category_progress_svg(state)
        + '<section id="dc-phases">'
        + ck_section_header(
            "Items by phase · click an evidence link to drill in",
            eyebrow="PHASES",
        )
        + phase_html
        + '</section>'
        + '<section id="dc-flat">'
        + ck_panel(
            _flat_checklist_table(state),
            title="Flat view · sortable · filterable · CSV export",
        )
        + '</section>'
        + '</div></div>'
        + '</div>'
        + bookmark_hint()
        + ck_next_section(
            "Open the deal profile",
            "/diligence/deal",
            eyebrow="Up next",
            italic_word="deal",
        )
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "RCM Diligence — Checklist",
        active_nav="/diligence/checklist",
        subtitle="Orchestration layer · auto-tracked from live analytics",
    )

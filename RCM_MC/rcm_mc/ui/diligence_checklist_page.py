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
    ChecklistItem, ChecklistStatus, DealChecklistState, DealObservations,
    ICReadinessGate, ItemStatus, Priority, compute_ic_readiness,
    compute_status, open_questions_for_ic_packet, summarize_coverage,
)
from ._chartis_kit import (
    P, chartis_shell, ck_affirm_empty, ck_editorial_head, ck_empty_state,
    ck_fmt_percent, ck_help_tooltip, ck_kpi_block, ck_next_section,
    ck_page_actions, ck_panel, ck_progress_dot_track, ck_section_header,
    ck_severity_panel, ck_signal_badge, ck_sticky_toc,
)
from .power_ui import (
    bookmark_hint, export_json_panel, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped styles — only classes this page actually emits. Colors are
# kit tokens (var(--sc-*)) with the canonical hex fallbacks; the
# type families come from the shell, so no font-family override on
# the page wrapper.
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.dc-section-note{font-size:12.5px;color:var(--sc-text-dim,#465366);
line-height:1.6;margin:2px 0 14px;max-width:72ch;}

/* ── One chip idiom for status + priority, page-wide ─────────── */
.dc-chip{display:inline-block;
font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:9.5px;font-weight:700;letter-spacing:0.08em;
text-transform:uppercase;text-align:center;padding:2px 7px;
border:1px solid currentColor;border-radius:2px;white-space:nowrap;}
.dc-chip.tone-positive{color:var(--sc-positive,#0a8a5f);}
.dc-chip.tone-warning{color:var(--sc-warning,#b8732a);}
.dc-chip.tone-negative{color:var(--sc-negative,#b5321e);}
.dc-chip.tone-neutral{color:var(--sc-text-dim,#465366);}

/* ── IC readiness gate ───────────────────────────────────────── */
.dc-gate-verdict__row{display:flex;gap:12px;align-items:baseline;
flex-wrap:wrap;}
.dc-gate-verdict__word{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:22px;font-weight:700;letter-spacing:0.02em;}
.dc-gate-verdict__word.tone-positive{color:var(--sc-positive,#0a8a5f);}
.dc-gate-verdict__word.tone-warning{color:var(--sc-warning,#b8732a);}
.dc-gate-verdict__word.tone-negative{color:var(--sc-negative,#b5321e);}
.dc-gate-verdict__word.tone-neutral{color:var(--sc-text-dim,#465366);}
.dc-gate-verdict__tag{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:9px;letter-spacing:0.14em;color:var(--sc-text-faint,#7a8699);
text-transform:uppercase;}
.dc-gate-verdict__cov{margin-left:auto;
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:11px;
color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums;}
.dc-gate-verdict__why{font-size:12.5px;color:var(--sc-text-dim,#465366);
line-height:1.6;margin:0;}
.dc-verify__labels{display:flex;justify-content:space-between;gap:10px;
font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10px;
color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums;
margin-bottom:3px;}
.dc-verify__track{height:8px;border-radius:4px;overflow:hidden;
background:var(--sc-rule,#d6cfc0);}
.dc-verify__fill{height:100%;background:var(--sc-positive,#0a8a5f);}
.dc-gate-group{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10px;letter-spacing:0.12em;font-weight:700;
text-transform:uppercase;}
.dc-gate-group.tone-negative{color:var(--sc-negative,#b5321e);}
.dc-gate-group.tone-warning{color:var(--sc-warning,#b8732a);}
.dc-gate-row__meta{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;}
.dc-gate-row__cat{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:9px;letter-spacing:0.08em;color:var(--sc-text-faint,#7a8699);
text-transform:uppercase;}
.dc-gate-row__verify{margin-left:auto;}
.dc-gate-row__verify .ck-badge{font-size:9px;padding:2px 6px;}
.dc-gate-row__q{font-size:12.5px;color:var(--sc-text,#1a2332);
font-weight:500;line-height:1.5;}
.dc-gate-row__crit{font-size:11px;color:var(--sc-text-dim,#465366);
line-height:1.5;}
.dc-gate-row__crit span{color:var(--sc-text-faint,#7a8699);}
.dc-gate-row__evidence{color:var(--sc-teal,#155752);font-size:11px;
font-weight:600;text-decoration:none;}
.dc-gate-row__evidence:hover{text-decoration:underline;}
.dc-gate-row__evidence:focus-visible{outline:2px solid var(--sc-teal,#155752);
outline-offset:2px;}
.dc-gate-row__manual{color:var(--sc-text-faint,#7a8699);font-size:11px;}

/* ── Category progress chart ─────────────────────────────────── */
.dc-catsvg{width:100%;max-width:660px;height:auto;display:block;}
.dc-legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px;}
.dc-legend__key{display:inline-flex;align-items:center;gap:5px;
font-size:10.5px;color:var(--sc-text-dim,#465366);}
.dc-legend__swatch{width:9px;height:9px;display:inline-block;}
.dc-legend__swatch.s-done{background:var(--sc-positive,#0a8a5f);}
.dc-legend__swatch.s-wip{background:var(--sc-warning,#b8732a);}
.dc-legend__swatch.s-open{background:var(--sc-text-faint,#7a8699);}
.dc-legend__swatch.s-blocked{background:var(--sc-negative,#b5321e);}

/* ── Phase cards + item rows ─────────────────────────────────── */
.dc-phase{background:#fff;border:1px solid var(--sc-rule,#d6cfc0);
border-radius:2px;padding:14px 18px;margin-bottom:12px;
transition:border-color 140ms ease;}
.dc-phase:hover{border-color:var(--sc-rule-2,#bfb6a2);}
.dc-phase__head{display:flex;justify-content:space-between;
align-items:baseline;gap:14px;margin-bottom:8px;flex-wrap:wrap;}
.dc-phase__title{font-size:14px;color:var(--sc-text,#1a2332);
font-weight:600;}
.dc-phase__meter{display:flex;align-items:center;gap:8px;}
.dc-phase__count{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:11px;color:var(--sc-text-dim,#465366);letter-spacing:0.06em;
text-transform:uppercase;font-variant-numeric:tabular-nums;}
.dc-phase__items{margin-top:8px;}
.dc-item{display:grid;
grid-template-columns:84px 48px 1fr 110px 90px 200px;
gap:10px;align-items:baseline;padding:9px 4px;
border-bottom:1px solid var(--sc-rule,#d6cfc0);font-size:12px;}
.dc-item:last-child{border-bottom:0;}
.dc-item:hover{background:var(--bg-tint,#e8e0d0);}
.dc-item__question{color:var(--sc-text,#1a2332);line-height:1.45;}
.dc-item__owner{color:var(--sc-text-dim,#465366);font-size:10px;
letter-spacing:1px;text-transform:uppercase;font-weight:600;}
.dc-item__category{color:var(--sc-text-faint,#7a8699);font-size:10px;
letter-spacing:1px;text-transform:uppercase;}
.dc-item__action{text-align:right;white-space:nowrap;font-size:11px;}
.dc-item__action a{color:var(--sc-teal,#155752);font-size:11px;
text-decoration:none;font-weight:600;white-space:nowrap;padding:2px 3px;}
.dc-item__action a + a{margin-left:2px;padding-left:8px;
border-left:1px solid var(--sc-rule,#d6cfc0);}
.dc-item__action a:hover{text-decoration:underline;}
.dc-item__action a:focus-visible{outline:2px solid var(--sc-teal,#155752);
outline-offset:1px;}
.dc-item__note{grid-column:3/-1;font-size:11px;
color:var(--sc-text-faint,#7a8699);font-style:italic;margin-top:4px;}
.dc-override{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:8.5px;letter-spacing:0.08em;color:var(--sc-warning,#b8732a);
border:1px solid currentColor;border-radius:2px;padding:1px 4px;
margin-left:6px;text-transform:uppercase;vertical-align:1px;cursor:help;}

/* ── Open questions for IC ───────────────────────────────────── */
.dc-oq-summary{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:11px;letter-spacing:0.08em;color:var(--sc-text-dim,#465366);
text-transform:uppercase;margin:0 0 6px;
font-variant-numeric:tabular-nums;}
.dc-oq-row{padding:8px 0;border-bottom:1px solid var(--sc-rule,#d6cfc0);
display:grid;grid-template-columns:44px 1fr 100px;gap:12px;
align-items:baseline;font-size:12.5px;color:var(--sc-text-dim,#465366);
line-height:1.5;}
.dc-oq-row:last-child{border-bottom:0;}
.dc-oq-row--break{border-top:2px solid var(--sc-rule-2,#bfb6a2);}
.dc-oq-row__owner{color:var(--sc-text-faint,#7a8699);font-size:10px;
letter-spacing:1px;text-transform:uppercase;text-align:right;
font-weight:600;}

/* ── Flat table ──────────────────────────────────────────────── */
.dc-itemid{font-family:var(--sc-mono,'JetBrains Mono',monospace);
font-size:10.5px;color:var(--sc-text-faint,#7a8699);}
.dc-flat-scroll{max-height:72vh;overflow:auto;}

@media (max-width:960px){
.dc-item{grid-template-columns:84px 48px 1fr;}
.dc-item__owner,.dc-item__category{display:none;}
.dc-item__action{grid-column:1/-1;text-align:left;}
.dc-item__note{grid-column:1/-1;}
}
"""
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

# One tone map, one chip idiom — the same DONE / IN PROGRESS / OPEN /
# BLOCKED (and P0/P1/P2) treatment renders in the phase roster, the
# gate punch-list, the open-questions panel, and the flat table.
_STATUS_TONE = {
    ItemStatus.DONE: "positive",
    ItemStatus.IN_PROGRESS: "warning",
    ItemStatus.OPEN: "neutral",
    ItemStatus.BLOCKED: "negative",
}

_PRIORITY_TONE = {
    Priority.P0: "negative",
    Priority.P1: "warning",
    Priority.P2: "neutral",
}


def _chip(text: str, tone: str) -> str:
    """The page's single status/priority chip. Dense-row sibling of
    ck_signal_badge — same border-pill grammar, mono + smaller so 40
    rows of chips don't shout."""
    tone = tone if tone in ("positive", "warning", "negative", "neutral") \
        else "neutral"
    return f'<span class="dc-chip tone-{tone}">{html.escape(text)}</span>'


def _status_chip(status: ItemStatus) -> str:
    return _chip(
        status.value.replace("_", " "),
        _STATUS_TONE.get(status, "neutral"),
    )


def _priority_chip(p: Priority) -> str:
    return _chip(p.value, _PRIORITY_TONE.get(p, "neutral"))


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

    # aria-labels tie each of the four repeated verbs back to its
    # item for screen readers — 40 bare "Mark done" links otherwise
    # read as an undifferentiated wall.
    iid = html.escape(item.item_id, quote=True)
    return (
        f'<a href="{_url_for("mark_done")}" '
        f'aria-label="Mark {iid} done">Mark done</a>'
        f'<a href="{_url_for("mark_blocked")}" '
        f'aria-label="Mark {iid} blocked">Block</a>'
        f'<a href="{_url_for("mark_in_progress")}" title="In progress" '
        f'aria-label="Mark {iid} in progress">WIP</a>'
        f'<a href="{_url_for("clear")}" '
        f'aria-label="Clear override on {iid}">Clear</a>'
    )


# Verdict → (tone, tagline). Tone keys map onto the kit severity
# tones (positive / warning / negative); the tagline is the mono
# caps strap beside the verdict word. test_ic_readiness_gate pins
# _GATE_TONE["READY"][1].
_GATE_TONE = {
    "READY": ("positive", "CLEARS THE IC GATE"),
    "CONDITIONAL": ("warning", "CONDITIONAL — NAME OPEN P1s IN THE MEMO"),
    "NOT_READY": ("negative", "DO NOT SCHEDULE IC"),
}

_GATE_PANEL_TONE = {
    "positive": "positive",
    "warning": "amber",
    "negative": "red",
}


def _gate_blocker_row(b) -> str:
    """One punch-list row: the blocker, its completion criterion, the
    evidence link that closes it, and whether the platform can verify
    closure itself."""
    status_label = "BLOCKED" if b.status == "blocked" else "OPEN"
    status_tone = "negative" if b.status == "blocked" else "neutral"
    verify = (
        ck_signal_badge("AUTO-VERIFIABLE", tone="positive")
        if b.auto_verifiable else
        ck_signal_badge("MANUAL ATTESTATION", tone="neutral")
    )
    evidence = (
        f'<a class="dc-gate-row__evidence" '
        f'href="{html.escape(b.evidence_url, quote=True)}">'
        f'Produce evidence →</a>'
        if b.evidence_url else
        '<span class="dc-gate-row__manual">manual workstream</span>'
    )
    crit = html.escape(b.completion_criteria or "—")
    prio_tone = "negative" if b.priority == "P0" else "warning"
    return (
        '<li class="dc-gate-row">'
        '<div class="dc-gate-row__meta">'
        f'{_chip(b.priority, prio_tone)}'
        f'{_chip(status_label, status_tone)}'
        f'<span class="dc-gate-row__cat">{html.escape(b.category)}</span>'
        f'<span class="dc-gate-row__verify">{verify}</span>'
        '</div>'
        f'<div class="dc-gate-row__q">{html.escape(b.question)}</div>'
        f'<div class="dc-gate-row__crit"><span>Closes when: </span>'
        f'{crit}</div>'
        f'<div>{evidence}</div>'
        '</li>'
    )


def _ic_readiness_section(gate: ICReadinessGate) -> str:
    """The auditable IC go/no-go gate — verdict band, verifiability
    split, and the evidence-linked punch-list of every blocker.

    This is the partner's single 'can we go to IC' answer, and it is
    self-justifying: each blocker names the criterion + link that
    closes it, so the gate doubles as the to-do list and the audit
    trail of why the answer is what it is.
    """
    tone, tagline = _GATE_TONE.get(gate.verdict, ("neutral", ""))
    cov = provenance(
        ck_fmt_percent(gate.p0_coverage),
        source="compute_ic_readiness()",
        formula="p0_done / p0_total",
        detail=(
            "The gate is a pure function of item statuses, so it can "
            "never disagree with the checklist below it."
        ),
    )
    verdict_li = (
        '<li class="dc-gate-verdict">'
        '<div class="dc-gate-verdict__row">'
        f'<span class="dc-gate-verdict__word tone-{tone}">'
        f'{html.escape(gate.verdict.replace("_", " "))}</span>'
        f'<span class="dc-gate-verdict__tag">{html.escape(tagline)}</span>'
        f'<span class="dc-gate-verdict__cov">'
        f'P0 {gate.p0_done}/{gate.p0_total} · {cov}</span>'
        '</div>'
        f'<p class="dc-gate-verdict__why">{html.escape(gate.rationale)}</p>'
        '</li>'
    )
    # Verifiability split: how much of the open work the platform can
    # confirm from observations vs. needs a human sign-off. Positive
    # fill over the kit rule-gray track.
    total_open = gate.auto_verifiable_open + gate.manual_attestation_open
    verify_li = ""
    if total_open:
        auto_pct = gate.auto_verifiable_open / total_open * 100.0
        verify_li = (
            '<li class="dc-verify">'
            '<div class="dc-verify__labels">'
            f'<span>{gate.auto_verifiable_open} auto-verifiable from data</span>'
            f'<span>{gate.manual_attestation_open} need partner attestation</span>'
            '</div>'
            f'<div class="dc-verify__track" role="img" aria-label="'
            f'{gate.auto_verifiable_open} of {total_open} open blockers '
            f'auto-verifiable">'
            f'<div class="dc-verify__fill" style="width:{auto_pct:.1f}%;">'
            '</div></div>'
            '</li>'
        )
    p0_block = ""
    if gate.blocking_p0:
        p0_block = (
            '<li class="dc-gate-group tone-negative">'
            f'P0 HARD STOPS · {len(gate.blocking_p0)}</li>'
            + "".join(_gate_blocker_row(b) for b in gate.blocking_p0)
        )
    p1_block = ""
    if gate.blocking_p1:
        p1_block = (
            '<li class="dc-gate-group tone-warning">'
            f'P1 — NAME IN MEMO · {len(gate.blocking_p1)}</li>'
            + "".join(_gate_blocker_row(b) for b in gate.blocking_p1)
        )
    return ck_severity_panel(
        tone=_GATE_PANEL_TONE.get(tone, "neutral"),
        label="IC readiness gate",
        count=gate.total_blockers,
        rows_html=f'{verdict_li}{verify_li}{p0_block}{p1_block}',
    )


def _masthead(state: DealChecklistState, *, empty: bool) -> str:
    """The page's single editorial deck — eyebrow, serif H1, honest
    mono meta, italic-first-phrase lede, and an honest source note
    (this default render is an illustrative demo fixture, not live
    deal state)."""
    banner = summarize_coverage(state)
    mode_tag = "EMPTY OBSERVATION SET" if empty else "DEMO SNAPSHOT"
    source_note = (
        "Empty observation set (?empty=1) — no analytics observed; "
        "every item renders OPEN."
        if empty else
        "Illustrative demo snapshot — statuses derive from a fixed "
        "observation set; wire a deal_id for live state."
    )
    return ck_editorial_head(
        eyebrow="RCM DILIGENCE",
        title="Diligence Checklist",
        meta=(
            f"{state.done}/{state.total} ITEMS DONE · "
            f"{ck_fmt_percent(state.total_coverage)} COMPLETE · {mode_tag}"
        ),
        lede_italic_phrase="Coverage + open questions for IC.",
        lede_body=(
            f"{html.escape(banner)} Items tied to analytics auto-mark "
            "DONE when the analytic runs; manual items (management "
            "references, legal review) take an explicit override — the "
            "Mark done link on each row. Every override is URL-encoded, "
            "so copying the link shares this exact snapshot."
        ),
        source_note=source_note,
    )


def _kpi_strip(state: DealChecklistState) -> str:
    """Four KPI tiles, every value provenance-wrapped so any figure a
    partner might quote in the memo explains itself on hover."""
    cov_num = provenance(
        ck_fmt_percent(state.p0_coverage),
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
    open_p0_num = provenance(
        f'{state.open_p0}',
        source="compute_status()",
        formula="count(P0 items where status in (OPEN, BLOCKED))",
        detail=(
            "Hard stops — every open P0 must close before an IC slot "
            "is scheduled."
        ),
    )
    open_p1_num = provenance(
        f'{state.open_p1}',
        source="compute_status()",
        formula="count(P1 items where status in (OPEN, BLOCKED))",
        detail=(
            "Should-close items — an open P1 doesn't block the "
            "meeting, but it must be named in the memo with an owner."
        ),
    )
    return (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "P0 coverage", cov_num,
            sub="Ready for IC" if state.p0_coverage >= 1.0 else "Blocking IC",
        )
        + ck_kpi_block(
            "Total done", done_num,
            sub=f"{ck_fmt_percent(state.total_coverage)} of all items",
        )
        + ck_kpi_block(
            "Open P0", open_p0_num,
            sub="must close before IC",
        )
        + ck_kpi_block(
            "Open P1", open_p1_num,
            sub="assign owners",
        )
        + '</div>'
    )


def _phase_section(
    phase: int,
    items: List[ChecklistStatus],
    qs: Dict[str, List[str]],
    overridden: Set[str],
) -> str:
    n_total = len(items)
    n_done = sum(1 for s in items if s.status == ItemStatus.DONE)
    frac = (n_done / n_total) if n_total > 0 else 0.0
    rows: List[str] = []
    for s in items:
        item = s.item
        evidence = ""
        if item.evidence_url:
            ev_url = html.escape(item.evidence_url, quote=True)
            evidence = (
                f'<a href="{ev_url}" title="Opens {ev_url}" '
                f'aria-label="Open evidence for {html.escape(item.item_id, quote=True)}">'
                f'Open →</a>'
            )
        # Completion criteria via the provenance idiom (dotted
        # underline + cursor:help) instead of an invisible bare
        # title attribute.
        if item.completion_criteria:
            q_html = provenance(
                item.question,
                source="completion_criteria",
                detail=item.completion_criteria,
            )
        else:
            q_html = html.escape(item.question)
        # Honesty split at row level: manually-overridden rows carry
        # a faint tag so a partner can tell attested state from
        # auto-verified state without opening the gate.
        override_tag = ""
        if item.item_id in overridden:
            override_tag = (
                '<span class="dc-override" title="Partner override — '
                'state set by hand, not auto-verified from '
                'observations">override</span>'
            )
        note_html = (
            f'<div class="dc-item__note">{html.escape(s.note)}</div>'
            if s.note else ''
        )
        rows.append(
            '<div class="dc-item">'
            f'{_status_chip(s.status)}'
            f'{_priority_chip(item.priority)}'
            f'<div class="dc-item__question">{q_html}{override_tag}</div>'
            f'<div class="dc-item__category">'
            f'{html.escape(item.category.value.replace("_", " "))}</div>'
            f'<div class="dc-item__owner">'
            f'{html.escape(item.default_owner.value)}</div>'
            f'<div class="dc-item__action">'
            f'{evidence}{_action_link(item, qs)}</div>'
            f'{note_html}'
            '</div>'
        )
    phase_title = _PHASE_TITLES.get(phase, f"Phase {phase}")
    phase_help = _PHASE_HELP.get(phase)
    title_html = (
        ck_help_tooltip(phase_title, phase_help)
        if phase_help else html.escape(phase_title)
    )
    dots = ck_progress_dot_track(
        n_done, n_total,
        show_caption=False,
        label_singular="item", label_plural="items",
    )
    return (
        '<div class="dc-phase">'
        '<div class="dc-phase__head">'
        f'<div class="dc-phase__title">{title_html}</div>'
        '<div class="dc-phase__meter">'
        f'{dots}'
        f'<span class="dc-phase__count">{n_done}/{n_total} done · '
        f'{ck_fmt_percent(frac)}</span>'
        '</div>'
        '</div>'
        f'<div class="dc-phase__items">{"".join(rows)}</div>'
        '</div>'
    )


def _open_questions_block(state: DealChecklistState, *, empty: bool) -> str:
    qs = open_questions_for_ic_packet(state)
    if not qs:
        # All clear — an affirmative band, not a bare paragraph.
        return ck_affirm_empty(
            headline="All diligence items covered.",
            body=(
                "No open questions for IC — every P0 and P1 item is "
                "closed. The IC Packet's Open Questions section will "
                "print empty."
            ),
            cta_text="Assemble the IC packet",
            cta_href="/diligence/ic-packet",
        )
    # Empty-observation mode renders every item open — frame the wall
    # of 39 rows as an onboarding state rather than a failure wall.
    lead_in = ""
    if empty and state.done == 0:
        lead_in = ck_empty_state(
            "Nothing observed yet.",
            (
                "No analytics have run for this deal, so every "
                "checklist item is open. Start with CCD ingest or "
                "open the diligence index to run the first analytic."
            ),
            eyebrow="EMPTY OBSERVATION SET",
            cta_label="Open the diligence index",
            cta_href="/diligence",
            tone="neutral",
        )
    n_p0 = sum(1 for q in qs if q.priority == "P0")
    n_p1 = sum(1 for q in qs if q.priority == "P1")
    n_p2 = len(qs) - n_p0 - n_p1
    summary_bits = [f"{n_p0} P0", f"{n_p1} P1"]
    if n_p2:
        summary_bits.append(f"{n_p2} P2")
    summary = (
        f'<div class="dc-oq-summary">{" · ".join(summary_bits)}</div>'
    )
    rows: List[str] = []
    prev_priority: Optional[str] = None
    for q in qs:
        tone = (
            "negative" if q.priority == "P0"
            else "warning" if q.priority == "P1"
            else "neutral"
        )
        # Subtle divider where the list steps down from P0s.
        break_cls = (
            " dc-oq-row--break"
            if prev_priority is not None and q.priority != prev_priority
            else ""
        )
        prev_priority = q.priority
        rows.append(
            f'<div class="dc-oq-row{break_cls}">'
            f'{_chip(q.priority, tone)}'
            f'<span>{html.escape(q.question)}</span>'
            f'<span class="dc-oq-row__owner">{html.escape(q.owner)}</span>'
            '</div>'
        )
    return ck_panel(
        lead_in
        + '<p class="ck-section-body">'
        'Every P0/P1 item that remains OPEN or BLOCKED. This list '
        'is what the IC Packet "Open Questions" section prints — '
        'close the loop on each before the memo ships.</p>'
        f'{summary}{"".join(rows)}',
        title=f"Open questions for IC ({len(qs)})",
    )


def _flat_checklist_table(state: DealChecklistState) -> str:
    """Sortable/filterable/exportable table of every item — the
    partner-facing question leads; the internal item_id demotes to a
    faint mono trailing column."""
    headers = [
        "Phase", "Category", "Question", "Priority", "Status",
        "Owner", "Item ID",
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
        rows.append([
            str(it.phase),
            html.escape(it.category.value.replace("_", " ")),
            html.escape(it.question),
            _priority_chip(it.priority),
            _status_chip(s.status),
            html.escape(it.default_owner.value),
            f'<span class="dc-itemid">{html.escape(it.item_id)}</span>',
        ])
        sort_keys.append([
            it.phase, it.category.value, it.question,
            priority_rank[it.priority],
            status_rank[s.status],
            it.default_owner.value,
            it.item_id,
        ])
    table = sortable_table(
        headers, rows, name="diligence_checklist", sort_keys=sort_keys,
        table_class="cad-table cad-table-sticky",
    )
    # Scroll container keeps the sticky header pinned while 40 rows
    # scroll beneath it.
    return f'<div class="dc-flat-scroll">{table}</div>'


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
    tone = {"DONE": P["positive"], "IN_PROGRESS": P["warning"],
            "OPEN": P["text_faint"], "BLOCKED": P["negative"]}
    order = ["DONE", "IN_PROGRESS", "OPEN", "BLOCKED"]
    legend_cls = {"DONE": "s-done", "IN_PROGRESS": "s-wip",
                  "OPEN": "s-open", "BLOCKED": "s-blocked"}
    row_h, pad_l, pad_r = 24, 170, 86
    pw = width - pad_l - pad_r
    rows = list(cats.items())
    h = len(rows) * row_h + 6
    parts = [f'<svg viewBox="0 0 {width} {h}" '
             'preserveAspectRatio="xMidYMid meet" class="dc-catsvg" '
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
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'fill="{P["text_dim"]}">'
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
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'fill="{P["text_dim"]}">'
            f'{done}/{len(items)}</text>')
    parts.append('</svg>')
    legend = "".join(
        '<span class="dc-legend__key">'
        f'<span class="dc-legend__swatch {legend_cls[s]}"></span>'
        f'{s.replace("_", " ").title()}</span>'
        for s in order)
    return ("".join(parts)
            + f'<div class="dc-legend">{legend}</div>')


def render_diligence_checklist_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    manual_done = _parse_id_set(qs, "mark_done")
    manual_blocked = _parse_id_set(qs, "mark_blocked")
    manual_in_progress = _parse_id_set(qs, "mark_in_progress")
    overridden = manual_done | manual_blocked | manual_in_progress

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
        _phase_section(phase, by_phase[phase], qs, overridden)
        for phase in sorted(by_phase.keys())
    )

    # Auditable IC go/no-go gate — derived purely from item statuses,
    # so it can never disagree with the checklist below it.
    gate = compute_ic_readiness(state)
    _payload = state.to_dict()
    _payload["ic_readiness_gate"] = gate.to_dict()

    # Wrap the KPI strip + gate + open-questions in an
    # export_json_panel so the partner can download the state
    # (incl. the gate) as JSON.
    hero_and_oq = export_json_panel(
        _kpi_strip(state)
        + _ic_readiness_section(gate)
        + _open_questions_block(state, empty=empty),
        payload=_payload,
        name="diligence_checklist_state",
    )

    chart_svg = _category_progress_svg(state)
    chart_html = (
        ck_panel(chart_svg, title="Progress by category",
                 anchor_id="dc-chart")
        if chart_svg else ""
    )

    # Sticky right-rail TOC — labels mirror the section content:
    # coverage + gate hero, the at-a-glance category chart, the
    # phase-grouped roster, and the flat all-items table.
    toc_sections = [{"id": "dc-hero", "title": "Coverage & IC gate"}]
    if chart_html:
        toc_sections.append(
            {"id": "dc-chart", "title": "Progress by category"})
    toc_sections.extend([
        {"id": "dc-phases", "title": "Items by phase"},
        {"id": "dc-flat", "title": "All items"},
    ])
    toc = ck_sticky_toc(toc_sections)

    body = (
        _scoped_styles()
        + '<div class="dc-wrap">'
        + _masthead(state, empty=empty)
        + '<div class="ck-toc-layout">'
        + toc
        + '<div class="ck-toc-content">'
        + f'<section id="dc-hero">{hero_and_oq}</section>'
        + chart_html
        + '<section id="dc-phases">'
        + ck_section_header("Items by phase", eyebrow="PHASES")
        + '<p class="dc-section-note">Each evidence link opens the '
          'analytic that closes its item; the [?] on a phase header '
          'explains what belongs in that phase.</p>'
        + phase_html
        + '</section>'
        + '<section id="dc-flat">'
        + ck_panel(
            _flat_checklist_table(state),
            title="Every item · export for the IC packet",
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
        # ck_page_actions adds Copy share link + Back-to-top
        # affordances. Idempotent JS guards.
        + ck_page_actions()
    )
    return chartis_shell(
        body, "RCM Diligence — Checklist",
        active_nav="/diligence/checklist",
        subtitle="Coverage + IC readiness · URL-encoded state",
    )

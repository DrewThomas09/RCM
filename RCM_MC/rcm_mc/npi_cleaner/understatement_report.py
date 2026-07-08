"""Claims-understatement scorecard — the print-ready one-pager.

Renders a :class:`understatement.Result` as a self-contained HTML page in the
same idiom as :mod:`.exec_report` (inline styles, no app shell, no JS), plus a
plain-text version for the CLI. Organized per growth lever — VOLUME, PRICE,
SCALE — each showing the detected understatement signals, the MODELED corrected
estimate with its low/base/high band, the method + assumption behind it, and
the diligence asks where the data can't support a gross-up.

Honesty is on the page: every corrected figure carries a MODELED (or OBSERVED)
badge and a basis label, and no "true" number is printed without its lever +
assumption. Every dynamic string is ``html.escape``-d.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from . import understatement as _u

_LEVER_TITLE = {
    _u.LEVER_VOLUME: "Volume / demographics",
    _u.LEVER_PRICE: "Price / reimbursement",
    _u.LEVER_SCALE: "Scale / consolidation",
}
_LEVER_BLURB = {
    _u.LEVER_VOLUME: "How many encounters — and whether claims miss the "
                     "denied, self-pay, capitated and recent-period volume.",
    _u.LEVER_PRICE: "The realized rate per encounter — hidden behind billed-vs-"
                    "paid, contractual adjustments and un-summed secondary pay.",
    _u.LEVER_SCALE: "One owner's true size — fragmented across many NPIs/TINs "
                    "with no parent field in the claim.",
}
_STATUS_BADGE = {
    _u.STATUS_DETECTED: ("sev-warning", "understatement signal"),
    _u.STATUS_CLEAN: ("sev-info", "captured"),
    _u.STATUS_NOT_DETECTABLE: ("sev-critical", "not detectable — ask"),
}

_CSS = """
body{font-family:Georgia,'Times New Roman',serif;color:#1a2332;margin:40px auto;
     max-width:860px;padding:0 24px;line-height:1.45}
h1{font-size:26px;margin:0 0 2px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;
   border-bottom:2px solid #155752;padding-bottom:4px;margin:30px 0 6px}
.small{color:#5b6770;font-size:12.5px}
.blurb{color:#5b6770;font-size:13px;margin:2px 0 10px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
   color:#5b6770;border-bottom:1px solid #d2ddd7;padding:4px 8px}
td{border-bottom:1px solid #eceff1;padding:5px 8px;vertical-align:top}
.num{text-align:right;font-variant-numeric:tabular-nums}
.sev-critical{color:#b5321e;font-weight:700}
.sev-warning{color:#b8732a;font-weight:700}
.sev-info{color:#5b6770}
.badge{display:inline-block;font-size:10.5px;text-transform:uppercase;
   letter-spacing:.04em;padding:1px 6px;border-radius:3px;font-weight:700}
.badge-modeled{background:#faf3ea;color:#b8732a;border:1px solid #e5cfa8}
.badge-observed{background:#eaf4ef;color:#0a8a5f;border:1px solid #b6ddc9}
.est{background:#f7f5f0;border-left:4px solid #155752;padding:8px 12px;
     margin:8px 0}
.est .band{font-size:20px;font-variant-numeric:tabular-nums}
.method{color:#5b6770;font-size:12px;margin-top:3px}
.ask{border-left:3px solid #b8732a;background:#faf7f2;padding:4px 10px;
     margin:4px 0;font-size:12.5px}
@media print{body{margin:10mm auto}}
"""


def _esc(v: object) -> str:
    return _html.escape(str(v if v is not None else ""))


def _money(v: Optional[float]) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _count(v: Optional[float]) -> str:
    try:
        return f"{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return "—"


def _est_line(g: "_u.GrossUp") -> str:
    """Render the low/base/high band for a gross-up in its basis unit."""
    is_money = "$" in (g.basis or "")
    fmt = _money if is_money else _count
    if g.base is None:
        return ""
    lo = fmt(g.low) if g.low is not None else fmt(g.base)
    hi = fmt(g.high) if g.high is not None else fmt(g.base)
    return (f"<span class='band'>{_esc(fmt(g.base))}</span> "
            f"<span class='small'>(band {_esc(lo)} – {_esc(hi)})</span>")


def _grossup_block(g: "_u.GrossUp") -> str:
    badge = ("badge-observed", "OBSERVED") if g.label == "OBSERVED" \
        else ("badge-modeled", "MODELED")
    parts: List[str] = ["<div class='est'>"]
    parts.append(
        f"<span class='badge {badge[0]}'>{_esc(badge[1])}</span> "
        f"<strong>{_esc(g.title)}</strong> "
        f"<span class='small'>· basis: {_esc(g.basis)}</span><br>")
    if g.computable:
        if g.observed is not None:
            unit_fmt = _money if "$" in (g.basis or "") else _count
            parts.append(
                f"<span class='small'>observed "
                f"{_esc(unit_fmt(g.observed))} → corrected </span>")
        parts.append(_est_line(g))
        parts.append(f"<div class='method'>Method: {_esc(g.method)}</div>")
        parts.append(f"<div class='method'>Assumption: "
                     f"{_esc(g.assumption)}</div>")
        # Volume component breakdown, if any.
        comps = [c for c in (g.components or []) if "uplift_base" in c]
        if comps:
            parts.append("<table><tr><th>Add-back</th><th>Method</th>"
                         "<th>Assumption</th><th class='num'>Uplift</th></tr>")
            for c in comps:
                parts.append(
                    f"<tr><td>{_esc(c.get('label'))}</td>"
                    f"<td class='small'>{_esc(c.get('method'))}</td>"
                    f"<td class='small'>{_esc(c.get('assumption'))}</td>"
                    f"<td class='num'>{float(c.get('uplift_base') or 0)*100:.1f}%"
                    "</td></tr>")
            parts.append("</table>")
        # Owner roll-up breakdown, if any (scale OBSERVED view).
        owner_comps = [c for c in (g.components or []) if "owner" in c]
        if owner_comps:
            parts.append("<table><tr><th>Owner</th><th class='num'>Lines</th>"
                         "<th class='num'>Charges</th></tr>")
            for c in owner_comps:
                parts.append(
                    f"<tr><td>{_esc(c.get('owner'))}</td>"
                    f"<td class='num'>{_count(c.get('lines'))}</td>"
                    f"<td class='num'>{_money(c.get('charges'))}</td></tr>")
            parts.append("</table>")
    else:
        parts.append("<span class='sev-critical small'>NOT COMPUTABLE from "
                     "this extract.</span>")
    if g.note:
        parts.append(f"<div class='method'>{_esc(g.note)}</div>")
    if g.diligence:
        parts.append(f"<div class='ask'>Diligence request: "
                     f"{_esc(g.diligence)}</div>")
    parts.append("</div>")
    return "".join(parts)


def _findings_table(findings: List["_u.Finding"]) -> str:
    if not findings:
        return ""
    parts = ["<table><tr><th>Cause</th><th>Status</th>"
             "<th>What the file shows</th></tr>"]
    for f in findings:
        cls, label = _STATUS_BADGE.get(f.status, ("sev-info", f.status))
        parts.append(
            f"<tr><td><strong>{_esc(f.name)}</strong></td>"
            f"<td class='{cls}'>{_esc(label)}</td>"
            f"<td class='small'>{_esc(f.summary)}</td></tr>")
    parts.append("</table>")
    return "".join(parts)


def build_report(result: "_u.Result", file_name: str, generated: str) -> str:
    """Render the understatement scorecard as a standalone HTML one-pager.

    ``generated`` is an ISO timestamp supplied by the caller (keeps this module
    pure). Every dynamic value is escaped; every corrected figure is badged
    MODELED/OBSERVED with a basis label."""
    A = result.assumptions
    parts: List[str] = [f"<style>{_CSS}</style>"]
    parts.append("<h1>Claims-understatement scorecard</h1>")
    parts.append(
        f"<div class='small'>{_esc(file_name)} · generated "
        f"{_esc(generated)} · {int(result.n_rows):,} claim lines · "
        "PE&nbsp;Desk claims cleaner</div>")
    parts.append(
        "<p class='blurb'>Claims systematically <strong>understate</strong> a "
        "target on all three growth levers. Below, per lever: the detected "
        "signals, a <span class='badge badge-modeled'>MODELED</span> corrected "
        "estimate with its band and assumption, and the diligence asks where "
        "the data can't support a gross-up. Nothing here is presented as an "
        "observed “true” number.</p>")

    # Assumptions banner — the knobs every gross-up rests on.
    parts.append(
        "<div class='est'><strong>Assumptions</strong> "
        "<span class='small'>(diligence conventions, not measured facts; each "
        "drives the estimate beside it)</span><br><span class='small'>"
        f"denial rate {A.denial_rate:.1%} · self-pay share {A.self_pay_share:.1%}"
        f" · COB uplift {A.cob_uplift:.1%} · run-out completion "
        f"{A.runout_completion:.0%} · band ±{A.band_rel:.0%}</span></div>")

    # Detected columns — what the analyzer keyed on.
    cm = result.columns or {}
    present = [(k, v) for k, v in cm.items() if v]
    missing = [k for k, v in cm.items() if not v]
    parts.append("<h2>Detected columns</h2>")
    if present:
        parts.append("<p class='small'>Using: "
                     + " · ".join(f"{_esc(k)}=<strong>{_esc(v)}</strong>"
                                  for k, v in present) + "</p>")
    if missing:
        parts.append("<p class='small'>Absent (drives diligence asks): "
                     + ", ".join(_esc(k) for k in missing) + "</p>")

    # Per-lever sections.
    for lever in _u.LEVERS:
        parts.append(f"<h2>{_esc(_LEVER_TITLE[lever])}</h2>")
        parts.append(f"<div class='blurb'>{_esc(_LEVER_BLURB[lever])}</div>")
        parts.append(_findings_table(result.findings_for_lever(lever)))
        for key, g in result.grossups.items():
            if g.lever == lever:
                parts.append(_grossup_block(g))

    # Consolidated diligence request list.
    reqs = result.diligence_requests or []
    if reqs:
        parts.append("<h2>Diligence requests (what to ask the target for)</h2>")
        # De-dup while preserving order.
        seen = set()
        for r in reqs:
            if r in seen:
                continue
            seen.add(r)
            parts.append(f"<div class='ask'>{_esc(r)}</div>")

    for w in (result.warnings or []):
        parts.append(f"<p class='sev-critical small'>{_esc(w)}</p>")

    parts.append(
        "<p class='small' style='margin-top:26px'>Every corrected figure is "
        "MODELED from the stated assumption (or OBSERVED where it is exact "
        "arithmetic on real rows) and shown with a band — never as a measured "
        "“true” number. Where the data can't support a gross-up, the "
        "output is a diligence request, not a guess. Deterministic, offline; "
        "no model, no sampling, no network.</p>")
    return "".join(parts)


def render_text(result: "_u.Result", file_name: str = "claims") -> str:
    """A plain-text scorecard for the CLI / terminal."""
    A = result.assumptions
    out: List[str] = []
    out.append(f"CLAIMS-UNDERSTATEMENT SCORECARD — {file_name}")
    out.append(f"{result.n_rows:,} claim lines analyzed")
    out.append(
        f"assumptions: denial {A.denial_rate:.1%} · self-pay "
        f"{A.self_pay_share:.1%} · COB uplift {A.cob_uplift:.1%} · run-out "
        f"completion {A.runout_completion:.0%} · band +/-{A.band_rel:.0%}")
    out.append("")
    for lever in _u.LEVERS:
        out.append(f"== {_LEVER_TITLE[lever].upper()} ==")
        for f in result.findings_for_lever(lever):
            _, label = _STATUS_BADGE.get(f.status, ("", f.status))
            out.append(f"  [{label:>22}] {f.name}")
            out.append(f"       {f.summary}")
        for key, g in result.grossups.items():
            if g.lever != lever:
                continue
            if g.computable and g.base is not None:
                is_money = "$" in (g.basis or "")
                if is_money:
                    b = f"${g.base:,.2f}"
                    lo = f"${(g.low if g.low is not None else g.base):,.2f}"
                    hi = f"${(g.high if g.high is not None else g.base):,.2f}"
                else:
                    b = f"{int(round(g.base)):,}"
                    lo = f"{int(round(g.low if g.low is not None else g.base)):,}"
                    hi = f"{int(round(g.high if g.high is not None else g.base)):,}"
                out.append(f"  >> [{g.label}] {g.title}")
                out.append(f"       {b} (band {lo} - {hi}); basis {g.basis}")
                out.append(f"       method: {g.method}")
                out.append(f"       assumption: {g.assumption}")
            else:
                out.append(f"  >> [{g.label}] {g.title}: NOT COMPUTABLE")
                if g.diligence:
                    out.append(f"       ask: {g.diligence}")
        out.append("")
    reqs = result.diligence_requests or []
    if reqs:
        out.append("DILIGENCE REQUESTS:")
        seen = set()
        for r in reqs:
            if r not in seen:
                seen.add(r)
                out.append(f"  - {r}")
    return "\n".join(out)

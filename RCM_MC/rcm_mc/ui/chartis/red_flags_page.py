"""Per-deal Red Flags — /deal/<id>/red-flags.

Focused "what's wrong with this deal" surface. Renders only the
heuristic hits and reasonableness violations — no narrative, no
stress grid, no investability composite. Partners click this when
they want the 30-second "should I care?" read without scrolling the
full partner review.

Data source: same partner_review(packet) invocation the partner-review
page uses — the server loads the review once in
_build_partner_review_context() and hands it to both renderers.
"""
from __future__ import annotations

import html as _html
from typing import Any, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import render_page_explainer
from ._sanity import REGISTRY as _METRIC_REGISTRY, render_number


_SEV_COLORS = {
    "CRITICAL": P["critical"],
    "HIGH": P["negative"],
    "MEDIUM": P["warning"],
    "LOW": P["text_dim"],
}

_VERDICT_COLORS = {
    "IN_BAND": P["positive"],
    "STRETCH": P["warning"],
    "OUT_OF_BAND": P["negative"],
    "IMPLAUSIBLE": P["critical"],
    "UNKNOWN": P["text_faint"],
}

_CLAUDE_STATUS_COLORS = {
    "confirmed": P["positive"],
    "needs_attention": P["warning"],
    "insufficient_support": P["negative"],
    "not_configured": P["text_faint"],
    "call_failed": P["negative"],
    "failed": P["negative"],
}


def _header_links(deal_id: str) -> str:
    did = _html.escape(deal_id)
    return (
        f'<div style="margin-bottom:14px;">'
        f'<a href="/deal/{did}" style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);font-size:10px;letter-spacing:0.10em;">'
        f'&larr; DEAL DASHBOARD</a>'
        f'<span style="color:{P["text_faint"]};padding:0 8px;">·</span>'
        f'<a href="/deal/{did}/partner-review" style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);font-size:10px;letter-spacing:0.10em;">'
        f'FULL PARTNER REVIEW →</a>'
        f'<span style="color:{P["text_faint"]};padding:0 8px;">·</span>'
        f'<a href="/analysis/{did}" style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);font-size:10px;letter-spacing:0.10em;">'
        f'ANALYSIS WORKBENCH →</a>'
        f'</div>'
    )


def _error_banner(deal_id: str, error: str, missing: List[str]) -> str:
    missing_list = ", ".join(_html.escape(m) for m in missing) if missing else "—"
    return (
        f'<div style="background:rgba(239,68,68,0.10);border:1px solid {P["negative"]};'
        f'border-radius:3px;padding:12px 14px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["negative"]};letter-spacing:0.12em;margin-bottom:4px;">'
        f'RED FLAG SCAN UNAVAILABLE</div>'
        f'<div style="color:{P["text"]};font-size:12px;margin-bottom:6px;">'
        f'{_html.escape(error)}</div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;">'
        f'Missing: <span style="font-family:var(--ck-mono);color:{P["warning"]};">'
        f'{missing_list}</span></div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:6px;">'
        f'Open the <a href="/analysis/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};">analysis workbench</a> to build a '
        f'richer packet.</div></div>'
    )


def _severity_banner(review: Any) -> str:
    sev = review.severity_counts()
    bands = review.band_counts()
    crit = sev.get("CRITICAL", 0)
    high = sev.get("HIGH", 0)
    medium = sev.get("MEDIUM", 0)
    low = sev.get("LOW", 0)
    oob = bands.get("OUT_OF_BAND", 0)
    impl = bands.get("IMPLAUSIBLE", 0)
    stretch = bands.get("STRETCH", 0)
    has_critical = review.has_critical_flag()

    col = P["critical"] if crit else (
        P["negative"] if high or impl else (
            P["warning"] if medium or oob or stretch else P["positive"]
        )
    )
    headline = (
        f"{crit} critical · {high} high · {impl} implausible · {oob} out-of-band"
        if (crit or high or impl or oob)
        else f"{medium} medium · {low} low · {stretch} stretch · no hard stops"
    )
    verdict = (
        "HARD STOP" if crit else (
            "SERIOUS CONCERNS" if (high or impl) else (
                "WATCHLIST" if (medium or oob or stretch) else "CLEAN SCAN"
            )
        )
    )
    return (
        f'<div style="background:{P["panel"]};border-left:4px solid {col};'
        f'border:1px solid {P["border"]};border-left-width:4px;'
        f'border-radius:3px;padding:14px 18px;margin-bottom:14px;">'
        f'<div style="display:flex;gap:12px;align-items:baseline;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">RED FLAG VERDICT</span>'
        f'<span style="font-family:var(--ck-mono);font-size:16px;font-weight:700;'
        f'letter-spacing:0.08em;color:{col};">{_html.escape(verdict)}</span>'
        + (
            f'<span style="font-family:var(--ck-mono);font-size:10px;'
            f'color:{P["critical"]};letter-spacing:0.10em;margin-left:10px;">'
            f'✕ has_critical_flag</span>' if has_critical else ""
        )
        + f'</div>'
        f'<div style="color:{P["text_dim"]};font-size:12px;margin-top:6px;'
        f'font-family:var(--ck-mono);">{_html.escape(headline)}</div>'
        f'</div>'
    )


def _kpi_strip(review: Any) -> str:
    sev = review.severity_counts()
    bands = review.band_counts()
    total_hits = len(review.heuristic_hits or [])
    total_bands = len(review.reasonableness_checks or [])

    violations = (
        bands.get("OUT_OF_BAND", 0)
        + bands.get("IMPLAUSIBLE", 0)
    )
    tiles = (
        ck_kpi_block("Critical", str(sev.get("CRITICAL", 0)), "hard-stop flags")
        + ck_kpi_block("High", str(sev.get("HIGH", 0)), "serious concerns")
        + ck_kpi_block("Medium+Low", str(sev.get("MEDIUM", 0) + sev.get("LOW", 0)),
                        "watchlist items")
        + ck_kpi_block("Band Violations", str(violations),
                        f"of {total_bands} checks")
        + ck_kpi_block("Total Hits", str(total_hits), "across all severities")
    )
    return f'<div class="ck-kpi-grid">{tiles}</div>'


def _healthcare_signal_card(review: Any) -> str:
    checks = getattr(review, "healthcare_checks", None) or {}
    sev = checks.get("severity_counts") or {}
    total_hits = int(checks.get("total_hits") or 0)
    summary = str(checks.get("summary") or "No supplemental healthcare checks available.")
    focus_areas = list(checks.get("focus_areas") or [])
    focus = ", ".join(
        f'{str(area.get("category", "OTHER"))}:{int(area.get("count", 0))}'
        for area in focus_areas[:4]
    ) or "none"
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">Supplemental Healthcare Signals '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'HCX · {total_hits}</span></div>'
        f'<div style="padding:12px 14px;">'
        f'<div class="ck-kpi-grid" style="margin-bottom:10px;">'
        f'{ck_kpi_block("Supplemental Hits", str(total_hits), "additive")}'
        f'{ck_kpi_block("Critical", str(sev.get("CRITICAL", 0)), "extra checks")}'
        f'{ck_kpi_block("High", str(sev.get("HIGH", 0)), "extra checks")}'
        f'{ck_kpi_block("Medium", str(sev.get("MEDIUM", 0)), "extra checks")}'
        f'</div>'
        f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;'
        f'margin:0 0 8px;">{_html.escape(summary)}</p>'
        f'<div style="font-family:var(--ck-mono);font-size:10px;color:{P["text_faint"]};">'
        f'Focus areas: {_html.escape(focus)}</div>'
        f'</div></div>'
    )


def _claude_status_card(review: Any) -> str:
    claude = getattr(review, "claude_review", None) or {}
    status = str(claude.get("status") or "not_configured")
    color = _CLAUDE_STATUS_COLORS.get(status, P["text_faint"])
    status_label = status.replace("_", " ").upper()
    summary = str(claude.get("summary") or "Claude review not available.")
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">Claude Look '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'CLD</span></div>'
        f'<div style="padding:12px 14px;">'
        f'<span class="ck-sig" style="color:{color};border:1px solid {color};'
        f'background:rgba(255,255,255,0.02);">{_html.escape(status_label)}</span>'
        f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;'
        f'margin:10px 0 0;">{_html.escape(summary)}</p>'
        f'</div></div>'
    )


def _hit_row(hit: Any) -> str:
    sev = str(getattr(hit, "severity", "LOW"))
    col = _SEV_COLORS.get(sev, P["text_dim"])
    title = _html.escape(str(getattr(hit, "title", "—")))
    finding = _html.escape(str(getattr(hit, "finding", "") or ""))
    voice = _html.escape(str(getattr(hit, "partner_voice", "") or ""))
    category = _html.escape(str(getattr(hit, "category", "") or ""))
    remediation = _html.escape(str(getattr(hit, "remediation", "") or ""))
    trigger = getattr(hit, "trigger_metrics", None) or []
    values = getattr(hit, "trigger_values", None) or {}

    trig_pairs = []
    if isinstance(values, dict):
        for m in trigger:
            v = values.get(m)
            if v is None:
                trig_pairs.append(_html.escape(str(m)))
            else:
                trig_pairs.append(
                    f'{_html.escape(str(m))}='
                    f'{_html.escape(str(v)[:40])}'
                )
    else:
        trig_pairs = [_html.escape(str(t)) for t in trigger]
    trig_html = ", ".join(trig_pairs) if trig_pairs else "—"

    return (
        f'<div style="padding:12px 14px;border-bottom:1px solid {P["border_dim"]};">'
        f'<div style="display:flex;gap:10px;align-items:baseline;">'
        f'<span class="ck-sig" style="color:{col};border:1px solid {col};'
        f'background:rgba(255,255,255,0.02);">{_html.escape(sev)}</span>'
        f'<span style="font-size:13px;font-weight:600;color:{P["text"]};">{title}</span>'
        + (
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:auto;">'
            f'{category}</span>' if category else ""
        )
        + f'</div>'
        + (
            f'<div style="color:{P["text_dim"]};font-size:12px;margin-top:6px;'
            f'line-height:1.55;">{finding}</div>' if finding else ""
        )
        + (
            f'<div style="color:{P["text"]};font-size:11.5px;margin-top:6px;'
            f'font-style:italic;line-height:1.55;">'
            f'<span style="color:{P["text_faint"]};font-style:normal;">'
            f'Partner: </span>&ldquo;{voice}&rdquo;</div>' if voice else ""
        )
        + (
            f'<div style="color:{P["warning"]};font-size:11.5px;margin-top:6px;'
            f'line-height:1.55;">'
            f'<span style="color:{P["text_faint"]};">Remediation: </span>'
            f'{remediation}</div>' if remediation else ""
        )
        + (
            f'<div style="font-family:var(--ck-mono);font-size:10px;'
            f'color:{P["text_faint"]};margin-top:6px;">'
            f'Triggered by: {trig_html}</div>' if trig_pairs else ""
        )
        + f'</div>'
    )


def _hits_section(review: Any, *, sev_filter: List[str], title: str, code: str) -> str:
    hits = [h for h in (review.heuristic_hits or [])
            if str(getattr(h, "severity", "")) in sev_filter]
    if not hits:
        inner = (
            f'<div style="padding:14px;color:{P["text_faint"]};font-size:11px;'
            f'font-style:italic;">No {title.lower()} on this deal.</div>'
        )
    else:
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        hits_sorted = sorted(hits, key=lambda h: order.get(str(h.severity), 9))
        inner = "".join(_hit_row(h) for h in hits_sorted)
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">{_html.escape(title)} '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'{code} · {len(hits)}</span></div>'
        f'{inner}</div>'
    )


def _violations_section(review: Any) -> str:
    violations = [
        b for b in (review.reasonableness_checks or [])
        if str(getattr(b, "verdict", "")) in ("OUT_OF_BAND", "IMPLAUSIBLE")
    ]
    if not violations:
        inner = (
            f'<div style="padding:14px;color:{P["text_faint"]};font-size:11px;'
            f'font-style:italic;">No band violations — the numbers sit inside '
            f'the reasonableness envelope.</div>'
        )
        return (
            f'<div class="ck-panel"><div class="ck-panel-title">Reasonableness '
            f'Violations <span style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
            f'BND · 0</span></div>{inner}</div>'
        )
    rows = []
    for b in violations:
        verdict = str(getattr(b, "verdict", "UNKNOWN"))
        col = _VERDICT_COLORS.get(verdict, P["text_faint"])
        metric_raw = str(getattr(b, "metric", "—"))
        metric = _html.escape(metric_raw)
        observed = getattr(b, "observed", None)
        if metric_raw in _METRIC_REGISTRY:
            obs_str = render_number(observed, metric_raw)
        else:
            obs_str = (
                f'{observed:.2f}' if isinstance(observed, (int, float))
                else _html.escape(str(observed) if observed is not None else "—")
            )
        band = getattr(b, "band", None)
        if isinstance(band, (list, tuple)) and len(band) == 2:
            try:
                band_str = f'[{float(band[0]):.2f}, {float(band[1]):.2f}]'
            except (TypeError, ValueError):
                band_str = "—"
        elif band is not None:
            band_str = _html.escape(str(band))
        else:
            band_str = "—"
        note = _html.escape(str(getattr(b, "partner_note", "") or ""))
        rationale = _html.escape(str(getattr(b, "rationale", "") or ""))
        rows.append(
            f'<tr>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-size:11px;">{metric}</td>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-size:11px;font-variant-numeric:tabular-nums;text-align:right;">'
            f'{obs_str}</td>'
            f'<td style="font-family:var(--ck-mono);color:{P["text_dim"]};'
            f'font-size:10.5px;text-align:right;">{band_str}</td>'
            f'<td><span class="ck-sig" style="color:{col};'
            f'border:1px solid {col};background:rgba(255,255,255,0.02);">'
            f'{_html.escape(verdict)}</span></td>'
            f'<td style="color:{P["text_dim"]};font-size:11px;'
            f'white-space:normal;line-height:1.45;">{note or rationale or "—"}</td>'
            f'</tr>'
        )
    table = (
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr><th>Metric</th><th class="num">Observed</th>'
        f'<th class="num">Band</th><th>Verdict</th><th>Partner Note</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )
    return (
        f'<div class="ck-panel"><div class="ck-panel-title">Reasonableness '
        f'Violations <span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'BND · {len(violations)}</span></div>{table}</div>'
    )


def render_red_flags(
    packet: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    """Render a focused red-flag page. ``packet`` is the PartnerReview."""
    label = deal_name or deal_id
    if error:
        body = _header_links(deal_id) + _error_banner(
            deal_id, error, missing_fields or []
        )
        return chartis_shell(
            body,
            title=f"Red Flags · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"Red-flag scan unavailable for {label}",
        )

    review = packet
    crit_section = _hits_section(
        review, sev_filter=["CRITICAL"],
        title="Critical Flags", code="CRT",
    )
    high_section = _hits_section(
        review, sev_filter=["HIGH"],
        title="High-Severity Findings", code="HI",
    )
    other_section = _hits_section(
        review, sev_filter=["MEDIUM", "LOW"],
        title="Watchlist (Medium + Low)", code="WL",
    )
    violations = _violations_section(review)

    explainer = render_page_explainer(
        what=(
            "Focused subset of the Partner Review — only the heuristic "
            "hits (red flags) and reasonableness band violations for "
            "this deal. Narrative, archetype, and analytics panels "
            "appear on the full Partner Review page."
        ),
        scale=(
            "Severity: CRITICAL = hard stop; HIGH = serious concerns; "
            "MEDIUM = watchlist; LOW = minor. Band verdicts: "
            "OUT_OF_BAND or IMPLAUSIBLE for metrics outside the "
            "partner-comfort envelope."
        ),
        use=(
            "Read this first for a 30-second triage. If the verdict "
            "banner says HARD STOP, stop before investing more "
            "diligence time; otherwise use the remediation line on "
            "each hit to scope the diligence ask."
        ),
        source=(
            "pe_intelligence/heuristics.py (SEV_CRITICAL / HIGH / "
            "MEDIUM / LOW); reasonableness.py (VERDICT_OUT_OF_BAND, "
            "VERDICT_IMPLAUSIBLE)."
        ),
        page_key="deal-red-flags",
    )

    body = (
        explainer
        + _header_links(deal_id)
        + _severity_banner(review)
        + _kpi_strip(review)
        + ck_section_header(
            "ADDITIONAL SIGNALS",
            "supplemental healthcare checks and Claude confirmation",
        )
        + _healthcare_signal_card(review)
        + _claude_status_card(review)
        + ck_section_header(
            "FINDINGS", "sorted by severity",
            count=len(review.heuristic_hits or []),
        )
        + crit_section
        + high_section
        + other_section
        + ck_section_header(
            "BAND CHECKS",
            "only metrics outside the reasonableness envelope",
        )
        + violations
    )

    subtitle = (
        f"{label} · {len(review.heuristic_hits or [])} hits · "
        f"{review.generated_at:%Y-%m-%d %H:%M UTC}"
    )
    return chartis_shell(
        body,
        title=f"Red Flags · {label}",
        active_nav="/pe-intelligence",
        subtitle=subtitle,
    )

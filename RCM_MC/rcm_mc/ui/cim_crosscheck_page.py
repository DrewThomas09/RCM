"""CIM Cross-Check page — /diligence/cim-crosscheck.

The consultant-facing surface for rcm_mc.diligence.cim_crosscheck: enter
management's CIM claims, get the independent HCRIS estimates, variance flags,
drill links, and the variance-memo / CSV exports. Claims are ENTERED;
estimates are ACTUAL public data — both badged, with the scope printed on
the table so nobody mistakes a statewide base for a metro one.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional
from urllib.parse import urlencode

from ..data.hcris import _get_latest_per_ccn
from ..diligence.cim_crosscheck import (
    CLAIM_TYPES, CrossCheckResult, run_crosscheck, variance_memo,
)
from ._chartis_kit import (
    chartis_shell, ck_basis_badge, ck_kpi_block, ck_page_title, ck_panel,
    ck_source_link,
)

_FLAG_STYLE = {
    "green": ("var(--sc-positive,#0a8a5f)", "WITHIN 10%"),
    "yellow": ("var(--sc-warning,#b8732a)", "10–25% OFF"),
    "red": ("var(--sc-negative,#b5321e)", ">25% OFF"),
    "unverifiable": ("var(--sc-text-dim,#6a7480)", "UNVERIFIABLE"),
}

_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC","PR",
]


def _f_or_none(qs: Dict[str, List[str]], key: str) -> Optional[float]:
    raw = (qs.get(key) or [""])[0].strip().replace(",", "").replace("$", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _fmt(value: Optional[float], unit: str) -> str:
    if value is None or value != value:
        return "—"
    if unit == "$":
        return f"${value:,.0f}"
    if unit == "%":
        return f"{value:,.1f}%"
    return f"{value:,.0f}"


def _flag_chip(flag: str) -> str:
    color, label = _FLAG_STYLE.get(flag, _FLAG_STYLE["unverifiable"])
    return (f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:0.06em;font-weight:700;padding:2px 7px;'
            f'border:1px solid {color};color:{color};border-radius:2px;'
            f'white-space:nowrap;">{label}</span>')


def _claims_from_qs(qs: Dict[str, List[str]]) -> Dict[str, float]:
    claims: Dict[str, float] = {}
    for ct in CLAIM_TYPES:
        v = _f_or_none(qs, f"c_{ct['key']}")
        if v is not None:
            claims[ct["key"]] = v
    return claims


def render_cim_crosscheck(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    state = (qs.get("state") or [""])[0].strip().upper()[:2]
    if state and state not in _STATES:
        state = ""
    ccn = (qs.get("ccn") or [""])[0].strip()[:10]
    min_beds = _f_or_none(qs, "min_beds")
    max_beds = _f_or_none(qs, "max_beds")
    claims = _claims_from_qs(qs)
    fmt = (qs.get("format") or [""])[0]

    result: Optional[CrossCheckResult] = None
    if state and claims:
        result = run_crosscheck(
            _get_latest_per_ccn(), state=state, claims=claims, ccn=ccn,
            min_beds=min_beds, max_beds=max_beds)

    # ── exports (memo txt / csv) — same computation, different envelope ──
    if result is not None and fmt == "memo":
        return variance_memo(result)
    if result is not None and fmt == "csv":
        out = ["claim,label,cim_claim,independent_estimate,n,variance_pct,flag,source"]
        for r in result.rows:
            est = "" if r.estimate.value is None else f"{r.estimate.value:.2f}"
            var = "" if r.variance is None else f"{r.variance*100:.1f}"
            out.append(
                f'{r.claim_key},"{r.label}",{r.claim_value:.2f},{est},'
                f'{r.estimate.n},{var},{r.flag},"{r.estimate.source}"')
        return "\n".join(out)

    # ── claim entry form ──
    _inp = ('style="padding:5px 8px;border:1px solid var(--sc-rule,#c9c1ac);'
            'font-variant-numeric:tabular-nums;width:170px;"')
    _lbl = 'style="font-family:var(--sc-mono);font-size:10px;display:block;"'
    state_opts = '<option value="">— state —</option>' + "".join(
        f'<option value="{s}"{" selected" if s == state else ""}>{s}</option>'
        for s in _STATES)
    claim_fields = ""
    for ct in CLAIM_TYPES:
        cur = (qs.get(f"c_{ct['key']}") or [""])[0]
        claim_fields += (
            f'<label {_lbl}>{_html.escape(ct["label"])}'
            f'<input name="c_{ct["key"]}" value="{_html.escape(cur)}" '
            f'placeholder="{_html.escape(ct["hint"])}" {_inp}></label>')
    form = ck_panel(
        '<p class="ck-section-body" style="margin:0 0 10px;font-size:11px;'
        'color:var(--sc-text-dim,#6a7480);">Claims are management\'s numbers '
        f'as the CIM states them{ck_basis_badge("entered")} — the engine '
        'computes the independent public side below.</p>'
        '<form method="get" action="/diligence/cim-crosscheck" '
        'style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));'
        'gap:12px;align-items:end;">'
        f'<label {_lbl}>Market (state) *<select name="state" {_inp}>{state_opts}</select></label>'
        f'<label {_lbl}>Target CCN (for revenue check)'
        f'<input name="ccn" value="{_html.escape(ccn)}" placeholder="e.g. 450358" {_inp}></label>'
        f'<label {_lbl}>Min beds<input name="min_beds" '
        f'value="{int(min_beds) if min_beds is not None else ""}" {_inp}></label>'
        f'<label {_lbl}>Max beds<input name="max_beds" '
        f'value="{int(max_beds) if max_beds is not None else ""}" {_inp}></label>'
        + claim_fields +
        '<button type="submit" class="tsw-vert" style="cursor:pointer;'
        'padding:7px 14px;">Run cross-check</button>'
        '</form>'
        '<p class="ck-section-body" style="font-size:11px;margin:10px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Enter only the claims the CIM '
        'actually makes — blank fields are skipped. $ in dollars, % in '
        'percent points.</p>',
        title="Management's claims",
    )

    # ── results ──
    if result is None:
        results_html = ck_panel(
            '<p class="ck-section-body">Pick a state and enter at least one '
            'CIM claim. The engine computes the independent public-data side '
            'from the HCRIS universe and flags the variance — green ≤10%, '
            'yellow ≤25%, red >25%, UNVERIFIABLE when the public side is a '
            'gap (which is a finding, not a pass).</p>',
            title="How this works")
    else:
        c = result.flag_counts()
        export_qs = {k: v[0] for k, v in qs.items() if v and v[0]}
        memo_qs = urlencode({**export_qs, "format": "memo"})
        csv_qs = urlencode({**export_qs, "format": "csv"})
        kpis = (
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("Scope", _html.escape(result.scope_label))
            + ck_kpi_block("Green", f'{c["green"]}')
            + ck_kpi_block("Yellow", f'{c["yellow"]}')
            + ck_kpi_block("Red / unverifiable", f'{c["red"]} / {c["unverifiable"]}')
            + '</div>')
        rows_html = ""
        for r in result.rows:
            est = r.estimate
            drill = (f' <a class="ck-link" href="{_html.escape(est.drill_url)}" '
                     f'style="font-size:10px;">inspect rows →</a>'
                     if est.drill_url else "")
            var_s = "—" if r.variance is None else f"{r.variance*100:+,.1f}%"
            rows_html += (
                '<tr>'
                f'<td style="padding:6px 8px;">{_html.escape(r.label)}'
                f'<div style="font-size:10px;color:var(--sc-text-dim,#6a7480);">'
                f'{_html.escape(est.method)}</div></td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;'
                f'font-variant-numeric:tabular-nums;">{_fmt(r.claim_value, est.unit)}'
                f'{ck_basis_badge("entered")}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;'
                f'font-variant-numeric:tabular-nums;">{_fmt(est.value, est.unit)}'
                f'{ck_basis_badge("actual") if est.value is not None else ""}'
                f'<div style="font-size:10px;color:var(--sc-text-dim,#6a7480);">'
                f'n={est.n} · {ck_source_link("CMS HCRIS")}{drill}</div></td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;'
                f'font-variant-numeric:tabular-nums;">{var_s}</td>'
                f'<td style="padding:6px 8px;">{_flag_chip(r.flag)}</td>'
                '</tr>')
        results_html = kpis + ck_panel(
            '<div style="overflow-x:auto;"><table class="ck-data-table" '
            'style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
            '<th style="text-align:left;padding:6px 8px;">Claim</th>'
            '<th style="text-align:right;padding:6px 8px;">CIM says</th>'
            '<th style="text-align:right;padding:6px 8px;">Independent estimate</th>'
            '<th style="text-align:right;padding:6px 8px;">Variance</th>'
            '<th style="text-align:left;padding:6px 8px;">Flag</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
            f'<p class="ck-section-body" style="font-size:11px;margin:10px 0 0;">'
            f'<a class="ck-link" href="/diligence/cim-crosscheck?{memo_qs}">'
            f'Variance memo (txt) ↓</a> · '
            f'<a class="ck-link" href="/diligence/cim-crosscheck?{csv_qs}">CSV ↓</a>'
            ' — memo includes a suggested expert-call question per claim.</p>',
            title=f"Variance vs public data — {_html.escape(result.scope_label)}")

    body = (
        ck_page_title(
            "CIM Cross-Check",
            eyebrow="DILIGENCE · VARIANCE ENGINE",
            meta="Pressure-test management's market claims against CMS HCRIS "
                 "— the week-one CDD motion, automated.")
        + form + results_html
    )
    return chartis_shell(body, "CIM Cross-Check",
                         active_nav="/diligence/cim-crosscheck",
                         subtitle="Claims vs independent public estimates")

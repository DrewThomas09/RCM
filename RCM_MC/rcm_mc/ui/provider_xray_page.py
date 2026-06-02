"""CMS Provider X-Ray — the diligence scanner page (/diligence/xray).

Search a CCN / provider id / name; PEdesk resolves the vertical, benchmarks
the provider against peers, and renders a transparent diligence report. The
page is a thin editorial-dossier view over the resolver (provider_xray) and
the benchmarked report (provider_xray_report) — it computes nothing itself
and fabricates nothing. Honest resolver / not-found / empty states throughout.
"""
from __future__ import annotations

import html as _html
from typing import List, Optional

from ..data.provider_xray import (
    Ambiguous, ProviderMatch, resolve_provider_xray, provider_match_by_ccn,
)
from ..data.provider_xray_report import (
    ProviderXrayReport, build_provider_xray_report,
)


def _e(s) -> str:
    return _html.escape("" if s is None else str(s))


_XRAY_CSS = """
.ck-xr-hero{margin:0 0 var(--sc-s-5);}
.ck-xr-form{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;
background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);padding:16px 18px;}
.ck-xr-field{display:flex;flex-direction:column;gap:5px;}
.ck-xr-field label{font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ck-xr-field input{font-family:var(--sc-serif);font-size:15px;padding:8px 12px;
border:1px solid var(--sc-rule,#c9c1ac);background:#fff;min-width:280px;}
.ck-xr-field input.st{min-width:90px;text-transform:uppercase;}
.ck-xr-run{font-family:var(--sc-mono);font-size:11px;font-weight:600;letter-spacing:.1em;
text-transform:uppercase;background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);
border:0;padding:10px 18px;cursor:pointer;}
.ck-xr-resolver{width:100%;border-collapse:collapse;margin-top:14px;}
.ck-xr-resolver th,.ck-xr-resolver td{text-align:left;padding:8px 12px;
border-bottom:1px solid var(--sc-rule,#c9c1ac);font-size:13px;}
.ck-xr-resolver th{font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ck-xr-vbadge{display:inline-block;font-family:var(--sc-mono);font-size:9.5px;
letter-spacing:.08em;text-transform:uppercase;background:var(--sc-bone,#f3eddb);
border:1px solid var(--sc-rule,#c9c1ac);padding:2px 8px;}
.ck-xr-identity{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
border-bottom:2px solid var(--sc-ink,#15202b);padding-bottom:12px;margin-bottom:18px;}
.ck-xr-name{font-family:var(--sc-serif);font-size:30px;color:var(--sc-navy,#15202b);margin:0;}
.ck-xr-meta{font-family:var(--sc-mono);font-size:11px;color:var(--sc-text-dim,#6a7480);
letter-spacing:.04em;}
.ck-xr-signals{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:12px;margin:0 0 var(--sc-s-5);}
.ck-xr-sig{background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);
border-left:4px solid var(--sc-rule);padding:12px 14px;}
.ck-xr-sig.green{border-left-color:var(--sc-positive,#0a8a5f);}
.ck-xr-sig.amber{border-left-color:var(--sc-warning,#b8842e);}
.ck-xr-sig.red{border-left-color:var(--sc-negative,#b5321e);}
.ck-xr-sig.gray{border-left-color:var(--sc-text-faint,#8b94a0);}
.ck-xr-sig-name{font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);display:flex;
justify-content:space-between;align-items:center;}
.ck-xr-sev{font-weight:700;}
.ck-xr-sev.green{color:var(--sc-positive,#0a8a5f);}
.ck-xr-sev.amber{color:var(--sc-warning,#b8842e);}
.ck-xr-sev.red{color:var(--sc-negative,#b5321e);}
.ck-xr-sev.gray{color:var(--sc-text-faint,#8b94a0);}
.ck-xr-sig-detail{font-family:var(--sc-serif);font-size:13.5px;line-height:1.45;
color:var(--sc-text,#2a3a4a);margin-top:6px;}
.ck-xr-bench{width:100%;border-collapse:collapse;margin:8px 0 var(--sc-s-5);}
.ck-xr-bench th,.ck-xr-bench td{padding:8px 10px;border-bottom:1px solid var(--sc-rule,#c9c1ac);
font-size:13px;text-align:right;}
.ck-xr-bench th:first-child,.ck-xr-bench td:first-child{text-align:left;}
.ck-xr-bench th{font-family:var(--sc-mono);font-size:10px;letter-spacing:.08em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ck-xr-bench .num{font-family:var(--sc-mono);font-variant-numeric:tabular-nums;}
.ck-xr-q{font-family:var(--sc-serif);font-size:14.5px;line-height:1.5;margin:5px 0;
padding-left:18px;position:relative;}
.ck-xr-q::before{content:"›";position:absolute;left:0;color:var(--sc-teal,#155752);}
.ck-xr-empty{font-family:var(--sc-serif);font-style:italic;color:var(--sc-text-dim,#6a7480);}
.ck-xr-prov{font-family:var(--sc-mono);font-size:10.5px;color:var(--sc-text-dim,#6a7480);
margin-top:6px;}
.ck-xr-coefbar{position:relative;height:10px;background:var(--sc-bone,#f3eddb);
border:1px solid var(--sc-rule,#c9c1ac);min-width:80px;}
.ck-xr-coef{position:absolute;top:0;bottom:0;left:0;}
.ck-xr-coef.pos{background:var(--sc-positive,#0a8a5f);}
.ck-xr-coef.neg{background:var(--sc-negative,#b5321e);}
/* Landing two-column layout — mirrors the HCRIS X-Ray landing (identify panel
   on the left, "what you'll get" sample preview on the right). */
.ck-xr-landing-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;
margin-top:var(--sc-s-4,12px);}
@media (max-width:820px){.ck-xr-landing-grid{grid-template-columns:1fr;}}
.ck-xr-sec{font-family:var(--sc-mono);font-size:11px;font-weight:700;
letter-spacing:.1em;text-transform:uppercase;color:var(--sc-teal,#155752);
border-bottom:1px solid var(--sc-rule,#d6cfc0);padding-bottom:6px;margin-bottom:14px;}
"""


def _search_form(q: str = "", state: str = "") -> str:
    return (
        '<form class="ck-xr-form" method="get" action="/diligence/xray" role="search">'
        '<div class="ck-xr-field"><label for="xr-q">CCN, provider ID, or name</label>'
        f'<input id="xr-q" type="search" name="q" value="{_e(q)}" '
        'placeholder="e.g. 015009 or Burns Nursing Home" autofocus></div>'
        '<div class="ck-xr-field"><label for="xr-st">State</label>'
        f'<input id="xr-st" class="st" type="text" name="state" value="{_e(state)}" '
        'maxlength="2" placeholder="TX"></div>'
        '<button class="ck-xr-run" type="submit">Run X-Ray</button>'
        '</form>'
    )


def _resolver_table(matches: List[ProviderMatch]) -> str:
    rows = "".join(
        '<tr>'
        f'<td><span class="ck-xr-vbadge">{_e(m.vertical_label)}</span></td>'
        f'<td><a class="ck-link" href="{_e(m.xray_url)}"><strong>{_e(m.name)}</strong></a></td>'
        f'<td class="num">{_e(m.ccn or m.provider_id)}</td>'
        f'<td>{_e(m.state)}</td>'
        f'<td>{_e(m.county or m.city or "—")}</td>'
        f'<td>{("<a class=ck-link href=" + chr(34) + _e(m.profile_url) + chr(34) + ">profile</a>") if m.profile_url else "—"}</td>'
        '</tr>'
        for m in matches
    )
    return (
        '<table class="ck-xr-resolver"><thead><tr>'
        '<th>Vertical</th><th>Provider</th><th>CCN</th><th>State</th>'
        '<th>Locality</th><th>Native</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def render_xray_landing(q: str = "", state: str = "",
                        resolver: Optional[List[ProviderMatch]] = None,
                        not_found: bool = False) -> str:
    from ._chartis_kit import chartis_shell, ck_panel, ck_editorial_head
    # Mirror the HCRIS X-Ray landing: editorial head + lede, a sourced line,
    # and a two-column "identify the provider" / "what you'll get" layout — so
    # the two sibling diligence scanners share one visual grammar.
    head = ck_editorial_head(
        eyebrow="CMS-NATIVE PROVIDER X-RAY",
        title="CMS X-Ray",
        meta="EVERY LIVE CMS VERTICAL · BENCHMARKED VS PEERS",
        lede_italic_phrase="One provider, x-rayed against its peers.",
        lede_body=(
            "Enter a CCN, provider ID, or facility name. PEdesk resolves the "
            "provider across every live CMS vertical (Hospital, SNF, Home "
            "Health, Hospice, Dialysis, IRF, LTCH), benchmarks it against "
            "peers, and turns the public data into a transparent diligence "
            "read — not an investment recommendation."
        ),
    )
    source_line = (
        '<p class="ck-xr-prov">SOURCE: CMS public provider datasets — '
        'refreshed from cms.gov. Area-level public data; descriptive, not a '
        'recommendation.</p>'
    )
    # Left — the search/identify panel.
    left = (
        '<div><div class="ck-xr-sec">&#9312; Identify the provider</div>'
        + _search_form(q, state)
        + '</div>'
    )
    # Right — a "what you'll get" sample of the X-Ray output (parallels HCRIS
    # X-Ray's SAMPLE OUTPUT). Illustrative; a real run renders live CMS values.
    sample = (
        '<div class="ck-xr-sig green"><div class="ck-xr-sig-name">Peer benchmarks'
        '<span class="ck-xr-sev green">SAMPLE</span></div>'
        '<div class="ck-xr-sig-detail">Quality, outcomes, and cost metrics vs '
        'national / state / locality / ownership peers — each with a percentile '
        'and a z-score, suppressed when fewer than 5 peers report.</div></div>'
        '<div class="ck-xr-sig amber"><div class="ck-xr-sig-name">Risk indicators'
        '<span class="ck-xr-sev amber">SAMPLE</span></div>'
        '<div class="ck-xr-sig-detail">Transparent, rule-based leading signals '
        '(staffing, deficiencies, ownership churn) — flagged for review, never a '
        'forecast.</div></div>'
        '<div class="ck-xr-sig gray"><div class="ck-xr-sig-name">Diligence questions'
        '<span class="ck-xr-sev gray">SAMPLE</span></div>'
        '<div class="ck-xr-sig-detail">A tailored question set + evidence and '
        'limitations, ready to carry into the diligence workflow.</div></div>'
    )
    right = (
        '<div><div class="ck-xr-sec">What you&rsquo;ll get</div>'
        f'<div class="ck-xr-signals">{sample}</div>'
        '<p class="ck-xr-prov">Illustrative — a real run renders live CMS '
        'values for the matched provider and its peer cohort.</p></div>'
    )
    body = head + source_line + f'<div class="ck-xr-landing-grid">{left}{right}</div>'
    if not_found:
        body += ck_panel(
            '<p class="ck-xr-empty">No provider matched '
            f'"<strong>{_e(q)}</strong>"'
            + (f' in {_e(state)}' if state else "")
            + '. Check the CCN (leading zeroes matter), try the full facility '
            'name, or drop the state filter.</p>',
            title="No match")
    elif resolver:
        body += ck_panel(
            f'<p>{len(resolver)} providers match — pick one to open its X-Ray. '
            '(A hospital-based IRF/LTCH unit shares its CCN with the HCRIS '
            'hospital record, so a CCN can resolve to more than one vertical.)</p>'
            + _resolver_table(resolver),
            title="Multiple matches")
    return chartis_shell(body, "CMS X-Ray", active_nav="/diligence",
                         extra_css=_XRAY_CSS)


_PEER_ORDER = ("national", "state", "locality", "ownership")
_PEER_HEAD = {"national": "National", "state": "State", "locality": "Locality",
              "ownership": "Ownership"}


def _pct_cell(p) -> str:
    if p is None:
        return '<td class="num">—</td>'
    if p.suppressed or p.percentile is None:
        return f'<td class="num" title="{_e(p.label)}: n={p.peer_n} (&lt;5, suppressed)">n/a</td>'
    return (f'<td class="num" title="{_e(p.label)} · n={p.peer_n}">'
            f'{p.percentile}</td>')


def _bench_table(report: ProviderXrayReport) -> str:
    bms = report.benchmarks
    if not bms:
        # Fall back to the single-percentile evidence view (or empty).
        ev = report.evidence
        if ev is None:
            return ('<p class="ck-xr-empty">Peer benchmarks are not computed '
                    'for this vertical here — open the native profile.</p>')
        rows = "".join(
            f'<tr><td>{_e(c.label)}</td>'
            f'<td class="num">{(str(c.raw_value)+c.suffix) if c.raw_value is not None else "—"}</td>'
            f'<td class="num">{c.peer_percentile if c.peer_percentile is not None else "—"}</td></tr>'
            for c in ev.components)
        return ('<table class="ck-xr-bench"><thead><tr><th>Metric</th>'
                '<th>Value</th><th>State %ile</th></tr></thead>'
                f'<tbody>{rows}</tbody></table>')
    rows = ""
    for b in bms:
        by_set = {p.peer_set: p for p in b.percentiles}
        raw = f'{b.value:g}{b.suffix}' if b.value is not None else "—"
        z = f'{b.z_state:+.2f}' if b.z_state is not None else "—"
        cells = "".join(_pct_cell(by_set.get(ps)) for ps in _PEER_ORDER)
        rows += (
            f'<tr><td>{_e(b.label)}</td>'
            f'<td class="num">{raw}</td>'
            f'{cells}'
            f'<td class="num">{z}</td></tr>'
        )
    heads = "".join(f'<th>{_PEER_HEAD[ps]}<br>%ile</th>' for ps in _PEER_ORDER)
    return (
        '<table class="ck-xr-bench"><thead><tr>'
        '<th>Metric (higher = better)</th><th>Value</th>'
        f'{heads}<th>z<br>(state)</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="ck-xr-prov">Percentile is peer deviation within each peer '
        'set (higher = better); "n/a" = fewer than 5 rated peers (suppressed). '
        'z-score is vs state peers (n&ge;5, sd&gt;0). Not a recommendation.</p>'
    )


def _risk_section(report: ProviderXrayReport) -> str:
    """Transparent rule-based risk indicators — explicitly NOT forecasts."""
    if not report.risk_indicators:
        return ""
    cards = "".join(
        f'<div class="ck-xr-sig {_risk_sev(r.level)}">'
        f'<div class="ck-xr-sig-name">{_e(r.name)}'
        f'<span class="ck-xr-sev {_risk_sev(r.level)}">{_e(r.level).upper()}</span></div>'
        f'<div class="ck-xr-sig-detail">{_e(r.basis)}</div></div>'
        for r in report.risk_indicators
    )
    return (
        f'<div class="ck-xr-signals">{cards}</div>'
        f'<p class="ck-xr-prov">{_e(report.risk_disclaimer)}</p>'
    )


def _risk_sev(level: str) -> str:
    # Map indicator levels to the signal-card color classes.
    return {"elevated": "red", "moderate": "amber", "low": "green",
            "insufficient": "gray"}.get(level, "gray")


def _g(v, suffix: str = "") -> str:
    return f"{v:g}{suffix}" if v is not None else "—"


# Flag → signal-card color. All six vertical headlines are higher-is-better,
# so a positive residual (above expectation) is encouraging (green); below is
# amber = worth a question; never red, since this is descriptive, not a verdict.
_EXP_SEV = {"above": "green", "below": "amber", "typical": "gray", "n/a": "gray"}


def _expectation_section(sector_id: str, ccn: str):
    """Both descriptive expected-vs-actual layers as paired signal cards.
    Returns "" when the vertical isn't one of the six cross-sector verticals."""
    from ..data.cross_sector import SECTOR_BY_ID
    from ..data.sector_expected_value import expected_vs_actual
    if sector_id not in SECTOR_BY_ID:
        return None  # hospital / unknown — no cross-sector model
    e = expected_vs_actual(sector_id, ccn)
    if e is None:
        return None
    suf = SECTOR_BY_ID[sector_id].headline_suffix

    mr = e.model_residual
    if mr.expected is not None:
        sev = _EXP_SEV[mr.flag]
        word = {"above": "ABOVE", "below": "BELOW", "typical": "IN LINE"}.get(mr.flag, "—")
        model_detail = (
            f'Actual {_g(mr.actual, suf)} vs model expectation '
            f'{_g(mr.expected, suf)} (residual {mr.residual:+g}{_e(suf)}, '
            f'{mr.std_residual:+.1f} SD). This provider performs <strong>{word}</strong> '
            f'what its other public measures predict.')
    else:
        sev, model_detail = "gray", (
            'Not enough complete measures for this provider to score against '
            'the model (no value is imputed).')

    pb = e.profile
    if pb.expected is not None:
        psev = _EXP_SEV[pb.flag]
        pword = {"above": "ABOVE", "below": "BELOW", "typical": "IN LINE"}.get(pb.flag, "—")
        prof_detail = (
            f'Actual {_g(pb.actual, suf)} vs cohort mean {_g(pb.expected, suf)} '
            f'(residual {pb.residual:+g}{_e(suf)}) across {pb.cohort_n} '
            f'structural peers [{_e(pb.cohort_label)}]. <strong>{pword}</strong> '
            'its structural cohort.')
    else:
        psev, pword = "gray", "—"
        prof_detail = (f'Structural cohort [{_e(pb.cohort_label)}] has only '
                       f'{pb.cohort_n} rated peer(s) — expectation suppressed.')

    cards = (
        f'<div class="ck-xr-sig {sev}"><div class="ck-xr-sig-name">'
        f'vs. its own measure profile<span class="ck-xr-sev {sev}">'
        f'{_e(mr.flag).upper()}</span></div>'
        f'<div class="ck-xr-sig-detail">{model_detail}</div></div>'
        f'<div class="ck-xr-sig {psev}"><div class="ck-xr-sig-name">'
        f'vs. structural peers<span class="ck-xr-sev {psev}">'
        f'{_e(pb.flag).upper()}</span></div>'
        f'<div class="ck-xr-sig-detail">{prof_detail}</div></div>')
    prov = ('<p class="ck-xr-prov">Descriptive expected-vs-actual over public '
            'CMS data — association, not causation; not a forecast or '
            'recommendation. A large gap flags a provider to investigate.</p>')
    return f'<div class="ck-xr-signals">{cards}</div>{prov}'


def _model_section(sector_id: str):
    """"What moves the headline" — the in-sample OLS coefficients with bars."""
    from ..data.cross_sector import SECTOR_BY_ID
    from ..data.sector_expected_value import _fit_measure_model
    if sector_id not in SECTOR_BY_ID:
        return None
    fit = _fit_measure_model(sector_id)
    if fit is None:
        return None
    model, _ = fit
    top = model.predictors[:8]
    mx = max((abs(c.std_coef) for c in top), default=1.0) or 1.0
    rows = ""
    for c in top:
        pos = c.std_coef >= 0
        w = round(100 * abs(c.std_coef) / mx)
        bar = (f'<div class="ck-xr-coefbar"><span class="ck-xr-coef {"pos" if pos else "neg"}" '
               f'style="width:{w}%"></span></div>')
        rows += (f'<tr><td>{_e(c.label)}</td>'
                 f'<td class="num">{c.std_coef:+.2f}</td>'
                 f'<td>{bar}</td></tr>')
    note = ("model expectation vs. the headline is a CMS composite — its "
            "sub-ratings are excluded so the fit isn't mechanical"
            if model.composite_target else "headline is a reported outcome")
    return (
        f'<p>In-sample ordinary-least-squares fit · n={model.n_fit:,} · '
        f'R&sup2;={model.r2:g}. Standardized coefficients show which public '
        f'measures move with <strong>{_e(model.target_label)}</strong> '
        f'({note}):</p>'
        '<table class="ck-xr-bench"><thead><tr><th>Measure</th>'
        '<th>Std&nbsp;coef</th><th>Direction &amp; magnitude</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="ck-xr-prov">Association, not causation. Standardized so '
        'coefficients are comparable; sign shows co-movement with the headline, '
        'not a causal effect.</p>')


def _correlations_section(sector_id: str):
    """Top pairwise measure associations for the vertical."""
    from ..data.cross_sector import SECTOR_BY_ID
    from ..data.sector_correlations import top_correlations
    if sector_id not in SECTOR_BY_ID:
        return None
    pairs = top_correlations(sector_id, k=8)
    if not pairs:
        return None
    rows = "".join(
        f'<tr><td>{_e(p.label_a)}</td><td>{_e(p.label_b)}</td>'
        f'<td class="num">{p.pearson_r:+.2f}</td>'
        f'<td class="num">{(f"{p.spearman_rho:+.2f}") if p.spearman_rho is not None else "—"}</td>'
        f'<td class="num">{p.n:,}</td></tr>'
        for p in pairs)
    return (
        '<table class="ck-xr-bench"><thead><tr><th>Measure A</th>'
        '<th>Measure B</th><th>Pearson&nbsp;r</th><th>Spearman&nbsp;&rho;</th>'
        '<th>n</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="ck-xr-prov">Pairwise-complete association across providers '
        'reporting both measures — NOT causation. Both measures may track an '
        'unmeasured factor (case mix, geography, size).</p>')


def render_xray_report(report: ProviderXrayReport) -> str:
    from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
    from . import xray_kit as k

    def _section(tag: str, body: str, ribsub: str = "") -> str:
        # HCRIS-X-Ray-style section: navy ribbon header + paper card body, so
        # CMS X-Ray shares the same visual grammar (not a generic sector table).
        return k.xr_ribbon(tag, ribsub) + f'<div class="xr-card">{body}</div>'

    m = report.match
    title = ck_page_title(
        "CMS X-Ray", eyebrow=f"DILIGENCE · {_e(m.vertical_label).upper()}",
        meta=f"CCN {_e(m.ccn or m.provider_id)}")
    loc = " · ".join(b for b in (m.city, m.county, m.state) if b)
    identity = (
        '<div class="ck-xr-identity">'
        f'<h2 class="ck-xr-name">{_e(m.name)}</h2>'
        f'<span class="ck-xr-meta">{_e(m.vertical_label)} &middot; CCN '
        f'{_e(m.ccn or m.provider_id)} &middot; {_e(loc)}</span>'
        '</div>'
        f'<p class="ck-xr-prov">Source: {_e(m.source_dataset)}'
        + (f' &middot; <a class="ck-link" href="{_e(m.profile_url)}">open native profile →</a>'
           if m.profile_url else "")
        + ' &middot; <a class="ck-link" href="/diligence/xray">new X-Ray</a></p>'
    )
    # Signal strip
    sig_cards = "".join(
        f'<div class="ck-xr-sig {s.severity}">'
        f'<div class="ck-xr-sig-name">{_e(s.name)}'
        f'<span class="ck-xr-sev {s.severity}">{s.severity.upper()}</span></div>'
        f'<div class="ck-xr-sig-detail">{_e(s.detail)}</div></div>'
        for s in report.signals
    )
    signals = f'<div class="ck-xr-signals">{sig_cards}</div>'

    bench = _section("Peer benchmarks", _bench_table(report),
                     ribsub="NATIONAL · STATE · LOCALITY · OWNERSHIP")

    # Market context (when available)
    mk = report.market
    if mk is not None:
        own = ", ".join(f"{_e(lbl)} ({n})" for lbl, n in mk.ownership_mix[:4])
        market = _section(
            f"Market context · {_e(mk.state)}",
            f'<p>{mk.provider_count} {_e(mk.sector_label)} providers in '
            f'{_e(mk.state)} across {mk.locality_count} localities · state '
            f'median {mk.headline_median}{_e(mk.headline_suffix)} '
            f'(national {mk.national_median}{_e(mk.headline_suffix)}) · state '
            f'percentile {mk.state_percentile if mk.state_percentile is not None else "—"}.</p>'
            f'<p class="ck-xr-prov">Ownership mix: {own or "—"} · ownership-count '
            f'HHI {mk.ownership_hhi if mk.ownership_hhi is not None else "—"} · '
            f'locality HHI {mk.locality_hhi if mk.locality_hhi is not None else "—"} '
            '(composition proxy, not market share).</p>')
    else:
        market = ""

    questions = _section(
        "Suggested diligence questions",
        "".join(f'<p class="ck-xr-q">{_e(q)}</p>' for q in report.suggested_questions))

    caveats = _section(
        "Evidence & limitations",
        "".join(f'<p class="ck-xr-q">{_e(c)}</p>' for c in report.caveats))

    note = (f'<p class="ck-xr-empty">{_e(report.note)}</p>') if report.note else ""

    risk = (_section("Risk indicators · leading signals, not forecasts",
                     _risk_section(report))
            if report.risk_indicators else "")

    # Analytic depth (six cross-sector verticals only): how this provider
    # performs vs. expectation, what moves the headline, and how the vertical's
    # measures co-move. Each returns None for Hospital/unknown → omitted.
    sid = m.vertical
    exp = _expectation_section(sid, m.ccn or m.provider_id)
    expectation = _section("Performs vs. expectation · descriptive, not a forecast",
                           exp, ribsub="MEASURE MODEL · STRUCTURAL PEERS") if exp else ""
    mdl = _model_section(sid)
    model_sec = _section("What moves the headline · standardized OLS", mdl,
                         ribsub="ASSOCIATION, NOT CAUSATION") if mdl else ""
    corr = _correlations_section(sid)
    corr_sec = _section("Measure correlations · how the vertical co-moves", corr,
                        ribsub="PAIRWISE · ASSOCIATION ONLY") if corr else ""

    source_purpose = ck_source_purpose(
        purpose=f"Scan this {_e(m.vertical_label)} provider's CMS public profile for diligence signals vs its peer cohort.",
        universe="cms",
        source=_e(m.source_dataset),
        next_action="Take the signals into the diligence question set",
        next_href="#xr-questions",
    )
    questions = questions.replace('<div class="xr-card">',
                                  '<div class="xr-card" id="xr-questions">', 1)
    body = ('<div class="xr">' + title + source_purpose + identity + signals + note + bench
            + expectation + model_sec + corr_sec
            + risk + market + questions + caveats + '</div>')
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, f"CMS X-Ray · {_e(m.name)}",
                         active_nav="/diligence", extra_css=_XRAY_CSS + k.XRAY_CSS)


def render_provider_xray(qs: dict) -> str:
    """Route entry: dispatch search vs report from query params.

    ``qs`` maps str→str (first value already unwrapped by the route handler).
    """
    ccn = (qs.get("ccn") or "").strip()
    vertical = (qs.get("vertical") or "").strip()
    q = (qs.get("q") or "").strip()
    state = (qs.get("state") or "").strip()

    # Direct report when ccn+vertical are given (resolver-row / profile link).
    if ccn and vertical:
        m = provider_match_by_ccn(ccn, vertical)
        if m is not None:
            return render_xray_report(build_provider_xray_report(m))
        return render_xray_landing(q=ccn, state=state, not_found=True)

    if not q and not ccn:
        return render_xray_landing()

    result = resolve_provider_xray(q or ccn, state or None)
    if result is None:
        return render_xray_landing(q=q or ccn, state=state, not_found=True)
    if isinstance(result, Ambiguous):
        return render_xray_landing(q=q or ccn, state=state, resolver=result.matches)
    return render_xray_report(build_provider_xray_report(result))

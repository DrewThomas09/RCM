"""IFT sourcing prompts page — Part 1 (``/ift-sourcing``).

The evidence-acquisition companion to the diligence question architecture: the
exact, scope-bounded research prompts that go out to gather the proof, each with
the boundary line that keeps NEMT and 911 out, its prioritized public sources,
the real connector datasets that feed it, and a live link to where the answer
already lives (a sized page + the matching /ift-diligence slide). Every prompt is
copy-pasteable with the boundary prefixed.

Reads :mod:`ift_sourcing`; resolves connector references against the live
:mod:`ift_connectors` estate. Renders through ``chartis_shell`` + ``ck_*``;
degrades to honest notes and never raises.

Public API:
    render_ift_sourcing(qs=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell, ck_next_section, ck_page_actions, ck_page_title, ck_panel,
    ck_section_header, ck_section_intro,
)
from ..market_reports import ift_sourcing as _sp


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "FRAMEWORK": "An analytic framework / diligence prompt, not a figure.",
    "GOV": "A published government source (CMS, MedPAC, OIG, Census, CDC, statute).",
    "ACADEMIC": "A peer-reviewed / analyst source.",
    "INDUSTRY": "An industry / trade source (AHA, AAA, AIMHI).",
    "SOURCED": "Live — a registered dataset in our connector estate.",
    "CONNECTOR": "A registered connector dataset — ingest-ready offline.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
}
_BASIS_CLASS = {"FRAMEWORK": "framework", "GOV": "gov", "ACADEMIC": "academic",
                "INDUSTRY": "industry", "SOURCED": "sourced",
                "CONNECTOR": "connector", "ILLUSTRATIVE": "illustrative"}


def _chip(basis: str) -> str:
    b = (basis or "FRAMEWORK").upper()
    key = b if b in _BASIS_TITLES else "FRAMEWORK"
    return (f'<span class="ifs-chip ifs-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _link_row(pairs: Tuple[Tuple[str, str], ...], *, label: str) -> str:
    if not pairs:
        return ""
    links = "".join(
        f'<a href="{_esc(href)}">{_esc(txt)} &rarr;</a>' for txt, href in pairs)
    return (f'<div class="ifs-answer"><span class="ifs-answer-lab">{_esc(label)}'
            f'</span><div class="ifs-links">{links}</div></div>')


# ── Inline RESEARCH findings — the current answer, pulled live from our sized
#    modules so the page is fully fleshed out (not just prompts to go run). Every
#    builder degrades to "" and never raises. ──────────────────────────────────
def _usd_b(x) -> str:
    try:
        return f"${float(x):,.2f}B"
    except (TypeError, ValueError):
        return "—"


def _num(x) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return "—"


def _find_table(headers, rows) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(v)}</td>" for v in r) + "</tr>" for r in rows)
    return ('<div class="ifs-ftwrap"><table class="ifs-ft"><thead><tr>'
            f'{head}</tr></thead><tbody>{body}</tbody></table></div>')


def _find_wrap(inner: str, *, source: str = "") -> str:
    if not inner:
        return ""
    src = (f'<p class="ifs-ftsrc">Read from: {_esc(source)}</p>' if source else "")
    return ('<div class="ifs-find"><span class="ifs-find-lab">Current research '
            'read — what we can answer now</span>' + inner + src + '</div>')


def _f_denominator() -> str:
    from ..market_reports import ift_analytics as _an
    t = _an.ground_tam()
    if not getattr(t, "available", False):
        return ""
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} <strong>Medicare FFS GROUND</strong> '
        f'ambulance = <strong>{_usd_b(t.medicare_ffs_ground_bn[0])}</strong> across '
        '~11.4M FFS ground transports / ~10,500 ground organizations (2023, '
        'MedPAC). ' + _chip("ILLUSTRATIVE") + ' US ground ambulance runs '
        '~25-30M transports/yr including ~22M 911; <strong>interfacility is '
        '~30-40% of ground DOLLARS</strong> (it over-indexes on spend, not '
        'volume). The all-payer ground market is ~$18-22B.</p>'
        '<div class="ifs-stats">'
        + _stat(_usd_b(t.allpayer_tam_bn_central), "US ground-IFT TAM (central)")
        + _stat(f"{_usd_b(t.medicare_ffs_ground_ift_bn[0])}-"
                f"{_usd_b(t.medicare_ffs_ground_ift_bn[1])}".replace("$", "", 1),
                "Medicare-FFS ground-IFT slice")
        + _stat(f"{t.transports_m[0]:.0f}-{t.transports_m[1]:.0f}M",
                "IFT legs/yr (all-payer, est.)")
        + '</div>')
    return _find_wrap(body, source="ift_analytics.ground_tam (GOV MedPAC anchor + "
                                   "ILLUSTRATIVE build)")


def _f_claims_method() -> str:
    from ..market_reports import ift_analytics as _an
    rvu = getattr(_an, "_AMBULANCE_RVU", ())
    if not rvu:
        return ""
    rows = [(h, lbl, f"{v:.2f}") for h, lbl, v in rvu]
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} The seven base HCPCS + A0425 mileage '
        'carry the RVU ladder below (42 CFR 414.610). ' + _chip("FRAMEWORK")
        + ' Interfacility = <strong>both endpoints in {H, N, E, G, J, D, I}</strong> '
        '(facility origin AND destination). The catch: the public AFS/Part-B PUF '
        'reports aggregate volume &amp; spend <em>by HCPCS</em> but NOT by the '
        '<strong>origin/destination modifier PAIR</strong> — isolating the '
        'interfacility book requires the CMS <strong>Limited Data Set</strong> or '
        'carrier claims, where the two-character modifier (e.g. NH, HN) is '
        'present. That is the exact data ask.</p>'
        + _find_table(("HCPCS", "Service", "RVU"), rows))
    return _find_wrap(body, source="ift_analytics fee-schedule RVUs + "
                                   "origin-modifier definition")


def _f_growth() -> str:
    from ..market_reports import ift_tracking as _tr
    gb = _tr.growth_bridge()
    if not getattr(gb, "available", False):
        return ""
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} Price growth is anchored by the AIF, '
        'which DECELERATES (2.6/2.4/2.0 for CY2024-26) — so the '
        f'~{gb.price_central_pct:.1f}%/yr price lever is carried above the GOV '
        'floor by commercial OON + escalators. ' + _chip("ILLUSTRATIVE")
        + f' Volume grows ~{gb.volume_central_pct:.1f}%/yr on aging + acuity. '
        f'RSNAT prior authorization (2021) is the SERIES BREAK — it removed the '
        'repetitive scheduled-dialysis book, so pre/post trends are not '
        'continuous.</p>'
        '<div class="ifs-stats">'
        + _stat(f"{gb.price_central_pct:.1f}%/yr", "price / reimbursement")
        + _stat(f"{gb.volume_central_pct:.1f}%/yr", "volume / demographics")
        + _stat(f"{gb.market_growth_central_pct:.1f}%/yr", "organic market growth")
        + '</div>')
    return _find_wrap(body, source="ift_tracking.growth_bridge (GOV AIF + "
                                   "ILLUSTRATIVE composites)")


def _f_prevalence() -> str:
    from ..market_reports import ift_clinical_demand as _cd
    try:
        rs = _cd.registry_summary()
        m = _cd.mission_mix()
    except Exception:  # noqa: BLE001
        return ""
    n_cond = rs.get("n_conditions", 0)
    dest = rs.get("destination_supply_national", 0)
    body = (
        f'<p class="ifs-prose">{_chip("SOURCED")} The clinical spine maps '
        f'<strong>{_num(n_cond)}</strong> acute-transfer scenarios to their '
        'ICD-10 / MS-DRG codes and destinations, anchored to '
        f'<strong>{_num(dest)}</strong> real post-acute destinations. The '
        'highest-transfer conditions are the escalation book — STEMI, stroke, '
        'sepsis, and major trauma up-transfers.</p>'
        '<div class="ifs-stats">'
        + _stat(f"{m['cct_sct_share'] * 100:.1f}%", "CCT/SCT tier (alone)")
        + _stat(f"{m['high_acuity_share'] * 100:.1f}%", "high-acuity (excl. behavioral)")
        + _stat(f"{m['high_acuity_incl_behavioral_share'] * 100:.1f}%",
                "high-acuity incl. behavioral")
        + '</div>')
    return _find_wrap(body, source="ift_clinical_demand registry + mission_mix "
                                   "(SOURCED destinations, GOV volumes)")


def _f_ed_transfers() -> str:
    body = (
        f'<p class="ifs-prose">{_chip("ACADEMIC")} The widely-cited '
        '<strong>~1.9M ED-to-acute transfers/yr</strong> traces to '
        '<strong>2009</strong> NHAMCS/NEDS data — it is stale and must be '
        're-pulled to the most recent NEDS year and dated. ' + _chip("SOURCED")
        + ' Our escalation registry already carries the ED-origin up-transfer '
        'scenarios (STEMI to PCI, stroke to thrombectomy, trauma to a trauma '
        'center); the OPEN GAP is the current-vintage national ED-transfer '
        'count.</p>')
    return _find_wrap(body, source="authored GOV/ACADEMIC + ift_clinical_demand "
                                   "ED-origin scenarios (vintage flagged)")


def _f_post_acute() -> str:
    from ..market_reports import ift_clinical_demand as _cd
    try:
        ds = _cd.destination_supply()
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(ds, dict) or not ds.get("by_setting"):
        return ""
    by = ds["by_setting"]
    rows = [(k, _num(v)) for k, v in by.items()]
    body = (
        f'<p class="ifs-prose">{_chip("SOURCED")} The post-acute destination '
        f'universe is <strong>{_num(ds.get("national", 0))}</strong> facilities '
        'nationally (below), from the CMS Care Compare / Provider-of-Services '
        'file. ' + _chip("ILLUSTRATIVE") + ' The stretcher-eligible share that '
        'needs ground IFT is ~7-12% of acute discharges (the f_IFT lever), plus '
        'recurring SNF-origin legs (~2-4 per occupied bed/yr) — the countable '
        'non-emergency discharge engine.</p>'
        + _find_table(("Post-acute setting", "Facilities (SOURCED)"), rows))
    return _find_wrap(body, source="ift_clinical_demand.destination_supply "
                                   "(SOURCED) + ift_analytics f_IFT / lambda levers")


def _f_demographics() -> str:
    from ..market_reports import ift_clinical_demand as _cd
    try:
        rs = _cd.registry_summary()
        gr = _cd.growth_ranked()
    except Exception:  # noqa: BLE001
        return ""
    blended = rs.get("escalation_volume_weighted_cagr")
    lead = ", ".join(c.name for c in gr[:3]) if gr else ""
    blended_txt = (f"{blended:.1f}%/yr" if isinstance(blended, (int, float))
                   else "—")
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} Applying Census age-band CAGRs '
        '(65-74, 75-84, 85+ — the 85+ band grows fastest) to the condition-level '
        'hospitalization volumes, holding incidence constant, yields a '
        f'<strong>volume-weighted blended escalation CAGR of {blended_txt}</strong>. '
        f'The fastest-growing transfer generators: {_esc(lead) if lead else "—"}.</p>'
        '<div class="ifs-stats">'
        + _stat(blended_txt, "blended escalation CAGR (vol-weighted)")
        + _stat(str(len(gr)) if gr else "—", "conditions modeled")
        + '</div>')
    return _find_wrap(body, source="ift_clinical_demand demographic engine "
                                   "(Census CAGRs x GOV condition volumes)")


def _f_throughput() -> str:
    from ..market_reports import ift_analytics as _an
    occ = _an.occupancy_trend()
    read = ""
    if getattr(occ, "available", False) and getattr(occ, "latest_fy", None):
        read = (f'National inpatient occupancy is ~{occ.latest_occupancy * 100:.1f}% '
                f'(FY{occ.latest_fy}, CMS HCRIS) — but the series ends FY{occ.latest_fy}, '
                'so read the rise as a COVID-recovery level normalizing, not an '
                'established trend. ')
    else:
        read = ("National inpatient occupancy (CMS HCRIS) is the throughput proxy; "
                "the panel ends FY2022, so its rise is a COVID-recovery artifact, "
                "not a trend. ")
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} {read}' + _chip("ACADEMIC")
        + ' ED boarding prevalence and duration are rising (Canellas et al., '
        '<em>Annals of Emergency Medicine</em>, 2024), and post-acute discharge '
        'LOS is lengthening (AHA discharge-delay reporting) — both increase '
        'transport demand, both lag by 1-2 years.</p>')
    return _find_wrap(body, source="ift_analytics.occupancy_trend (GOV HCRIS) + "
                                   "authored ED-boarding / LOS evidence")


def _f_spend_index() -> str:
    from ..market_reports import ift_analytics as _an
    rvu = getattr(_an, "_AMBULANCE_RVU", ())
    if not rvu:
        return ""
    by = {h: v for h, lbl, v in rvu}
    sct = by.get("A0434")
    bls = by.get("A0428")
    ratio = (f"{sct / bls:.2f}x" if sct and bls else "—")
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} The RVU ladder proves the '
        'over-index directly: <strong>SCT (A0434) carries RVU '
        f'{sct:.2f}</strong> vs <strong>BLS non-emergency (A0428) '
        f'{bls:.2f}</strong> — a <strong>{ratio}</strong> base-rate gap before '
        'mileage. SCT is <strong>definitionally interfacility</strong> under '
        '42 CFR 414.605. An interfacility book concentrates ALS2/SCT + long '
        'mileage, so it earns materially more per transport than a 911/scene '
        'book at the same volume.</p>')
    return _find_wrap(body, source="ift_analytics fee-schedule RVUs "
                                   "(42 CFR 414.605/.610, GOV)")


def _f_rsnat() -> str:
    body = (
        f'<p class="ifs-prose">{_chip("GOV")} RSNAT prior authorization went '
        '<strong>nationwide in 2021</strong> after the 2014-19 demonstration; it '
        'sharply cut <strong>repetitive scheduled non-emergency (dialysis) '
        'volume and spend</strong> (HHS-OIG / CMS found large reductions and low '
        'approval rates in the demo states). The consequence for sizing: today\'s '
        '"non-emergency" ground ambulance market is <strong>interfacility '
        'discharge and up-transfer work</strong>, not the scheduled-dialysis book '
        'regulators dismantled — which is why our TAM explicitly EXCLUDES '
        'residence-origin recurring dialysis (R→G/J).</p>')
    return _find_wrap(body, source="authored GOV (RSNAT / OIG) + ift_analytics "
                                   "TAM exclusions")


_FINDINGS = {
    "denominator": _f_denominator,
    "claims-method": _f_claims_method,
    "growth": _f_growth,
    "prevalence": _f_prevalence,
    "ed-transfers": _f_ed_transfers,
    "post-acute": _f_post_acute,
    "demographics": _f_demographics,
    "throughput": _f_throughput,
    "spend-index": _f_spend_index,
    "rsnat": _f_rsnat,
}


def _findings_for(slug: str) -> str:
    fn = _FINDINGS.get(slug)
    if not fn:
        return ""
    try:
        return fn() or ""
    except Exception:  # noqa: BLE001 — degrade, never raise
        return ""


def _stat(value: str, label: str) -> str:
    return (f'<div class="ifs-stat"><div class="ifs-stat-v">{_esc(value)}</div>'
            f'<div class="ifs-stat-l">{_esc(label)}</div></div>')


def _connector_chips(keys: Tuple[str, ...], ce) -> str:
    if not (ce and ce.available and keys):
        return ""
    chips: List[str] = []
    for k in keys:
        p = ce.probes_by_key.get(k)
        if p is None:
            continue
        live = getattr(p, "available", False)
        cls = "ifs-cx-live" if live else "ifs-cx-gated"
        status = "LIVE" if live else "INGEST-READY"
        href = "/connector-estate?dataset=" + _esc(getattr(p, "dataset_id", ""))
        chips.append(
            f'<a class="ifs-cx {cls}" href="{href}" '
            f'title="{_esc(getattr(p, "ift_signal", ""))}">'
            f'{_esc(getattr(p, "title", k))} '
            f'<span class="ifs-cx-st">{status}</span></a>')
    if not chips:
        return ""
    return ('<div class="ifs-cxrow"><span class="ifs-cx-lab">Feeds from our '
            'connector estate</span>' + "".join(chips) + '</div>')


# ── Scoped stylesheet + copy-to-clipboard shim ───────────────────────────────
_STYLES = """<style>
.ifs-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;margin:0 2px 2px 0;}
.ifs-chip-framework{background:#ece9f2;color:#463a63;}
.ifs-chip-gov{background:#e7efe9;color:#154e36;}
.ifs-chip-academic{background:#efeae0;color:#6b5426;}
.ifs-chip-industry{background:#eef1f5;color:#31465e;}
.ifs-chip-sourced{background:#e7efe9;color:#154e36;}
.ifs-chip-connector{background:#eef1f5;color:#31465e;border:1px solid #cdd6e2;}
.ifs-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.ifs-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:90ch;margin:0 0 10px;}
.ifs-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);
margin:14px 0 6px;}
.ifs-why{font-family:var(--sc-serif,Georgia,serif);font-size:14px;font-style:italic;
line-height:1.5;color:var(--sc-navy,#0b2341);border-left:3px solid var(--sc-teal,#155752);
padding:6px 0 6px 14px;margin:2px 0 10px;background:rgba(21,87,82,0.035);}
.ifs-boundary{border:1px solid var(--sc-warning,#b8732a);
background:rgba(184,115,42,0.06);border-radius:6px;padding:14px 16px;margin:8px 0 14px;}
.ifs-boundary-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-warning,#b8732a);display:block;margin:0 0 6px;}
.ifs-pre{font-family:var(--sc-mono,Consolas,monospace);font-size:12px;line-height:1.55;
color:var(--sc-text,#1a2332);white-space:pre-wrap;word-break:break-word;margin:0;
padding:10px 12px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-radius:4px;}
.ifs-copy{font-family:var(--sc-mono,Consolas,monospace);font-size:10.5px;
font-weight:600;letter-spacing:.03em;color:var(--sc-teal,#155752);background:#fff;
border:1px solid var(--sc-teal,#155752);border-radius:3px;padding:4px 10px;
cursor:pointer;margin:6px 0 0;}
.ifs-copy:hover{background:var(--sc-teal,#155752);color:#fff;}
.ifs-priority-badge{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:700;letter-spacing:.06em;color:#fff;
background:var(--sc-teal,#155752);padding:2px 7px;border-radius:10px;margin-left:8px;
vertical-align:middle;}
.ifs-runthree{border:1px solid var(--sc-teal,#155752);border-radius:6px;
background:var(--sc-navy,#0b2341);color:#f3efe6;padding:14px 18px;margin:6px 0 16px;}
.ifs-runthree b{color:#fff;}
.ifs-runthree-eyebrow{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#a9c3bd;margin:0 0 6px;}
.ifs-runthree p{font-family:var(--sc-serif,Georgia,serif);font-size:15px;line-height:1.5;
margin:0;}
.ifs-runthree a{color:#a9c3bd;font-weight:700;text-decoration:none;}
.ifs-list{margin:2px 0 8px 18px;font-family:var(--sc-serif,Georgia,serif);
font-size:13px;line-height:1.55;color:var(--sc-text,#2a3340);}
.ifs-list li{margin:0 0 4px;}
.ifs-answer{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin:8px 0 4px;
padding:8px 12px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-left:3px solid var(--sc-teal,#155752);
border-radius:4px;}
.ifs-answer-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);}
.ifs-links{display:flex;flex-wrap:wrap;gap:6px 16px;}
.ifs-links a{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
font-weight:600;color:var(--sc-teal,#155752);text-decoration:none;}
.ifs-links a:hover{text-decoration:underline;}
.ifs-cxrow{margin:8px 0 2px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;}
.ifs-cx-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;font-weight:700;
letter-spacing:.05em;text-transform:uppercase;color:var(--sc-muted,#6b6357);margin-right:4px;}
.ifs-cx{display:inline-block;font-family:var(--sc-sans,Inter,system-ui,sans-serif);
font-size:11px;text-decoration:none;padding:3px 9px;border-radius:13px;
border:1px solid var(--sc-border,#e4dccb);background:#fff;color:var(--sc-text,#1a2332);}
.ifs-cx:hover{border-color:var(--sc-teal,#155752);}
.ifs-cx-st{font-family:var(--sc-mono,Consolas,monospace);font-size:8.5px;font-weight:700;
letter-spacing:.04em;margin-left:3px;}
.ifs-cx-live .ifs-cx-st{color:#154e36;}
.ifs-cx-gated{color:var(--sc-muted,#6b6357);}
.ifs-cx-gated .ifs-cx-st{color:#8a7f6b;}
.ifs-links-lg{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ifs-links-lg a{color:var(--sc-teal,#155752);text-decoration:none;}
.ifs-num{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;font-weight:700;
letter-spacing:.08em;color:var(--sc-teal,#155752);display:inline-block;margin:0 0 2px;}
.ifs-find{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-navy,#0b2341);border-radius:4px;background:#fff;padding:12px 14px;
margin:6px 0 12px;}
.ifs-find-lab{display:block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-navy,#0b2341);margin:0 0 8px;}
.ifs-ftsrc{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:6px 0 0;line-height:1.5;}
.ifs-ftwrap{overflow-x:auto;margin:4px 0 6px;}
.ifs-ft{border-collapse:collapse;width:100%;font-size:12px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.ifs-ft th,.ifs-ft td{border:1px solid var(--sc-border,#e4dccb);padding:5px 9px;
text-align:left;vertical-align:top;line-height:1.4;}
.ifs-ft thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;font-size:10.5px;}
.ifs-ft tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.ifs-stats{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 2px;}
.ifs-stat{flex:1 1 150px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-radius:4px;padding:8px 12px;}
.ifs-stat-v{font-family:var(--sc-mono,Consolas,monospace);font-size:17px;font-weight:700;
color:var(--sc-navy,#0b2341);font-variant-numeric:tabular-nums;line-height:1.15;}
.ifs-stat-l{font-size:9.5px;letter-spacing:.03em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin-top:3px;}
</style>
<script>
(function(){
  function copyText(t, btn){
    var done=function(){var o=btn.textContent;btn.textContent="Copied \\u2713";
      setTimeout(function(){btn.textContent=o;},1400);};
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(t).then(done,function(){fallback(t,done);});
    } else {fallback(t,done);}
  }
  function fallback(t,done){try{var ta=document.createElement("textarea");
    ta.value=t;ta.style.position="fixed";ta.style.opacity="0";
    document.body.appendChild(ta);ta.select();document.execCommand("copy");
    document.body.removeChild(ta);done();}catch(e){}}
  document.addEventListener("click",function(e){
    var b=e.target.closest?e.target.closest(".ifs-copy"):null;
    if(!b)return;var id=b.getAttribute("data-target");
    var el=id?document.getElementById(id):null;if(el){copyText(el.textContent,b);}
  });
})();
</script>"""


def _crosslinks() -> str:
    return (
        '<div class="ifs-links-lg">'
        '<a href="/ift-diligence">Diligence question architecture &rarr;</a>'
        '<a href="/ift-study">Investor market study &rarr;</a>'
        '<a href="/ift-markets">Geographic markets &amp; TAM/SAM/SOM &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/ift-research">Market research brief &rarr;</a>'
        '<a href="/connector-estate">Live data-connector estate &rarr;</a>'
        '</div>')


def _boundary_block(boundary: str) -> str:
    return (
        '<div class="ifs-boundary">'
        '<span class="ifs-boundary-lab">The scope boundary — paste into every '
        'prompt</span>'
        f'<pre class="ifs-pre" id="ifs-boundary-text">{_esc(boundary)}</pre>'
        '<button type="button" class="ifs-copy" data-target="ifs-boundary-text">'
        'Copy boundary</button>'
        '<p class="ifs-prose" style="margin-top:8px;font-size:12.5px;">Without this '
        'line the research drags Medicaid NEMT and 911/scene back into the '
        'denominator — every prompt below is emitted <em>with the boundary '
        'prefixed</em>, and the copy button on each one copies the full, '
        'ready-to-send text.</p>'
        '</div>')


def _runthree_block(priority: Tuple[int, ...]) -> str:
    nums = ", ".join(str(n) for n in priority) if priority else "2, 4, 6"
    anchors = "".join(
        f'<a href="#ifs-p{n}">{n}</a>' + ("" if n == priority[-1] else ", ")
        for n in priority) if priority else ""
    return (
        '<div class="ifs-runthree">'
        '<div class="ifs-runthree-eyebrow">If you only run three</div>'
        f'<p>Run <b>{anchors or nums}</b> — the claims method (2), prevalence per '
        'admission (4), and the post-acute backbone (6). Those three prove '
        'prevalence with a method that survives diligence.</p>'
        '</div>')


def _prompt_panel(p, ce) -> str:
    badge = ('<span class="ifs-priority-badge">RUN-THESE-3</span>'
             if p.priority else "")
    src_items = "".join(
        f'<li>{_esc(name)} {_chip(basis)}</li>' for name, basis in p.sources)
    pre_id = f"ifs-prompt-{_esc(p.slug)}"
    body = (
        f'<span class="ifs-num">PROMPT {p.num}</span>{badge}'
        f'<p class="ifs-why">{_esc(p.why)}</p>'
        # The current research read, inline — the page carries the findings, not
        # just the prompt to go get them.
        + _findings_for(p.slug)
        + '<p class="ifs-sub">The prompt (boundary prefixed — copy &amp; send)</p>'
        f'<pre class="ifs-pre" id="{pre_id}">{_esc(p.full_prompt)}</pre>'
        f'<button type="button" class="ifs-copy" data-target="{pre_id}">'
        'Copy prompt</button>'
        '<p class="ifs-sub">Prioritized sources</p>'
        f'<ul class="ifs-list">{src_items}</ul>'
        + _connector_chips(p.connector_keys, ce)
        + _link_row(p.answered_by, label="Where the answer already lives")
    )
    return ck_panel(body, title=f"{p.num}. {p.title}",
                    anchor_id=f"ifs-p{p.num}")


def render_ift_sourcing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT sourcing-prompts page (Part 1). Degrades, never raises."""
    prompts = _sp.sourcing_prompts()
    priority = _sp.priority_prompts()
    ce = _sp.connector_evidence()
    summ = _sp.sourcing_summary()

    meta = (f"Part {summ['part']} · {summ['n_prompts']} scope-bounded prompts · "
            f"{summ['n_sources']} prioritized sources · "
            f"{summ['n_connectors_used']} connector datasets wired · "
            f"run-these-3: {', '.join(str(n) for n in summ['priority_set'])}")
    head = ck_page_title(
        "IFT Sourcing Prompts — Part 1",
        eyebrow="INTERFACILITY TRANSPORT · HOW THE EVIDENCE IS GATHERED",
        meta=meta)
    explainer = (
        '<p class="ifs-prose" style="font-size:15px;">The <strong>evidence-'
        'acquisition layer</strong> of the IFT study — and it is fully fleshed '
        'out: every prompt carries a <strong>current research read</strong> '
        'rendered inline (the best answer we can give now, pulled live from our '
        'sized modules — the TAM/Part-B build, the transfer registry &amp; '
        'mission mix, the demographic engine, occupancy, and the RVU ladder), '
        'THEN the scope-bounded prompt to close the remaining gap. Each also '
        'carries the boundary line that keeps NEMT and 911 out, its prioritized '
        'public sources, the real <strong>connector datasets</strong> that feed '
        'it, and a live link to <strong>where the answer lives</strong> (a sized '
        'page and the matching diligence slide). Findings carry their own basis — '
        + _chip("GOV") + ' ' + _chip("SOURCED") + ' ' + _chip("ILLUSTRATIVE") + ' '
        + _chip("ACADEMIC") + '; prompts are ' + _chip("FRAMEWORK")
        + '. This is Part 1.</p>')

    panels = "".join(_prompt_panel(p, ce) for p in prompts)

    body = "".join([
        _STYLES,
        head,
        explainer,
        _crosslinks(),
        _boundary_block(_sp.scope_boundary()),
        _runthree_block(priority),
        ck_section_intro(
            "THE PROMPTS",
            "Ten prompts, each scope-bounded and wired to its evidence.",
            italic_word="wired",
            body=("Every prompt is emitted with the boundary prefixed and a copy "
                  "button, followed by its prioritized sources, the connector "
                  "datasets that feed it, and a link to the sized page and "
                  "diligence slide that already answer it.")),
        panels,
        _crosslinks(),
        ck_next_section(
            "See the question architecture these prompts source the answers for",
            "/ift-diligence", eyebrow="The questions", italic_word="architecture"),
        ck_next_section(
            "Browse the live data-connector estate behind the sources",
            "/connector-estate", eyebrow="The data", italic_word="live"),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Sourcing Prompts — Part 1", active_nav="/market",
        subtitle="Interfacility-transport sourcing prompts (Part 1) — the "
                 "scope-bounded research questions that gather the evidence")

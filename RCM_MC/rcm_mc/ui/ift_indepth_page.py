"""IFT In-Depth page (``/ift-indepth``) — the answered question architecture.

Renders :mod:`rcm_mc.market_reports.ift_indepth`: ten questions, every
subsection as a conclusion-led block (Conclusion → Why it is true → Why it
matters → Evidence), every subquestion answered in one line inside a
collapsible coverage panel, and one bespoke visual per question.

Design notes (2026-07-10): visuals are HTML/CSS diagrams in the editorial
system — identity colors are fixed (911 = navy, IFT = teal, NEMT = amber)
and every element carries a text label, never color alone. Built markup is
NEVER routed through an escaping table helper (the /ift-demand incident);
data fields are escaped individually at build time. Degrades — never raises.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_page_actions, ck_page_title, ck_section_header,
)
from ..market_reports import ift_indepth as _idp


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "GOV": "A published government figure (CMS, MedPAC, Census, CFR).",
    "SOURCED": "A real dataset / registry / claims database.",
    "ACADEMIC": "A peer-reviewed study, cited by journal and year.",
    "DERIVED": "Computed by an explicit equation from cited inputs.",
    "FRAMEWORK": "A stated analytical scaffold with corroborating anchors.",
}


def _chip(basis: str) -> str:
    b = (basis or "FRAMEWORK").upper().split()[0]
    key = b if b in _BASIS_TITLES else "FRAMEWORK"
    return (f'<span class="idp-chip idp-chip-{key.lower()}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


_STYLES = """<style>
.idp-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;
line-height:1.62;color:var(--sc-text,#1a2332);max-width:92ch;margin:0 0 10px;}
.idp-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:700;letter-spacing:.06em;padding:1px 6px;
border-radius:2px;vertical-align:middle;text-transform:uppercase;}
.idp-chip-gov{background:#e7efe9;color:#154e36;}
.idp-chip-sourced{background:#e0efed;color:#0f3d39;}
.idp-chip-academic{background:#e6edf7;color:#243b57;}
.idp-chip-derived{background:#e9e6f4;color:#3d3268;}
.idp-chip-framework{background:#efe9e2;color:#6a4e2a;}
/* storyline arc */
.idp-arc{display:flex;flex-wrap:wrap;gap:0;margin:14px 0 20px;
counter-reset:arc;}
.idp-arc span{position:relative;flex:1 1 170px;background:#fff;
border:1px solid var(--sc-rule,#d8d0bc);border-left:none;padding:10px 12px
 10px 22px;font-family:var(--sc-serif,Georgia,serif);font-size:12.5px;
line-height:1.4;color:var(--sc-text,#1a2332);counter-increment:arc;}
.idp-arc span::before{content:counter(arc);position:absolute;left:6px;
top:9px;font-family:var(--sc-mono,Consolas,monospace);font-size:9px;
font-weight:700;color:var(--sc-teal,#155752);}
.idp-arc span:first-child{border-left:1px solid var(--sc-rule,#d8d0bc);}
.idp-arc span:last-child{background:var(--sc-teal,#155752);color:#fff;}
.idp-arc span:last-child::before{color:#c9e3da;}
/* TOC */
.idp-toc{columns:2;column-gap:26px;margin:8px 0 18px;padding:12px 16px;
background:var(--sc-surface,#faf7f1);border:1px solid var(--sc-rule,#d8d0bc);
border-radius:4px;}
.idp-toc a{display:block;font-family:var(--sc-mono,Consolas,monospace);
font-size:11.5px;color:var(--sc-teal,#155752);text-decoration:none;
padding:3px 0;break-inside:avoid;}
/* question banner */
.idp-qbanner{border-left:4px solid var(--sc-teal,#155752);background:#fff;
border-top:1px solid var(--sc-rule,#d8d0bc);
border-right:1px solid var(--sc-rule,#d8d0bc);
border-bottom:1px solid var(--sc-rule,#d8d0bc);
padding:12px 16px;margin:8px 0 16px;font-family:var(--sc-serif,Georgia,serif);
font-size:15px;line-height:1.55;color:var(--sc-navy,#0b2341);}
.idp-qbanner b{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
letter-spacing:.08em;color:var(--sc-teal,#155752);display:block;
margin-bottom:4px;}
/* block card */
.idp-block{background:#fff;border:1px solid var(--sc-rule,#d8d0bc);
border-radius:4px;padding:16px 18px;margin:0 0 16px;}
.idp-block h3{font-family:var(--sc-serif,Georgia,serif);font-weight:600;
font-size:16.5px;margin:0 0 8px;color:var(--sc-navy,#0b2341);}
.idp-k{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-teal,#155752);margin:12px 0 4px;}
.idp-conclusion{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;
line-height:1.6;color:var(--sc-text,#1a2332);margin:0;
padding:10px 12px;background:rgba(21,87,82,0.05);
border-left:3px solid var(--sc-teal,#155752);}
.idp-why{margin:4px 0 0 18px;padding:0;max-width:92ch;}
.idp-why li{font-family:var(--sc-serif,Georgia,serif);font-size:13px;
line-height:1.55;margin:5px 0;color:var(--sc-text,#2a3340);}
.idp-matters{font-family:var(--sc-serif,Georgia,serif);font-style:italic;
font-size:13px;line-height:1.55;color:var(--sc-navy,#0b2341);
margin:4px 0 0;max-width:92ch;}
.idp-ev{margin:4px 0 0;padding:0;list-style:none;max-width:96ch;}
.idp-ev li{font-size:12px;line-height:1.5;margin:5px 0;padding-left:10px;
border-left:2px solid var(--sc-rule,#d8d0bc);
color:var(--sc-text,#2a3340);}
.idp-ev .src{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);}
.idp-ev a{color:var(--sc-teal,#155752);}
/* subquestion coverage */
.idp-block details{margin:12px 0 0;border-top:1px dashed
 var(--sc-rule,#d8d0bc);padding-top:8px;}
.idp-block summary{cursor:pointer;font-family:var(--sc-mono,Consolas,
monospace);font-size:11px;font-weight:600;letter-spacing:.05em;
color:var(--sc-teal,#155752);}
.idp-sub{margin:8px 0 0;padding:0;list-style:none;}
.idp-sub li{margin:0 0 8px;padding:8px 10px;background:
var(--sc-surface,#faf7f1);border-radius:3px;font-size:12.5px;
line-height:1.5;}
.idp-sub .q{font-weight:600;color:var(--sc-navy,#0b2341);display:block;}
.idp-sub .a{color:var(--sc-text,#2a3340);display:block;margin-top:2px;}
.idp-sub .skip{color:#8a5a20;display:block;margin-top:2px;
font-style:italic;}
.idp-sub .skip::before{content:"⟂ ";font-style:normal;}
/* ── visuals (shared) ── */
.idp-vis{background:#fff;border:1px solid var(--sc-rule,#d8d0bc);
border-radius:4px;padding:16px 18px;margin:0 0 18px;overflow-x:auto;}
.idp-vis-title{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin:0 0 10px;}
.idp-vis-note{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:10px 0 0;line-height:1.5;}
/* three systems */
.idp-3s{display:grid;grid-template-columns:130px repeat(3,1fr);gap:2px;
min-width:720px;}
.idp-3s .h{padding:8px 10px;font-family:var(--sc-mono,Consolas,monospace);
font-size:11px;font-weight:700;color:#fff;letter-spacing:.04em;}
.idp-3s .h.s911{background:var(--sc-navy,#0b2341);}
.idp-3s .h.sift{background:var(--sc-teal,#155752);}
.idp-3s .h.snemt{background:#8a6420;}
.idp-3s .rl{padding:7px 8px;font-family:var(--sc-mono,Consolas,monospace);
font-size:9.5px;font-weight:700;letter-spacing:.05em;text-transform:
uppercase;color:var(--sc-muted,#6b6357);background:
var(--sc-surface,#faf7f1);display:flex;align-items:center;}
.idp-3s .c{padding:7px 10px;font-size:12px;line-height:1.45;background:#fff;
border:1px solid var(--sc-rule,#d8d0bc);}
.idp-3s .c.s911{border-top:2px solid var(--sc-navy,#0b2341);border-top-width:0;
border-left:3px solid var(--sc-navy,#0b2341);}
.idp-3s .c.sift{border-left:3px solid var(--sc-teal,#155752);}
.idp-3s .c.snemt{border-left:3px solid #8a6420;}
.idp-3s-conc{margin-top:10px;padding:9px 12px;background:
rgba(11,35,65,0.05);font-family:var(--sc-serif,Georgia,serif);
font-size:13px;font-style:italic;}
/* two engines */
.idp-2e{display:grid;grid-template-columns:1fr 1fr;gap:14px;min-width:640px;}
.idp-2e .eng{border:1px solid var(--sc-rule,#d8d0bc);border-radius:4px;}
.idp-2e .eng h4{margin:0;padding:9px 12px;font-family:var(--sc-mono,
Consolas,monospace);font-size:11px;letter-spacing:.05em;color:#fff;}
.idp-2e .ems h4{background:var(--sc-navy,#0b2341);}
.idp-2e .ift h4{background:var(--sc-teal,#155752);}
.idp-2e ul{margin:8px 0 10px;padding:0 14px 0 30px;}
.idp-2e li{font-size:12.5px;line-height:1.5;margin:4px 0;}
.idp-chain{display:flex;flex-wrap:wrap;align-items:center;gap:6px;
margin-top:14px;min-width:640px;}
.idp-chain span{background:var(--sc-surface,#faf7f1);border:1px solid
 var(--sc-rule,#d8d0bc);border-radius:3px;padding:6px 10px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;}
.idp-chain b{color:var(--sc-teal,#155752);font-size:13px;}
/* journey map */
.idp-jm-nodes{display:flex;flex-wrap:wrap;gap:8px;min-width:640px;}
.idp-jm-nodes span{flex:1 1 120px;text-align:center;background:
var(--sc-navy,#0b2341);color:#fff;border-radius:3px;padding:7px 8px;
font-family:var(--sc-mono,Consolas,monospace);font-size:10.5px;}
.idp-jm-nodes span.pa{background:var(--sc-teal,#155752);}
.idp-jm-nodes span.home{background:#8a6420;}
.idp-routes{margin-top:12px;display:grid;
grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;}
.idp-route{border:1px solid var(--sc-rule,#d8d0bc);border-radius:4px;
padding:9px 11px;background:var(--sc-surface,#faf7f1);}
.idp-route .rt{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
font-weight:700;color:var(--sc-navy,#0b2341);}
.idp-route .meta{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
color:var(--sc-muted,#6b6357);margin:3px 0;}
.idp-route .fail{font-size:11.5px;line-height:1.45;
color:var(--sc-text,#2a3340);}
.idp-route .fail b{color:#8a3a1e;}
/* ecosystem lanes */
.idp-eco{min-width:680px;}
.idp-eco .center{background:var(--sc-teal,#155752);color:#fff;text-align:
center;border-radius:3px;padding:8px;font-family:var(--sc-mono,Consolas,
monospace);font-size:11.5px;letter-spacing:.04em;margin-bottom:10px;}
.idp-lane{display:flex;align-items:flex-start;gap:8px;margin:7px 0;}
.idp-lane .ln{flex:0 0 118px;font-family:var(--sc-mono,Consolas,monospace);
font-size:9.5px;font-weight:700;letter-spacing:.05em;text-transform:
uppercase;padding-top:7px;}
.idp-lane .steps{display:flex;flex-wrap:wrap;gap:5px;}
.idp-lane .steps span{background:#fff;border:1px solid
 var(--sc-rule,#d8d0bc);border-radius:3px;padding:5px 8px;font-size:11px;}
.idp-lane .steps .arr{border:none;background:none;color:
var(--sc-muted,#6b6357);padding:5px 0;}
.idp-lane.l-req .ln{color:var(--sc-navy,#0b2341);}
.idp-lane.l-clin .ln{color:var(--sc-teal,#155752);}
.idp-lane.l-move .ln{color:#155752;}
.idp-lane.l-pay .ln{color:#8a6420;}
.idp-lane.l-acct .ln{color:#8a3a1e;}
/* spectrum */
.idp-spec{min-width:680px;}
.idp-spec-bar{display:flex;gap:3px;margin:6px 0 12px;}
.idp-spec-bar span{flex:1;text-align:center;padding:8px 6px;color:#fff;
font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
line-height:1.35;border-radius:2px;}
.idp-spec-tbl{width:100%;border-collapse:collapse;font-size:11.5px;}
.idp-spec-tbl th,.idp-spec-tbl td{border:1px solid var(--sc-rule,#d8d0bc);
padding:5px 8px;text-align:center;}
.idp-spec-tbl td:first-child,.idp-spec-tbl th:first-child{text-align:left;
font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;text-transform:uppercase;letter-spacing:.04em;
background:var(--sc-surface,#faf7f1);}
.idp-spec-tbl thead th{background:var(--sc-navy,#0b2341);color:#fff;
font-size:10px;}
/* maturity staircase */
.idp-stairs{display:flex;align-items:flex-end;gap:6px;min-width:680px;}
.idp-stair{flex:1;border:1px solid var(--sc-rule,#d8d0bc);
border-radius:4px 4px 0 0;background:#fff;padding:8px 10px;}
.idp-stair h5{margin:0 0 4px;font-family:var(--sc-mono,Consolas,monospace);
font-size:10px;letter-spacing:.04em;color:#fff;background:
var(--sc-teal,#155752);padding:4px 7px;border-radius:2px;}
.idp-stair ul{margin:0;padding-left:16px;}
.idp-stair li{font-size:10.5px;line-height:1.45;margin:2px 0;}
/* cascade */
.idp-casc{width:100%;border-collapse:separate;border-spacing:6px 6px;
min-width:720px;}
.idp-casc th{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
letter-spacing:.06em;text-transform:uppercase;text-align:left;
padding:0 8px;}
.idp-casc td{border-radius:3px;padding:8px 10px;font-size:11.5px;
line-height:1.45;vertical-align:top;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-rule,#d8d0bc);}
.idp-casc td:first-child{border-left:3px solid var(--sc-navy,#0b2341);}
.idp-casc td:nth-child(2){border-left:3px solid var(--sc-teal,#155752);}
.idp-casc td:nth-child(3){border-left:3px solid #8a6420;}
.idp-casc td:last-child{border-left:3px solid #8a3a1e;}
/* mmt system + flywheel share chain styles */
.idp-sys{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,
1fr));gap:10px;min-width:680px;}
.idp-sys .box{border:1px solid var(--sc-rule,#d8d0bc);border-radius:4px;
padding:9px 11px;background:#fff;}
.idp-sys .box h5{margin:0 0 4px;font-family:var(--sc-mono,Consolas,
monospace);font-size:10px;letter-spacing:.05em;
color:var(--sc-teal,#155752);}
.idp-sys .box p{margin:0;font-size:11.5px;line-height:1.5;}
/* tradeoff grid */
.idp-tro{width:100%;border-collapse:collapse;font-size:11px;min-width:720px;}
.idp-tro th,.idp-tro td{border:1px solid var(--sc-rule,#d8d0bc);
padding:6px 8px;text-align:center;}
.idp-tro thead th{background:var(--sc-navy,#0b2341);color:#fff;
font-size:10px;}
.idp-tro td:first-child,.idp-tro th:first-child{text-align:left;
font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;letter-spacing:.04em;text-transform:uppercase;
background:var(--sc-surface,#faf7f1);}
.idp-dot{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:10px;font-weight:700;padding:2px 7px;border-radius:8px;}
.idp-dot.s{background:#dcebe4;color:#0f5132;}
.idp-dot.m{background:#f0ead8;color:#6a4e2a;}
.idp-dot.w{background:#f3e2dc;color:#8a3a1e;}
/* flywheel */
.idp-fly{display:flex;flex-wrap:wrap;gap:6px;align-items:stretch;
min-width:680px;}
.idp-fly .st{flex:1 1 160px;background:#fff;border:1px solid
 var(--sc-rule,#d8d0bc);border-left:3px solid var(--sc-teal,#155752);
border-radius:4px;padding:8px 10px;font-size:11.5px;line-height:1.45;}
.idp-fly .st b{display:block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9.5px;letter-spacing:.05em;color:var(--sc-teal,#155752);
margin-bottom:3px;}
.idp-fly-loop{margin-top:8px;font-family:var(--sc-mono,Consolas,monospace);
font-size:10px;color:var(--sc-muted,#6b6357);}
</style>"""


# ─────────────────────────────────────────────────────────────────────────────
# Visual builders — one per question. All labels are text; identity colors
# (911 navy / IFT teal / NEMT amber) are reinforced by column headers.
# ─────────────────────────────────────────────────────────────────────────────
def _vis_three_systems() -> str:
    rows = (
        ("Trip initiated by", "Public 911 call (PSAP)",
         "Hospital clinician / transfer center", "Medicaid member booking"),
        ("Dispatched via", "EMD protocol → nearest posted unit",
         "Scheduler / dedicated dispatch plan", "Broker network assignment"),
        ("Demand it serves", "Unscheduled community emergencies",
         "Facility care transitions — scheduled + urgent",
         "Covered-service appointments"),
        ("Capability required", "Full-spectrum scene response (unknown "
         "acuity)", "Tiered: BLS → ALS → ALS2 → SCT/CCT, matched per trip",
         "Driver + accessible vehicle; no monitoring"),
        ("Who pays", "Insurers + municipal subsidy",
         "Insurers + the HOSPITAL for non-covered trips",
         "State Medicaid via capitated broker"),
        ("Provider optimizes", "Response time & readiness (UHU held low)",
         "ETA reliability, chaining, unit-hour utilization",
         "Route batching & cost per ride"),
    )
    cells = ['<div class="idp-3s">',
             '<div class="rl"></div>',
             '<div class="h s911">911 EMERGENCY</div>',
             '<div class="h sift">IFT — INTERFACILITY</div>',
             '<div class="h snemt">NEMT — MEDICAID BENEFIT</div>']
    for label, a, b, c in rows:
        cells.append(f'<div class="rl">{_esc(label)}</div>')
        cells.append(f'<div class="c s911">{_esc(a)}</div>')
        cells.append(f'<div class="c sift">{_esc(b)}</div>')
        cells.append(f'<div class="c snemt">{_esc(c)}</div>')
    cells.append("</div>")
    cells.append('<div class="idp-3s-conc">Three different operating '
                 "systems that share vehicles — not three labels for the "
                 "same service. The boundary is origin/destination + buyer; "
                 "acuity and vehicle type cross all three.</div>")
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "THREE SYSTEMS, COMPARED</div>" + "".join(cells) + "</div>")


def _vis_two_engines() -> str:
    return (
        '<div class="idp-vis"><div class="idp-vis-title">VISUAL · TWO '
        "OPERATING ENGINES</div>"
        '<div class="idp-2e">'
        '<div class="eng ems"><h4>TRADITIONAL EMS — READINESS ENGINE</h4>'
        "<ul><li>Optimizes jurisdiction COVERAGE and response time</li>"
        "<li>Capacity posted idle against unknown calls (UHU 0.30–0.50)</li>"
        "<li>Emergency calls supersede accepted transfers</li>"
        "<li>Performance = fractile response compliance</li></ul></div>"
        '<div class="eng ift"><h4>DEDICATED IFT — LOGISTICS ENGINE</h4>'
        "<ul><li>Optimizes forecastable health-system demand</li>"
        "<li>Capacity reserved against discharge/transfer curves</li>"
        "<li>Clinical tier matched per trip (BLS→CCT)</li>"
        "<li>Performance = ETA reliability + hospital flow</li></ul></div>"
        "</div>"
        '<div class="idp-chain">'
        "<span>Forecasted demand</span><b>→</b>"
        "<span>Planned capacity</span><b>→</b>"
        "<span>Reliable pickup</span><b>→</b>"
        "<span>Faster transfer</span><b>→</b>"
        "<span>Improved patient flow</span></div>"
        '<div class="idp-vis-note">The chain is the sale: each link is '
        "measurable, and the last one is the hospital outcome the buyer "
        "actually prices.</div></div>")


def _vis_journey_map() -> str:
    routes = (
        ("ED → tertiary/quaternary hub", "high freq · ALS/CCT · urgent",
         "Delay holds an ED bed and the receiving team; time-critical "
         "cases (STEMI/stroke) lose their treatment window."),
        ("Inpatient → SNF / IRF / LTACH", "highest freq · BLS/stretcher · "
         "scheduled", "Delay blocks a staffed acute bed; the post-acute "
         "placement window can lapse and the discharge reverses."),
        ("Hospital → home / hospice", "high freq · BLS/wheelchair · "
         "scheduled", "Lowest acuity, biggest bed-turnover effect; "
         "failures convert to avoidable overnight stays."),
        ("Facility ↔ dialysis", "recurring 3x/week · BLS · scheduled",
         "Missed runs create clinical risk and re-bookings; RSNAT "
         "prior-auth gates the Medicare book."),
        ("Hub → community repatriation", "moderate freq · BLS/ALS · "
         "scheduled", "The return leg that keeps hub beds available — "
         "first volume cut when capacity is scarce."),
        ("Behavioral health placement", "episodic · monitored · urgent",
         "Longest waits in the ED; placements are distant and "
         "time-boxed."),
    )
    nodes = ('<div class="idp-jm-nodes">'
             "<span>Community hospital / CAH</span><span>Emergency "
             "department</span><span>Tertiary / quaternary hub</span>"
             '<span class="pa">SNF · IRF · LTACH</span>'
             '<span class="pa">Dialysis / outpatient</span>'
             '<span class="home">Home / hospice</span></div>')
    cards = "".join(
        '<div class="idp-route">'
        f'<div class="rt">{_esc(rt)}</div>'
        f'<div class="meta">{_esc(meta)}</div>'
        f'<div class="fail"><b>If it fails:</b> {_esc(fail)}</div></div>'
        for rt, meta, fail in routes)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "CARE-CONTINUUM JOURNEY MAP</div>" + nodes
            + f'<div class="idp-routes">{cards}</div>'
            '<div class="idp-vis-note">IFT is the connective '
            "infrastructure BETWEEN the sites — each route is a distinct "
            "submarket with its own modality, urgency and failure cost. "
            "Acute-transfer scenario detail lives on /ift-clinical.</div>"
            "</div>")


def _vis_ecosystem() -> str:
    lanes = (
        ("l-req", "Service request", ("Nurse / case manager identifies "
         "need", "Transfer center / call list selects provider",
         "Provider accepts & assigns unit")),
        ("l-clin", "Clinical information", ("PCS + medical necessity "
         "documented", "Acuity → modality selection",
         "Crew receives patient report")),
        ("l-move", "Patient movement", ("Vehicle dispatched",
         "Bedside handoff → transport", "Destination handoff & "
         "turnaround")),
        ("l-pay", "Payment", ("Payer determined (Medicare / MCO / "
         "commercial / hospital)", "Claim or facility invoice submitted",
         "Denials worked · 19.7% collect nothing")),
        ("l-acct", "Accountability", ("SLA — usually absent",
         "Escalation — usually a phone chain",
         "Performance review — rare outside dedicated contracts")),
    )
    out = ['<div class="idp-eco"><div class="center">THE PATIENT '
           "TRANSFER — five flows that do NOT follow the same path</div>"]
    for cls, label, steps in lanes:
        chips = '<span class="arr">→</span>'.join(
            f"<span>{_esc(s)}</span>" for s in steps)
        out.append(f'<div class="idp-lane {cls}">'
                   f'<div class="ln">{_esc(label)}</div>'
                   f'<div class="steps">{chips}</div></div>')
    out.append('<div class="idp-vis-note">Fragmentation is structural: '
               "the request, the clinical record, the patient, the money "
               "and the accountability travel on different rails with "
               "different owners — failures fall into the gaps between "
               "them.</div></div>")
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "ECOSYSTEM, FIVE FLOWS AROUND ONE TRANSFER</div>"
            + "".join(out) + "</div>")


def _vis_spectrum() -> str:
    models = ("Fully insourced", "Hospital assets + outsourced ops",
              "Dedicated outsourcing", "Primary + backup vendors",
              "Multi-vendor / call list", "Broker-managed")
    shades = ("#0b2341", "#123a56", "#155752", "#4a7c68", "#8a6420",
              "#8a3a1e")
    bar = "".join(
        f'<span style="background:{c};">{_esc(m)}</span>'
        for m, c in zip(models, shades))
    dims = (
        ("Asset ownership", "Hospital", "Hospital", "Provider", "Provider",
         "Provider", "Network"),
        ("Operational control", "Hospital", "Shared", "Shared (contracted)",
         "Provider", "Provider", "Broker"),
        ("Capacity commitment", "Owned", "Owned", "Contractually dedicated",
         "Best-efforts primary", "None", "Network adequacy"),
        ("Capital exposure", "Full", "Fleet only", "None", "None", "None",
         "None"),
        ("Accountability", "Internal", "Split", "Single counterparty",
         "Diluted", "Fragmented", "Broker SLA"),
        ("Flexibility", "Low", "Low-mid", "Mid (contract-gated)", "Mid",
         "High", "Mid"),
    )
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>"
        for row in dims)
    head = "".join(f"<th>{_esc(m)}</th>" for m in models)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "OPERATING-MODEL SPECTRUM</div>"
            '<div class="idp-spec">'
            f'<div class="idp-spec-bar">{bar}</div>'
            '<table class="idp-spec-tbl"><thead><tr><th>Dimension</th>'
            f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
            '<div class="idp-vis-note">Classification rule: models are '
            "assigned by how service is DELIVERED AND CONTROLLED (assets, "
            "workforce, dispatch, committed capacity) — never by who "
            "bills the trip.</div></div>")


def _vis_maturity() -> str:
    stairs = (
        ("1 · AD HOC", ("Trips sourced call-by-call", "No visibility, no "
         "SLAs", "Facility-level habits")),
        ("2 · PREFERRED PROVIDER", ("A named first-call letter",
         "Unenforced expectations", "Rate card only")),
        ("3 · PRIMARY + BACKUP", ("Structured escalation order",
         "Basic KPI reporting", "Still no committed capacity")),
        ("4 · DEDICATED CONTRACT", ("Reserved units / crews",
         "Enforceable service levels", "Minimums + retainers")),
        ("5 · INTEGRATED PARTNERSHIP", ("Workflow + data integration",
         "Joint capacity planning", "Governance with executives")),
    )
    heights = (96, 122, 148, 176, 204)
    cells = "".join(
        f'<div class="idp-stair" style="min-height:{h}px;">'
        f"<h5>{_esc(t)}</h5><ul>"
        + "".join(f"<li>{_esc(i)}</li>" for i in items)
        + "</ul></div>"
        for (t, items), h in zip(stairs, heights))
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · '
            "PROCUREMENT MATURITY CURVE</div>"
            f'<div class="idp-stairs">{cells}</div>'
            '<div class="idp-vis-note">Each step changes five things: '
            "capacity (requested → committed), accountability (nobody → "
            "one counterparty), integration (phone → workflow), "
            "visibility (none → shared data), governance (complaints → "
            "structured review).</div></div>")


def _vis_cascade() -> str:
    rows = (
        ("Trip-by-trip purchasing — no committed capacity",
         "Trips declined or accepted with soft ETAs",
         "Discharges slip; patients board in the ED",
         "Staffed-bed hours lost at ~$3k/day adjusted expense; "
         "throughput bottleneck"),
        ("Shared 911/IFT fleets — emergencies supersede transfers",
         "Accepted transfers reassigned mid-task; ETA breaks",
         "Transfer centers re-call and escalate by phone",
         "Nursing/case-management hours burned; time-critical transfers "
         "delayed"),
        ("Payer-gated economics (necessity documentation, thin mix)",
         "Providers shrink to profitable corridors",
         "'No capacity' for unfunded / long / psych trips",
         "Placements lost; length of stay extends; denials absorbed"),
        ("Fragmented vendor field — no single counterparty",
         "Sequential call-arounds; inconsistent standards",
         "No comparable performance data; blame diffusion",
         "Failures persist without commercial consequence"),
        ("Patient-not-ready at pickup (hospital-side)",
         "Crews wait at the door; downstream trips cascade late",
         "Provider utilization falls; later ETAs widen",
         "Wait cost priced back into rates; reliability spiral"),
    )
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>"
        for row in rows)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "FAILURE CASCADE</div>"
            '<table class="idp-casc"><thead><tr>'
            "<th>Structural issue</th><th>Transportation failure</th>"
            "<th>Hospital consequence</th><th>Financial / patient effect</th>"
            f"</tr></thead><tbody>{body}</tbody></table>"
            '<div class="idp-vis-note">Read left to right: the pain lists '
            "hospitals recite are SYMPTOMS; the left column is what a "
            "model change actually has to fix.</div></div>")


def _vis_mmt_system() -> str:
    boxes = (
        ("HEALTH-SYSTEM DEMAND", "Transfer centers, discharge planning and "
         "recurring books feed known, facility-level demand."),
        ("DEDICATED CAPACITY", "Units and crews reserved against the "
         "contracted book; overflow via the market fleet."),
        ("DISPATCH", "Centralized scheduling balances scheduled, urgent "
         "and critical trips against the plan."),
        ("CLINICAL MODALITY", "Tier matched per trip across wheelchair → "
         "BLS → ALS → CCT within one network."),
        ("LOCAL FLEET OPERATIONS", "Market-level stations, positioning and "
         "chaining — density is the cost engine."),
        ("CUSTOMER VISIBILITY", "Status/ETA back to the hospital; delay "
         "reasons split hospital-caused vs provider-caused."),
        ("PERFORMANCE MANAGEMENT", "Account-level KPIs against the "
         "contract; the loop that feeds the next capacity plan."),
    )
    cells = "".join(
        f'<div class="box"><h5>{_esc(t)}</h5><p>{_esc(p)}</p></div>'
        for t, p in boxes)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "MMT OPERATING SYSTEM</div>"
            f'<div class="idp-sys">{cells}</div>'
            '<div class="idp-chain" style="margin-top:12px;">'
            "<span>Known demand</span><b>→</b><span>Reserved capacity</span>"
            "<b>→</b><span>Matched modality</span><b>→</b>"
            "<span>Reliable ETA</span><b>→</b>"
            "<span>Measured performance</span><b>→</b>"
            "<span>Next capacity plan</span></div>"
            '<div class="idp-vis-note">How the model is DESIGNED to work; '
            "company-internal throughput figures are diligence requests, "
            "flagged in the blocks below.</div></div>")


def _vis_tradeoff() -> str:
    # strength dots: s=strong, m=moderate, w=weak — labeled, never
    # color-alone.
    D = {"s": '<span class="idp-dot s">STRONG</span>',
         "m": '<span class="idp-dot m">MID</span>',
         "w": '<span class="idp-dot w">WEAK</span>'}
    rows = (
        ("Control", "s", "w", "m", "w", "s"),
        ("Reliability (committed capacity)", "m", "w", "m", "w", "s"),
        ("Flexibility / redundancy", "w", "m", "m", "s", "m"),
        ("Capital efficiency", "w", "s", "s", "s", "s"),
        ("Scalability across markets", "w", "m", "w", "m", "s"),
        ("Clinical breadth (WC→CCT)", "m", "m", "w", "m", "s"),
        ("Single-point accountability", "s", "w", "m", "w", "s"),
    )
    head = ("<th>Health-system need</th><th>Insource</th>"
            "<th>Traditional EMS</th><th>Regional vendor</th>"
            "<th>Multi-vendor</th><th>MMT dedicated</th>")
    body = "".join(
        f"<tr><td>{_esc(r[0])}</td>"
        + "".join(f"<td>{D[c]}</td>" for c in r[1:]) + "</tr>"
        for r in rows)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · '
            "ALTERNATIVE-MODEL TRADE-OFFS</div>"
            f'<table class="idp-tro"><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table>"
            '<div class="idp-vis-note">Positions are the FRAMEWORK read '
            "from Questions 5–9 (each defended in the blocks): every "
            "model trades something; the dedicated model's compromise is "
            "dependence on one provider — mitigated, not eliminated, by "
            "backup structures.</div></div>")


def _vis_flywheel() -> str:
    steps = (
        ("01 · DEMAND DATA", "More integrated demand data from booked "
         "facility volume"),
        ("02 · FORECASTING", "Better facility×hour×modality forecasts"),
        ("03 · CAPACITY", "Better capacity allocation and staffing"),
        ("04 · PERFORMANCE", "Stronger service performance (ETA, "
         "acceptance)"),
        ("05 · HOSPITAL FLOW", "Better discharge timing and bed "
         "availability"),
        ("06 · ADOPTION", "Deeper partnership, more facilities and "
         "modalities"),
    )
    cells = "".join(
        f'<div class="st"><b>{_esc(t)}</b>{_esc(p)}</div>'
        for t, p in steps)
    return ('<div class="idp-vis"><div class="idp-vis-title">VISUAL · THE '
            "STRATEGIC-CAPABILITY FLYWHEEL</div>"
            f'<div class="idp-fly">{cells}</div>'
            '<div class="idp-fly-loop">06 feeds back into 01 — each turn '
            "adds demand data. Links 01→04 are analytically supported "
            "(forecastable demand + the MedPAC volume-cost curve); links "
            "05→06 are the partnership hypothesis the account evidence "
            "must keep proving.</div></div>")


_VISUALS = {
    "three-systems": _vis_three_systems,
    "two-engines": _vis_two_engines,
    "journey-map": _vis_journey_map,
    "ecosystem": _vis_ecosystem,
    "spectrum": _vis_spectrum,
    "maturity": _vis_maturity,
    "cascade": _vis_cascade,
    "mmt-system": _vis_mmt_system,
    "tradeoff": _vis_tradeoff,
    "flywheel": _vis_flywheel,
}


# ─────────────────────────────────────────────────────────────────────────────
# Renderers
# ─────────────────────────────────────────────────────────────────────────────
def _render_block(b) -> str:
    why = "".join(f"<li>{_esc(w)}</li>" for w in b.why_true)
    ev = ""
    if b.evidence:
        items = []
        for e in b.evidence:
            src = (f'<a href="{_esc(e.url)}" target="_blank" '
                   f'rel="noopener">{_esc(e.source)}</a>'
                   if e.url else _esc(e.source))
            items.append(f"<li>{_esc(e.text)} {_chip(e.basis)} "
                         f'<span class="src">{src}</span></li>')
        ev = ('<div class="idp-k">Evidence</div>'
              f'<ul class="idp-ev">{"".join(items)}</ul>')
    subs = ""
    if b.subqs:
        n_ans = sum(1 for s in b.subqs if s.a)
        n_skip = sum(1 for s in b.subqs if not s.a and s.skip)
        lis = []
        for s in b.subqs:
            if s.a:
                lis.append(f'<li><span class="q">{_esc(s.q)}</span>'
                           f'<span class="a">{_esc(s.a)}</span></li>')
            else:
                lis.append(f'<li><span class="q">{_esc(s.q)}</span>'
                           f'<span class="skip">{_esc(s.skip)}</span></li>')
        label = (f"All {len(b.subqs)} subquestions — {n_ans} answered"
                 + (f", {n_skip} marked as diligence requests" if n_skip
                    else ""))
        subs = (f"<details><summary>{_esc(label)}</summary>"
                f'<ul class="idp-sub">{"".join(lis)}</ul></details>')
    return (
        f'<div class="idp-block" id="{_esc(b.key)}">'
        f"<h3>{_esc(b.title)}</h3>"
        '<div class="idp-k">Conclusion</div>'
        f'<p class="idp-conclusion">{_esc(b.conclusion)}</p>'
        '<div class="idp-k">Why it is true</div>'
        f'<ul class="idp-why">{why}</ul>'
        '<div class="idp-k">Why it matters</div>'
        f'<p class="idp-matters">{_esc(b.why_matters)}</p>'
        f"{ev}{subs}</div>")


def _render_question(q) -> str:
    vis = _VISUALS.get(q.visual_key, lambda: "")()
    blocks = "".join(_render_block(b) for b in q.blocks)
    return (
        f'<div id="idp-q{q.num}"></div>'
        + ck_section_header(f"Question {q.num} — {q.title}",
                            eyebrow=f"Q{q.num} OF 10",
                            count=len(q.blocks))
        + ('<div class="idp-qbanner"><b>THE ANSWER IN ONE LINE</b>'
           f"{_esc(q.storyline)}</div>")
        + vis + blocks)


def render_ift_indepth(qs=None) -> str:
    """Render the In-Depth page. Degrades — never raises."""
    try:
        questions = _idp.questions()
        cov = _idp.coverage()
        arc = _idp.STORYLINE
    except Exception:  # noqa: BLE001
        questions, cov, arc = (), {}, ()
    head = ck_page_title(
        "IFT — In Depth",
        eyebrow="INTERFACILITY TRANSPORT · THE ANSWERED QUESTION "
                "ARCHITECTURE",
        meta=(f"{cov.get('questions', 0)} questions · "
              f"{cov.get('blocks', 0)} conclusion-led answers · "
              f"{cov.get('answered', 0)} subquestions answered · "
              f"{cov.get('skipped', 0)} marked as diligence requests"))
    intro = (
        '<p class="idp-prose">Every question and subquestion of the IFT '
        "market study, ANSWERED from desk research — company materials, "
        "claims data, public filings, regulations and the study's cited "
        "evidence registries — not deferred to future interviews. Each "
        "topic leads with its conclusion, then the findings behind it, "
        "the implication, and the evidence with its honesty basis "
        f"({_chip('GOV')} {_chip('SOURCED')} {_chip('ACADEMIC')} "
        f"{_chip('DERIVED')} {_chip('FRAMEWORK')}). Where a subquestion "
        "is unanswerable without company data, it is marked ⟂ as a "
        "diligence request — never invented.</p>")
    arc_html = ""
    if arc:
        arc_html = ('<div class="idp-arc">'
                    + "".join(f"<span>{_esc(s)}</span>" for s in arc)
                    + "</div>")
    toc = ""
    if questions:
        toc = ('<div class="idp-toc">'
               + "".join(
                   f'<a href="#idp-q{q.num}">Q{q.num} · {_esc(q.title)}</a>'
                   for q in questions)
               + "</div>")
    body_qs = "".join(_render_question(q) for q in questions)
    if not questions:
        body_qs = ('<p class="idp-prose">Content modules are not '
                   "available in this build — an honest empty state, not "
                   "an error.</p>")
    footer = ""
    if cov and not cov.get("unaccounted"):
        footer = (
            '<p class="idp-vis-note" style="margin-top:18px;">Coverage '
            f"check: {cov.get('subquestions', 0)} subquestions — "
            f"{cov.get('answered', 0)} answered, {cov.get('skipped', 0)} "
            "explicitly marked as company-data diligence requests, 0 "
            "unaccounted. Cross-references: /ift-demand (growth "
            "evidence), /ift-mmt (company file), /ift-study (framework "
            "homes).</p>")
    return chartis_shell(
        _STYLES + head + intro + arc_html + toc + body_qs + footer
        + ck_page_actions(),
        "IFT — In Depth", active_nav="/market",
        subtitle="The IFT question architecture, answered — conclusions, "
                 "evidence and visuals")

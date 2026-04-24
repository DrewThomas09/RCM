"""Bankruptcy-Survivor Scan — HTTP surface.

Two renderers:

    render_scan_landing()          — form page (no target yet)
    render_scan_result(scan)       — one-page result suitable for
                                      Print → Save as PDF (IC-packet
                                      attachment)

The result page is intentionally standalone — no Chartis shell —
so partners can print it cleanly.
"""
from __future__ import annotations

import html
from typing import List

from ..diligence.screening import (
    BankruptcySurvivorScan, BankruptcySurvivorVerdict, PatternCheck,
)


_VERDICT_COLOR = {
    BankruptcySurvivorVerdict.GREEN:    "#1f7a3a",
    BankruptcySurvivorVerdict.YELLOW:   "#b07c1f",
    BankruptcySurvivorVerdict.RED:      "#b23a2d",
    BankruptcySurvivorVerdict.CRITICAL: "#8a1e1e",
}

_VERDICT_COPY = {
    BankruptcySurvivorVerdict.GREEN: (
        "No named-case pattern matched. Safe to proceed to full-"
        "packet diligence."
    ),
    BankruptcySurvivorVerdict.YELLOW: (
        "1-2 patterns matched. Flag in IC open-questions; proceed "
        "with focused diligence on the flagged vectors."
    ),
    BankruptcySurvivorVerdict.RED: (
        "Three or more patterns matched. Do not commit partner hours "
        "until the flagged vectors are addressed."
    ),
    BankruptcySurvivorVerdict.CRITICAL: (
        "Full named-case pattern replay detected. This target matches "
        "the profile of a historical PE healthcare bankruptcy at time "
        "of signing. Escalate immediately."
    ),
}


def _style() -> str:
    return """<style>
body{font-family:Georgia,'Times New Roman',serif;font-size:11pt;
     color:#1a1a1a;max-width:7.5in;margin:0 auto;padding:0.75in 0.5in;
     line-height:1.45;}
h1{font-size:22pt;margin:0 0 6pt 0;color:#0b2341;font-weight:700;}
h2{font-size:14pt;margin:18pt 0 4pt 0;color:#0b2341;
   border-bottom:1px solid #c9b98a;padding-bottom:2pt;}
.eyebrow{font-size:9pt;letter-spacing:1.5pt;text-transform:uppercase;
   color:#6b5d3c;font-family:'Helvetica Neue',Arial,sans-serif;}
.verdict{border:2pt solid;padding:10pt 14pt;margin:10pt 0 14pt 0;
   background:#f8f6f0;}
.verdict-band{font-size:11pt;font-weight:700;letter-spacing:1.5pt;
   text-transform:uppercase;font-family:'Helvetica Neue',Arial,sans-serif;}
.verdict-copy{font-size:11pt;color:#1a1a1a;margin-top:4pt;}
table.checks{width:100%;border-collapse:collapse;font-size:10pt;
   margin:6pt 0 10pt 0;}
table.checks th{text-align:left;padding:4pt 6pt;
   border-bottom:1pt solid #0b2341;font-size:9pt;letter-spacing:.5pt;
   text-transform:uppercase;color:#6b5d3c;
   font-family:'Helvetica Neue',Arial,sans-serif;font-weight:700;}
table.checks td{padding:4pt 6pt;border-bottom:1px solid #e6dfca;}
.sev-CRITICAL{color:#8a1e1e;font-weight:700;}
.sev-HIGH{color:#b23a2d;font-weight:700;}
.sev-MEDIUM{color:#b07c1f;font-weight:600;}
.sev-LOW{color:#6b5d3c;}
.fired{background:#fbf0ee;}
.passed{background:transparent;}
ul{margin:6pt 0 10pt 0;padding-left:20pt;}
li{margin:3pt 0;}
.caveat{font-size:8pt;color:#6b5d3c;margin-top:24pt;padding-top:6pt;
   border-top:1px solid #c9b98a;font-family:'Helvetica Neue',Arial,sans-serif;}
.form-field{display:block;margin:10pt 0 4pt 0;font-size:10pt;
   color:#6b5d3c;letter-spacing:.5pt;text-transform:uppercase;}
input,select{width:100%;padding:6pt 8pt;font-size:11pt;
   border:1px solid #c9b98a;font-family:inherit;}
button{margin-top:14pt;padding:8pt 20pt;background:#0b2341;color:#fff;
   border:0;font-size:11pt;letter-spacing:.5pt;text-transform:uppercase;
   cursor:pointer;}
@page{size:Letter;margin:0.75in 0.5in;}
@media print{body{max-width:none;padding:0;}}
</style>"""


def render_scan_landing() -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Bankruptcy-Survivor Scan</title>"
        f"{_style()}"
        "</head><body>"
        "<div class='eyebrow'>Pre-screening</div>"
        "<h1>Bankruptcy-Survivor Scan</h1>"
        "<p>A 12-pattern screen against the named PE-healthcare "
        "bankruptcy playbook (Steward, Envision, APP, Cano, "
        "Prospect, Wellpath) plus six forward-looking regulatory "
        "vectors. Public data only — no CCD required. Result renders "
        "in &lt;30 seconds.</p>"
        "<form method='POST' action='/screening/bankruptcy-survivor'>"
        "<label class='form-field'>Target name</label>"
        "<input name='target_name' required maxlength='120' "
        "placeholder='Project Aurora'>"
        "<label class='form-field'>Specialty (HOSPITAL, EMERGENCY_MEDICINE, "
        "ANESTHESIOLOGY, …)</label>"
        "<input name='specialty' maxlength='40'>"
        "<label class='form-field'>States (comma-separated, e.g. CA, OR)</label>"
        "<input name='states' maxlength='120'>"
        "<label class='form-field'>CBSA codes (comma-separated)</label>"
        "<input name='cbsa_codes' maxlength='120'>"
        "<label class='form-field'>Legal structure</label>"
        "<select name='legal_structure'>"
        "<option value=''>(not specified)</option>"
        "<option>FRIENDLY_PC_PASS_THROUGH</option>"
        "<option>MSO_PC_MANAGEMENT_FEE</option>"
        "<option>DIRECT_EMPLOYMENT</option>"
        "<option>PROFESSIONAL_LLC</option>"
        "</select>"
        "<label class='form-field'>Landlord (REIT name or operator)</label>"
        "<input name='landlord' maxlength='120'>"
        "<label class='form-field'>Lease term (years)</label>"
        "<input name='lease_term_years' type='number' min='0' max='50'>"
        "<label class='form-field'>Escalator % (e.g. 0.035 for 3.5%)</label>"
        "<input name='lease_escalator_pct' type='number' step='0.001'>"
        "<label class='form-field'>EBITDAR coverage ratio</label>"
        "<input name='ebitdar_coverage' type='number' step='0.01'>"
        "<label class='form-field'>Geography</label>"
        "<select name='geography'>"
        "<option value=''>(not specified)</option>"
        "<option>RURAL</option><option>SAFETY_NET</option>"
        "<option>URBAN_ACADEMIC</option><option>SUBURBAN</option>"
        "</select>"
        "<label class='form-field'>Is hospital-based physician group?</label>"
        "<select name='is_hospital_based_physician'>"
        "<option value='false'>No</option><option value='true'>Yes</option>"
        "</select>"
        "<label class='form-field'>Out-of-network revenue share (0–1)</label>"
        "<input name='oon_revenue_share' type='number' step='0.01' min='0' max='1'>"
        "<button type='submit'>Run scan</button>"
        "</form></body></html>"
    )


def render_scan_result(scan: BankruptcySurvivorScan) -> str:
    color = _VERDICT_COLOR[scan.verdict]
    copy = _VERDICT_COPY[scan.verdict]
    rows = []
    for c in scan.checks:
        sev_class = f"sev-{c.severity}"
        fired_class = "fired" if c.fired else "passed"
        status = "FIRED" if c.fired else "pass"
        case = (
            f"<br><em>{html.escape(c.case_study)}</em>"
            if c.fired and c.case_study else ""
        )
        rows.append(
            f"<tr class='{fired_class}'>"
            f"<td>{html.escape(c.category)}</td>"
            f"<td>{html.escape(c.name)}</td>"
            f"<td class='{sev_class}'>{status}</td>"
            f"<td>{html.escape(c.narrative)}{case}</td>"
            f"</tr>"
        )
    questions_html = "".join(
        f"<li>{html.escape(q)}</li>" for q in scan.diligence_questions
    ) or "<li>No structural questions generated — target profile is clean.</li>"

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Bankruptcy-Survivor Scan — {html.escape(scan.target_name)}</title>"
        f"{_style()}</head><body>"
        "<div class='eyebrow'>Pre-screening result</div>"
        f"<h1>Bankruptcy-Survivor Scan</h1>"
        f"<p style='font-size:13pt;color:#2a2a2a;'>{html.escape(scan.target_name)}</p>"
        f"<div class='verdict' style='border-color:{color};'>"
        f"<div class='verdict-band' style='color:{color};'>"
        f"{html.escape(scan.verdict.value)}</div>"
        f"<div class='verdict-copy'>{html.escape(copy)}</div>"
        f"<div style='margin-top:6pt;font-size:10pt;color:#6b5d3c;'>"
        f"Patterns hit: {scan.patterns_hit} / 12  ·  "
        f"Critical matches: {scan.critical_hits}</div>"
        f"</div>"
        "<h2>Pattern checks</h2>"
        "<table class='checks'>"
        "<thead><tr><th>Category</th><th>Check</th><th>Status</th>"
        "<th>Narrative</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<h2>Diligence questions</h2>"
        f"<ul>{questions_html}</ul>"
        "<div class='caveat'>Pre-screening only. Structural pattern "
        "matching against known historical failure modes — not a legal "
        "opinion and not a replacement for the full DealAnalysisPacket. "
        "Every case-study comparison cites the named historical deal's "
        "entry EV and outcome from the public-deals corpus.</div>"
        f"<div class='caveat'>Computed {html.escape(scan.computed_at)}.</div>"
        "</body></html>"
    )

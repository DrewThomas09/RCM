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
    analyze_distress_fingerprint,
    BankruptcySurvivorScan, BankruptcySurvivorVerdict, PatternCheck,
)


_EXPLAINER_CSS = """
.ck-bs-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-bs-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""

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


def _landing_form_style() -> str:
    """Form-only styles for the landing page, scoped under .bsv-landing
    so they cannot leak into chartis_shell's body / h1 / h2 / table /
    button rules (which is what broke the entire page layout when this
    landing was rendered inside the shell — user-reported as "the
    Bankruptcy tab makes my entire view get augmented and spacing is
    messed up"). _style() below stays unscoped because render_scan_result
    is intentionally standalone (no shell) for print/PDF export."""
    return """<style>
.bsv-landing .form-field{display:block;margin:10pt 0 4pt 0;font-size:10pt;
   color:#6b5d3c;letter-spacing:.5pt;text-transform:uppercase;
   font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);}
.bsv-landing input,.bsv-landing select{width:100%;padding:6pt 8pt;
   font-size:11pt;border:1px solid #c9b98a;font-family:inherit;}
.bsv-landing button{margin-top:14pt;padding:8pt 20pt;background:#0b2341;
   color:#fff;border:0;font-size:11pt;letter-spacing:.5pt;
   text-transform:uppercase;cursor:pointer;
   font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);}
</style>"""


def _style() -> str:
    return """<style>
body{font-family:Georgia,'Times New Roman',serif;font-size:11pt;
     color:#1a1a1a;max-width:7.5in;margin:0 auto;padding:0.75in 0.5in;
     line-height:1.45;}
h1{font-size:22pt;margin:0 0 6pt 0;color:#0b2341;font-weight:700;}
h2{font-size:14pt;margin:18pt 0 4pt 0;color:#0b2341;
   border-bottom:1px solid #c9b98a;padding-bottom:2pt;}
.eyebrow{font-size:9pt;letter-spacing:1.5pt;text-transform:uppercase;
   color:#6b5d3c;font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);}
.verdict{border:2pt solid;padding:10pt 14pt;margin:10pt 0 14pt 0;
   background:#f8f6f0;}
.verdict-band{font-size:11pt;font-weight:700;letter-spacing:1.5pt;
   text-transform:uppercase;font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);}
.verdict-copy{font-size:11pt;color:#1a1a1a;margin-top:4pt;}
table.checks{width:100%;border-collapse:collapse;font-size:10pt;
   margin:6pt 0 10pt 0;}
table.checks th{text-align:left;padding:4pt 6pt;
   border-bottom:1pt solid #0b2341;font-size:9pt;letter-spacing:.5pt;
   text-transform:uppercase;color:#6b5d3c;
   font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);font-weight:700;}
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
   border-top:1px solid #c9b98a;font-family:var(--sc-sans,'Helvetica Neue',Arial,sans-serif);}
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
    """Landing/form page for the Bankruptcy-Survivor scan.

    Wrapped in chartis_shell so the form lives inside the v5 chrome.
    The result page (``render_scan_result`` below) is intentionally
    standalone — see module docstring — to keep the print/PDF flow
    clean.
    """
    from ._chartis_kit import chartis_shell

    body = (
        f"{_landing_form_style()}"
        "<div class='bsv-landing'>"
        "<p>A 12-pattern screen against the named PE-healthcare "
        "bankruptcy playbook (Steward, Envision, APP, Cano, "
        "Prospect, Wellpath) plus six forward-looking regulatory "
        "vectors. Public data only: no CCD required. Result renders "
        "in &lt;30 seconds.</p>"
        "<form method='POST' action='/screening/bankruptcy-survivor'>"
        "<label class='form-field'>Target name</label>"
        "<input name='target_name' required maxlength='120' "
        "placeholder='Project Aurora'>"
        "<label class='form-field'>Specialty (HOSPITAL, EMERGENCY_MEDICINE, "
        "ANESTHESIOLOGY, …)</label>"
        "<input name='specialty' maxlength='40' aria-label='Specialty (HOSPITAL, EMERGENCY_MEDICINE, ANESTHESIOLOGY)'>"
        "<label class='form-field'>States (comma-separated, e.g. CA, OR)</label>"
        "<input name='states' maxlength='120' aria-label='States (comma-separated, e.g. CA, OR)'>"
        "<label class='form-field'>CBSA codes (comma-separated)</label>"
        "<input name='cbsa_codes' maxlength='120' aria-label='CBSA codes (comma-separated)'>"
        "<label class='form-field'>Legal structure</label>"
        "<select name='legal_structure' aria-label='Legal structure'>"
        "<option value=''>(not specified)</option>"
        "<option>FRIENDLY_PC_PASS_THROUGH</option>"
        "<option>MSO_PC_MANAGEMENT_FEE</option>"
        "<option>DIRECT_EMPLOYMENT</option>"
        "<option>PROFESSIONAL_LLC</option>"
        "</select>"
        "<label class='form-field'>Landlord (REIT name or operator)</label>"
        "<input name='landlord' maxlength='120' aria-label='Landlord (REIT name or operator)'>"
        "<label class='form-field'>Lease term (years)</label>"
        "<input name='lease_term_years' type='number' min='0' max='50' aria-label='Lease term (years)'>"
        "<label class='form-field'>Escalator % (e.g. 0.035 for 3.5%)</label>"
        "<input name='lease_escalator_pct' type='number' step='0.001' aria-label='Escalator % (e.g. 0.035 for 3.5%)'>"
        "<label class='form-field'>EBITDAR coverage ratio</label>"
        "<input name='ebitdar_coverage' type='number' step='0.01' aria-label='EBITDAR coverage ratio'>"
        "<label class='form-field'>Geography</label>"
        "<select name='geography' aria-label='Geography'>"
        "<option value=''>(not specified)</option>"
        "<option>RURAL</option><option>SAFETY_NET</option>"
        "<option>URBAN_ACADEMIC</option><option>SUBURBAN</option>"
        "</select>"
        "<label class='form-field'>Is hospital-based physician group?</label>"
        "<select name='is_hospital_based_physician' aria-label='Is hospital-based physician group?'>"
        "<option value='false'>No</option><option value='true'>Yes</option>"
        "</select>"
        "<label class='form-field'>Out-of-network revenue share (0–1)</label>"
        "<input name='oon_revenue_share' type='number' step='0.01' min='0' max='1' aria-label='Out-of-network revenue share (0-1)'>"
        "<button type='submit'>Run scan</button>"
        "</form>"
        "</div>"  # close .bsv-landing
    )
    from ._chartis_kit import (
        ck_kpi_block, ck_next_section, ck_page_title, ck_provenance_tooltip,
    )
    patterns_value = ck_provenance_tooltip(
        "Patterns in the screen",
        "12",
        explainer=(
            "Twelve falsifiable bear-thesis patterns drawn from "
            "PE-healthcare bankruptcy precedents (Steward, "
            "Envision, Mednax). Each is a structural pattern + "
            "case-study citation, not a verdict."
        ),
    )
    case_studies_value = ck_provenance_tooltip(
        "Case studies cited",
        "3",
        explainer=(
            "Steward, Envision, Mednax. Each fired pattern cites "
            "the named historical deal's entry EV + actual outcome "
            "from the public-deals corpus. Use as a precedent map, "
            "not a legal opinion."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block(
            "Patterns", patterns_value, "in screen",
            help={
                "definition": (
                    "Twelve falsifiable structural patterns drawn from "
                    "PE-healthcare bankruptcy precedents (Steward, "
                    "Envision, Mednax). Each pattern is a specific "
                    "claim a partner can either confirm or rule out: "
                    "not a vague risk theme."
                ),
            },
        )
        + ck_kpi_block(
            "Case Studies", case_studies_value, "named precedents",
            help={
                "definition": (
                    "Documented PE-healthcare collapses the screen "
                    "tests against. Each case ships with its dated "
                    "trigger events, sponsor identity, and what the "
                    "early-warning structural signal was so the "
                    "partner can pattern-match the target deal."
                ),
            },
        )
        + ck_kpi_block(
            "Severity Tiers", "3", "critical / high / med",
            help={
                "definition": (
                    "How findings are ranked. CRITICAL = thesis-killing "
                    "on its own (covenant default at Y1, payer "
                    "concentration > 70%). HIGH = IC-level discussion "
                    "with mitigants. MEDIUM = name in memo but doesn't "
                    "block the deal."
                ),
            },
        )
        + '</div>'
    )
    title_block = ck_page_title(
        "Bankruptcy-Survivor Scan", eyebrow="BANKRUPTCY SURVIVOR",
        meta="12 patterns · Steward / Envision / Mednax precedents",
    )
    explainer_html = (
        '<p class="ck-bs-explainer">'
        '<em>Whether the deal survives the playbook.</em> '
        "12 patterns drawn from PE-healthcare bankruptcies (Steward, "
        "Envision, Mednax): a rapid pre-screen against the structural "
        "moves that have already broken deals. Each fired pattern is a "
        "falsifiable claim, not a verdict."
        "</p>"
    )
    body = (
        title_block
        + explainer_html
        + kpi_strip
        + body
        + ck_next_section(
            "Cross-check against named bear cases",
            "/bear-cases",
            eyebrow="Up next",
            italic_word="bear",
        )
    )
    return chartis_shell(
        body, "Bankruptcy-Survivor Scan",
        active_nav="/screening/bankruptcy-survivor",
        extra_css=_EXPLAINER_CSS,
    )


def _replay_section(scan: BankruptcySurvivorScan) -> str:
    """Named-case replay read: the distinct public-record bankruptcies
    this deal's fingerprint matches, ranked by severity. Every line
    recomputes from the fired checks — a replay, not a hunch."""
    fp = analyze_distress_fingerprint(scan)
    tone = {"CRITICAL": "#b5321e", "HIGH": "#b8732a",
            "MEDIUM": "#a98545", "LOW": "#7a8699"}
    if not fp.replays:
        return (
            '<div style="margin:0 0 14px;padding:10px 14px;'
            'background:#eef3ee;border-left:3px solid #0a8a5f;'
            'border-radius:0 3px 3px 0;font-size:12px;color:#2f5d3f;">'
            f'{html.escape(fp.headline)}</div>')
    rows = ""
    for r in fp.replays:
        col = tone.get(r.severity, "#7a8699")
        case = (f'<div style="font-style:italic;font-size:11px;color:#465366;'
                f'margin-top:2px;">{html.escape(r.case_study)}</div>'
                if r.case_study else
                '<div style="font-size:10.5px;color:#9aa3ad;margin-top:2px;">'
                'fired without a named public-record precedent</div>')
        rows += (
            f'<div style="padding:8px 0;border-bottom:1px solid #e4ddca;">'
            f'<div style="display:flex;gap:8px;align-items:baseline;">'
            f'<span style="font-family:var(--sc-mono,monospace);font-size:9px;'
            f'font-weight:700;letter-spacing:0.08em;color:{col};">'
            f'{html.escape(r.severity)}</span>'
            f'<span style="font-size:12px;font-weight:600;color:#1a2332;">'
            f'{html.escape(r.pattern.replace("_", " ").title())}</span>'
            f'<span style="margin-left:auto;font-size:9px;color:#9aa3ad;'
            f'text-transform:uppercase;letter-spacing:0.06em;">'
            f'{html.escape(r.category)}</span></div>'
            f'{case}</div>')
    return (
        '<div style="margin:0 0 16px;padding:12px 16px;'
        'border:1px solid #d6cfc0;border-radius:4px;background:#faf7f0;">'
        '<div style="font-family:var(--sc-mono,monospace);font-size:10px;'
        'letter-spacing:0.1em;color:#7a8699;font-weight:700;margin-bottom:4px;">'
        f'NAMED-CASE REPLAY · {len(fp.distinct_cases)} DISTINCT CASES · '
        f'SEVERITY {fp.weighted_severity}</div>'
        f'<p style="font-size:12.5px;color:#1a2332;line-height:1.6;'
        f'margin:0 0 8px;">{html.escape(fp.headline)}</p>'
        f'{rows}'
        '<p style="font-size:9.5px;color:#9aa3ad;margin:8px 0 0;">'
        'Ranked by severity weight; de-duped by named case. Recomputes '
        'from the fired pattern checks below.</p></div>')


def _pattern_strip(scan: BankruptcySurvivorScan) -> str:
    """The scan at a glance before the table: one chip per pattern
    check — fired chips lit in their severity tone, passed chips muted.
    The eye finds the lit CRITICALs instantly."""
    if not scan.checks:
        return ""
    tone = {"CRITICAL": "#b5321e", "HIGH": "#b8732a",
            "MEDIUM": "#a98545", "LOW": "#7a8699"}
    chips = ""
    for c in scan.checks:
        color = tone.get(c.severity, "#7a8699")
        if c.fired:
            style = (f"background:{color};color:#fff;border:1px solid "
                     f"{color};")
        else:
            style = ("background:transparent;color:#9aa3ad;"
                     "border:1px solid #d6cfc0;")
        label = c.name.replace("_", " ").title()
        chips += (
            f'<span title="{html.escape(c.severity)} · '
            f'{"FIRED" if c.fired else "pass"}" '
            f'style="display:inline-block;padding:4px 10px;margin:0 6px '
            f'6px 0;border-radius:2px;font-size:10.5px;'
            f'font-family:var(--sc-mono,monospace);{style}">'
            f'{html.escape(label)}</span>'
        )
    summary = (
        f'<p style="margin:0 0 6px;font-size:11px;color:#465366;">'
        f'<strong>{scan.patterns_hit}</strong> of {len(scan.checks)} '
        f'patterns fired · <strong>{scan.critical_hits}</strong> '
        'critical — lit chips read in severity tone.</p>'
    )
    return f'<div style="margin:0 0 14px;">{summary}{chips}</div>'


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
    ) or "<li>No structural questions generated: target profile is clean.</li>"

    # Editorial port (2026-04-29): wrap the scan result body in
    # chartis_shell so it inherits the navy topbar + parchment palette
    # + italic-serif headings instead of standing alone in the legacy
    # _style() doctype.
    from ._chartis_kit import (
        chartis_shell, ck_kpi_block, ck_page_title, ck_provenance_tooltip,
    )
    result_title = ck_page_title(
        f"Bankruptcy-Survivor Scan · {html.escape(scan.target_name)}",
        eyebrow="BANKRUPTCY SURVIVOR",
        meta=f"{scan.patterns_hit}/12 patterns hit · {scan.critical_hits} critical",
    )
    result_explainer = (
        '<p class="ck-bs-explainer">'
        f'<em>Verdict: {html.escape(scan.verdict.value)}.</em> '
        f"{html.escape(_VERDICT_COPY[scan.verdict])} "
        "Each fired pattern cites a falsifiable historical precedent: "
        "refute or confirm before proceeding."
        "</p>"
    )
    body = (
        f"<p style='font-size:13pt;color:#2a2a2a;'>{html.escape(scan.target_name)}</p>"
        f"<div class='verdict' style='border-color:{color};'>"
        f"<div class='verdict-band' style='color:{color};'>"
        f"{html.escape(scan.verdict.value)}</div>"
        f"<div class='verdict-copy'>{html.escape(copy)}</div>"
        f"<div style='margin-top:6pt;font-size:10pt;color:#6b5d3c;'>"
        f"Patterns hit: {scan.patterns_hit} / 12  ·  "
        f"Critical matches: {scan.critical_hits}</div>"
        f"</div>"
        f"{_replay_section(scan)}"
        "<h2>Pattern checks</h2>"
        f"{_pattern_strip(scan)}"
        "<table class='checks'>"
        "<thead><tr><th>Category</th><th>Check</th><th>Status</th>"
        "<th>Narrative</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<h2>Diligence questions</h2>"
        f"<ul>{questions_html}</ul>"
        "<div class='caveat'>Pre-screening only. Structural pattern "
        "matching against known historical failure modes: not a legal "
        "opinion and not a replacement for the full DealAnalysisPacket. "
        "Every case-study comparison cites the named historical deal's "
        "entry EV and outcome from the public-deals corpus.</div>"
        f"<div class='caveat'>Computed {html.escape(scan.computed_at)}.</div>"
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        result_title + result_explainer + body,
        title=f"Bankruptcy-Survivor Scan · {html.escape(scan.target_name)}",
        active_nav="/screening/bankruptcy-survivor",
        extra_css=_EXPLAINER_CSS + _style(),
    )

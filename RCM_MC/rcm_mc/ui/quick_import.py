"""PE Desk Quick Import — create deals directly from the browser.

Renders a form that POSTs to /api/deals/import, so users never
need to use curl or edit files.
"""
from __future__ import annotations

import html
from typing import Any

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip,
)
from .brand import PALETTE


def _field(
    name: str,
    label: str,
    *,
    placeholder: str = "",
    required: bool = False,
    type_: str = "text",
    step: str = "",
    maxlength: str = "",
    hint: str = "",
    pattern: str = "",
    min_: str = "",
    max_: str = "",
    value: str = "",
) -> str:
    req = " required" if required else ""
    val = f' value="{html.escape(value)}"' if value else ""
    req_mark = ' <span style="color:var(--cad-amber);">*</span>' if required else ""
    ml = f' maxlength="{maxlength}"' if maxlength else ""
    st = f' step="{step}"' if step else ""
    pat = f' pattern="{html.escape(pattern)}"' if pattern else ""
    mn = f' min="{min_}"' if min_ else ""
    mx = f' max="{max_}"' if max_ else ""
    # Format-hint line below the input. Renders in muted mono so it
    # reads as a tooltip-like aside rather than a label suffix.
    hint_html = (
        f'<div style="font-family:var(--cad-mono);font-size:10px;'
        f'color:var(--cad-text-faint,#9aa3ad);letter-spacing:0.03em;'
        f'margin-top:3px;">{html.escape(hint)}</div>'
        if hint else ""
    )
    return (
        f'<div class="cad-field">'
        f'<label>{html.escape(label)}{req_mark}</label>'
        f'<input class="cad-input" type="{type_}" name="{name}" '
        f'placeholder="{html.escape(placeholder)}"{val}{req}{st}{ml}{pat}{mn}{mx}>'
        f'{hint_html}'
        f'</div>'
    )


def render_quick_import(success_msg: str = "", error_msg: str = "",
                        prefill: "dict | None" = None) -> str:
    """Render the quick import form page.

    ``prefill`` (e.g. from the Target Screener's "Promote to Pipeline" link)
    pre-populates deal_id / name / state so a screened provider becomes a deal
    in one step — completing the Source → Pipeline workflow.
    """
    prefill = prefill or {}

    def _pf(key: str) -> str:
        return str(prefill.get(key, "") or "")

    alert = ""
    if success_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};'
            f'padding:10px 14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span class="cad-section-code" style="color:{PALETTE["positive"]};'
            f'border-color:{PALETTE["positive"]};">OK</span>'
            f'<p style="margin:0;color:{PALETTE["positive"]};font-family:var(--cad-mono);'
            f'font-size:11.5px;letter-spacing:0.04em;text-transform:uppercase;">'
            f'{html.escape(success_msg)}</p></div></div>'
        )
    if error_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["negative"]};'
            f'padding:10px 14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span class="cad-section-code" style="color:{PALETTE["negative"]};'
            f'border-color:{PALETTE["negative"]};">ERR</span>'
            f'<p style="margin:0;color:{PALETTE["negative"]};font-family:var(--cad-mono);'
            f'font-size:11.5px;letter-spacing:0.04em;text-transform:uppercase;">'
            f'{html.escape(error_msg)}</p></div></div>'
        )

    # Required section
    required_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">Required Identity</h3>'
        f'<span class="cad-section-code">IDN</span></div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field(
            "deal_id", "Deal ID",
            placeholder="e.g. southeast_health",
            required=True,
            pattern="[a-z0-9_-]+",
            hint="Lowercase, digits, _ or - only. Becomes part of the URL.",
            maxlength="64",
            value=_pf("deal_id"),
        )
        + _field(
            "name", "Hospital Name",
            placeholder="e.g. Southeast Health Medical Ctr",
            required=True,
            hint="Free text — appears in headlines and IC memo.",
            maxlength="200",
            value=_pf("name"),
        )
        + '</div>'
    )

    rcm_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">RCM Metrics</h3>'
        f'<span class="cad-section-code">RCM</span>'
        f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
        f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;">Optional</span>'
        f'</div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field(
            "denial_rate", "Denial Rate (%)",
            placeholder="14.2", type_="number", step="0.1",
            min_="0", max_="100",
            hint="As a percent (14.2 not 0.142). HFMA peer median ~10%.",
        )
        + _field(
            "days_in_ar", "Days in AR",
            placeholder="52", type_="number", step="1",
            min_="0", max_="500",
            hint="Integer days. PE healthcare median 45-55; >75 flags AR drag.",
        )
        + _field(
            "net_collection_rate", "Net Collection (%)",
            placeholder="94.5", type_="number", step="0.1",
            min_="0", max_="100",
            hint="Realized cash ÷ allowable charges. PE target 92-95%.",
        )
        + _field(
            "clean_claim_rate", "Clean Claim (%)",
            placeholder="88", type_="number", step="0.1",
            min_="0", max_="100",
            hint="First-pass clean claims. PE target 85-92%.",
        )
        + _field(
            "cost_to_collect", "Cost to Collect (%)",
            placeholder="5.1", type_="number", step="0.1",
            min_="0", max_="100",
            hint="RCM operating cost ÷ net collected. PE target 3-5%.",
        )
        + _field(
            "claims_volume", "Claims Volume",
            placeholder="180,000", type_="text",
            hint="Annual count. Commas are stripped on submit.",
        )
        + '</div>'
    )

    fin_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">Financial Metrics</h3>'
        f'<span class="cad-section-code">FIN</span>'
        f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
        f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;">Optional</span>'
        f'</div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field("net_revenue", "Net Revenue ($)", placeholder="386,000,000", type_="text")
        + _field("bed_count", "Bed Count", placeholder="332", type_="number", step="1")
        + _field("state", "State", placeholder="AL", maxlength="2", value=_pf("state"))
        + '</div>'
    )

    # Cycle 54 — KPI strip with provenance.
    fields_value = ck_provenance_tooltip(
        "Required vs. optional fields",
        "2 / 14",
        explainer=(
            "Only Deal ID and Hospital Name are required - the "
            "platform fills missing RCM and financial fields with "
            "Bayesian priors. Provide more fields to tighten "
            "the predictions and avoid imputation flags on the "
            "first run."
        ),
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Required Fields", "2", "Deal ID + Name")
        + ck_kpi_block("Optional Fields", fields_value, "richer analysis")
        + ck_kpi_block("Bayesian Priors", "12+", "for missing data")
        + '</div>'
    )

    form = (
        ck_eyebrow("Quick Import")
        + kpi_strip
        + f'{alert}'
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">New Deal</h2>'
        f'<span class="cad-section-code">IMP</span></div>'
        f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.04em;color:{PALETTE["text_muted"]};'
        f'text-transform:uppercase;margin-bottom:16px;">'
        f'Only Deal ID and Name required · more fields = richer analysis</p>'
        f'<form method="POST" action="/quick-import" id="quick-import-form">'
        + required_fields
        + rcm_fields
        + fin_fields
        + '<div style="display:flex;gap:8px;padding-top:12px;'
          f'border-top:1px solid {PALETTE["border"]};">'
        + '<button type="submit" class="cad-btn cad-btn-primary">Create Deal &rarr;</button>'
        + '<a href="/portfolio" class="cad-btn" style="text-decoration:none;">Cancel</a>'
        + '</div>'
        + '</form></div>'

        # JSON bulk-import
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Bulk Import</h2>'
        f'<span class="cad-section-code">JSON</span></div>'
        f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.04em;color:{PALETTE["text_muted"]};'
        f'text-transform:uppercase;margin-bottom:12px;">'
        f'Paste a JSON array of deals to import multiple at once</p>'
        f'<form method="POST" action="/quick-import-json">'
        f'<textarea name="json_data" rows="8" class="cad-input" '
        f'placeholder=\'[{{"deal_id": "southeast", "name": "Southeast Health", '
        f'"profile": {{"denial_rate": 14.2, "days_in_ar": 52, "net_revenue": 386000000}}}}]\' '
        f'style="width:100%;resize:vertical;line-height:1.5;"></textarea>'
        f'<div style="display:flex;gap:8px;margin-top:10px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Import JSON &rarr;</button>'
        f'<a href="/api/docs" class="cad-btn" style="text-decoration:none;">Schema Docs</a>'
        f'</div></form></div>'
    )

    # Auto-format the large-number text inputs with commas as the user
    # types, and strip commas back to plain integers right before submit
    # (server expects clean numerics). Targets net_revenue + claims_volume.
    comma_js = """
(function(){
  var ids = ['net_revenue', 'claims_volume'];
  function fmt(v) {
    var clean = (v || '').replace(/[^0-9]/g, '');
    if (!clean) return '';
    return clean.replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
  }
  ids.forEach(function(name){
    var el = document.querySelector('input[name="' + name + '"]');
    if (!el) return;
    el.addEventListener('input', function(){
      var caret = el.selectionStart;
      var before = el.value;
      var formatted = fmt(before);
      if (formatted !== before) {
        el.value = formatted;
        // Best-effort caret restoration
        try { el.setSelectionRange(formatted.length, formatted.length); } catch(e){}
      }
    });
    var form = el.form;
    if (form && !form.__commaStripBound) {
      form.__commaStripBound = true;
      form.addEventListener('submit', function(){
        ids.forEach(function(n){
          var x = form.querySelector('input[name="' + n + '"]');
          if (x) x.value = (x.value || '').replace(/,/g, '');
        });
      });
    }
  });
})();
"""
    next_up = ck_next_section(
        "Open the pipeline",
        "/pipeline",
        eyebrow="Continue —",
        italic_word="pipeline",
    )
    return chartis_shell(
        form + next_up, "Import Deals",
        subtitle="Create deals directly in your browser",
        extra_js=comma_js,
        editorial_intro={
            "eyebrow": "IMPORT DEALS",
            "headline": "Where the deal first lands in the platform.",
            "italic_word": "first",
            "body": (
                "Quick-import form for new deals - paste headline "
                "economics, the platform creates the deal record "
                "and seeds the analysis packet. For bulk imports, "
                "use the JSON / CSV uploaders linked below."
            ),
        },
    )

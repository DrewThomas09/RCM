"""Excel model template library — /excel-templates.

The desk had three ad-hoc .xlsx exports (analysis packet, TAM-SAM,
EBITDA bridge) but no place where an associate grabs a working model
at the start of a CDD or QoE sprint. This page is that shelf: every
card downloads a live-formula workbook from
``rcm_mc.exports.model_templates`` (blue inputs / black formulas),
grouped by the three jobs partners actually staff — deal math, QoE &
accounting, CDD & market work.
"""
from __future__ import annotations

import html as _html

from rcm_mc.exports.model_templates import TEMPLATES, TemplateSpec
from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_page_explainer,
    ck_page_title,
)

# Render order. Categories beyond these (from future templates) append
# after, alphabetically, so a new category can't silently vanish.
_CATEGORY_ORDER = ["Deal Math", "QoE & Accounting", "CDD & Market"]

_CATEGORY_BLURBS = {
    "Deal Math": ("Screen-stage transaction models — answer \"does the "
                  "deal math work?\" before the data room opens."),
    "QoE & Accounting": ("The accounting-diligence workbooks every QoE "
                         "sprint rebuilds: the EBITDA walk and the "
                         "working-capital peg."),
    "CDD & Market": ("Commercial-diligence exhibits: market sizing, payer "
                     "economics, and revenue-quality cohorts."),
}


def _template_card(spec: TemplateSpec) -> str:
    sheets = " · ".join(_html.escape(s) for s in spec.sheets)
    return f"""
<div class="xt-card">
  <div class="xt-card-title">{_html.escape(spec.title)}</div>
  <p class="xt-card-desc">{_html.escape(spec.description)}</p>
  <div class="xt-card-sheets">Sheets: {sheets}</div>
  <a class="xt-download" href="/excel-templates/{_html.escape(spec.slug)}.xlsx"
     download>Download .xlsx</a>
</div>"""


def render_excel_templates(params: dict | None = None) -> str:
    cats: dict = {}
    for spec in TEMPLATES:
        cats.setdefault(spec.category, []).append(spec)
    ordered = [c for c in _CATEGORY_ORDER if c in cats]
    ordered += sorted(c for c in cats if c not in _CATEGORY_ORDER)

    sections = []
    for cat in ordered:
        cards = "".join(_template_card(s) for s in cats[cat])
        blurb = _CATEGORY_BLURBS.get(cat, "")
        sections.append(f"""
<section class="xt-section">
  <h2 class="xt-section-h">{_html.escape(cat)}</h2>
  <p class="xt-section-blurb">{_html.escape(blurb)}</p>
  <div class="xt-grid">{cards}</div>
</section>""")

    n = len(TEMPLATES)
    title = ck_page_title(
        "Excel Model Templates",
        eyebrow="RESEARCH · EXCEL RESOURCES",
        meta=(f"{n} downloadable workbooks · live formulas · "
              "blue inputs / black formulas convention"),
    )
    explainer = ck_page_explainer(
        "Working models, not data dumps.",
        "Every template opens as a functioning model: blue cells are the "
        "assumptions you edit, black cells recompute live. Built for the "
        "first hour of a sprint — swap the seed inputs for the target's "
        "numbers and the workbook is your starting draft, with the desk's "
        "formatting conventions already applied.",
    )
    css = """
<style>
.xt-section { margin: 28px 0; }
.xt-section-h { font-size: 21px; margin: 0 0 4px; color: #0b2341; }
.xt-section-blurb { margin: 0 0 14px; color: #4a5568; max-width: 70ch; }
.xt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.xt-card { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px;
           padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.xt-card-title { font-weight: 600; font-size: 16px; color: #0b2341; }
.xt-card-desc { margin: 0; font-size: 13.5px; line-height: 1.45; color: #1a2332; flex: 1; }
.xt-card-sheets { font-family: "JetBrains Mono", monospace; font-size: 11px;
                  color: #6b7280; letter-spacing: 0.02em; }
.xt-download { align-self: flex-start; background: #155752; color: #fffdf9;
               padding: 7px 14px; border-radius: 4px; font-size: 13px;
               font-weight: 600; text-decoration: none; }
.xt-download:hover { background: #0e3f3b; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  {title}
  {explainer}
  {''.join(sections)}
</div>"""
    return chartis_shell(
        body, title="Excel Model Templates",
        active_nav="/excel-templates", extra_css=css,
    )

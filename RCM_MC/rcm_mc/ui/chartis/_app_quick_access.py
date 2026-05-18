"""Quick-access card row for the /app dashboard.

Ported from the Claude Design home handoff (``HomePage.jsx``
``QuickAccessRow``). Curated cards linking to the surfaces a
returning partner opens most, plus an HCRIS X-Ray screening
shortcut and an All Surfaces catalog entry promoted from the
old small top-right link.

Deliberately a *static* block — no ``store``, no queries — so it is
a zero-cost additive insert into ``app_page.render_app_page``'s
``body_parts`` list. It does not touch the existing data layer or
the page's 3-query perf budget.

Every href is a verified-live route (see ``_CARDS`` — each was
checked against server.py's route table before wiring). The scoped
``<style>`` block is prefixed ``.app-qa`` so its hover rules cannot
leak into the rest of the editorial shell — same scoping discipline
as the bankruptcy-survivor CSS-leak fix.
"""
from __future__ import annotations

import html as _html

# (kicker, label, copy, href, variant). variant="default" is the
# parchment workbench card; variant="catalog" is the navy-filled
# All-Surfaces card that promotes the old small top-right link
# into a properly weighted button. Every href verified present in
# server.py's route table:
#   /analysis · /portfolio/heatmap · /diligence/ic-packet
#   /diligence/hcris-xray · /diligence/bridge-audit
#   /payer-intelligence · /ops · /module-index
_CARDS = [
    ("LFC · Analyze", "Deal workbench",
     "Bloomberg-dense console for the active deal.", "/analysis", "default"),
    ("PRT · Monitor", "Portfolio heatmap",
     "Health scores across every hold in one grid.", "/portfolio/heatmap", "default"),
    ("LFC · Decide", "IC packet",
     "One-click investment committee narrative.", "/diligence/ic-packet", "default"),
    ("DIL · X-Ray", "HCRIS X-Ray",
     "Full filing-level cost-report drill-down.", "/diligence/hcris-xray", "default"),
    ("ANL · Model", "EBITDA bridge",
     "Value-creation waterfall with sensitivity.", "/diligence/bridge-audit", "default"),
    ("MKT · Research", "Payer intelligence",
     "Concentration, mix shift, and reimbursement.", "/payer-intelligence", "default"),
    ("TLS · Operate", "Operations",
     "Global alerts, jobs, and system status.", "/ops", "default"),
    ("NAV · Index", "All surfaces",
     "The full catalog — every page, every workbench.", "/module-index", "catalog"),
]

_STYLE = """
<style>
.app-qa { background:#fff; border-top:1px solid var(--sc-rule);
  border-bottom:1px solid var(--sc-rule); padding:32px 0 36px;
  margin:0 0 var(--sc-s-5); }
.app-qa-inner { max-width:1720px; margin:0 auto;
  padding:0 var(--sc-s-7); }
.app-qa-head { display:flex; align-items:baseline;
  justify-content:space-between; margin-bottom:20px; gap:12px;
  flex-wrap:wrap; }
.app-qa-eyebrow { font-family:var(--sc-sans); font-size:11px;
  font-weight:600; letter-spacing:0.18em; text-transform:uppercase;
  color:var(--sc-text-dim); margin-bottom:8px; }
.app-qa-h2 { font-family:var(--sc-serif); font-weight:400;
  font-size:22px; line-height:1.2; color:var(--sc-navy); margin:0; }
.app-qa-grid { display:grid;
  grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));
  gap:14px; }
.app-qa-card { display:block; padding:18px 18px 16px;
  border:1px solid var(--sc-rule); background:var(--sc-parchment);
  text-decoration:none; position:relative;
  transition:background 120ms ease, border-color 120ms ease; }
.app-qa-card:hover { border-color:var(--sc-teal); background:#fff; }
.app-qa-kicker { font-family:var(--sc-mono); font-size:10px;
  letter-spacing:0.14em; text-transform:uppercase;
  color:var(--sc-teal-ink); margin-bottom:10px; }
.app-qa-label { font-family:var(--sc-serif); font-size:20px;
  font-weight:500; color:var(--sc-navy); line-height:1.2;
  margin-bottom:8px; }
.app-qa-copy { font-size:12.5px; color:var(--sc-text-dim);
  line-height:1.5; }
.app-qa-arrow { position:absolute; right:14px; bottom:12px;
  font-family:var(--sc-mono); font-size:14px; color:var(--sc-teal); }
/* Catalog variant — All Surfaces card. Navy fill so it reads as
   the meta/index entry instead of one more workbench tile. */
.app-qa-card--catalog { background:var(--sc-navy);
  border-color:var(--sc-navy); }
.app-qa-card--catalog:hover { background:var(--sc-navy-2);
  border-color:var(--sc-teal-2); }
.app-qa-card--catalog .app-qa-kicker { color:var(--sc-teal-2); }
.app-qa-card--catalog .app-qa-label { color:#fff; }
.app-qa-card--catalog .app-qa-copy { color:var(--sc-on-navy-dim,
  rgba(255,255,255,0.72)); }
.app-qa-card--catalog .app-qa-arrow { color:var(--sc-teal-2); }
</style>
"""


def render_quick_access() -> str:
    """Render the quick-access card row.

    Static block — no ``store`` arg, no queries. Safe to drop
    anywhere in the /app ``body_parts`` list. The All-Surfaces
    catalog used to be a small top-right link; promoted into the
    grid as a navy-filled card so partners can find it without
    hunting in the header.
    """
    cards = ""
    for kicker, label, copy, href, variant in _CARDS:
        variant_cls = " app-qa-card--catalog" if variant == "catalog" else ""
        cards += (
            f'<a class="app-qa-card{variant_cls}" '
            f'href="{_html.escape(href, quote=True)}">'
            f'<div class="app-qa-kicker">{_html.escape(kicker)}</div>'
            f'<div class="app-qa-label">{_html.escape(label)}</div>'
            f'<div class="app-qa-copy">{_html.escape(copy)}</div>'
            f'<div class="app-qa-arrow">&rarr;</div>'
            f'</a>'
        )
    return (
        _STYLE
        + '<section class="app-qa">'
        '<div class="app-qa-inner">'
        '<div class="app-qa-head">'
        '<div>'
        '<div class="app-qa-eyebrow">Quick access &middot; '
        'the surfaces you open most</div>'
        '<h2 class="app-qa-h2">Jump back into work.</h2>'
        '</div>'
        '</div>'
        f'<div class="app-qa-grid">{cards}</div>'
        '</div>'
        '</section>'
    )

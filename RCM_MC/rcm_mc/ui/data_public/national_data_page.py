"""National Data Catalog — /national-data.

The map of every major U.S. national health database used in healthcare-PE
diligence, grouped by agency, with each one's access model and whether PE
Desk already ingests it. Reference metadata only (from
``data_public.national_data_registry``) — nothing fetches here.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_explainer, ck_page_title,
)

# access model -> (badge label, fg, bg)
_ACCESS_BADGE = {
    "estate":     ("WIRED",       "#0a6a48", "#d9ece2"),
    "api":        ("FREE API",    "#155752", "#e0ece9"),
    "bulk":       ("FREE FILES",  "#155752", "#e0ece9"),
    "query":      ("QUERY ONLY",  "#7a4c16", "#f2e7d1"),
    "restricted": ("RESTRICTED",  "#8a2a1a", "#f2ded7"),
}


def _badge(access: str) -> str:
    label, fg, bg = _ACCESS_BADGE.get(access, (access.upper(), "#5a6472", "#ece5d6"))
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{bg};color:{fg};font-size:10px;font-weight:700;'
        f'font-family:JetBrains Mono,monospace;white-space:nowrap;">{label}</span>'
    )


def _row(d: dict) -> str:
    name = _html.escape(d["name"])
    url = _html.escape(d["url"])
    wired = d.get("wired") or ""
    # Action: wired -> browse in the estate; else -> the source (how to get).
    if d["access"] == "estate" and wired:
        action = (f'<a href="/connector-estate?connector={_html.escape(wired)}" '
                  f'style="color:#155752;font-size:11px;white-space:nowrap;">'
                  f'browse →</a>')
    else:
        action = (f'<a href="{url}" target="_blank" rel="noopener" '
                  f'style="color:#155752;font-size:11px;white-space:nowrap;">'
                  f'source →</a>')
    return (
        '<tr>'
        f'<td style="padding:7px 10px;font-weight:600;color:#0b2341;'
        f'vertical-align:top;">{name}'
        f'<div style="font-weight:400;color:#5a6472;font-size:11.5px;'
        f'margin-top:2px;line-height:1.4;">{_html.escape(d["blurb"])}</div>'
        f'<div style="font-weight:400;color:#8a94a3;font-size:10.5px;'
        f'margin-top:3px;font-style:italic;line-height:1.35;">'
        f'{_html.escape(d["relevance"])}</div></td>'
        f'<td style="padding:7px 10px;vertical-align:top;">{_badge(d["access"])}'
        + (f'<div style="font-size:9.5px;color:#8a94a3;margin-top:3px;'
           f'font-family:JetBrains Mono,monospace;">{_html.escape(wired)}</div>'
           if wired else "")
        + f'</td>'
        f'<td style="padding:7px 10px;vertical-align:top;text-align:right;">{action}</td>'
        '</tr>'
    )


def _agency_section(label: str, rows) -> str:
    trs = "".join(_row(d) for d in rows)
    return (
        '<section style="margin-top:22px;">'
        f'<h2 style="font-size:15px;color:#0b2341;margin:0 0 8px;'
        f'font-family:Source Serif 4,Georgia,serif;">{_html.escape(label)} '
        f'<span style="font-size:11px;color:#8a94a3;font-weight:400;">'
        f'({len(rows)})</span></h2>'
        '<div style="overflow-x:auto;"><table class="nd-table" '
        'style="width:100%;border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #d8cfbf;text-align:left;'
        'font-size:10px;text-transform:uppercase;letter-spacing:0.05em;'
        'color:#7a8699;">'
        '<th style="padding:5px 10px;">Database</th>'
        '<th style="padding:5px 10px;">Access</th>'
        '<th style="padding:5px 10px;text-align:right;">Link</th>'
        f'</tr></thead><tbody>{trs}</tbody></table></div>'
        '</section>'
    )


_FILTER_JS = r"""
(function(){
  var box=document.getElementById('nd-filter');
  if(!box) return;
  var tables=document.querySelectorAll('table.nd-table');
  box.addEventListener('input', function(){
    var q=box.value.trim().toLowerCase();
    tables.forEach(function(tbl){
      var rows=tbl.tBodies[0].rows, anyShown=0;
      for(var i=0;i<rows.length;i++){
        var hit=!q || rows[i].textContent.toLowerCase().indexOf(q)>-1;
        rows[i].style.display=hit?'':'none'; if(hit) anyShown++;
      }
      var sec=tbl.closest('section'); if(sec) sec.style.display=anyShown?'':'none';
    });
  });
})();
"""


def _legend() -> str:
    items = [
        ("estate", "already ingested — browse/query now"),
        ("api", "free public API — candidate ingest"),
        ("bulk", "free downloadable files — candidate ingest"),
        ("query", "free online query tool only — no microdata"),
        ("restricted", "needs a DUA / registration / purchase"),
    ]
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'margin:0 14px 6px 0;font-size:11px;color:#5a6472;">'
        f'{_badge(a)} {_html.escape(desc)}</span>'
        for a, desc in items
    )
    return (
        '<div style="margin:14px 0 4px;padding:10px 12px;background:#fbf8f1;'
        'border:1px solid #ddd3c2;border-radius:8px;">' + chips + '</div>'
    )


def render_national_data(params: dict = None) -> str:
    from rcm_mc.data_public import national_data_registry as ndr

    cov = ndr.coverage()
    meta = (f"{cov['total']} national databases · {cov['agencies']} agencies · "
            f"{cov['wired']} wired · {cov['free']} free · "
            f"{cov['restricted']} restricted")

    kpis = (
        ck_kpi_block("Databases", f'<span class="mn">{cov["total"]}</span>',
                     f'{cov["agencies"]} federal agencies', "") +
        ck_kpi_block("Wired now", f'<span class="mn">{cov["wired"]}</span>',
                     "ingested by an estate connector", "") +
        ck_kpi_block("Free, unwired", f'<span class="mn">{cov["free"]}</span>',
                     "API / bulk — candidate ingest", "") +
        ck_kpi_block("Restricted", f'<span class="mn">{cov["restricted"]}</span>',
                     "DUA / registration / purchase", "")
    )

    filt = (
        '<div style="display:flex;gap:10px;align-items:center;margin:8px 0 4px;">'
        '<input type="search" id="nd-filter" '
        'placeholder="Filter — e.g. emergency, dialysis, drug, readmission, behavioral…" '
        'aria-label="Filter national databases" '
        'style="flex:1;max-width:480px;padding:8px 12px;border:1px solid #d8cfbf;'
        'border-radius:6px;font-size:12.5px;background:#fff;color:#1a2332;">'
        '</div>'
    )

    sections = "".join(
        _agency_section(label, rows) for _aid, label, rows in ndr.by_agency())

    body = (
        ck_page_title("National Data Catalog",
                      eyebrow="Research · The data universe", meta=meta)
        + ck_page_explainer(
            "The map of every major U.S. national health database — not just "
            "the ones we can auto-pull.",
            "PE Desk already ingests the free, API-accessible sources (the "
            "WIRED rows — browse them on the Data Hub). This catalog adds the "
            "rest of the universe a research desk needs: HCUP (NEDS / NIS / "
            "NRD), MEPS, NHANES, SAMHSA, USRDS, SEER and more — each with its "
            "real access model and how to obtain it. Restricted databases "
            "(DUA / purchase) are listed honestly so you know they exist and "
            "how to get them, not pretended to be one-click.",
            source="curated registry · agency access models",
        )
        + f'<div class="ck-kpi-grid" style="margin-top:14px;">{kpis}</div>'
        + _legend()
        + filt
        + sections
    )
    return chartis_shell(
        body, "National Data Catalog",
        active_nav="/national-data",
        subtitle=f"National health-data universe · {meta}",
        extra_js=_FILTER_JS,
    )

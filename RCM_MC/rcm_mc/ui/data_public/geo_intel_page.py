"""Geographic Intelligence hub — /geo-intel.

One landing page for PEdesk's all-real-data state analysis trio:
  • State Comparison (/state-compare) — 2–4 states side by side
  • State Rankings  (/state-rankings) — rank all 50 + DC on one metric
  • State Profile   (/state-profile)  — one state's metrics + national ranks

All three read the same shared metric registry over real public datasets
(Census/ACS · CMS FFS · HRSA HPSA · CMS CHOW · CMS MA · CDC PLACES · CMS
HCAHPS). This hub makes the trio discoverable from the top nav. No data is
rendered here — it is a navigation surface — so nothing can be fabricated.
"""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title

_CARDS = [
    ("State Comparison", "/state-compare",
     "Put 2–4 states side by side across every real state-keyed metric in one table.",
     "Best for: a head-to-head read on a shortlist of target geographies."),
    ("State Rankings", "/state-rankings",
     "Rank all 50 states + DC on any single metric, best-first, with an inline bar.",
     "Best for: origination screening — where does opportunity (or risk) concentrate?"),
    ("State Profile", "/state-profile",
     "One state's full metric set, each shown with its national rank (#k of n).",
     "Best for: a quick dossier on a single market you're underwriting."),
    ("Similar States", "/state-peers",
     "Find the states whose real public-data profile is most like a chosen state.",
     "Best for: building a comp set — “if the thesis works here, where else?”"),
    ("County Explorer", "/county-explorer",
     "Drill into a state's counties on real Census/ACS demographics, sortable.",
     "Best for: sub-state targeting — which counties carry the market?"),
    ("Metro Markets", "/metro-markets",
     "Rank U.S. metro/micro areas (CBSAs) on real demographics rolled up from counties.",
     "Best for: metro-level market sizing — the standard healthcare market unit."),
]

_DATASETS = [
    "Census/ACS demographics", "CMS FFS provider supply", "HRSA HPSA shortage areas",
    "CMS SNF ownership changes", "CMS Medicare Advantage", "CDC PLACES social determinants",
    "CMS HCAHPS patient experience", "CMS MSSP ACOs", "OIG LEIE exclusions",
]


def render_geo_intel(params=None) -> str:
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    cards = ""
    for title, href, desc, best in _CARDS:
        cards += (
            f'<a href="{href}" style="text-decoration:none;display:block;background:{P["panel"]};'
            f'border:1px solid {border};border-left:3px solid {ac};border-radius:3px;'
            f'padding:16px 18px;transition:border-color .15s">'
            f'<div style="font-family:Inter Tight,sans-serif;font-size:15px;font-weight:600;'
            f'color:{tp};margin-bottom:6px">{title} &rarr;</div>'
            f'<div style="font-size:12px;color:{td};margin-bottom:8px;line-height:1.5">{desc}</div>'
            f'<div style="font-size:10px;color:{fa};font-style:italic">{best}</div></a>'
        )

    chips = "".join(
        f'<span style="display:inline-block;background:{P["panel_alt"]};border:1px solid {border};'
        f'border-radius:2px;padding:3px 8px;margin:0 6px 6px 0;font-family:JetBrains Mono,monospace;'
        f'font-size:10px;color:{td}">{d}</span>'
        for d in _DATASETS
    )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("Geographic Intelligence", eyebrow="MARKET INTEL", meta="Three real-data ways to read U.S. healthcare markets by state")}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 18px">
    Screen and underwrite geographies on 100% real public data. The three modes
    below share one metric layer, so the numbers reconcile across them. Every
    figure is sourced; states without a value on record show &ldquo;&mdash;&rdquo;
    and are never fabricated.
  </p>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-bottom:22px">
    {cards}
  </div>
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Powered by these real datasets</div>
  <div>{chips}</div>
  <p style="font-size:11px;color:{td};margin-top:14px">
    See exactly what each metric measures, its source and coverage on
    <a href="/geo-metrics" style="color:{ac};text-decoration:none">Metrics &amp; Sources &rarr;</a>
  </p>
</div>"""
    return chartis_shell(body, "Geographic Intelligence", active_nav="/geo-intel")

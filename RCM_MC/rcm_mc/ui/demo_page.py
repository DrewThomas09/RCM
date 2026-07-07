"""Demo Mode page — /demo.

The partner-facing tutorial entry point (reached from Settings → Demo Mode).
One click loads a curated, credible **KKR healthcare portfolio** into the
workspace so the command center, portfolio map, alerts, cohorts, deal pages and
PE math all populate with real deals — letting the demo showcase every feature
with true (real deals / disclosed EVs) and consistent (modeled ops) numbers.
Also offers the same data as downloadable ingestion files (JSON + CSV) plus
step-by-step instructions, so a partner can learn the import format too.

This is the outward-facing first impression for prospects, so it renders through
the full v5 chartis editorial cadence: an ``ck_editorial_head`` masthead (eyebrow
→ serif headline → italic-first-phrase lede → meta → legend), a KPI strip with
provenance tooltips, a reversible load/loaded action card, dataset cards for the
downloads, a ``ck_data_table`` portfolio preview with human tier chips, and a
numbered walkthrough — all built from kit primitives and page-scoped classes so
the surface carries zero inline styles and no legacy Bloomberg-navy chrome.
"""
from __future__ import annotations

import html as _html
import statistics

from ._chartis_kit import (
    chartis_shell,
    ck_action_button,
    ck_arrow_link,
    ck_data_cell,
    ck_data_table,
    ck_editorial_head,
    ck_fmt_currency,
    ck_fmt_moic,
    ck_illustrative_note,
    ck_kpi_block,
    ck_next_section,
    ck_page_actions,
    ck_panel,
    ck_provenance_tooltip,
    ck_section_header,
    ck_signal_badge,
    ck_tier_chip,
)
from ..demo.kkr_demo import demo_deal_rows


# Semantic tier mapping — supersedes the legacy color-only ``_TIER_COLOR``
# hex map. Each tier gets (a) a kit semantic color (dot on the chip) and
# (b) a human label, so the column is no longer colorblind-hostile internal
# jargon ("green"/"amber"/"red") but a readable status a prospect understands.
_TIER_PALETTE = {
    "green": "var(--sc-positive,#0a8a5f)",
    "amber": "var(--sc-warning,#b8732a)",
    "red": "var(--sc-negative,#b5321e)",
}
_TIER_LABEL = {"green": "On plan", "amber": "Watch", "red": "Distressed"}
_TIER_GLOSS = {
    "green": "healthy compounders",
    "amber": "levered / drifting",
    "red": "covenant-tripped",
}


# Page-scoped CSS. Every rule uses a kit CSS custom property with its
# canonical fallback (no invented hexes), so the page inherits the v5
# palette while keeping the handful of page-local affordances (the
# negative-tone unload ghost button, the download CTAs, the numbered
# walkthrough) styled by class rather than inline ``style=`` attributes.
_EXTRA_CSS = """
.demo-wrap{max-width:1040px;margin:0 auto;}
.demo-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:14px;}
.demo-actions .cad-btn{margin:0;}
.demo-lede-copy{font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:13px;
  line-height:1.6;color:var(--sc-text-dim,#5C6878);margin:0;}
.demo-loaded-head{font-family:var(--sc-serif,Georgia,serif);font-size:17px;font-weight:600;
  color:var(--sc-positive,#0a8a5f);margin:0 0 4px;}
.demo-loaded>.ck-panel{border-left:3px solid var(--sc-positive,#0a8a5f);}
.demo-cta{display:inline-flex;align-items:center;gap:7px;}
.demo-warn{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:14px 0 0;}
.demo-note-dim{font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:11.5px;
  color:var(--sc-text-dim,#5C6878);}
.demo-unload-row{margin-top:16px;padding-top:14px;border-top:1px solid var(--sc-rule,#d6cfc0);
  display:flex;flex-wrap:wrap;align-items:center;gap:8px;}
.demo-unload-btn{background:none;border:1px solid var(--sc-negative,#b5321e);
  color:var(--sc-negative,#b5321e);padding:6px 14px;border-radius:3px;
  font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:11.5px;font-weight:600;cursor:pointer;}
.demo-unload-btn:hover{background:var(--sc-negative,#b5321e);color:#fff;}
.demo-unload-btn:focus-visible{outline:2px solid var(--sc-negative,#b5321e);outline-offset:2px;}
.demo-file-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(248px,1fr));gap:14px;}
.demo-file{display:flex;flex-direction:column;align-items:flex-start;gap:9px;}
.demo-file-name{font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:13px;
  font-weight:600;color:var(--ink,#16263a);}
.demo-file-desc{font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:12px;
  line-height:1.55;color:var(--sc-text-dim,#5C6878);margin:0;}
.demo-download{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;
  border:1px solid var(--green-deep,#154e36);border-radius:3px;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;font-weight:600;color:var(--green-deep,#154e36);text-decoration:none;}
.demo-download:hover{background:var(--green-deep,#154e36);color:var(--paper-card,#fefcf3);}
.demo-download:focus-visible{outline:2px solid var(--green-deep,#154e36);outline-offset:2px;}
.demo-steps{list-style:none;counter-reset:demostep;margin:0;padding:0;}
.demo-steps li{position:relative;counter-increment:demostep;padding:0 0 16px 46px;}
.demo-steps li:last-child{padding-bottom:0;}
.demo-steps li::before{content:counter(demostep,decimal-leading-zero);position:absolute;
  left:0;top:1px;font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:12px;
  font-weight:600;color:var(--green-deep,#154e36);letter-spacing:.04em;}
.demo-step-title{font-family:var(--sc-serif,Georgia,serif);font-size:15px;font-weight:600;
  color:var(--ink,#16263a);display:block;margin-bottom:3px;}
.demo-step-body{font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:12.5px;
  line-height:1.55;color:var(--sc-text-dim,#5C6878);}
.demo-legend{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;
  font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:11.5px;
  color:var(--sc-text-dim,#5C6878);margin:12px 0 0;}
.demo-foot{font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10.5px;
  line-height:1.55;color:var(--sc-text-faint,#8A92A0);margin:10px 0 0;}
.demo-modeled{color:var(--sc-warning,#b8732a);font-weight:600;cursor:help;margin-left:1px;}
.demo-src{color:var(--sc-teal-ink,#0f3d39);text-decoration:none;font-weight:600;}
.demo-src:hover{text-decoration:underline;}
.demo-src-arrow{font-size:10px;color:var(--sc-text-faint,#8A92A0);}
"""


def _ev_cell(mm: int, disclosed: bool) -> str:
    """Format an entry-EV value via the kit currency helper, marking modeled
    figures with an asterisk whose meaning is disclosed in the table footnote
    and the ``Disclosed EVs`` KPI tooltip. Disclosed EVs render clean."""
    cur = ck_fmt_currency(mm * 1e6)
    if disclosed:
        return cur
    return (
        f'{cur}<span class="demo-modeled" title="Modeled at a sector-typical '
        'entry multiple — not a publicly disclosed figure.">*</span>'
    )


def _deal_name_cell(name: str, source_url: str) -> str:
    """Deal name, linked to its public source when one exists (the whole pitch
    is credibility — every deal carries a press-release / filing URL). Falls
    back to plain escaped text when a source is missing."""
    safe = _html.escape(name)
    if not source_url:
        return safe
    return (
        f'<a class="demo-src" href="{_html.escape(source_url)}" target="_blank" '
        f'rel="noopener" title="Open the public source for {safe}">{safe} '
        '<span class="demo-src-arrow" aria-hidden="true">&#8599;</span></a>'
    )


def _kpi_strip(n: int, total_ev_mm: int, disclosed: int, median_moic: float) -> str:
    """Four-tile KPI strip leading with the numbers that make the dataset
    credible. ``value`` fields are trusted server-rendered markup (the
    documented ``ck_kpi_block`` exemption) — no user input reaches them."""
    ev_value = ck_provenance_tooltip(
        "Entry EV",
        ck_fmt_currency(total_ev_mm * 1e6),
        explainer=(
            "Aggregate entry enterprise value across all "
            f"{n} deals. Publicly disclosed where reported "
            "(Envision, Cotiviti, BrightSpring, Therapy Brands); "
            "the remainder modeled at sector-typical entry multiples."
        ),
    )
    disclosed_value = ck_provenance_tooltip(
        "Disclosed EVs",
        f'<span class="mn">{disclosed} of {n}</span>',
        explainer=(
            "Enterprise values are the real, publicly reported figures "
            "for the deals where one was disclosed; the remaining EVs are "
            "modeled at sector-typical entry multiples and flagged with an "
            "asterisk (*) in the preview table below."
        ),
        inject_css=False,
    )
    moic_value = ck_provenance_tooltip(
        "Median MOIC",
        ck_fmt_moic(median_moic),
        explainer=(
            "Median modeled multiple-on-invested-capital across the roster. "
            "MOIC, IRR, leverage and quarterly variance are modeled from each "
            "deal's performance tier — internally consistent, not audited returns."
        ),
        inject_css=False,
    )
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Deals", f'<span class="mn">{n}</span>',
                       "real KKR investments")
        + ck_kpi_block("Entry EV", ev_value, "disclosed + modeled")
        + ck_kpi_block("Disclosed EVs", disclosed_value, "publicly reported")
        + ck_kpi_block("Median MOIC", moic_value, "modeled from tier")
        + '</div>'
    )


def _action_card(loaded: bool, deal_count: int) -> str:
    """The reversible load / loaded action card.

    Unloaded → a panel with the primary ``Load KKR demo portfolio`` submit
    (posts to /demo/load) plus a warning badge when the workspace already
    holds deals. Loaded → a positive-accented panel with the command-center
    CTA, teal secondaries, and the reversible unload form (posts to
    /demo/unload). Both states are kit panels — no hand-rolled navy chrome.
    """
    if loaded:
        body = (
            '<p class="demo-loaded-head">Your demo workspace is live.</p>'
            f'<p class="demo-lede-copy">The KKR portfolio is in your workspace '
            f'— {deal_count} deals total. Open the command center to see every '
            'surface populated with real deals and modeled operating metrics.</p>'
            '<div class="demo-actions">'
            '<a class="cad-btn cad-btn-primary demo-cta" href="/app">'
            'Open command center <span aria-hidden="true">&#8594;</span></a>'
            + ck_arrow_link("Portfolio map", "/portfolio/map")
            + ck_arrow_link("Alerts", "/alerts")
            + '</div>'
            '<form method="post" action="/demo/unload">'
            '<div class="demo-unload-row">'
            '<span class="demo-note-dim">Done exploring?</span>'
            '<button type="submit" class="demo-unload-btn">Unload demo portfolio</button>'
            '<span class="demo-note-dim">Removes the KKR deals and all their '
            'data — your own deals are untouched.</span>'
            '</div></form>'
        )
        return (
            '<div class="demo-loaded">'
            + ck_panel(body, title="Demo portfolio loaded")
            + '</div>'
        )

    warn = ""
    if deal_count:
        warn = (
            '<p class="demo-warn">'
            + ck_signal_badge(f"{deal_count} existing deal(s)", tone="warning")
            + '<span class="demo-note-dim">Loading the demo adds the KKR deals '
            'alongside your own — your deals stay untouched.</span></p>'
        )
    body = (
        '<p class="demo-lede-copy">Seeds your workspace with the KKR deals below '
        '— snapshots, MOIC/IRR, covenant headroom, RCM metrics, quarterly '
        'variance, tags and owners — so every surface populates. Idempotent: '
        'safe to click more than once.</p>'
        '<form method="post" action="/demo/load"><div class="demo-actions">'
        + ck_action_button("Load KKR demo portfolio")
        + '</div></form>'
        + warn
    )
    return ck_panel(body, title="Load the demo portfolio")


def _file_card(fmt: str, filename: str, href: str, desc: str) -> str:
    """One dataset card — format badge, mono filename, what-it-contains
    description, and a download CTA. Kit panel, page-local CTA class."""
    body = (
        '<div class="demo-file">'
        + ck_signal_badge(fmt, tone="neutral")
        + f'<span class="demo-file-name">{_html.escape(filename)}</span>'
        + f'<p class="demo-file-desc">{desc}</p>'
        + f'<a class="demo-download" href="{href}" download>Download {fmt} '
        '<span aria-hidden="true">&#8595;</span></a>'
        + '</div>'
    )
    return ck_panel(body)


# Step-by-step walkthrough. Bodies carry trusted developer markup (in-app
# links, <b>, <code>) rendered raw; only the title is escaped. Anchors carry
# no inline color — the shell styles them teal.
_STEPS = [
    ("Load the demo",
     "Click <b>Load KKR demo portfolio</b> at the top of this page. The "
     "workspace fills with KKR's real healthcare deals; the command center, "
     "map, alerts and every deal page populate at once. A <b>Demo mode</b> "
     "banner appears on the home page so you always know you're in the demo — "
     "and you can <b>unload</b> it from here in one click when you're done."),
    ("Open the command center",
     "Go to <a href='/app'>the command center</a> — the home view now shows "
     "KKR's portfolio: pipeline funnel, active alerts, the health-band "
     "distribution (green winners through the red Envision write-off), recent "
     "deals and deadlines."),
    ("Explore the portfolio map and cohorts",
     "The <a href='/portfolio/map'>portfolio map</a> shades the real US states "
     "the deals sit in (16 deals across 12 states, CON jurisdictions flagged); "
     "<a href='/portfolio/heatmap'>heatmap</a>, <a href='/cohorts'>cohorts</a> "
     "and <a href='/watchlist'>watchlist</a> all resolve to these KKR deals."),
    ("Drill into a deal",
     "Open <b>Cotiviti</b> (a healthy compounder) and the distressed "
     "<b>Envision</b> side by side: snapshot trail, the seven-quarter EBITDA "
     "trajectory plus variance, RCM profile, the PE bridge with its modeled "
     "improvement opportunity, covenant headroom and the health trend. Envision "
     "tells the honest downside (covenant tripped, EBITDA sliding ~30% below "
     "plan into Chapter 11); <b>Gland Pharma</b> is the ~4x upside bookend."),
    ("Work the alerts and deadlines",
     "<a href='/alerts'>Alerts</a> are already mid-lifecycle — one acked, one "
     "snoozed, and Envision's covenant breach left live — so you can see ack / "
     "snooze / escalate end to end. <a href='/deadlines'>Deadlines</a> show "
     "upcoming and overdue items (restructuring review, covenant tests)."),
    ("(Optional) inspect and re-import the data",
     "The ingestion files above are the real import format and round-trip "
     "cleanly: feed <b>kkr-deals.json</b> to <code>/api/deals/import</code> or "
     "<b>kkr-deals.csv</b> to the CSV importer and the KKR deals (sector, "
     "sponsor, vintage, RCM metrics) come back. Hand them to a colleague to "
     "seed their own workspace."),
]


def render_demo_page(loaded: bool = False, deal_count: int = 0) -> str:
    """Render the Demo Mode page.

    ``loaded`` — the KKR demo portfolio is already present in this workspace.
    ``deal_count`` — number of deals currently in the workspace (any source).
    """
    rows = demo_deal_rows()
    n = len(rows)
    total_ev_mm = sum(r["entry_ev_mm"] for r in rows)
    disclosed = sum(1 for r in rows if r["ev_disclosed"])
    median_moic = statistics.median([r["moic"] for r in rows])

    # --- Editorial masthead (eyebrow → serif h1 → meta → italic lede → legend)
    head = ck_editorial_head(
        "SETTINGS · DEMO MODE",
        "Demo Mode — KKR healthcare portfolio",
        meta=(
            f"{n} REAL KKR DEALS · {ck_fmt_currency(total_ev_mm * 1e6)} ENTRY EV "
            f"· {disclosed} DISCLOSED EVS · ONE-CLICK LOAD"
        ),
        lede_italic_phrase="One click loads a credible KKR healthcare portfolio",
        lede_body=(
            "so the command center, portfolio map, alerts, cohorts and every "
            "deal page populate at once with real KKR investments and modeled, "
            "internally consistent operating metrics — including the honest "
            "downside of the Envision write-off."
        ),
        source_note=(
            "Real KKR investments; operating metrics modeled per performance tier"
        ),
        show_legend=True,
    )

    kpi_strip = _kpi_strip(n, total_ev_mm, disclosed, median_moic)
    action = _action_card(loaded, deal_count)

    # --- Portfolio preview table ---------------------------------------------
    trows = []
    for s in sorted(rows, key=lambda r: -r["entry_ev_mm"]):
        moic = s["moic"]
        moic_tone = "pos" if moic >= 2.5 else ("neg" if moic < 1.0 else None)
        tier = s["performance_tier"]
        tier_chip = ck_tier_chip(
            tier, palette=_TIER_PALETTE, label=_TIER_LABEL.get(tier, tier))
        sector = _html.escape(s["sector"].replace("_", " ").title())
        trows.append(
            "<tr>"
            + ck_data_cell(_deal_name_cell(s["name"], s.get("source_url") or ""),
                           weight=600)
            + ck_data_cell(sector, tone="dim")
            + ck_data_cell(str(s["vintage"]), align="right", mono=True)
            + ck_data_cell(_ev_cell(s["entry_ev_mm"], s["ev_disclosed"]),
                           align="right", mono=True)
            + ck_data_cell(ck_fmt_moic(moic), align="right", mono=True, tone=moic_tone)
            + ck_data_cell(tier_chip)
            + "</tr>"
        )
    table = ck_data_table(
        headers=[
            {"label": "Deal"},
            {"label": "Sector"},
            {"label": "Vintage", "align": "right"},
            {"label": "Entry EV", "align": "right"},
            {"label": "MOIC", "align": "right"},
            {"label": "Tier"},
        ],
        rows_html="".join(trows),
    )
    legend = (
        '<p class="demo-legend"><span>Tier drives the modeled operating metrics:</span>'
        + "".join(
            ck_tier_chip(t, palette=_TIER_PALETTE, label=_TIER_LABEL[t])
            + f'<span>{_TIER_GLOSS[t]}</span>'
            for t in ("green", "amber", "red")
        )
        + '</p>'
    )
    foot = (
        '<p class="demo-foot">* Enterprise value modeled at a sector-typical '
        'entry multiple; unmarked EVs are publicly disclosed (Envision, '
        'Cotiviti, BrightSpring, Therapy Brands). MOIC, IRR, leverage and '
        "quarterly variance are modeled from each deal's performance tier — "
        'realistic and internally consistent, not audited returns. Every deal '
        'is a real KKR investment.</p>'
    )
    preview = (
        ck_section_header("The portfolio you will load", eyebrow="PREVIEW", count=n)
        + table + legend + foot + ck_illustrative_note("operating metrics")
    )

    # --- Ingestion files ------------------------------------------------------
    files = (
        ck_section_header("Ingestion files", eyebrow="DOWNLOADS", count=2)
        + '<div class="demo-file-grid">'
        + _file_card(
            "JSON", "kkr-deals.json", "/demo/download/kkr-deals.json",
            f"{n} deals with nested profile — sponsor, sector, vintage, HQ "
            "state, EV, MOIC/IRR and RCM observed metrics. The exact shape "
            "POST /api/deals/import consumes, so it round-trips to real, "
            "profile-populated deals.")
        + _file_card(
            "CSV", "kkr-deals.csv", "/demo/download/kkr-deals.csv",
            f"The same {n} deals as a flat, spreadsheet-friendly table (one "
            "row per deal, no nested profile) for the CSV importer or a quick "
            "review in Excel.")
        + '</div>'
    )

    # --- Walkthrough ----------------------------------------------------------
    steps_html = "".join(
        f'<li><span class="demo-step-title">{_html.escape(t)}</span>'
        f'<span class="demo-step-body">{b}</span></li>'
        for t, b in _STEPS
    )
    tutorial = (
        ck_section_header("How to run the demo", eyebrow="WALKTHROUGH",
                          count=len(_STEPS))
        + f'<ol class="demo-steps">{steps_html}</ol>'
    )

    body = (
        '<div class="demo-wrap">'
        + head + kpi_strip + action + preview + files + tutorial
        + ck_page_actions()
        + ck_next_section("Open the command center", "/app",
                          eyebrow="Ready", italic_word="command")
        + '</div>'
    )
    return chartis_shell(
        body, "Demo Mode", active_nav="/settings",
        subtitle="Load a credible KKR healthcare portfolio to showcase every feature",
        extra_css=_EXTRA_CSS,
    )

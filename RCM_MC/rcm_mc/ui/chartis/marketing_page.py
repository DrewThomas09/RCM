"""PE Desk — public marketing landing page.

Standalone self-contained HTML served at ``GET /`` for anonymous
visitors (under ``CHARTIS_UI_V2=1``). Port of
``marketing-handoff/reference.html`` — the Claude Design editorial
target. This page renders its own ``<style>`` block and does NOT go
through ``chartis_shell``: marketing pages stay standalone so the
public front door is a single clean document with no app chrome.

Uses the refined editorial palette (warm parchment ``#F2EDE3``,
deep editorial teal ``#1F7A75``) embedded locally — the same
refinement that the WS3-A platform-palette PR rolls out app-wide.

Sections, top to bottom:
  1. Top bar — brand + nav + Sign In + Request Access
  2. Crumbs — Home > PE Desk
  3. Hero — eyebrow, serif H1 w/ italic, lede, 2 CTAs, mono meta col
  4. Value-prop trio — 3 bordered cells
  5. Platform — section header + paired funnel / conversion table
  6. Proof grid — 8 fund-level KPI cells
  7. Modules — section header + 4-column module catalog
  8. Pull quote — quote + 3-stat sidebar
  9. Sources — section header + paired sources funnel / inventory
  10. CTA strip — dark, "Bring your own model"
  11. Footer

All CTAs route to ``/login?next=/app``. Top-nav links smooth-scroll
within the page (``#platform`` / ``#modules`` / ``#proof`` /
``#sources``). Numbers on the page are illustrative showcase
figures — this is a pre-login surface, not a live data view.
"""
from __future__ import annotations

# CTA target — every "sign in" / "request access" / "open console"
# affordance on this page points here. Kept as a module constant so
# the route is wired in exactly one place.
_LOGIN = "/login?next=/app"


# ── Style block — ported verbatim from reference.html, refined palette ──

_STYLE = """
<style>
  :root {
    --bg: #F2EDE3;
    --bg-alt: #ECE5D6;
    --bg-tint: #E8E0D0;
    --paper: #FAF7F0;
    --paper-pure: #FFFFFF;
    --border: #D6CFC0;
    --rule: #BFB6A2;
    --ink: #0F1C2E;
    --ink-2: #1A2840;
    --muted: #5C6878;
    --faint: #8A92A0;
    --teal: #1F7A75;
    --teal-soft: #D4E4E2;
    --teal-deep: #155752;
    --green: #3F7D4D;
    --amber: #B7791F;
    --red: #A53A2D;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: "Source Serif 4", Georgia, serif; font-size: 16px; line-height: 1.55;
    -webkit-font-smoothing: antialiased; scroll-behavior: smooth;
  }
  .sans { font-family: "Inter", sans-serif; }
  .mono { font-family: "JetBrains Mono", monospace; font-feature-settings: "tnum" on; }

  /* TOP BAR */
  .topbar {
    background: var(--paper-pure); border-bottom: 1px solid var(--border);
    padding: 0 2rem; display: flex; align-items: center; gap: 1rem; height: 72px;
  }
  .brand { display:flex; align-items:center; gap:.7rem; text-decoration:none; }
  .brand-mark {
    width: 38px; height: 38px; border: 1.5px solid var(--ink); border-radius: 999px;
    display: flex; align-items: center; justify-content: center;
    font-family: "Source Serif 4", serif; font-size: 1rem; font-weight: 600;
    color: var(--ink);
  }
  .brand-name { font-family: "Source Serif 4", serif; font-size: 1.4rem; font-weight: 600; color: var(--ink); }
  .brand-name em { font-style: italic; font-weight: 500; }
  .topnav {
    display: flex; gap: 0; margin-left: 2rem;
    font-family: "Inter", sans-serif; font-size: .76rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
  }
  .topnav a { padding: 0 1.1rem; color: var(--ink); text-decoration: none; }
  .topnav a:hover { color: var(--teal-deep); }
  .topbar-right { margin-left: auto; display: flex; align-items: center; gap: 1rem; }
  .signin {
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    text-decoration: none; padding: 0 .75rem;
  }
  .signin:hover { color: var(--ink); }
  .cta-btn {
    background: var(--ink); color: var(--paper);
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: .8rem 1.4rem; border: none; cursor: pointer; text-decoration: none;
    display: inline-block;
  }
  .cta-btn:hover { background: var(--teal-deep); }

  /* CRUMBS */
  .crumbs {
    background: var(--bg); padding: .9rem 2rem; border-bottom: 1px solid var(--border);
    font-family: "Inter", sans-serif; font-size: .72rem; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
  }
  .crumbs .sep { margin: 0 .55rem; color: var(--faint); }
  .crumbs .here { color: var(--ink); font-weight: 600; }

  /* HERO */
  .page { padding: 0 2rem 4rem; max-width: 1500px; margin: 0 auto; }
  .hero {
    display: grid; grid-template-columns: 1fr 360px; gap: 3rem;
    padding: 4rem 0 3rem; border-bottom: 1px solid var(--rule);
  }
  .eyebrow {
    font-family: "Inter", sans-serif; font-size: .72rem; letter-spacing: .14em;
    text-transform: uppercase; color: var(--muted); font-weight: 600;
    display: flex; align-items: center; gap: .6rem; margin-bottom: 1.25rem;
  }
  .eyebrow .dot { color: var(--faint); }
  .eyebrow .slug { font-family: "JetBrains Mono", monospace; color: var(--teal-deep); letter-spacing: .04em; }
  h1.title {
    font-family: "Source Serif 4", serif; font-weight: 400;
    font-size: clamp(3.5rem, 6vw, 5.5rem); line-height: 0.98; letter-spacing: -0.025em;
    color: var(--ink); margin: 0 0 1.5rem;
  }
  h1.title em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .lede {
    font-family: "Source Serif 4", serif; font-size: 1.4rem; line-height: 1.4;
    color: var(--muted); max-width: 620px; margin: 0 0 2rem;
  }
  .hero-actions { display: flex; gap: 1rem; align-items: center; }
  .ghost-btn {
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--ink);
    padding: .8rem 0; border-bottom: 1px solid var(--ink); text-decoration: none;
  }
  .ghost-btn:hover { color: var(--teal-deep); border-bottom-color: var(--teal-deep); }
  .hero-meta {
    border-left: 1px solid var(--rule); padding-left: 2rem;
    font-family: "JetBrains Mono", monospace; font-size: .8rem;
    color: var(--muted); display: flex; flex-direction: column; gap: .9rem;
  }
  .hero-meta .row { display: flex; gap: .5rem; }
  .hero-meta .row .k { color: var(--faint); width: 80px; }
  .hero-meta .row .v { color: var(--ink); font-weight: 600; }
  .hero-meta .stamp {
    margin-top: .5rem; padding: .9rem 0;
    border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    font-family: "Source Serif 4", serif; font-style: italic;
    font-size: .9rem; color: var(--ink); line-height: 1.5;
  }

  /* VALUE PROP TRIO */
  .triplet {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 3rem 0;
  }
  .trip-cell { padding: 2rem 1.75rem; border-right: 1px solid var(--border); }
  .trip-cell:last-child { border-right: none; }
  .trip-num {
    font-family: "JetBrains Mono", monospace; font-size: .72rem;
    color: var(--teal-deep); letter-spacing: .04em; margin-bottom: .8rem;
  }
  .trip-h {
    font-family: "Source Serif 4", serif; font-weight: 400; font-size: 1.4rem;
    line-height: 1.2; color: var(--ink); margin: 0 0 .75rem;
  }
  .trip-h em { font-style: italic; color: var(--teal-deep); }
  .trip-p { font-size: .92rem; color: var(--muted); line-height: 1.55; margin: 0; }

  /* SECTION HEADERS */
  .sect {
    display: grid; grid-template-columns: 1fr 1.3fr; gap: 3rem; align-items: end;
    padding: 4rem 0 1.5rem; border-top: 1px solid var(--rule); margin-top: 1rem;
  }
  .sect h2 {
    font-family: "Source Serif 4", serif; font-weight: 400;
    font-size: clamp(2.3rem, 3.6vw, 3.4rem); line-height: 1.05;
    letter-spacing: -0.018em; color: var(--ink); margin: .35rem 0 0;
  }
  .sect h2 em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .micro {
    font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
  }
  .desc {
    font-family: "Source Serif 4", serif; font-size: 1.05rem; line-height: 1.55;
    color: var(--muted); margin: 0; max-width: 620px;
  }

  /* DATA SHOWCASE — paired viz + dataset (signature element) */
  .pair {
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 1.5rem 0;
  }
  .pair .viz { padding: 2rem; border-right: 1px solid var(--border); }
  .pair .data { background: var(--bg); }
  .data-h {
    padding: .9rem 1.25rem; border-bottom: 1px solid var(--border);
    font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    display: flex; justify-content: space-between; align-items: center;
  }
  .data-h .src {
    font-family: "JetBrains Mono", monospace; text-transform: none;
    letter-spacing: 0; color: var(--teal-deep); font-size: .72rem;
  }
  .pair table { width: 100%; border-collapse: collapse;
    font-family: "JetBrains Mono", monospace; font-size: .82rem; }
  .pair th {
    text-align: left; padding: .55rem 1.25rem; color: var(--faint);
    font-weight: 600; font-size: .62rem; letter-spacing: .12em;
    text-transform: uppercase; border-bottom: 1px solid var(--border);
    font-family: "Inter", sans-serif;
  }
  .pair td {
    padding: .55rem 1.25rem; border-bottom: 1px solid var(--border);
    color: var(--ink); font-variant-numeric: tabular-nums;
  }
  .pair tr:last-child td { border-bottom: none; }
  .pair td.r { text-align: right; }
  .pair td.lbl { color: var(--muted); font-family: "Inter", sans-serif; font-size: .9rem; }
  .pair tr.hot td { background: var(--bg-tint); }
  .pair tr.hot td:first-child { border-left: 2px solid var(--amber); }

  /* FUNNEL */
  .funnel { display: grid; grid-template-columns: repeat(7, 1fr); gap: .15rem; }
  .funnel .stage { background: var(--bg); padding: 1rem .85rem; border-top: 2px solid var(--teal); }
  .funnel .nm {
    font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    margin-bottom: .5rem;
  }
  .funnel .ct {
    font-family: "Source Serif 4", serif; font-size: 1.7rem; color: var(--ink);
    line-height: 1; margin-bottom: .25rem;
  }
  .funnel .ev {
    font-family: "JetBrains Mono", monospace; font-size: .72rem;
    color: var(--teal-deep); margin-bottom: .5rem;
  }
  .funnel .bar { height: 3px; background: var(--border); }
  .funnel .bar i { display: block; height: 100%; background: var(--teal); }

  /* PROOF GRID */
  .proof {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 1.5rem 0 0;
  }
  .proof-cell {
    padding: 1.5rem 1.25rem; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
  }
  .proof-cell:nth-child(4n) { border-right: none; }
  .proof-cell:nth-last-child(-n+4) { border-bottom: none; }
  .proof-v {
    font-family: "Source Serif 4", serif; font-size: 2.2rem; line-height: 1;
    color: var(--ink); margin-bottom: .5rem;
  }
  .proof-v em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .proof-l {
    font-family: "Inter", sans-serif; font-size: .72rem; letter-spacing: .12em;
    text-transform: uppercase; color: var(--muted); font-weight: 600;
  }
  .proof-d {
    font-family: "Source Serif 4", serif; font-size: .88rem; color: var(--muted);
    margin-top: .5rem; line-height: 1.45;
  }

  /* MODULE CATALOG */
  .catalog {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 1.5rem 0;
  }
  .cat-col { border-right: 1px solid var(--border); }
  .cat-col:last-child { border-right: none; }
  .cat-h {
    padding: .9rem 1.25rem; border-bottom: 1px solid var(--border); background: var(--bg);
    display: flex; justify-content: space-between; align-items: center;
  }
  .cat-h .ttl {
    font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .14em; color: var(--ink);
  }
  .cat-h .lvl {
    font-family: "JetBrains Mono", monospace; font-size: .6rem;
    padding: .15rem .45rem; border: 1px solid var(--border); color: var(--muted);
  }
  .cat-h .lvl.fund { background: var(--teal-soft); color: var(--teal-deep); border-color: var(--teal); }
  .cat-col table { width: 100%; border-collapse: collapse; }
  .cat-col td {
    padding: .55rem 1.25rem; font-size: .82rem;
    border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums;
  }
  .cat-col tr:last-child td { border-bottom: none; }
  .cat-col td.lbl { color: var(--muted); font-family: "Inter", sans-serif; }
  .cat-col td.r { text-align: right; font-family: "JetBrains Mono", monospace; color: var(--ink); font-weight: 600; }
  .cat-col tr:hover td { background: var(--bg-tint); }

  /* TESTIMONIAL / PULL QUOTE */
  .pull {
    margin: 3rem 0; padding: 2.5rem 3rem; background: var(--paper-pure);
    border: 1px solid var(--rule); border-left: 3px solid var(--teal);
    display: grid; grid-template-columns: 1fr 280px; gap: 3rem; align-items: center;
  }
  .pull q {
    font-family: "Source Serif 4", serif; font-style: italic; font-weight: 400;
    font-size: 1.6rem; line-height: 1.4; color: var(--ink);
  }
  .pull .attr {
    font-family: "Inter", sans-serif; font-size: .82rem; color: var(--muted);
    margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border);
  }
  .pull .attr b { color: var(--ink); display: block; margin-bottom: .15rem; }
  .pull .stats {
    border-left: 1px solid var(--border); padding-left: 2rem;
    display: flex; flex-direction: column; gap: 1rem;
  }
  .pull .stat-v {
    font-family: "Source Serif 4", serif; font-size: 2rem; color: var(--teal-deep); line-height: 1;
  }
  .pull .stat-l {
    font-family: "Inter", sans-serif; font-size: .68rem; letter-spacing: .14em;
    text-transform: uppercase; color: var(--muted); margin-top: .35rem;
  }

  /* CTA STRIP */
  .cta-strip {
    margin: 3rem 0 0; padding: 3.5rem 2.5rem; background: var(--ink); color: var(--paper);
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 3rem; align-items: center;
  }
  .cta-strip h3 {
    font-family: "Source Serif 4", serif; font-weight: 400;
    font-size: 2.6rem; line-height: 1.05; letter-spacing: -0.015em;
    color: var(--paper); margin: 0;
  }
  .cta-strip h3 em { font-style: italic; color: var(--teal-soft); }
  .cta-strip .micro { color: rgba(245, 240, 225, .6); margin-bottom: .9rem; }
  .cta-strip p {
    font-size: .98rem; color: rgba(245, 240, 225, .75);
    margin: 1.2rem 0 0; max-width: 520px;
  }
  .cta-strip-actions { display: flex; flex-direction: column; gap: .75rem; }
  .cta-light {
    background: var(--paper); color: var(--ink);
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
  }
  .cta-light:hover { background: var(--teal); color: var(--paper); }
  .cta-outline {
    background: transparent; border: 1px solid var(--paper); color: var(--paper);
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
  }
  .cta-outline:hover { background: var(--paper); color: var(--ink); }

  /* FOOTER */
  footer {
    margin-top: 3rem; padding: 2rem; border-top: 1px solid var(--rule);
    display: flex; justify-content: space-between; align-items: center;
    font-family: "Inter", sans-serif; font-size: .82rem; color: var(--muted);
  }
  footer em { font-style: italic; color: var(--teal-deep); }

  @media (max-width: 1100px) {
    .hero, .sect, .pull, .cta-strip { grid-template-columns: 1fr; gap: 2rem; }
    .triplet, .proof, .catalog { grid-template-columns: repeat(2, 1fr); }
    .funnel { grid-template-columns: repeat(4, 1fr); }
    .pair { grid-template-columns: 1fr; }
    .pair .viz { border-right: none; border-bottom: 1px solid var(--border); }
  }
</style>
"""

_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700'
    '&family=Inter:wght@400;500;600;700'
    '&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
)


# ── Section builders ────────────────────────────────────────────────

def _topbar() -> str:
    return (
        '<header class="topbar">'
        f'<a href="/" class="brand" aria-label="PE Desk home">'
        '<div class="brand-mark">PD</div>'
        '<div class="brand-name">PE <em>Desk</em></div>'
        '</a>'
        '<nav class="topnav">'
        '<a href="#platform">Platform</a>'
        '<a href="#modules">Modules</a>'
        '<a href="#proof">Proof</a>'
        '<a href="#sources">Data sources</a>'
        '</nav>'
        '<div class="topbar-right">'
        f'<a href="{_LOGIN}" class="signin">SIGN IN</a>'
        f'<a href="{_LOGIN}" class="cta-btn">Request Access</a>'
        '</div>'
        '</header>'
    )


def _crumbs() -> str:
    return (
        '<div class="crumbs">'
        '<span>Home</span>'
        '<span class="sep">&rsaquo;</span>'
        '<span class="here">PE Desk</span>'
        '</div>'
    )


def _hero() -> str:
    return (
        '<section class="hero">'
        '<div>'
        '<div class="eyebrow">'
        '<span>HEALTHCARE&nbsp;PRIVATE&nbsp;EQUITY</span>'
        '<span class="dot">&middot;</span>'
        '<span>FUND&nbsp;II</span>'
        '<span class="dot">&middot;</span>'
        '<span class="slug">/v1.0.0</span>'
        '</div>'
        '<h1 class="title">Healthcare diligence,<br/><em>instrument-grade</em>.</h1>'
        '<p class="lede">'
        'Sourced through hold, in one canvas. Weighted MOIC, covenant heatmaps, '
        'EBITDA drag decomposition, and forty-seven initiative levers &mdash; all '
        'reading from the same in-process model registry. No SaaS dependencies.'
        '</p>'
        '<div class="hero-actions">'
        f'<a href="{_LOGIN}" class="cta-btn">Open Command Center</a>'
        '<a href="#platform" class="ghost-btn">See how it works &darr;</a>'
        '</div>'
        '</div>'
        '<div class="hero-meta">'
        '<div class="row"><span class="k">PRODUCT</span><span class="v">CCF-FUND2</span></div>'
        '<div class="row"><span class="k">KIND</span><span class="v">ROLLUP</span></div>'
        '<div class="row"><span class="k">STATUS</span>'
        '<span class="v" style="color:var(--green)">LIVE</span></div>'
        '<div class="stamp">'
        'Built for partners who run their own model. Public data only '
        '&mdash; no PHI on this instance.'
        '</div>'
        '</div>'
        '</section>'
    )


def _triplet() -> str:
    cells = [
        ("/01", "One source <em>of truth</em>",
         "Each deal gets a unique URL. Enter parameters once &mdash; every "
         "downstream analytic opens with them pre-filled. State persists locally."),
        ("/02", "Six layers, <em>one console</em>",
         "Econometrics, variance &amp; drift, RCM drag, covenant engine, market "
         "&amp; peer, delivery. Every panel reads from the same registry."),
        ("/03", "Provenance, <em>preserved</em>",
         "HCRIS, APCD, CMS-MA citations live next to every number. Drop-in "
         "compatible with the existing output v1/ structure."),
    ]
    inner = "".join(
        f'<div class="trip-cell">'
        f'<div class="trip-num">{num}</div>'
        f'<h3 class="trip-h">{head}</h3>'
        f'<p class="trip-p">{body}</p>'
        f'</div>'
        for num, head, body in cells
    )
    return f'<div class="triplet">{inner}</div>'


def _sect(micro: str, headline: str, desc: str) -> str:
    """Two-column section header — micro label + serif headline left,
    descriptive paragraph right. ``headline`` may contain <em> spans."""
    return (
        '<div class="sect">'
        f'<div><div class="micro">{micro}</div><h2>{headline}</h2></div>'
        f'<p class="desc">{desc}</p>'
        '</div>'
    )


def _funnel(stages: list, columns: int = 7) -> str:
    """Pipeline funnel — one stage cell per tuple
    ``(name, count, sub, bar_pct, accent)``. ``accent`` is "" for
    teal (default) or a CSS color for the final hold stage."""
    cells = ""
    grid = (
        f' style="grid-template-columns: repeat({columns}, 1fr)"'
        if columns != 7 else ""
    )
    for name, count, sub, pct, accent in stages:
        stage_style = (
            f' style="border-top-color:{accent}"' if accent else ""
        )
        bar_style = (
            f'width:{pct}%; background:{accent}' if accent
            else f'width:{pct}%'
        )
        cells += (
            f'<div class="stage"{stage_style}>'
            f'<div class="nm">{name}</div>'
            f'<div class="ct">{count}</div>'
            f'<div class="ev">{sub}</div>'
            f'<div class="bar"><i style="{bar_style}"></i></div>'
            f'</div>'
        )
    return f'<div class="funnel"{grid}>{cells}</div>'


def _platform_section() -> str:
    funnel = _funnel([
        ("Sourced", "14", "$3.2B", 100, ""),
        ("Screened", "9", "$2.1B", 64, ""),
        ("IOI", "4", "$1.4B", 29, ""),
        ("LOI", "2", "$680M", 14, ""),
        ("SPA", "1", "$450M", 7, ""),
        ("Closed", "1", "$450M", 7, ""),
        ("Hold", "3", "$1.2B", 21, "var(--green)"),
    ])
    rows = (
        '<tr><td class="lbl">Sourced</td><td class="r">14</td>'
        '<td class="r">$3.2B</td>'
        '<td class="r" style="color:var(--faint)">&mdash;</td></tr>'
        '<tr><td class="lbl">Screened</td><td class="r">9</td>'
        '<td class="r">$2.1B</td>'
        '<td class="r" style="color:var(--green)">64%</td></tr>'
        '<tr><td class="lbl">IOI</td><td class="r">4</td>'
        '<td class="r">$1.4B</td>'
        '<td class="r" style="color:var(--amber)">44%</td></tr>'
        '<tr><td class="lbl">LOI</td><td class="r">2</td>'
        '<td class="r">$680M</td>'
        '<td class="r" style="color:var(--amber)">50%</td></tr>'
        '<tr><td class="lbl">SPA</td><td class="r">1</td>'
        '<td class="r">$450M</td>'
        '<td class="r" style="color:var(--amber)">50%</td></tr>'
        '<tr><td class="lbl">Closed</td><td class="r">1</td>'
        '<td class="r">$450M</td>'
        '<td class="r" style="color:var(--green)">100%</td></tr>'
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">Hold</td>'
        '<td class="r" style="font-weight:700">3</td>'
        '<td class="r" style="font-weight:700">$1.2B</td>'
        '<td class="r">&mdash;</td></tr>'
    )
    return (
        '<section id="platform">'
        + _sect(
            "THE PLATFORM",
            "Sourced through<br/><em>hold</em>, in one place.",
            "Pipeline funnel with stage-relative widths, conversion ratios "
            "computed against the prior stage, entry EV summed where modeled. "
            "Click a stage in the live console to filter the deal table beneath.",
        )
        + '<div class="pair">'
        f'<div class="viz">{funnel}</div>'
        '<div class="data">'
        '<div class="data-h"><span>FUNNEL CONVERSION</span>'
        '<span class="src">portfolio.db / funnel</span></div>'
        '<table><thead><tr><th>Stage</th><th class="r">N</th>'
        '<th class="r">EV</th><th class="r">&rarr; prior</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _proof_section() -> str:
    cells = [
        ("<em>2.69</em>x", "Weighted MOIC", "+0.18x QoQ on a 7-quarter trajectory"),
        ("<em>21.9</em>%", "Weighted IRR", "&minus;1.4 pts QoQ; covenant pressure flagged"),
        ("<em>0</em>", "Covenants at Risk", "All hold deals SAFE; 2 lines on watch"),
        ("$<em>17.5</em>M", "Avg EBITDA Drag", "&minus;$1.2M QoQ vs RCM benchmark"),
        ("<em>12.1</em>d", "Avg DAR Drag", "Trending toward 11d benchmark"),
        ("<em>47</em>", "Initiatives Tracked", "12 lagging across hold portfolio"),
        ("<em>84</em>d", "Avg Days Cash", "+3d QoQ; well above 60d covenant"),
        ("<em>3</em>/14", "Pipeline &rarr; Hold", "21% conversion sourced to hold"),
    ]
    inner = "".join(
        f'<div class="proof-cell">'
        f'<div class="proof-v">{v}</div>'
        f'<div class="proof-l">{label}</div>'
        f'<div class="proof-d">{desc}</div>'
        f'</div>'
        for v, label, desc in cells
    )
    return (
        '<section id="proof">'
        + _sect(
            "FUND-LEVEL PROOF",
            "Numbers <em>that hold up</em><br/>in a partners' meeting.",
            "Eight tracked KPIs across Fund II, weighted by entry EV. Every "
            "value carries a 7-quarter provenance chain &mdash; click into the "
            "Command Center to see the underlying simulations and source rows.",
        )
        + f'<div class="proof">{inner}</div>'
        + '</section>'
    )


def _catalog_section() -> str:
    columns = [
        ("RETURNS", "fund", [
            ("Weighted MOIC", "2.69x", ""),
            ("Weighted IRR", "21.9%", ""),
            ("DPI", "0.42x", ""),
            ("TVPI", "2.69x", ""),
        ]),
        ("RCM DRAG", "", [
            ("Denial write-off", "$14.6M", ""),
            ("DAR carry cost", "$1.4M", ""),
            ("Underpay leakage", "$1.7M", ""),
            ("Recovery cost", "$0.2M", ""),
        ]),
        ("COVENANTS", "", [
            ("Net leverage", "6.1x", "var(--amber)"),
            ("Interest coverage", "2.2x", "var(--amber)"),
            ("Days cash", "84d", "var(--green)"),
            ("EBITDA / Plan", "87%", "var(--amber)"),
        ]),
        ("INITIATIVES", "", [
            ("Coding &amp; CDI", "&minus;10.0%", "var(--amber)"),
            ("Prior auth reform", "+28.0%", "var(--red)"),
            ("Denials workflow", "+6.4%", "var(--green)"),
            ("Underpay recovery", "&minus;15.2%", "var(--amber)"),
        ]),
    ]
    cols_html = ""
    for title, level, rows in columns:
        lvl_cls = "lvl fund" if level == "fund" else "lvl"
        lvl_txt = "FUND" if level == "fund" else "DEAL"
        row_html = "".join(
            f'<tr><td class="lbl">{label}</td>'
            f'<td class="r"'
            + (f' style="color:{color}"' if color else "")
            + f'>{value}</td></tr>'
            for label, value, color in rows
        )
        cols_html += (
            '<div class="cat-col">'
            f'<div class="cat-h"><span class="ttl">{title}</span>'
            f'<span class="{lvl_cls}">{lvl_txt}</span></div>'
            f'<table><tbody>{row_html}</tbody></table>'
            '</div>'
        )
    return (
        '<section id="modules">'
        + _sect(
            "MODULE CATALOG",
            "Every <em>number</em><br/>has a home.",
            "Cross-reference of fund- and deal-level metrics with their "
            "visualization anchors. The catalog is the spine of the Command "
            "Center &mdash; click any row in the live app to scroll its source.",
        )
        + f'<div class="catalog">{cols_html}</div>'
        + '</section>'
    )


def _pull_quote() -> str:
    stats = [
        ("$24.4M", "EBITDA drag identified"),
        ("+$7.0M", "Modeled recovery, base case"),
        ("4 quarters", "To close half the gap"),
    ]
    stats_html = "".join(
        f'<div><div class="stat-v">{v}</div>'
        f'<div class="stat-l">{label}</div></div>'
        for v, label in stats
    )
    return (
        '<section class="pull">'
        '<div>'
        '<q>The covenant heatmap caught the EBITDA-to-plan drift two quarters '
        'before our last operator review would have. We re-priced the bridge '
        'that week.</q>'
        '<div class="attr"><b>Operating Partner</b>'
        'Healthcare Opportunity Fund II</div>'
        '</div>'
        f'<div class="stats">{stats_html}</div>'
        '</section>'
    )


def _sources_section() -> str:
    funnel = _funnel([
        ("HCRIS", "2,847", "cost reports", 100, ""),
        ("APCD", "14", "state feeds", 50, ""),
        ("CMS-MA", "312", "enrollment", 35, ""),
        ("portfolio.db", "7", "tables", 25, ""),
        ("simulations", "10k", "runs", 75, ""),
    ], columns=5)
    rows = (
        '<tr><td class="lbl">HCRIS cost reports</td><td class="r">2,847</td></tr>'
        '<tr><td class="lbl">APCD claims (14 states)</td><td class="r">38.2M</td></tr>'
        '<tr><td class="lbl">CMS-MA enrollment</td><td class="r">312 cnty</td></tr>'
        '<tr><td class="lbl">portfolio.db tables</td><td class="r">7</td></tr>'
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">'
        'simulations.csv runs</td>'
        '<td class="r" style="font-weight:700">10,000</td></tr>'
    )
    return (
        '<section id="sources">'
        + _sect(
            "DATA SOURCES",
            "Public data, <em>cited inline</em>.",
            "Every number traces back to a public filing or simulation. No "
            "PHI, no proprietary data, no SaaS calls. The model is yours.",
        )
        + '<div class="pair">'
        f'<div class="viz">{funnel}</div>'
        '<div class="data">'
        '<div class="data-h"><span>SOURCE INVENTORY</span>'
        '<span class="src">manifest.json</span></div>'
        f'<table><tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _cta_strip() -> str:
    return (
        '<section class="cta-strip">'
        '<div>'
        '<div class="micro">READY TO OPEN THE CONSOLE</div>'
        '<h3>Bring your <em>own model</em>.<br/>'
        'Keep your <em>own data</em>.</h3>'
        '<p>Sign in to your partner instance. Public data is preloaded '
        '&mdash; connect your private feeds when you\'re ready.</p>'
        '</div>'
        '<div class="cta-strip-actions">'
        f'<a href="{_LOGIN}" class="cta-light">Sign In &rarr;</a>'
        f'<a href="{_LOGIN}" class="cta-outline">Request Access</a>'
        '</div>'
        '</section>'
    )


def _footer() -> str:
    return (
        '<footer>'
        '<span>PE <em>Desk</em> v1.0.0 &mdash; Healthcare diligence, '
        'instrument-grade</span>'
        '<span class="mono" style="font-size:.75rem">'
        'HCRIS &middot; APCD &middot; CMS-MA &middot; simulations.csv '
        '&middot; portfolio.db</span>'
        '</footer>'
    )


# ── Public entry point ──────────────────────────────────────────────

def render_marketing_page() -> str:
    """Render the full standalone PE Desk marketing landing page.

    Returns one self-contained HTML document — no chartis_shell, no
    server-side state. Served at ``GET /`` for anonymous visitors.
    """
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        '<title>PE Desk &mdash; Healthcare diligence, instrument-grade</title>'
        '<meta name="description" content="PE Desk is the diligence and '
        'portfolio-operations platform for healthcare-focused private equity. '
        'Sourced through hold, in one canvas — weighted MOIC, covenant '
        'heatmaps, EBITDA drag decomposition, public data cited inline.">'
        + _FONTS
        + _STYLE
        + '</head><body>'
        + _topbar()
        + _crumbs()
        + '<div class="page">'
        + _hero()
        + _triplet()
        + _platform_section()
        + _proof_section()
        + _catalog_section()
        + _pull_quote()
        + _sources_section()
        + _cta_strip()
        + '</div>'
        + _footer()
        + '</body></html>'
    )

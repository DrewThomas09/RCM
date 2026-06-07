"""PE Desk, public marketing landing page.

Standalone self-contained HTML served at ``GET /`` for anonymous
visitors (under ``CHARTIS_UI_V2=1``). This page renders its own
``<style>`` block and does NOT go through ``chartis_shell``: the public
front door stays a single clean document with no app chrome.

Design intent (2026 refresh): calm and editorial, not a templated SaaS
splash. Flat parchment, hairline rules, one teal accent used sparingly,
no gradients or animation. The copy says what the product actually does
in plain language, names the real analytic surfaces it ships, and labels
every illustrative figure as a worked sample rather than dressing
fabricated numbers up as "proof".

Sections, top to bottom:
  1. Top bar      brand + anchor nav + Sign in + Request access
  2. Crumbs       Home > PE Desk
  3. Hero         eyebrow, serif H1, lede, two CTAs, honest meta column
  4. Value trio   three plain statements of how it works
  5. Workspace    section header + sample deal funnel (labelled sample)
  6. Capability   what the workspace actually computes (real surfaces)
  7. Profile      section header + sample profile catalog (labelled)
  8. Sources      section header + the real data the workspace runs on
  9. CTA strip    "bring your own model, keep your own data" (flat dark)
  10. Footer

All CTAs route to ``/login?next=/app``. Top-nav links smooth-scroll
within the page. Sample figures are an illustrative worked example and
are labelled as such; the capability and source lists are real.
"""
from __future__ import annotations

# CTA target. Every "sign in" / "request access" / "open workspace"
# affordance points here. Kept as a module constant so the route is
# wired in exactly one place (and so basic-auth retargeting is a single
# string replace in render_marketing_page).
_LOGIN = "/login?next=/app"


# ── Style block — calm editorial, flat (no gradients / animation) ──

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
    font-family: "Source Serif 4", "Source Serif Pro", "Iowan Old Style", Georgia, serif; font-size: 16px; line-height: 1.55;
    -webkit-font-smoothing: antialiased; scroll-behavior: smooth;
  }
  .sans { font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; }
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
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1rem; font-weight: 600;
    color: var(--ink);
  }
  .brand-name { font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1.4rem; font-weight: 600; color: var(--ink); }
  .brand-name em { font-style: italic; font-weight: 500; }
  .topnav {
    display: flex; gap: 0; margin-left: 2rem;
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .76rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
  }
  .topnav a { padding: 0 1.1rem; color: var(--ink); text-decoration: none; }
  .topnav a:hover { color: var(--teal-deep); }
  .topbar-right { margin-left: auto; display: flex; align-items: center; gap: 1rem; }
  .signin {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    text-decoration: none; padding: 0 .75rem;
  }
  .signin:hover { color: var(--ink); }
  .cta-btn {
    background: var(--ink); color: var(--paper);
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: .8rem 1.4rem; border: none; cursor: pointer; text-decoration: none;
    display: inline-block; transition: background .18s ease;
  }
  .cta-btn:hover { background: var(--teal-deep); }

  /* CRUMBS */
  .crumbs {
    background: var(--bg); padding: .9rem 2rem; border-bottom: 1px solid var(--border);
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
  }
  .crumbs .sep { margin: 0 .55rem; color: var(--faint); }
  .crumbs .here { color: var(--ink); font-weight: 600; }

  /* HERO */
  .page { padding: 0 2rem 4rem; max-width: 1500px; margin: 0 auto; }
  .hero {
    padding: 4.5rem 0 3.5rem; border-bottom: 1px solid var(--rule);
    display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr);
    gap: 4rem; align-items: center;
  }
  .eyebrow {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; letter-spacing: .14em;
    text-transform: uppercase; color: var(--muted); font-weight: 600;
    display: flex; align-items: center; gap: .6rem; margin-bottom: 1.5rem;
  }
  .eyebrow .dot { color: var(--faint); }
  .eyebrow .slug { font-family: "JetBrains Mono", monospace; color: var(--teal-deep); letter-spacing: .04em; }
  .eyebrow::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%;
    background: var(--teal); display: inline-block;
  }
  h1.title {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-weight: 400;
    font-size: clamp(3rem, 5.2vw, 4.7rem); line-height: 1.02; letter-spacing: -0.022em;
    color: var(--ink); margin: 0 0 1.5rem;
  }
  h1.title em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .lede {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1.28rem; line-height: 1.5;
    color: var(--ink-2); max-width: 640px; margin: 0 0 2rem;
  }
  .lede b { font-weight: 600; color: var(--ink); }
  .hero-actions { display: flex; gap: 1.5rem; align-items: center; }
  .ghost-btn {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--ink);
    padding: .8rem 0; border-bottom: 1px solid var(--ink); text-decoration: none;
  }
  .ghost-btn:hover { color: var(--teal-deep); border-bottom-color: var(--teal-deep); }
  /* HERO ART — illustrative "sample workspace" card (flat, hairline) */
  .hero-art { justify-self: end; width: 100%; max-width: 430px; position: relative; }
  .ha-card {
    position: relative; z-index: 1; background: var(--paper-pure);
    border: 1px solid var(--rule); padding: 1.45rem 1.55rem 1.3rem;
  }
  /* offset hairline behind the card — reads as "a file behind the file" */
  .ha-card::before {
    content: ""; position: absolute; z-index: -1;
    top: 11px; left: 11px; right: -11px; bottom: -11px;
    background: var(--paper); border: 1px solid var(--border);
  }
  .ha-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.05rem;
  }
  .ha-eyebrow {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif;
    font-size: .6rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
    color: var(--muted); display: flex; align-items: center; gap: .45rem;
  }
  .ha-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--teal); display: inline-block;
  }
  .ha-chip {
    font-family: "JetBrains Mono", monospace; font-size: .56rem; letter-spacing: .06em;
    color: var(--teal-deep); background: var(--teal-soft);
    padding: .2rem .45rem; border-radius: 2px; white-space: nowrap;
  }
  .ha-ctitle {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif;
    font-size: 1.05rem; line-height: 1.2; color: var(--ink); margin: 0;
  }
  .ha-ctitle span { font-style: italic; color: var(--faint); }
  .ha-csub {
    font-family: "JetBrains Mono", monospace; font-size: .58rem; letter-spacing: .04em;
    color: var(--faint); margin: .15rem 0 .55rem;
  }
  .ha-chart { display: block; width: 100%; height: auto; }
  .ha-chart .ha-tick {
    font-family: "JetBrains Mono", monospace; font-size: 8px;
    fill: var(--faint); letter-spacing: .02em;
  }
  .ha-kpis { border-top: 1px solid var(--border); margin-top: .85rem; padding-top: .75rem; }
  .ha-row {
    display: flex; align-items: baseline; justify-content: space-between; padding: .28rem 0;
  }
  .ha-row .k {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif;
    font-size: .78rem; color: var(--muted);
  }
  .ha-row .v {
    font-family: "JetBrains Mono", monospace; font-feature-settings: "tnum" on;
    font-size: .92rem; font-weight: 600; color: var(--ink);
  }
  .ha-foot {
    margin-top: .85rem; padding-top: .75rem; border-top: 1px solid var(--border);
    font-family: "JetBrains Mono", monospace; font-size: .62rem; letter-spacing: .02em;
    color: var(--faint); display: flex; align-items: center; gap: .4rem;
  }
  .ha-foot .arr { color: var(--teal); font-size: .85rem; line-height: 1; }

  /* sample tag — honest "this is a worked example" marker */
  .sample-tag {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .58rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--amber);
    border: 1px solid var(--amber); border-radius: 2px; padding: .12rem .4rem;
    white-space: nowrap;
  }

  /* VALUE TRIO */
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
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-weight: 400; font-size: 1.35rem;
    line-height: 1.2; color: var(--ink); margin: 0 0 .75rem;
  }
  .trip-h em { font-style: italic; color: var(--teal-deep); }
  .trip-p { font-size: .94rem; color: var(--muted); line-height: 1.6; margin: 0; }

  /* SECTION HEADERS */
  .sect {
    display: grid; grid-template-columns: 1fr 1.3fr; gap: 3rem; align-items: end;
    padding: 4rem 0 1.5rem; margin-top: 1rem;
    border-top: 1px solid var(--rule); position: relative;
  }
  .sect::before {
    content: ""; position: absolute; top: -1px; left: 0; width: 64px; height: 2px;
    background: var(--teal);
  }
  .sect h2 {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-weight: 400;
    font-size: clamp(2.1rem, 3.4vw, 3.1rem); line-height: 1.08;
    letter-spacing: -0.016em; color: var(--ink); margin: .35rem 0 0;
  }
  .sect h2 em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .micro {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
  }
  .desc {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1.05rem; line-height: 1.6;
    color: var(--muted); margin: 0; max-width: 640px;
  }

  /* PAIRED viz + dataset (signature element) */
  .pair {
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 1.5rem 0;
  }
  .pair .viz { padding: 2rem; border-right: 1px solid var(--border); }
  .pair .data { background: var(--bg); }
  .data-h {
    padding: .9rem 1.25rem; border-bottom: 1px solid var(--border);
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    display: flex; justify-content: space-between; align-items: center; gap: .5rem;
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
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif;
  }
  .pair td {
    padding: .55rem 1.25rem; border-bottom: 1px solid var(--border);
    color: var(--ink); font-variant-numeric: tabular-nums;
  }
  .pair tr:last-child td { border-bottom: none; }
  .pair td.r { text-align: right; }
  .pair td.lbl { color: var(--muted); font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .9rem; }
  .pair tr.hot td { background: var(--bg-tint); }
  .pair tr.hot td:first-child { border-left: 2px solid var(--amber); }

  /* FUNNEL */
  .funnel { display: grid; grid-template-columns: repeat(7, 1fr); gap: .15rem; }
  .funnel .stage { background: var(--bg); padding: 1rem .85rem; border-top: 2px solid var(--teal); }
  .funnel .nm {
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
    margin-bottom: .5rem;
  }
  .funnel .ct {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1.7rem; color: var(--ink);
    line-height: 1; margin-bottom: .25rem;
  }
  .funnel .ev {
    font-family: "JetBrains Mono", monospace; font-size: .72rem;
    color: var(--teal-deep); margin-bottom: .5rem;
  }
  .funnel .bar { height: 3px; background: var(--border); }
  .funnel .bar i { display: block; height: 100%; background: var(--teal); }

  /* CAPABILITY GRID — what the workspace actually computes (real) */
  .caps {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
    background: var(--paper-pure); border: 1px solid var(--rule); margin: 1.5rem 0 0;
  }
  .cap {
    padding: 1.5rem 1.4rem; border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
  }
  .cap:nth-child(4n) { border-right: none; }
  .cap:nth-last-child(-n+4) { border-bottom: none; }
  .cap-tag {
    font-family: "JetBrains Mono", monospace; font-size: .64rem;
    letter-spacing: .04em; color: var(--teal-deep); margin-bottom: .6rem;
  }
  .cap-name {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: 1.22rem; line-height: 1.2;
    color: var(--ink); margin: 0 0 .5rem;
  }
  .cap-d {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-size: .9rem; color: var(--muted);
    line-height: 1.5; margin: 0;
  }

  /* PROFILE CATALOG */
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
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .68rem; font-weight: 700;
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
  .cat-col td.lbl { color: var(--muted); font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; }
  .cat-col td.r { text-align: right; font-family: "JetBrains Mono", monospace; color: var(--ink); font-weight: 600; }

  /* CTA STRIP — flat dark, no glow */
  .cta-strip {
    margin: 3.5rem 0 0; padding: 3.5rem 2.5rem; background: var(--ink);
    color: var(--paper);
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 3rem; align-items: center;
  }
  .cta-strip h3 {
    font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif; font-weight: 400;
    font-size: 2.4rem; line-height: 1.08; letter-spacing: -0.015em;
    color: var(--paper); margin: 0;
  }
  .cta-strip h3 em { font-style: italic; color: var(--teal-soft); }
  .cta-strip .micro { color: rgba(245, 240, 225, .6); margin-bottom: .9rem; }
  .cta-strip p {
    font-size: .98rem; color: rgba(245, 240, 225, .78);
    margin: 1.2rem 0 0; max-width: 520px; line-height: 1.6;
  }
  .cta-strip-actions { display: flex; flex-direction: column; gap: .75rem; }
  .cta-light {
    background: var(--paper); color: var(--ink);
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
    transition: background .18s ease, color .18s ease;
  }
  .cta-light:hover { background: var(--teal); color: var(--paper); }
  .cta-outline {
    background: transparent; border: 1px solid rgba(245,240,225,.4); color: var(--paper);
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
    transition: background .18s ease, color .18s ease, border-color .18s ease;
  }
  .cta-outline:hover { background: var(--paper); color: var(--ink); border-color: var(--paper); }

  /* FOOTER */
  footer {
    margin-top: 3rem; padding: 2rem; border-top: 1px solid var(--rule);
    display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    flex-wrap: wrap;
    font-family: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif; font-size: .82rem; color: var(--muted);
  }
  footer em { font-style: italic; color: var(--teal-deep); }

  @media (max-width: 1100px) {
    .hero, .sect, .cta-strip { grid-template-columns: 1fr; gap: 2rem; }
    .hero-art { justify-self: start; max-width: 460px; margin-top: .5rem; }
    .triplet, .caps, .catalog { grid-template-columns: repeat(2, 1fr); }
    .caps .cap:nth-child(4n) { border-right: 1px solid var(--border); }
    .caps .cap:nth-child(2n) { border-right: none; }
    .funnel { grid-template-columns: repeat(4, 1fr); }
    .pair { grid-template-columns: 1fr; }
    .pair .viz { border-right: none; border-bottom: 1px solid var(--border); }
  }
  @media (max-width: 960px) {
    /* the fixed-height topbar's brand + anchor-nav + CTAs overran the
       viewport ~26px at 768; tighten padding/nav spacing so it fits the
       tablet width (desktop ≥961 unchanged). */
    .topbar { padding: 0 1rem; gap: .6rem; }
    .topnav { margin-left: 1rem; }
    .topnav a { padding: 0 .7rem; }
  }
  @media (max-width: 640px) {
    .topbar { padding: 0 1rem; gap: .5rem; height: auto; flex-wrap: wrap; padding-top: .6rem; padding-bottom: .6rem; }
    .topnav { display: none; }
    .page { padding: 0 1.1rem 3rem; }
    .triplet, .caps, .catalog { grid-template-columns: 1fr; }
    .trip-cell, .cap { border-right: none; }
  }
</style>
"""

# Offline-first: no external font CDN. The response CSP (style-src
# 'self' / font-src 'self') blocked these on every render. The _STYLE
# block uses the same local font fallbacks the app does.


# ── Section builders ────────────────────────────────────────────────

def _topbar() -> str:
    return (
        '<header class="topbar">'
        f'<a href="/" class="brand" aria-label="PE Desk home">'
        '<div class="brand-mark">PD</div>'
        '<div class="brand-name">PE <em>Desk</em></div>'
        '</a>'
        '<nav class="topnav">'
        '<a href="#workspace">Workspace</a>'
        '<a href="#modules">What it computes</a>'
        '<a href="#proof">Sample profile</a>'
        '<a href="#sources">Data</a>'
        '</nav>'
        '<div class="topbar-right">'
        f'<a href="{_LOGIN}" class="signin">Sign in</a>'
        f'<a href="{_LOGIN}" class="cta-btn">Request access</a>'
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
        '<span>COMMERCIAL&nbsp;DILIGENCE</span>'
        '<span class="dot">&middot;</span>'
        '<span>HEALTHCARE</span>'
        '<span class="dot">&middot;</span>'
        '<span class="slug">built on public data</span>'
        '</div>'
        '<h1 class="title">The deal file that <br/>'
        '<em>shows its work.</em></h1>'
        '<p class="lede">'
        'PE Desk gives a healthcare deal team one workspace per target: '
        'market structure, peer benchmarks, comparable transactions, '
        'customer and competitor signals, interviews, and notes. '
        '<b>Every figure links back to the filing, cost report, or call '
        'it came from.</b> It runs on your own infrastructure, off public '
        'CMS data, and nothing leaves the box.'
        '</p>'
        '<div class="hero-actions">'
        f'<a href="{_LOGIN}" class="cta-btn">Open a workspace &rarr;</a>'
        '<a href="#workspace" class="ghost-btn">See a sample profile &darr;</a>'
        '</div>'
        '</div>'
        + _hero_art()
        + '</section>'
    )


def _hero_art() -> str:
    """Illustrative 'sample workspace' card for the hero's right column.

    Replaces the white space left when the old meta block was removed. It is
    decorative support for the headline ('shows its work'), not a live readout:
    the chart is an illustrative market-activity shape, but the figures shown
    are true and durable (1,936 deals in the library, 30+ catalogued open-data
    sources, the product's link-to-source promise). Marked 'Sample workspace'
    so it never reads as a live dashboard.
    """
    # (x, y, height) per year bar; y = 110 - height. Last year deepened to draw
    # the eye to the most recent period.
    bars = [
        (16, 90, 20), (50, 82, 28), (84, 85, 25), (118, 76, 34), (152, 80, 30),
        (186, 66, 44), (220, 58, 52), (254, 63, 47), (288, 44, 66),
    ]
    rects = "".join(
        f'<rect x="{x}" y="{y}" width="22" height="{h}" rx="1" fill="var(--teal)"/>'
        for (x, y, h) in bars
    )
    rects += '<rect x="322" y="30" width="22" height="80" rx="1" fill="var(--teal-deep)"/>'
    ticks = "".join(
        f'<text x="{cx}" y="124" text-anchor="middle" class="ha-tick">&rsquo;{yr}</text>'
        for (cx, yr) in ((27, "15"), (129, "18"), (231, "21"), (333, "24"))
    )
    return (
        '<aside class="hero-art">'
        '<div class="ha-card">'
        '<div class="ha-head">'
        '<span class="ha-eyebrow"><span class="ha-dot"></span>Sample workspace</span>'
        '<span class="ha-chip">HEALTHCARE&nbsp;SERVICES</span>'
        '</div>'
        '<div class="ha-ctitle">Comparable transactions <span>by year</span></div>'
        '<div class="ha-csub">M&amp;A activity &middot; 2015&ndash;2024</div>'
        '<svg class="ha-chart" role="img" '
        'aria-label="Comparable healthcare transactions per year, trending upward '
        'from 2015 to 2024" viewBox="0 0 360 132" preserveAspectRatio="xMidYMid meet">'
        '<line x1="14" y1="110" x2="346" y2="110" stroke="var(--border)" stroke-width="1"/>'
        + rects + ticks +
        '</svg>'
        '<div class="ha-kpis">'
        '<div class="ha-row"><span class="k">Comparable deals</span>'
        '<span class="v">1,936</span></div>'
        '<div class="ha-row"><span class="k">Open data sources</span>'
        '<span class="v">30+</span></div>'
        '<div class="ha-row"><span class="k">Figures linked to source</span>'
        '<span class="v">100%</span></div>'
        '</div>'
        '<div class="ha-foot"><span class="arr">&#8627;</span> '
        'Source: CMS HCRIS &middot; SEC &middot; HCPEA</div>'
        '</div>'
        '</aside>'
    )


def _triplet() -> str:
    cells = [
        ("/01", "Enter the deal <em>once</em>",
         "Name the target, set the thesis, drop in the financials. Every "
         "analytic downstream opens already filled in. Nobody re-keys the "
         "same revenue number into five different tools."),
        ("/02", "Read the market and the target <em>together</em>",
         "The target sits inside its market: structure, growth, payer mix, "
         "named competitors, and the comparable transactions that set the "
         "multiple. Read across the page, not just down it."),
        ("/03", "Every figure <em>shows its source</em>",
         "Filings, CMS cost reports, interviews, benchmarks, prior-engagement "
         "notes. Click any number to land on the document behind it, and "
         "hand the file to the next analyst without losing the trail."),
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
    """Two-column section header: micro label + serif headline left,
    descriptive paragraph right. ``headline`` may contain <em> spans."""
    return (
        '<div class="sect">'
        f'<div><div class="micro">{micro}</div><h2>{headline}</h2></div>'
        f'<p class="desc">{desc}</p>'
        '</div>'
    )


def _funnel(stages: list, columns: int = 7) -> str:
    """Pipeline funnel, one stage cell per tuple
    ``(name, count, sub, bar_pct, accent)``."""
    cells = ""
    grid = (
        f' style="grid-template-columns: repeat({columns}, 1fr)"'
        if columns != 7 else ""
    )
    for name, count, sub, pct, accent in stages:
        stage_style = f' style="border-top-color:{accent}"' if accent else ""
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


def _workspace_section() -> str:
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
        '<section id="workspace">'
        + _sect(
            "THE WORKSPACE",
            "From scattered files <br/>to <em>one deal view.</em>",
            "Open a workspace per opportunity. The target profile, the "
            "market map, the comparable set, the interview log, and the "
            "diligence questions all live in one place and stay tied to the "
            "deal, so the whole team is reading the same file as it moves "
            "from sourced to close.",
        )
        + '<div class="pair">'
        f'<div class="viz">{funnel}</div>'
        '<div class="data">'
        '<div class="data-h"><span>Deal funnel</span>'
        '<span class="sample-tag">Sample</span></div>'
        '<table><thead><tr><th>Stage</th><th class="r">N</th>'
        '<th class="r">EV</th><th class="r">&rarr; prior</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _capability_section() -> str:
    """What the workspace actually computes. These are the real analytic
    surfaces the platform ships — not illustrative numbers."""
    caps = [
        ("Monte Carlo", "Forward EBITDA",
         "EBITDA, MOIC and IRR distributions across thousands of trials, "
         "with driver attribution."),
        ("EBITDA bridge", "Value creation",
         "Entry to exit, decomposed into the operating levers that get "
         "you there."),
        ("Peer X-ray", "Public data",
         "Any hospital read against its HCRIS cost-report cohort on 15 "
         "operating metrics."),
        ("Comparables", "Market",
         "Reference transactions and public comps matched to the target "
         "by profile distance."),
        ("Covenant stress", "Credit",
         "Per-quarter breach probability and equity-cure sizing under "
         "rate and EBITDA shocks."),
        ("Regulatory calendar", "Timing",
         "CMS, OIG and payer dates mapped to the specific thesis driver "
         "each one moves."),
        ("Management read", "Team",
         "Forecast reliability, comp structure, tenure and prior-role "
         "track record, scored."),
        ("Source library", "Provenance",
         "Every figure on every surface cites the public document it "
         "was computed from."),
    ]
    inner = "".join(
        f'<div class="cap">'
        f'<div class="cap-tag">{tag}</div>'
        f'<h3 class="cap-name">{name}</h3>'
        f'<p class="cap-d">{desc}</p>'
        f'</div>'
        for name, tag, desc in caps
    )
    return (
        '<section id="modules">'
        + _sect(
            "WHAT IT COMPUTES",
            "Analysis that <br/>ships <em>in the box.</em>",
            "Every workspace carries the same analytic surfaces, run on "
            "public data and your own inputs. No add-on modules, no "
            "per-seat math, no waiting on a data vendor; the deal "
            "team opens the file and the analysis is already there.",
        )
        + f'<div class="caps">{inner}</div>'
        + '</section>'
    )


def _profile_section() -> str:
    columns = [
        ("COMPANY", "deal", [
            ("Revenue", "$418M", ""),
            ("Locations", "62 sites", ""),
            ("Ownership", "Sponsor-backed", ""),
            ("Mgmt tenure", "4.2y avg", ""),
        ]),
        ("MARKET", "market", [
            ("TAM", "$28B", ""),
            ("Growth (5y CAGR)", "+7.4%", "var(--green)"),
            ("Top-3 share", "31%", "var(--amber)"),
            ("Reg exposure", "Moderate", "var(--amber)"),
        ]),
        ("COMPETITORS", "market", [
            ("Peer count", "14", ""),
            ("Peer median EV/EBITDA", "11.4x", ""),
            ("Pricing position", "Premium", "var(--green)"),
            ("Edge", "Network density", ""),
        ]),
        ("CUSTOMERS", "deal", [
            ("Net retention", "108%", "var(--green)"),
            ("Top-10 concentration", "34%", "var(--amber)"),
            ("Referral velocity", "+12% QoQ", "var(--green)"),
            ("Churn flags", "3", "var(--amber)"),
        ]),
    ]
    cols_html = ""
    for title, level, rows in columns:
        lvl_cls = "lvl fund" if level == "deal" else "lvl market"
        lvl_txt = "DEAL" if level == "deal" else "MARKET"
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
        '<section id="proof">'
        + _sect(
            "A SAMPLE PROFILE",
            "One target, <br/>four <em>angles.</em>",
            "A profile pulls the company, its market, its competitors, and "
            "its customers onto one screen so a reviewer can read the whole "
            "commercial picture in a sitting. Figures below are an "
            "illustrative example; in the app every row links to its source.",
        )
        + '<div class="data-h" style="border:1px solid var(--rule);'
          'border-bottom:none;background:var(--paper-pure)">'
          '<span>Project Meridian &middot; regional services platform</span>'
          '<span class="sample-tag">Illustrative sample</span></div>'
        + f'<div class="catalog" style="margin-top:0">{cols_html}</div>'
        + '</section>'
    )


def _sources_section() -> str:
    funnel = _funnel([
        ("CMS public", "2,847", "cost reports", 100, ""),
        ("Filings", "412", "10-K / S-1", 55, ""),
        ("Market research", "184", "sector briefs", 70, ""),
        ("Interviews", "26", "calls logged", 35, ""),
        ("Your notes", "98", "engagements", 80, ""),
    ], columns=5)
    rows = (
        '<tr><td class="lbl">CMS public data (HCRIS, MA, CMS Compare)</td>'
        '<td class="r">2,847</td></tr>'
        '<tr><td class="lbl">SEC filings (10-K, S-1, proxies)</td>'
        '<td class="r">412</td></tr>'
        '<tr><td class="lbl">Sector &amp; market research</td>'
        '<td class="r">184</td></tr>'
        '<tr><td class="lbl">Customer / channel / competitor calls</td>'
        '<td class="r">26</td></tr>'
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">'
        'Your own engagement notes &amp; decks</td>'
        '<td class="r" style="font-weight:700">98</td></tr>'
    )
    return (
        '<section id="sources">'
        + _sect(
            "THE DATA",
            "Public where it can be, <br/><em>yours</em> where it counts.",
            "The workspace ships loaded with CMS public data and reads SEC "
            "filings out of the box. Add your own research, interviews, and "
            "engagement notes alongside them. Nothing you add is sent "
            "anywhere; the file stays on your infrastructure.",
        )
        + '<div class="pair">'
        f'<div class="viz">{funnel}</div>'
        '<div class="data">'
        '<div class="data-h"><span>Source inventory</span>'
        '<span class="sample-tag">Sample</span></div>'
        f'<table><tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _cta_strip() -> str:
    return (
        '<section class="cta-strip">'
        '<div>'
        '<div class="micro">GET ACCESS</div>'
        '<h3>Bring your own <em>model</em>. <br/>'
        'Keep your own <em>data</em>.</h3>'
        '<p>PE Desk runs on your infrastructure with the model you choose '
        'in local or hosted form. Public sources come preloaded; connect '
        'your research and CRM when you are ready. No data leaves the box, '
        'and there is no SaaS lock-in.</p>'
        '</div>'
        '<div class="cta-strip-actions">'
        f'<a href="{_LOGIN}" class="cta-light">Open a workspace &rarr;</a>'
        f'<a href="{_LOGIN}" class="cta-outline">Request access</a>'
        '</div>'
        '</section>'
    )


def _footer() -> str:
    return (
        '<footer>'
        '<span>PE <em>Desk</em>: the diligence workspace for '
        'healthcare deal teams</span>'
        '<span class="mono" style="font-size:.75rem">'
        'CMS public data &middot; SEC filings &middot; market research '
        '&middot; interviews &middot; your notes</span>'
        '</footer>'
    )


# ── Public entry point ──────────────────────────────────────────────

def render_marketing_page(basic_auth: bool = False) -> str:
    """Render the full standalone PE Desk marketing landing page.

    Returns one self-contained HTML document — no chartis_shell, no
    server-side state. Served at ``GET /`` for anonymous visitors.

    ``basic_auth=True`` (deployment has ``RCM_MC_AUTH`` set): the Sign In
    CTAs point straight at ``/app`` instead of the in-app ``/login`` form,
    so the browser's native Basic Auth prompt collects the shared
    credential. (The in-app form rejects the Basic Auth credential.)
    """
    html = (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg"/>'
        '<title>PE Desk: the diligence workspace for healthcare '
        'deal teams</title>'
        '<meta name="description" content="PE Desk gives a healthcare deal '
        'team one workspace per target: market structure, peer benchmarks, '
        'comparable transactions, customer and competitor signals, '
        'interviews, and notes, with every figure cited to its source. '
        'Built on public CMS data, run on your own infrastructure.">'
        + _STYLE
        + '</head><body>'
        + _topbar()
        + _crumbs()
        + '<div class="page">'
        + _hero()
        + _triplet()
        + _workspace_section()
        + _capability_section()
        + _profile_section()
        + _sources_section()
        + _cta_strip()
        + '</div>'
        + _footer()
        + '</body></html>'
    )
    if basic_auth:
        # Retarget the Sign In CTAs to /app (browser Basic Auth prompt).
        html = html.replace(_LOGIN, "/app")
    return html

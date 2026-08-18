"""PE Desk, public marketing landing page.

Standalone self-contained HTML served at ``GET /`` for anonymous
visitors (under ``CHARTIS_UI_V2=1``). This page renders its own
``<style>`` block and does NOT go through ``chartis_shell``: the public
front door stays a single clean document with no app chrome.

Design intent (2026 refresh): calm and editorial, not a templated SaaS
splash. Flat parchment, hairline rules, one teal accent used sparingly,
no gradients or animation. The copy says what the product actually does
in plain language and names the real surfaces it ships.

2026-08-18 rewrite. Two things were wrong with the previous version,
and they turned out to be the same thing.

It sold the product to one audience — "healthcare deal teams" — when
what it actually does (read what a Medicare-certified provider filed,
against its peers) is the same work whether you are underwriting an
acquisition, advising a health system, lending against one, regulating
one, or checking a claim someone made about one.

And it advertised eight capabilities of which FIVE no longer exist:
Monte Carlo, EBITDA bridge, comparables, covenant stress and the
management read were all hidden by the 2026-08 visibility sweeps as
deal-execution machinery. A public front door promising a product the
app no longer offers is worse than a plain one. The capability grid now
names surfaces that are live, and every one of them is asserted against
the visibility registry by test.

Fabricated figures are gone with them. The old page ran on an invented
deal funnel (14 sourced / $3.2B), an invented target ("Project
Meridian", $418M revenue, 108% net retention) and an invented source
inventory. Everything quantitative here now comes from the shipped data
and is checked by test: 48,510 certified CCNs across seven provider
classes, 6,123 hospital cost reports, 445 source-cited transactions.

Sections, top to bottom:
  1. Top bar      brand + anchor nav + Sign in + Request access
  2. Crumbs       Home > the workspace
  3. Hero         eyebrow, serif H1, lede, two CTAs, real coverage card
  4. Value trio   three plain statements of how it works
  5. Coverage     section header + the real provider universe, by class
  6. Capability   what it actually computes (live surfaces only)
  7. Provider file section header + what a provider file holds (fields,
                  not fabricated values)
  8. Sources      section header + the real data it runs on
  9. CTA strip    "bring your own model, keep your own data" (flat dark)
  10. Footer

All CTAs route to ``/login?next=/app``. Top-nav links smooth-scroll
within the page.
"""
from __future__ import annotations

# ── Real figures ────────────────────────────────────────────────────
#
# Everything quantitative on this page is read from the shipped data at
# import, not typed in. The previous version quoted an invented deal
# funnel and an invented source inventory; on a page whose whole claim
# is "every figure traces to its source", numbers we made up were the
# one thing that could not be defended.
#
# Resolved once at import (the crosswalk is memoised, so this costs
# nothing on a warm process) and behind a try/except: a marketing page
# must render even if a data file is absent in a slim deployment. The
# fallbacks are the counts observed on 2026-08-18, so the page degrades
# to slightly-stale-but-true rather than to zeros.

_CLASS_BLURB = {
    "Hospital": "cost reports",
    "Nursing home": "SNF",
    "Home health": "HHA",
    "Dialysis": "ESRD",
    "Hospice": "hospice",
    "Rehab": "IRF",
}
_CLASS_SOURCE = {
    "Hospital": "HCRIS + Care Compare",
    "Nursing home": "Care Compare",
    "Home health": "Care Compare",
    "Dialysis": "Care Compare",
    "Hospice": "Care Compare",
    "Rehab": "Care Compare",
}
#: Display label per crosswalk provider_class. LTCH is deliberately
#: absent: the crosswalk currently resolves only a handful of LTCH CCNs,
#: and a bar reading "8" next to 14,699 nursing homes would misdescribe
#: the coverage rather than report it. The LTCH universe still has its
#: own surface in the app.
_CLASS_LABELS = {
    "hospital": "Hospital", "snf": "Nursing home", "hha": "Home health",
    "dialysis": "Dialysis", "hospice": "Hospice", "irf": "Rehab",
}
_FALLBACK_BY_CLASS = {
    "Nursing home": 14699, "Home health": 12392, "Dialysis": 7557,
    "Hospice": 6852, "Hospital": 6123, "Rehab": 879,
}


def _load_counts():
    """(total CCNs, per-class counts) from the provider crosswalk."""
    try:
        from collections import Counter

        from ...data.provider_crosswalk import SCOPE_ALL, get_crosswalk
        xw = get_crosswalk(scope=SCOPE_ALL)
        counts = Counter(xw["provider_class"].astype(str))
        by_class = {
            label: counts[key]
            for key, label in _CLASS_LABELS.items() if counts.get(key)
        }
        if not by_class:
            raise ValueError("no provider classes resolved")
        return len(xw), dict(sorted(
            by_class.items(), key=lambda kv: -kv[1]))
    except Exception:                              # noqa: BLE001
        return 48510, dict(sorted(
            _FALLBACK_BY_CLASS.items(), key=lambda kv: -kv[1]))


def _load_verified_deal_count() -> int:
    try:
        from ...data_public.verified_deals import VERIFIED_DEALS
        return len(VERIFIED_DEALS) or 445
    except Exception:                              # noqa: BLE001
        return 445


def _load_system_count() -> int:
    try:
        from ...data.health_systems import ACUTE_REGISTRY
        return len(ACUTE_REGISTRY) or 298
    except Exception:                              # noqa: BLE001
        return 298


_N_CCNS, _CCNS_BY_CLASS = _load_counts()
_N_HOSPITALS = _CCNS_BY_CLASS.get("Hospital", 6123)
_N_VERIFIED_DEALS = _load_verified_deal_count()
_N_SYSTEMS = _load_system_count()


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

    /* Type — one stack per role, declared once so every surface stays
       consistent. (Mirrors the platform's --sc-serif/sans/mono tokens;
       this page is standalone so it carries its own copy.) */
    --serif: "Source Serif 4", "Source Serif Pro", "Iowan Old Style", Georgia, serif;
    --sans: "Inter Tight", "Inter", ui-sans-serif, system-ui, sans-serif;
    --mono: "JetBrains Mono", "SF Mono", ui-monospace, monospace;

    /* Uppercase-label scale — three steps so eyebrows/tags don't drift
       to a dozen near-identical sizes across sections.
         --label    primary: nav, buttons, hero eyebrow
         --label-sm secondary: section micro, table + panel headers
         --label-xs tiny tags: hero-card eyebrow, "sample" markers */
    --label: .72rem;
    --label-sm: .68rem;
    --label-xs: .58rem;
    --track: .14em;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: var(--serif); font-size: 16px; line-height: 1.6;
    -webkit-font-smoothing: antialiased; scroll-behavior: smooth;
    text-rendering: optimizeLegibility; text-wrap: pretty;
  }
  .sans { font-family: var(--sans); }
  .mono { font-family: var(--mono); font-feature-settings: "tnum" on; }

  /* TOP BAR */
  .topbar {
    background: var(--paper-pure); border-bottom: 1px solid var(--border);
    padding: 0 2rem; display: flex; align-items: center; gap: 1rem; height: 72px;
  }
  .brand { display:flex; align-items:center; gap:.7rem; text-decoration:none; }
  .brand-mark {
    width: 38px; height: 38px; border: 1.5px solid var(--ink); border-radius: 999px;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--serif); font-size: 1rem; font-weight: 600;
    color: var(--ink);
  }
  .brand-name { font-family: var(--serif); font-size: 1.4rem; font-weight: 600; color: var(--ink); }
  .brand-name em { font-style: italic; font-weight: 500; }
  .topnav {
    display: flex; gap: 0; margin-left: 2rem;
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase;
  }
  .topnav a { padding: 0 1.1rem; color: var(--ink); text-decoration: none; transition: color .18s ease; }
  .topnav a:hover { color: var(--teal-deep); }
  .topbar-right { margin-left: auto; display: flex; align-items: center; gap: 1rem; }
  .signin {
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase; color: var(--muted);
    text-decoration: none; padding: 0 .75rem;
  }
  .signin:hover { color: var(--ink); }
  .cta-btn {
    background: var(--ink); color: var(--paper);
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase;
    padding: .8rem 1.4rem; border: none; cursor: pointer; text-decoration: none;
    display: inline-block; transition: background .18s ease;
  }
  .cta-btn:hover { background: var(--teal-deep); }

  /* CRUMBS */
  .crumbs {
    background: var(--bg); padding: .9rem 2rem; border-bottom: 1px solid var(--border);
    font-family: var(--sans); font-size: var(--label); letter-spacing: var(--track);
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
    font-family: var(--sans); font-size: var(--label); letter-spacing: var(--track);
    text-transform: uppercase; color: var(--muted); font-weight: 600;
    display: flex; align-items: center; gap: .6rem; margin-bottom: 1.5rem;
  }
  .eyebrow .dot { color: var(--faint); }
  .eyebrow .slug { font-family: var(--mono); color: var(--teal-deep); letter-spacing: .04em; }
  .eyebrow::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%;
    background: var(--teal); display: inline-block;
  }
  h1.title {
    font-family: var(--serif); font-weight: 400;
    font-size: clamp(3rem, 5.2vw, 4.7rem); line-height: 1.02; letter-spacing: -0.022em;
    color: var(--ink); margin: 0 0 1.5rem;
  }
  h1.title em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .lede {
    font-family: var(--serif); font-size: 1.28rem; line-height: 1.58;
    color: var(--ink-2); max-width: 33rem; margin: 0 0 2.25rem;
  }
  .lede b { font-weight: 600; color: var(--ink); }
  .hero-actions { display: flex; gap: 1.5rem; align-items: center; }
  .ghost-btn {
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase; color: var(--ink);
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
    font-family: var(--sans);
    font-size: var(--label-xs); font-weight: 700; letter-spacing: var(--track); text-transform: uppercase;
    color: var(--muted); display: flex; align-items: center; gap: .45rem;
  }
  .ha-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--teal); display: inline-block;
  }
  .ha-chip {
    font-family: var(--mono); font-size: .56rem; letter-spacing: .06em;
    color: var(--teal-deep); background: var(--teal-soft);
    padding: .2rem .45rem; border-radius: 2px; white-space: nowrap;
  }
  .ha-ctitle {
    font-family: var(--serif);
    font-size: 1.05rem; line-height: 1.2; color: var(--ink); margin: 0;
  }
  .ha-ctitle span { font-style: italic; color: var(--faint); }
  .ha-csub {
    font-family: var(--mono); font-size: .58rem; letter-spacing: .04em;
    color: var(--faint); margin: .15rem 0 .55rem;
  }
  .ha-chart { display: block; width: 100%; height: auto; }
  .ha-chart .ha-tick {
    font-family: var(--mono); font-size: 8px;
    fill: var(--faint); letter-spacing: .02em;
  }
  .ha-kpis { border-top: 1px solid var(--border); margin-top: .85rem; padding-top: .75rem; }
  .ha-row {
    display: flex; align-items: baseline; justify-content: space-between; padding: .28rem 0;
  }
  .ha-row .k {
    font-family: var(--sans);
    font-size: .78rem; color: var(--muted);
  }
  .ha-row .v {
    font-family: var(--mono); font-feature-settings: "tnum" on;
    font-size: .92rem; font-weight: 600; color: var(--ink);
  }
  .ha-foot {
    margin-top: .85rem; padding-top: .75rem; border-top: 1px solid var(--border);
    font-family: var(--mono); font-size: .62rem; letter-spacing: .02em;
    color: var(--faint); display: flex; align-items: center; gap: .4rem;
  }
  .ha-foot .arr { color: var(--teal); font-size: .85rem; line-height: 1; }

  /* sample tag — honest "this is a worked example" marker */
  .sample-tag {
    font-family: var(--sans); font-size: var(--label-xs); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase; color: var(--amber);
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
    font-family: var(--mono); font-size: .72rem;
    color: var(--teal-deep); letter-spacing: .04em; margin-bottom: .8rem;
  }
  .trip-h {
    font-family: var(--serif); font-weight: 400; font-size: 1.35rem;
    line-height: 1.2; color: var(--ink); margin: 0 0 .75rem;
    text-wrap: balance;
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
    font-family: var(--serif); font-weight: 400;
    font-size: clamp(2.1rem, 3.4vw, 3.1rem); line-height: 1.08;
    letter-spacing: -0.016em; color: var(--ink); margin: .35rem 0 0;
  }
  .sect h2 em { font-style: italic; color: var(--teal-deep); font-weight: 400; }
  .micro {
    font-family: var(--sans); font-size: var(--label-sm); font-weight: 700;
    letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
  }
  .desc {
    font-family: var(--serif); font-size: 1.05rem; line-height: 1.6;
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
    font-family: var(--sans); font-size: var(--label-sm); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase; color: var(--muted);
    display: flex; justify-content: space-between; align-items: center; gap: .5rem;
  }
  .data-h .src {
    font-family: var(--mono); text-transform: none;
    letter-spacing: 0; color: var(--teal-deep); font-size: .72rem;
  }
  .pair table { width: 100%; border-collapse: collapse;
    font-family: var(--mono); font-size: .82rem; }
  .pair th {
    text-align: left; padding: .55rem 1.25rem; color: var(--faint);
    font-weight: 600; font-size: .62rem; letter-spacing: .12em;
    text-transform: uppercase; border-bottom: 1px solid var(--border);
    font-family: var(--sans);
  }
  .pair td {
    padding: .55rem 1.25rem; border-bottom: 1px solid var(--border);
    color: var(--ink); font-variant-numeric: tabular-nums;
  }
  .pair tr:last-child td { border-bottom: none; }
  .pair td.r { text-align: right; }
  .pair td.lbl { color: var(--muted); font-family: var(--sans); font-size: .9rem; }
  .pair tr.hot td { background: var(--bg-tint); }
  .pair tr.hot td:first-child { border-left: 2px solid var(--amber); }

  /* FUNNEL */
  .funnel { display: grid; grid-template-columns: repeat(7, 1fr); gap: .15rem; }
  .funnel .stage { background: var(--bg); padding: 1rem .85rem; border-top: 2px solid var(--teal); }
  .funnel .nm {
    font-family: var(--sans); font-size: var(--label-sm); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase; color: var(--muted);
    margin-bottom: .5rem;
  }
  .funnel .ct {
    font-family: var(--serif); font-size: 1.7rem; color: var(--ink);
    line-height: 1; margin-bottom: .25rem;
  }
  .funnel .ev {
    font-family: var(--mono); font-size: .72rem;
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
    font-family: var(--mono); font-size: .64rem;
    letter-spacing: .04em; color: var(--teal-deep); margin-bottom: .6rem;
  }
  .cap-name {
    font-family: var(--serif); font-size: 1.22rem; line-height: 1.2;
    color: var(--ink); margin: 0 0 .5rem; text-wrap: balance;
  }
  .cap-d {
    font-family: var(--serif); font-size: .9rem; color: var(--muted);
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
    font-family: var(--sans); font-size: var(--label-sm); font-weight: 700;
    letter-spacing: var(--track); color: var(--ink);
  }
  .cat-h .lvl {
    font-family: var(--mono); font-size: .6rem;
    padding: .15rem .45rem; border: 1px solid var(--border); color: var(--muted);
  }
  .cat-h .lvl.fund { background: var(--teal-soft); color: var(--teal-deep); border-color: var(--teal); }
  .cat-col table { width: 100%; border-collapse: collapse; }
  .cat-col td {
    padding: .55rem 1.25rem; font-size: .82rem;
    border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums;
  }
  .cat-col tr:last-child td { border-bottom: none; }
  .cat-col td.lbl { color: var(--muted); font-family: var(--sans); }
  .cat-col td.r { text-align: right; font-family: var(--mono); color: var(--ink); font-weight: 600; }

  /* CTA STRIP — flat dark, no glow */
  .cta-strip {
    margin: 3.5rem 0 0; padding: 3.5rem 2.5rem; background: var(--ink);
    color: var(--paper);
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 3rem; align-items: center;
  }
  .cta-strip h3 {
    font-family: var(--serif); font-weight: 400;
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
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
    transition: background .18s ease, color .18s ease;
  }
  .cta-light:hover { background: var(--teal); color: var(--paper); }
  .cta-outline {
    background: transparent; border: 1px solid rgba(245,240,225,.4); color: var(--paper);
    font-family: var(--sans); font-size: var(--label); font-weight: 700;
    letter-spacing: var(--track); text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
    transition: background .18s ease, color .18s ease, border-color .18s ease;
  }
  .cta-outline:hover { background: var(--paper); color: var(--ink); border-color: var(--paper); }

  /* FOOTER */
  footer {
    margin-top: 3rem; padding: 2rem; border-top: 1px solid var(--rule);
    display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    flex-wrap: wrap;
    font-family: var(--sans); font-size: .82rem; color: var(--muted);
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
        '<nav class="topnav" aria-label="Primary">'
        '<a href="#coverage">Coverage</a>'
        '<a href="#modules">What it computes</a>'
        '<a href="#proof">A provider file</a>'
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
        '<span class="here">The workspace</span>'
        '</div>'
    )


def _hero() -> str:
    return (
        '<section class="hero">'
        '<div>'
        '<div class="eyebrow">'
        '<span>PROVIDER&nbsp;DILIGENCE</span>'
        '<span class="dot">&middot;</span>'
        '<span>US&nbsp;HEALTHCARE</span>'
        '<span class="dot">&middot;</span>'
        '<span class="slug">built on public data</span>'
        '</div>'
        '<h1 class="title">Every number, <br/>'
        '<em>back to the filing.</em></h1>'
        '<p class="lede">'
        'Take any Medicare-certified provider apart against what it '
        'actually filed &mdash; cost report, quality measures, ownership, '
        'and the peers it sits among. Read a whole CMS program '
        'nationally, or one facility line by line. '
        '<b>Every figure traces to the public document it came from</b>, '
        'and nothing you add ever leaves your infrastructure.'
        '</p>'
        '<div class="hero-actions">'
        f'<a href="{_LOGIN}" class="cta-btn">Open the workspace &rarr;</a>'
        '<a href="#coverage" class="ghost-btn">See what it covers &darr;</a>'
        '</div>'
        '</div>'
        + _hero_art()
        + '</section>'
    )


def _hero_art() -> str:
    """Coverage card for the hero's right column.

    Was an illustrative "comparable transactions by year" chart with a
    made-up shape. It is now the real certified-provider universe: one
    bar per CMS program class, heights proportional to the actual counts
    in the shipped provider crosswalk, and three figures underneath that
    are read from the data rather than typed in.
    """
    total = max(_CCNS_BY_CLASS.values())
    bars, ticks, x = "", "", 16
    for label, n in _CCNS_BY_CLASS.items():
        h = max(6, round(80 * n / total))
        fill = "var(--teal-deep)" if label == "Hospital" else "var(--teal)"
        bars += (f'<rect x="{x}" y="{110 - h}" width="30" height="{h}" '
                 f'rx="1" fill="{fill}"/>')
        ticks += (f'<text x="{x + 15}" y="124" text-anchor="middle" '
                  f'class="ha-tick">{label[:4]}</text>')
        x += 48
    return (
        '<aside class="hero-art">'
        '<div class="ha-card">'
        '<div class="ha-head">'
        '<span class="ha-eyebrow"><span class="ha-dot"></span>'
        'Coverage</span>'
        '<span class="ha-chip">CERTIFIED&nbsp;PROVIDERS</span>'
        '</div>'
        '<div class="ha-ctitle">Certified facilities '
        '<span>by program</span></div>'
        '<div class="ha-csub">Medicare-certified CCNs &middot; '
        'seven provider classes</div>'
        '<svg class="ha-chart" role="img" '
        'aria-label="Medicare-certified facility counts by provider '
        'class: skilled nursing largest, then home health, dialysis, '
        'hospice, hospital, inpatient rehab, long-term care" '
        'viewBox="0 0 360 132" preserveAspectRatio="xMidYMid meet">'
        '<line x1="14" y1="110" x2="346" y2="110" '
        'stroke="var(--border)" stroke-width="1"/>'
        + bars + ticks +
        '</svg>'
        '<div class="ha-kpis">'
        '<div class="ha-row"><span class="k">Certified CCNs</span>'
        f'<span class="v">{_N_CCNS:,}</span></div>'
        '<div class="ha-row"><span class="k">Hospital cost reports</span>'
        f'<span class="v">{_N_HOSPITALS:,}</span></div>'
        '<div class="ha-row"><span class="k">Source-cited deals</span>'
        f'<span class="v">{_N_VERIFIED_DEALS}</span></div>'
        '</div>'
        '<div class="ha-foot"><span class="arr">&#8627;</span> '
        'Source: CMS Provider of Services &middot; HCRIS &middot; '
        'Care Compare</div>'
        '</div>'
        '</aside>'
    )


def _triplet() -> str:
    cells = [
        ("/01", "Start from a <em>provider</em>",
         "Type a CCN, an NPI, or a facility name. It resolves across "
         "every CMS program that provider bills under &mdash; so an "
         "operator running a hospital, two home-health agencies and a "
         "hospice reads as one operator, not four rows."),
        ("/02", "Read the whole <em>universe</em>",
         "Not just your target. Every certified nursing home, home-health "
         "agency, hospice, dialysis centre, rehab and long-term-care "
         "hospital in the country, on the measures CMS publishes for "
         "each &mdash; so you can see where one facility actually sits."),
        ("/03", "Every figure <em>shows its source</em>",
         "Each number names the cost report, Care Compare file or "
         "ownership filing it was computed from, and the data catalog "
         "says how fresh that file is and what is missing from it."),
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
    """Horizontal stat strip, one cell per tuple
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


def _coverage_section() -> str:
    """The provider universe, by CMS program class.

    Replaces a "deal funnel" (Sourced / Screened / IOI / LOI / SPA /
    Closed / Hold, on invented counts and EVs). That funnel described
    one audience's workflow and ran entirely on made-up numbers; this
    describes what the product actually holds, on counts read from the
    shipped crosswalk at import.
    """
    top = max(_CCNS_BY_CLASS.values())
    strip = _funnel(
        [(label, f"{n:,}", _CLASS_BLURB[label], round(100 * n / top),
          "var(--teal-deep)" if label == "Hospital" else "")
         for label, n in _CCNS_BY_CLASS.items()],
        columns=len(_CCNS_BY_CLASS),
    )
    rows = "".join(
        '<tr>'
        f'<td class="lbl">{label}</td>'
        f'<td class="r">{n:,}</td>'
        f'<td class="r" style="color:var(--muted)">{_CLASS_SOURCE[label]}</td>'
        '</tr>'
        for label, n in _CCNS_BY_CLASS.items()
    )
    rows += (
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">'
        'All certified CCNs</td>'
        f'<td class="r" style="font-weight:700">{_N_CCNS:,}</td>'
        '<td class="r" style="color:var(--muted)">'
        'CMS Provider of Services</td></tr>'
    )
    return (
        '<section id="coverage">'
        + _sect(
            "THE COVERAGE",
            "Every certified provider, <br/><em>not just yours.</em>",
            "Seven Medicare programs, read nationally rather than one "
            "target at a time. The point of holding the whole universe is "
            "that a single facility&rsquo;s numbers only mean something "
            "next to the ones it sits among.",
        )
        + '<div class="pair">'
        f'<div class="viz">{strip}</div>'
        '<div class="data">'
        '<div class="data-h"><span>Certified facilities by program</span>'
        '<span class="sample-tag">Live count</span></div>'
        '<table><thead><tr><th>Program</th><th class="r">Facilities</th>'
        '<th class="r">Source</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _capability_section() -> str:
    """What the workspace actually computes.

    Every route named here is asserted VISIBLE by
    ``tests/test_marketing_page.py``. The previous version advertised
    eight capabilities of which five (Monte Carlo, EBITDA bridge,
    comparables, covenant stress, management read) had been hidden as
    deal-execution machinery — a front door selling a product the app
    no longer offered.
    """
    caps = [
        ("CMS X-Ray", "Identity", "/diligence/xray",
         "One CCN, provider ID or name resolved across every CMS "
         "vertical the provider appears in."),
        ("HCRIS X-Ray", "Cost report",  "/diligence/hcris-xray",
         "A hospital's Medicare cost report read line by line, against "
         "peer percentiles, with the outliers flagged."),
        ("Provider universes", "Quality", "/verticals",
         "Care Compare for all seven programs: star ratings, staffing, "
         "outcomes, certified beds, ownership."),
        ("Screeners", "Search", "/target-screener",
         "Filter any provider universe on filed figures &mdash; size, "
         "margin, mix, geography. Nothing on the screen is modelled."),
        ("Health system lookup", "Ownership", "/health-system-lookup",
         "Which system operates which facility, and who actually "
         "controls the beds in a given market."),
        ("Identity crosswalks", "Plumbing", "/provider-crosswalk.csv",
         "CCN to NPI to system to county to CBSA, as CSV, each mapping "
         "beside the source that produced it."),
        ("Deal tracking", "Market", "/verified-deals",
         f"{_N_VERIFIED_DEALS} publicly-reported transactions, each row "
         "carrying the citation it was read from."),
        ("Data catalog", "Provenance", "/data",
         "Every source with its refresh cadence and row count &mdash; "
         "and a companion page for what is missing."),
    ]
    inner = "".join(
        f'<div class="cap">'
        f'<div class="cap-tag">{tag}</div>'
        f'<h3 class="cap-name">{name}</h3>'
        f'<p class="cap-d">{desc}</p>'
        f'</div>'
        for name, tag, _route, desc in caps
    )
    return (
        '<section id="modules">'
        + _sect(
            "WHAT IT COMPUTES",
            "Analysis that <br/>ships <em>in the box.</em>",
            "Every one of these runs on public data the moment you sign "
            "in &mdash; no add-on modules, no per-seat math, no waiting "
            "on a vendor to load your file.",
        )
        + f'<div class="caps">{inner}</div>'
        + '</section>'
    )


#: Routes named by the capability grid. Kept module-level so the test
#: can assert every one is still a visible surface without scraping HTML.
CAPABILITY_ROUTES = (
    "/diligence/xray", "/diligence/hcris-xray", "/verticals",
    "/target-screener", "/health-system-lookup", "/provider-crosswalk.csv",
    "/verified-deals", "/data",
)


def _profile_section() -> str:
    """What a provider file actually holds.

    Was "Project Meridian", an invented target with invented figures
    ($418M revenue, 108% net retention, 11.4x peer median). Naming the
    FIELDS instead of fabricating values makes the same point — four
    angles on one screen — without putting a made-up number on the
    public front door of a product whose promise is traceability.
    """
    columns = [
        ("IDENTITY", "filed", [
            ("CCN &amp; NPIs", "who this is"),
            ("Programs certified", "what it bills under"),
            ("Parent system", "who operates it"),
            ("County &middot; CBSA", "where it sits"),
        ]),
        ("COST REPORT", "filed", [
            ("Revenue &amp; operating margin", "HCRIS"),
            ("Beds &middot; patient days", "HCRIS"),
            ("Payer day mix", "HCRIS"),
            ("Opex per bed, per day", "HCRIS"),
        ]),
        ("QUALITY", "public", [
            ("Star ratings", "Care Compare"),
            ("Staffing hours", "Care Compare"),
            ("Outcome measures", "Care Compare"),
            ("Inspection history", "Care Compare"),
        ]),
        ("CONTEXT", "public", [
            ("Peer percentile, each metric", "vs cohort"),
            ("MA penetration", "county"),
            ("Payment updates this cycle", "CMS rules"),
            ("Reported transactions", "cited"),
        ]),
    ]
    cols_html = ""
    for title, level, rows in columns:
        lvl_cls = "lvl fund" if level == "filed" else "lvl market"
        lvl_txt = "FILED" if level == "filed" else "PUBLIC"
        row_html = "".join(
            f'<tr><td class="lbl">{label}</td>'
            f'<td class="r" style="color:var(--muted)">{src}</td></tr>'
            for label, src in rows
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
            "A PROVIDER FILE",
            "One facility, <br/>four <em>angles.</em>",
            "Identity, cost report, quality and context on one screen. "
            "These are the fields a provider file carries &mdash; not a "
            "worked example. There is no sample company here, because "
            "every value in the app is read from a filing rather than "
            "written by us.",
        )
        + '<div class="data-h" style="border:1px solid var(--rule);'
          'border-bottom:none;background:var(--paper-pure)">'
          '<span>What the X-ray pulls for any certified provider</span>'
          '<span class="sample-tag">Fields, not values</span></div>'
        + f'<div class="catalog" style="margin-top:0">{cols_html}</div>'
        + '</section>'
    )


def _sources_section() -> str:
    strip = _funnel([
        ("Provider of Services", f"{_N_CCNS:,}", "certified CCNs", 100, ""),
        ("HCRIS", f"{_N_HOSPITALS:,}", "cost reports", 62, ""),
        ("Care Compare", "7", "program files", 40, ""),
        ("Ownership filings", f"{_N_SYSTEMS}", "systems mapped", 34, ""),
        ("Reported deals", f"{_N_VERIFIED_DEALS}", "with citations", 30,
         "var(--green)"),
    ], columns=5)
    rows = (
        '<tr><td class="lbl">CMS Provider of Services '
        '(all seven certified classes)</td>'
        f'<td class="r">{_N_CCNS:,}</td></tr>'
        '<tr><td class="lbl">HCRIS hospital cost reports</td>'
        f'<td class="r">{_N_HOSPITALS:,}</td></tr>'
        '<tr><td class="lbl">CMS Care Compare quality files</td>'
        '<td class="r">7</td></tr>'
        '<tr><td class="lbl">Health systems mapped to their facilities</td>'
        f'<td class="r">{_N_SYSTEMS}</td></tr>'
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">'
        'Transactions with a citation URL</td>'
        f'<td class="r" style="font-weight:700">{_N_VERIFIED_DEALS}</td></tr>'
    )
    return (
        '<section id="sources">'
        + _sect(
            "THE DATA",
            "Public where it can be, <br/><em>yours</em> where it counts.",
            "It ships loaded with the CMS public estate &mdash; every "
            "certified provider, the cost reports, the quality files and "
            "the ownership behind them. Add your own research and notes "
            "alongside; nothing you add is sent anywhere.",
        )
        + '<div class="pair">'
        f'<div class="viz">{strip}</div>'
        '<div class="data">'
        '<div class="data-h"><span>What ships loaded</span>'
        '<span class="sample-tag">Live count</span></div>'
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
        '<p>It runs on your infrastructure with the model you choose, '
        'local or hosted. The CMS estate comes preloaded; add your own '
        'research when you&rsquo;re ready. No data leaves the box, '
        'no SaaS lock-in.</p>'
        '</div>'
        '<div class="cta-strip-actions">'
        f'<a href="{_LOGIN}" class="cta-light">Open the workspace &rarr;</a>'
        f'<a href="{_LOGIN}" class="cta-outline">Request access</a>'
        '</div>'
        '</section>'
    )


def _footer() -> str:
    return (
        '<footer>'
        '<span>PE <em>Desk</em>: diligence on US healthcare providers, '
        'from public data</span>'
        '<span class="mono" style="font-size:.75rem">'
        'CMS Provider of Services &middot; HCRIS &middot; Care Compare '
        '&middot; ownership filings &middot; your notes</span>'
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
        '<title>PE Desk: diligence on US healthcare providers, '
        'from public data</title>'
        '<meta name="description" content="Take any Medicare-certified '
        'provider apart against what it filed: cost report, quality '
        'measures, ownership, and the peers it sits among. Every '
        'certified CCN across seven CMS programs, with each figure '
        'traced to the public document it came from. For anyone doing '
        'diligence on US healthcare - investors, operators, advisors, '
        'lenders and researchers alike. Runs on your own '
        'infrastructure.">'
        + _STYLE
        + '</head><body>'
        + _topbar()
        + _crumbs()
        + '<div class="page">'
        + _hero()
        + _triplet()
        + _coverage_section()
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

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
  body {
    background-image:
      radial-gradient(circle at 12% 4%, rgba(31,122,117,.07), transparent 38%),
      radial-gradient(circle at 92% 22%, rgba(21,87,82,.05), transparent 42%),
      linear-gradient(180deg, var(--bg) 0%, var(--bg) 100%);
    background-attachment: fixed;
  }
  .sans { font-family: "Inter", sans-serif; }
  .mono { font-family: "JetBrains Mono", monospace; font-feature-settings: "tnum" on; }

  @keyframes ck-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: .55; transform: scale(1.15); }
  }
  @keyframes ck-rise {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

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
    background: linear-gradient(135deg, var(--ink) 0%, var(--ink-2) 100%);
    color: var(--paper);
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: .8rem 1.4rem; border: none; cursor: pointer; text-decoration: none;
    display: inline-block;
    transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
    box-shadow: 0 1px 0 rgba(15,28,46,.08);
  }
  .cta-btn:hover {
    background: linear-gradient(135deg, var(--teal-deep) 0%, var(--teal) 100%);
    transform: translateY(-1px);
    box-shadow: 0 8px 20px -8px rgba(21,87,82,.45);
  }

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
    position: relative;
  }
  .hero::before {
    content: ""; position: absolute; left: -1.5rem; top: 5rem;
    width: 3px; height: 7rem;
    background: linear-gradient(180deg, var(--teal-deep) 0%, var(--teal) 60%, transparent 100%);
  }
  .hero > div:first-child { animation: ck-rise .6s ease-out; }
  .eyebrow {
    font-family: "Inter", sans-serif; font-size: .72rem; letter-spacing: .14em;
    text-transform: uppercase; color: var(--muted); font-weight: 600;
    display: flex; align-items: center; gap: .6rem; margin-bottom: 1.25rem;
  }
  .eyebrow .dot { color: var(--faint); }
  .eyebrow .slug { font-family: "JetBrains Mono", monospace; color: var(--teal-deep); letter-spacing: .04em; }
  .eyebrow::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%;
    background: var(--teal); display: inline-block;
    animation: ck-pulse 2.4s ease-in-out infinite;
    box-shadow: 0 0 0 3px rgba(31,122,117,.12);
  }
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
    position: relative; overflow: hidden;
  }
  .triplet::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg,
      var(--teal-deep) 0%, var(--teal) 33%,
      var(--teal-soft) 50%, var(--teal) 67%, var(--teal-deep) 100%);
    opacity: .85;
  }
  .trip-cell {
    padding: 2rem 1.75rem; border-right: 1px solid var(--border);
    transition: background .25s ease, transform .25s ease;
    position: relative;
  }
  .trip-cell:hover {
    background: linear-gradient(180deg, var(--teal-soft) 0%, var(--paper-pure) 80%);
  }
  .trip-cell:hover .trip-num { color: var(--teal); }
  .trip-cell:last-child { border-right: none; }
  .trip-num {
    font-family: "JetBrains Mono", monospace; font-size: .72rem;
    color: var(--teal-deep); letter-spacing: .04em; margin-bottom: .8rem;
    transition: color .25s ease;
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
    padding: 4rem 0 1.5rem; margin-top: 1rem;
    border-top: 1px solid var(--rule);
    position: relative;
  }
  .sect::before {
    content: ""; position: absolute; top: -1px; left: 0; width: 80px; height: 3px;
    background: linear-gradient(90deg, var(--teal-deep), var(--teal) 70%, transparent);
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
    background-image:
      linear-gradient(135deg, rgba(31,122,117,.04) 0%, transparent 40%),
      linear-gradient(315deg, rgba(31,122,117,.03) 0%, transparent 40%);
  }
  .proof-cell {
    padding: 1.5rem 1.25rem; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
    transition: background .2s ease;
    position: relative;
  }
  .proof-cell:hover { background: rgba(31,122,117,.045); }
  .proof-cell:hover .proof-v em { color: var(--teal); }
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
  .cat-col {
    border-right: 1px solid var(--border);
    transition: background .25s ease;
  }
  .cat-col:hover .cat-h { background: var(--teal-soft); }
  .cat-col:hover .cat-h .ttl { color: var(--teal-deep); }
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
    margin: 3rem 0; padding: 2.5rem 3rem;
    background: linear-gradient(135deg, var(--paper-pure) 0%, rgba(212,228,226,.55) 100%);
    border: 1px solid var(--rule); border-left: 3px solid var(--teal);
    display: grid; grid-template-columns: 1fr 280px; gap: 3rem; align-items: center;
    position: relative; overflow: hidden;
  }
  .pull::before {
    content: "\\201C"; position: absolute; top: -2rem; right: 2rem;
    font-family: "Source Serif 4", serif; font-style: italic;
    font-size: 9rem; color: rgba(21,87,82,.08); line-height: 1;
    pointer-events: none;
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
    margin: 3rem 0 0; padding: 3.5rem 2.5rem;
    background:
      radial-gradient(circle at 85% 30%, rgba(31,122,117,.18) 0%, transparent 55%),
      linear-gradient(135deg, var(--ink) 0%, var(--ink-2) 100%);
    color: var(--paper);
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 3rem; align-items: center;
    position: relative; overflow: hidden;
  }
  .cta-strip::before {
    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, var(--teal) 50%, transparent);
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
  .cta-light {
    transition: transform .18s ease, box-shadow .18s ease, background .18s ease, color .18s ease;
  }
  .cta-light:hover {
    background: var(--teal); color: var(--paper);
    transform: translateY(-1px);
    box-shadow: 0 10px 24px -10px rgba(31,122,117,.55);
  }
  .cta-outline {
    background: transparent; border: 1px solid var(--paper); color: var(--paper);
    font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 1rem 1.5rem; text-decoration: none; text-align: center;
    transition: background .18s ease, color .18s ease;
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
        '<span>COMMERCIAL&nbsp;DILIGENCE</span>'
        '<span class="dot">&middot;</span>'
        '<span>CLIENT-FACING&nbsp;INTELLIGENCE</span>'
        '<span class="dot">&middot;</span>'
        '<span class="slug">/v1.0.0</span>'
        '</div>'
        '<h1 class="title">Commercial diligence,<br/>'
        '<em>personalized</em> to every deal.</h1>'
        '<p class="lede">'
        'Built for client-facing deal teams working across markets, '
        'clients, and targets. Create living deal profiles that '
        'combine market research, company intelligence, customer '
        'signals, benchmarks, interviews, and source-backed findings '
        '&mdash; all organized around the opportunity at hand.'
        '</p>'
        '<div class="hero-actions">'
        f'<a href="{_LOGIN}" class="cta-btn">Open Deal Workspace</a>'
        '<a href="#platform" class="ghost-btn">See a sample profile &darr;</a>'
        '</div>'
        '</div>'
        '<div class="hero-meta">'
        '<div class="row"><span class="k">WORKSPACE</span>'
        '<span class="v">CCF-DILIGENCE</span></div>'
        '<div class="row"><span class="k">KIND</span>'
        '<span class="v">INTELLIGENCE LAYER</span></div>'
        '<div class="row"><span class="k">STATUS</span>'
        '<span class="v" style="color:var(--green)">LIVE</span></div>'
        '<div class="stamp">'
        'Built for diligence teams who want every source, benchmark, '
        'and client priority connected to the deal. Public sources '
        'only &mdash; no PHI on this instance.'
        '</div>'
        '</div>'
        '</section>'
    )


def _triplet() -> str:
    cells = [
        ("/01", "One profile <em>per opportunity</em>",
         "Each target gets a living intelligence layer: company facts, "
         "market context, client priorities, competitors, benchmarks, "
         "and open diligence questions. Enter once &mdash; every "
         "downstream analytic opens with the deal pre-filled."),
        ("/02", "Market, client, <em>and deal together</em>",
         "Connect the target company to the broader commercial picture: "
         "market structure, growth drivers, customer behavior, competitive "
         "positioning, pricing, and comparable assets &mdash; all linked "
         "to the deal."),
        ("/03", "Source-backed <em>and reusable</em>",
         "Every claim traces back to its underlying source &mdash; "
         "filings, research, interviews, benchmarks, notes, or prior "
         "engagement work. Verify, reuse, and turn research into "
         "client-ready recommendations."),
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
            "THE WORKSPACE",
            "Market, client, <em>and deal</em><br/>"
            "intelligence in one place.",
            "Create a workspace for each opportunity that combines target "
            "profiles, market maps, commercial benchmarks, client context, "
            "research notes, and deal history. Move from scattered "
            "information to a clear view of what matters, what is changing, "
            "and what the client needs to know.",
        )
        + '<div class="pair">'
        f'<div class="viz">{funnel}</div>'
        '<div class="data">'
        '<div class="data-h"><span>SAMPLE DEAL FUNNEL</span>'
        '<span class="src">deal.profile / funnel</span></div>'
        '<table><thead><tr><th>Stage</th><th class="r">N</th>'
        '<th class="r">EV</th><th class="r">&rarr; prior</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</div>'
        '</div>'
        '</section>'
    )


def _proof_section() -> str:
    cells = [
        ("<em>247</em>",
         "Source-backed Claims",
         "Across the sample profile &mdash; every claim cited"),
        ("<em>42</em>",
         "Market Briefs",
         "Sector maps, demand drivers, growth signals"),
        ("<em>18</em>",
         "Client Priorities",
         "Engagement-specific watch-list connected to the deal"),
        ("$<em>4.2</em>B",
         "Comparable TEV",
         "Reference transactions matched to the target"),
        ("<em>11.4</em>x",
         "Median Peer Multiple",
         "EV / EBITDA across the matched comparable set"),
        ("<em>26</em>",
         "Interviews Logged",
         "Customer + channel + competitor calls, transcribed"),
        ("<em>9</em>",
         "Open Diligence Risks",
         "Tracked from kickoff to readout with status updates"),
        ("<em>4</em>/14",
         "Targets &rarr; Long-list",
         "29% screen-to-long-list conversion this engagement"),
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
            "DILIGENCE SIGNAL",
            "Insight <em>that supports</em><br/>the diligence story.",
            "Eight tracked signals across a sample engagement &mdash; "
            "market evidence, customer interviews, comparable transactions, "
            "and client priorities, all carrying source citations. Click "
            "into the workspace to see the underlying notes and references.",
        )
        + f'<div class="proof">{inner}</div>'
        + '</section>'
    )


def _catalog_section() -> str:
    columns = [
        ("COMPANY PROFILE", "deal", [
            ("Revenue", "$418M", ""),
            ("Locations", "62 sites", ""),
            ("Ownership", "Sponsor-backed", ""),
            ("Management tenure", "4.2y avg", ""),
        ]),
        ("MARKET LANDSCAPE", "market", [
            ("TAM", "$28B", ""),
            ("Growth (5y CAGR)", "+7.4%", "var(--green)"),
            ("Top 3 share", "31%", "var(--amber)"),
            ("Reg exposure", "Moderate", "var(--amber)"),
        ]),
        ("COMPETITIVE SET", "market", [
            ("Peer count", "14", ""),
            ("Peer median EV/EBITDA", "11.4x", ""),
            ("Pricing position", "Premium", "var(--green)"),
            ("Differentiator", "Network density", ""),
        ]),
        ("CUSTOMER SIGNALS", "deal", [
            ("Net retention", "108%", "var(--green)"),
            ("Top-10 concentration", "34%", "var(--amber)"),
            ("Referral velocity", "+12% QoQ", "var(--green)"),
            ("Churn risk flags", "3", "var(--amber)"),
        ]),
    ]
    cols_html = ""
    for title, level, rows in columns:
        lvl_cls = (
            "lvl fund" if level == "deal"
            else "lvl market" if level == "market"
            else "lvl"
        )
        lvl_txt = (
            "DEAL" if level == "deal"
            else "MARKET" if level == "market"
            else "—"
        )
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
            "PROFILE CATALOG",
            "Every <em>insight</em><br/>has context.",
            "Organize research by target, market, customer segment, "
            "competitor, workstream, and client priority. The catalog is "
            "the spine of the deal workspace &mdash; click any row in "
            "the live app to scroll to its underlying source.",
        )
        + f'<div class="catalog">{cols_html}</div>'
        + '</section>'
    )


def _pull_quote() -> str:
    stats = [
        ("3 hours", "Saved per profile, on average"),
        ("100%", "Of claims traceable to a source"),
        ("1 workspace", "Replaces 6+ decks per engagement"),
    ]
    stats_html = "".join(
        f'<div><div class="stat-v">{v}</div>'
        f'<div class="stat-l">{label}</div></div>'
        for v, label in stats
    )
    return (
        '<section class="pull">'
        '<div>'
        '<q>The profile gave us a market view, target context, and '
        'client-specific talking points before the first diligence '
        'readout. We stopped rebuilding the story from scratch every '
        'engagement.</q>'
        '<div class="attr"><b>Director, Commercial Diligence</b>'
        'Strategy Consulting Firm</div>'
        '</div>'
        f'<div class="stats">{stats_html}</div>'
        '</section>'
    )


def _sources_section() -> str:
    funnel = _funnel([
        ("HCRIS", "2,847", "cost reports", 100, ""),
        ("Market reports", "184", "sector briefs", 70, ""),
        ("Interviews", "26", "calls logged", 35, ""),
        ("Filings", "412", "10-K / S-1", 55, ""),
        ("Internal notes", "98", "engagements", 80, ""),
    ], columns=5)
    rows = (
        '<tr><td class="lbl">CMS public data (HCRIS, MA, CMS-Compare)</td>'
        '<td class="r">2,847</td></tr>'
        '<tr><td class="lbl">Sector + market research reports</td>'
        '<td class="r">184</td></tr>'
        '<tr><td class="lbl">Customer / channel / competitor interviews</td>'
        '<td class="r">26</td></tr>'
        '<tr><td class="lbl">SEC filings (10-K, S-1, proxies)</td>'
        '<td class="r">412</td></tr>'
        '<tr class="hot">'
        '<td class="lbl" style="font-weight:700; color:var(--ink)">'
        'Internal engagement notes &amp; decks</td>'
        '<td class="r" style="font-weight:700">98</td></tr>'
    )
    return (
        '<section id="sources">'
        + _sect(
            "SOURCE LIBRARY",
            "Every claim, <em>cited inline</em>.",
            "Filings, market research, interviews, benchmarks, and "
            "engagement notes &mdash; every number traces back to its "
            "underlying source. No PHI, no proprietary data leaving the "
            "workspace, no SaaS lock-in. The intelligence layer is yours.",
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
        '<div class="micro">READY TO OPEN A WORKSPACE</div>'
        '<h3>Bring the <em>research</em>.<br/>'
        'Keep the <em>client view</em>.</h3>'
        '<p>Sign in to your team workspace. Public sources are preloaded '
        '&mdash; connect CRM, market data, or research feeds when you\'re '
        'ready.</p>'
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
        '<span>PE <em>Desk</em> v1.0.0 &mdash; Commercial diligence, '
        'personalized to every deal</span>'
        '<span class="mono" style="font-size:.75rem">'
        'CMS public data &middot; market reports &middot; filings '
        '&middot; interviews &middot; engagement notes</span>'
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
        '<title>PE Desk &mdash; Commercial diligence, personalized '
        'to every deal</title>'
        '<meta name="description" content="PE Desk is the commercial '
        'diligence intelligence layer for client-facing deal teams. '
        'Build living target-company profiles with market research, '
        'customer signals, benchmarks, competitive context, client '
        'priorities, and source-backed notes — organized around the '
        'opportunity at hand.">'
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

"""SeekingChartis — public marketing landing page.

Phase 13 of the UI v2 editorial rework. New page at ``GET /``
(under ``CHARTIS_UI_V2=1``); the legacy dashboard stays at ``/``
when the flag is off so existing partners see no change.

Port of ``components/MarketingPage.jsx`` from the Claude Design
handoff. Rendered server-side as a single ~400-line HTML document
using the editorial navy / teal / parchment palette + Source Serif
4 + Inter Tight typography. No React at runtime — the JSX was a
prototype medium, the truth is the visual composition.

Sections (top → bottom):
  1. Hero — display headline + lead paragraph + primary CTA
  2. Capabilities — four-engine grid (Monte Carlo v2, PE-math,
     Health/Completeness, AI-augmented memos)
  3. Modules — seven-stage pipeline (Screen → Source → Diligence
     → Analyze → IC Prep → Hold → Exit)
  4. Stats — platform-depth numbers (HCRIS hospitals, tests,
     modules, routes)
  5. CTA strip — "Open Platform" card
  6. Footer

Visual truth: navy on parchment for most sections; modules and
CTA strip invert to parchment-on-navy for rhythm. Teal accents
(eyebrows, primary CTA, progress dots) land in both.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ..brand import PALETTE


# ── Small primitives ────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return _html.escape(str(s), quote=True) if s is not None else ""


def _eyebrow(text: str, *, on_navy: bool = False) -> str:
    color = "var(--teal)" if on_navy else "var(--teal-deep)"
    tx = "var(--muted)" if on_navy else "var(--muted)"
    return (
        '<div class="sc-eyebrow" style="'
        'display:inline-flex;align-items:center;gap:12px;'
        f'font-family:\"JetBrains Mono\", monospace;font-size:11px;font-weight:600;'
        'letter-spacing:0.16em;text-transform:uppercase;'
        f'color:{tx};">'
        f'<span style="display:inline-block;width:24px;height:2px;'
        f'background:{color};"></span>{_esc(text)}'
        '</div>'
    )


def _h_display(text: str) -> str:
    return (
        '<h1 style="font-family:\"Source Serif 4\", Georgia, serif;font-weight:400;'
        'font-size:clamp(40px, 5.5vw, 72px);line-height:1.05;'
        'letter-spacing:-0.02em;color:var(--ink-2);margin:0;">'
        f'{text}</h1>'
    )


def _h_section(text: str, *, on_navy: bool = False) -> str:
    color = "var(--paper)" if on_navy else "var(--ink-2)"
    return (
        '<h2 style="font-family:\"Source Serif 4\", Georgia, serif;font-weight:400;'
        'font-size:clamp(30px, 3.6vw, 44px);line-height:1.08;'
        f'letter-spacing:-0.015em;color:{color};margin:0;max-width:22ch;">'
        f'{text}</h2>'
    )


def _lead(text: str, *, on_navy: bool = False) -> str:
    color = "var(--muted)" if on_navy else "var(--muted)"
    return (
        '<p style="font-family:\"Source Serif 4\", Georgia, serif;font-weight:400;'
        f'font-size:19px;line-height:1.6;color:{color};'
        'max-width:46ch;margin:0;">'
        f'{_esc(text)}</p>'
    )


def _cta_primary(href: str, label: str) -> str:
    return (
        f'<a href="{_esc(href)}" style="'
        'display:inline-flex;align-items:center;gap:12px;'
        'padding:16px 28px;background:var(--ink-2);color:var(--paper);'
        'font-family:\"Inter\", -apple-system, sans-serif;font-size:14px;font-weight:600;'
        'letter-spacing:0.04em;text-decoration:none;border-radius:2px;'
        'transition:background 0.15s;">'
        f'{_esc(label)}'
        '<svg width="14" height="14" viewBox="0 0 12 12" style="flex-shrink:0;">'
        '<path d="M2 10 L10 2 M4 2 L10 2 L10 8" '
        'stroke="currentColor" stroke-width="1.5" fill="none"/>'
        '</svg></a>'
    )


def _cta_ghost(href: str, label: str, *, on_navy: bool = False) -> str:
    color = "var(--paper)" if on_navy else "var(--ink-2)"
    border = "var(--faint)" if on_navy else "var(--ink-2)"
    return (
        f'<a href="{_esc(href)}" style="'
        'display:inline-flex;align-items:center;gap:12px;'
        f'padding:14px 26px;color:{color};'
        f'border:1px solid {border};'
        'font-family:\"Inter\", -apple-system, sans-serif;font-size:14px;font-weight:600;'
        'letter-spacing:0.04em;text-decoration:none;border-radius:2px;">'
        f'{_esc(label)}</a>'
    )


# ── Hero ───────────────────────────────────────────────────────────

def _hero() -> str:
    return (
        '<section style="background:var(--bg);">'
        '<div style="max-width:1280px;margin:0 auto;padding:72px 32px 96px;'
        'display:grid;grid-template-columns:1.05fr 1fr;gap:80px;'
        'align-items:center;">'
        '<div>'
        f'{_eyebrow("Healthcare PE Diligence Platform")}'
        '<div style="height:28px;"></div>'
        + _h_display("Purpose-built<br/>to codify partner<br/>judgment at scale.")
        + '<div style="height:32px;"></div>'
        + _lead(
            "SeekingChartis is the diligence and portfolio-operations "
            "platform for healthcare-focused private equity. From "
            "screening to exit, 278 partner-reflex modules run on "
            "6,024 HCRIS hospitals and thousands of regression tests.")
        + '<div style="height:36px;"></div>'
        + '<div style="display:flex;gap:16px;align-items:center;">'
        + _cta_primary("/home", "Open Platform")
        + _cta_ghost("/methodology", "Methodology")
        + '</div>'
        + '</div>'
        '<div style="padding-right:20px;padding-top:20px;">'
        + _hero_chart_svg()
        + '</div>'
        '</div>'
        '</section>'
    )


def _hero_chart_svg() -> str:
    """A stylised data-chart mark — a navy-on-bone composition that
    suggests the density of the platform without needing a real image
    asset. Matches the DataHero() component from the JSX prototype."""
    points_path = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="3" fill="#0b2341"/>'
        for cx, cy in [(20, 300), (70, 270), (120, 240), (170, 210),
                        (220, 180), (270, 220), (320, 160), (370, 130),
                        (420, 90), (460, 60)]
    )
    return (
        '<svg viewBox="0 0 480 360" style="width:100%;height:auto;'
        'background:var(--paper);border-radius:2px;'
        'box-shadow:0 1px 2px rgba(6,22,38,0.06);">'
        '<defs><pattern id="gridMkt" width="40" height="40" '
        'patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" '
        'stroke="rgba(29,60,105,0.06)" stroke-width="1"/>'
        '</pattern></defs>'
        '<rect width="480" height="360" fill="url(#gridMkt)"/>'
        '<polyline points="20,300 70,270 120,240 170,210 220,180 270,220 '
        '320,160 370,130 420,90 460,60" '
        'fill="none" stroke="#0b2341" stroke-width="2.5"/>'
        '<polyline points="20,260 70,245 120,220 170,195 220,175 270,205 '
        '320,175 370,155 420,130 460,110" '
        'fill="none" stroke="#2fb3ad" stroke-width="1.5" '
        'stroke-dasharray="4 4"/>'
        f'{points_path}'
        '<line x1="20" y1="320" x2="460" y2="320" stroke="#d6cfc3" '
        'stroke-width="1"/>'
        '<line x1="20" y1="40" x2="20" y2="320" stroke="#d6cfc3" '
        'stroke-width="1"/>'
        '<text x="30" y="335" font-family="JetBrains Mono, monospace" '
        'font-size="9" fill="#7a8699" letter-spacing="1">2018</text>'
        '<text x="430" y="335" font-family="JetBrains Mono, monospace" '
        'font-size="9" fill="#7a8699" letter-spacing="1">2026</text>'
        '<text x="30" y="60" font-family="JetBrains Mono, monospace" '
        'font-size="9" fill="#0f5e5a" letter-spacing="1">MOIC 3.2x</text>'
        '</svg>'
    )


# ── Capabilities grid ──────────────────────────────────────────────

def _capabilities() -> str:
    items = [
        ("01", "Monte Carlo v2",
         "Correlated portfolio simulation with named-scenario "
         "compare. 10,000 draws per deal, calibrated against stored "
         "priors at /api/calibration/priors."),
        ("02", "PE-math layer",
         "Bridge, MOIC, IRR, covenant headroom on every draw. "
         "EBITDA bridge and portfolio bridge render from a single "
         "DealAnalysisPacket."),
        ("03", "Health & completeness",
         "Health score 0–100 with component breakdown. Profile "
         "completeness graded A/B/C/D against the 38-metric RCM "
         "registry. Live at /api/deals/<id>/health."),
        ("04", "AI-augmented memos",
         "IC memos with per-section fact-checking against the "
         "packet. Document QA + multi-turn chat. Graceful template "
         "fallback when no LLM key is configured."),
    ]
    cards: List[str] = []
    for i, (num, title, body) in enumerate(items):
        border_right = ("1px solid var(--rule)"
                        if i < len(items) - 1 else "none")
        cards.append(
            '<div style="padding:32px 28px;'
            f'border-right:{border_right};">'
            '<div style="font-family:\"JetBrains Mono\", monospace;font-size:11px;'
            'color:var(--teal-deep);letter-spacing:0.16em;'
            f'margin-bottom:24px;">— {num}</div>'
            '<h3 style="font-family:\"Source Serif 4\", Georgia, serif;font-weight:500;'
            'font-size:22px;line-height:1.2;color:var(--ink-2);'
            f'margin:0 0 14px 0;">{_esc(title)}</h3>'
            '<p style="font-family:\"Inter\", -apple-system, sans-serif;font-size:14px;'
            'line-height:1.6;color:var(--muted);margin:0;">'
            f'{_esc(body)}</p>'
            '</div>'
        )
    return (
        '<section style="background:var(--bg);padding:96px 0;">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 32px;">'
        # Header row
        '<div style="display:grid;grid-template-columns:1fr 2fr;'
        'gap:80px;margin-bottom:56px;">'
        '<div>'
        f'{_eyebrow("What we do")}'
        '<div style="height:20px;"></div>'
        + _h_section("Four engines, one platform.")
        + '</div>'
        '<p style="font-family:\"Source Serif 4\", Georgia, serif;font-size:19px;'
        'line-height:1.6;color:var(--muted);padding-top:40px;'
        'margin:0;max-width:46ch;">'
        "SeekingChartis / RCM-MC compresses the least-leveraged hours "
        "of healthcare PE diligence. Dozens of API endpoints, hundreds "
        "of source files, thousands of passing tests, one SQLite file."
        '</p>'
        '</div>'
        # Grid row
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        'border-top:1px solid var(--border-strong);">'
        + "".join(cards) +
        '</div>'
        '</div></section>'
    )


# ── Modules (navy-inverted rhythm) ─────────────────────────────────

def _modules() -> str:
    stages = [
        ("Screen",    "Paste hospital names, ranked verdicts.",       "GET /screen"),
        ("Source",    "Thesis-driven origination, 6K+ HCRIS.",         "GET /source"),
        ("Diligence", "5-step wizard, CCN lookup to upload.",          "GET /new-deal"),
        ("Analyze",   "7-tab Bloomberg workbench.",                    "GET /analysis/<id>"),
        ("IC Prep",   "Checklist, memo, packet ZIP.",                  "GET /api/deals/<id>/checklist"),
        ("Hold",      "Notes, deadlines, variance, alerts.",           "GET /deal/<id>"),
        ("Exit",      "Exit modeling + multiple decomp.",              "GET /exit"),
    ]
    rows: List[str] = []
    for i, (k, desc, route) in enumerate(stages):
        rows.append(
            '<div style="display:grid;grid-template-columns:120px 1fr 200px;'
            'gap:40px;padding:24px 0;'
            f'border-bottom:1px solid var(--ink-2);'
            'align-items:baseline;">'
            # Stage number + label
            '<div>'
            '<div style="font-family:\"JetBrains Mono\", monospace;font-size:10px;'
            'color:var(--teal);letter-spacing:0.18em;'
            f'margin-bottom:6px;">STAGE {i+1:02d}</div>'
            '<div style="font-family:\"Source Serif 4\", Georgia, serif;font-size:22px;'
            f'font-weight:500;color:var(--paper);">{_esc(k)}</div>'
            '</div>'
            # Description
            '<div style="font-family:\"Source Serif 4\", Georgia, serif;font-size:16px;'
            'line-height:1.55;color:var(--muted);">'
            f'{_esc(desc)}</div>'
            # Route tag
            '<div style="font-family:\"JetBrains Mono\", monospace;font-size:11px;'
            'color:var(--faint);letter-spacing:0.04em;'
            f'text-align:right;">{_esc(route)}</div>'
            '</div>'
        )
    return (
        '<section style="background:var(--ink-2);color:var(--paper);'
        'padding:96px 0;">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 32px;">'
        '<div style="margin-bottom:56px;">'
        + _eyebrow("Platform modules", on_navy=True)
        + '<div style="height:20px;"></div>'
        + _h_section("From screening to exit, every stage has a "
                     "partner-reflex module.", on_navy=True)
        + '</div>'
        '<div style="border-top:1px solid var(--teal);">'
        + "".join(rows) +
        '</div>'
        '</div></section>'
    )


# ── Stats strip ────────────────────────────────────────────────────

def _stats() -> str:
    stats = [
        ("6,024",  "HCRIS hospitals"),
        ("278",    "Brain modules"),
        ("2,878",  "Regression tests"),
        ("52",     "API endpoints"),
    ]
    items: List[str] = []
    for i, (val, label) in enumerate(stats):
        border = ("1px solid var(--rule)"
                  if i < len(stats) - 1 else "none")
        items.append(
            '<div style="padding:40px 28px;'
            f'border-right:{border};">'
            '<div style="font-family:\"Source Serif 4\", Georgia, serif;font-size:48px;'
            'font-weight:400;letter-spacing:-0.02em;line-height:1;'
            f'color:var(--ink-2);margin-bottom:12px;">{_esc(val)}</div>'
            '<div style="font-family:\"JetBrains Mono\", monospace;font-size:11px;'
            'color:var(--faint);letter-spacing:0.14em;'
            f'text-transform:uppercase;">{_esc(label)}</div>'
            '</div>'
        )
    return (
        '<section style="background:var(--bg);padding:64px 0;">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 32px;">'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        'border-top:1px solid var(--border-strong);'
        'border-bottom:1px solid var(--border-strong);">'
        + "".join(items) +
        '</div></div></section>'
    )


# ── CTA strip ──────────────────────────────────────────────────────

def _cta_strip() -> str:
    return (
        '<section style="background:var(--paper);padding:96px 0;">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 32px;">'
        '<div style="display:grid;grid-template-columns:1fr 1fr;'
        'gap:80px;align-items:center;background:var(--ink-2);'
        'padding:64px 56px;border-radius:2px;">'
        '<div>'
        + _eyebrow("Ready to diligence", on_navy=True)
        + '<div style="height:20px;"></div>'
        + _h_section("Open the platform. The workbench is one click "
                     "from every deal.", on_navy=True)
        + '</div>'
        '<div style="display:flex;flex-direction:column;gap:14px;'
        'align-items:flex-start;">'
        + _cta_primary("/home", "Open Platform")
        + _cta_ghost("/library", "Browse Library", on_navy=True)
        + '</div>'
        '</div></div></section>'
    )


# ── Footer ─────────────────────────────────────────────────────────

def _footer() -> str:
    return (
        '<footer style="background:var(--ink);color:var(--muted);'
        'padding:48px 0 40px;font-family:\"Inter\", -apple-system, sans-serif;font-size:13px;">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 32px;'
        'display:flex;justify-content:space-between;align-items:center;">'
        '<div style="font-family:\"Source Serif 4\", Georgia, serif;font-size:18px;'
        'font-weight:500;color:var(--paper);letter-spacing:-0.005em;">'
        'Seeking<em style="font-weight:400;color:var(--teal-soft);">Chartis</em></div>'
        '<div style="font-family:\"JetBrains Mono\", monospace;font-size:11px;'
        'letter-spacing:0.1em;">© 2026 — Healthcare PE diligence, '
        'instrument-grade</div>'
        '</div></footer>'
    )


# ── Top-nav (minimal, marketing variant) ───────────────────────────

def _marketing_topnav() -> str:
    """Navy topbar mirroring chartis.com chrome — same wordmark +
    teal-on-navy CTA cluster as the signed-in app's chartis_shell.

    Continuity from `/` → `/login` → `/home` requires the topbar
    silhouette to be unchanged across all three; only the right-
    side action cluster differs (Methodology / Sign in on
    marketing, user chip on app).
    """
    return (
        '<header style="position:sticky;top:0;z-index:50;'
        'background:#0b2341;border-bottom:2px solid #2fb3ad;">'
        '<div style="max-width:1440px;margin:0 auto;padding:18px 32px;'
        'display:flex;align-items:center;justify-content:space-between;">'
        # Wordmark — white with teal accent arc, italic Chartis
        '<a href="/" style="text-decoration:none;'
        'font-family:\"Source Serif 4\", Georgia, serif;font-size:20px;font-weight:500;'
        'color:#e9eef5;letter-spacing:-0.005em;'
        'display:flex;align-items:center;gap:10px;">'
        '<svg width="26" height="26" viewBox="0 0 48 48" style="flex-shrink:0;">'
        '<circle cx="24" cy="24" r="22" fill="none" stroke="#e9eef5" stroke-width="1.5"/>'
        '<circle cx="24" cy="24" r="3" fill="#2fb3ad"/>'
        '<path d="M24 6 L19 15 L24 12 L29 15 Z" fill="#e9eef5"/>'
        '<path d="M42 24 L33 19 L36 24 L33 29 Z" fill="#e9eef5"/>'
        '<path d="M24 42 L29 33 L24 36 L19 33 Z" fill="#e9eef5"/>'
        '<path d="M6 24 L15 29 L12 24 L15 19 Z" fill="#e9eef5"/>'
        '</svg>'
        'Seeking<em style="font-weight:400;font-style:italic;color:#66c8c3;">'
        'Chartis</em></a>'
        # Right-side actions
        '<div style="display:flex;align-items:center;gap:18px;">'
        '<a href="/methodology" style="font-family:\"Inter Tight\", -apple-system, sans-serif;'
        'font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
        'color:#a5b4ca;text-decoration:none;">Methodology</a>'
        '<a href="/home" style="font-family:\"Inter Tight\", -apple-system, sans-serif;'
        'font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#0b2341;background:#2fb3ad;'
        'padding:10px 18px;border-radius:2px;text-decoration:none;'
        'display:inline-flex;align-items:center;gap:8px;">'
        'Open Platform <span style="font-size:14px;">↗</span></a>'
        '</div></div></header>'
    )


# ── Top-level render ────────────────────────────────────────────────

def render_marketing_page() -> str:
    """Full editorial marketing landing. Single self-contained
    HTML document — the tokens CSS provides var(--sc-*) tokens; no
    dependency on ``chartis_shell`` (the marketing page is its own
    surface, editorially distinct from the signed-in app).
    """
    fonts = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400&'
        'family=Inter+Tight:wght@400;500;600;700&'
        'family=JetBrains+Mono:wght@400;500;700&display=swap" '
        'rel="stylesheet">'
    )
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>SeekingChartis — Healthcare PE Diligence Platform</title>'
        '<meta name="description" content="'
        'SeekingChartis is the diligence and portfolio-operations '
        'platform for healthcare-focused private equity. From screening '
        'to exit, partner-reflex modules on 6,024 HCRIS hospitals.">'
        + fonts +
        '<link rel="stylesheet" href="/static/v3/chartis.css">'
        '<style>'
        '*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}'
        'body{background:var(--bg);color:var(--ink);'
        'font-family:\"Inter\", -apple-system, sans-serif;-webkit-font-smoothing:antialiased;}'
        'em{font-style:italic;}'
        '@media (max-width: 960px) {'
        '  [style*="grid-template-columns:1.05fr 1fr"],'
        '  [style*="grid-template-columns:1fr 2fr"],'
        '  [style*="grid-template-columns:repeat(4,1fr)"],'
        '  [style*="grid-template-columns:120px 1fr 200px"],'
        '  [style*="grid-template-columns:1fr 1fr"] {'
        '    grid-template-columns: 1fr !important; gap: 32px !important;'
        '  }'
        '  [style*="padding:64px 56px"] { padding: 40px 28px !important; }'
        '}'
        '</style>'
        '</head><body>'
        + _marketing_topnav()
        + _hero()
        + _capabilities()
        + _modules()
        + _stats()
        + _cta_strip()
        + _footer()
        + '</body></html>'
    )

"""Shared design system for all UI-generated HTML (UI-2).

One palette, one CSS bundle, one document shell consumed by every HTML
generator (output index, text wrapper, CSV view, PE JSON views). Before
this, each module carried its own CSS, so adjustments had to be replicated
4+ places and the visual language drifted.

Public API:

    BASE_CSS           — the shared stylesheet (one copy)
    PALETTE            — named colors for programmatic use (badges, etc.)
    shell(body, title, *, back_href=None, subtitle=None, extra_css="",
          extra_js="", generated=True) -> str
        Wraps a body fragment in the standard document layout with
        breadcrumb, title, footer, and generation timestamp.

Non-goals: replacing the legacy ``report.html`` / ``partner_brief.html``
CSS (those have their own long-established visual treatments and more
complex layout needs). Those surfaces stay on their current kits; the
shared kit covers the new UI-1 through UI-7 generators.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Optional


# ── Palette (single source of truth) ───────────────────────────────────────
#
# Every color used by any UI-generated HTML. Named so programmatic callers
# can reference ``PALETTE["green"]`` instead of scattered hex literals.
PALETTE = {
    "bg":           "#F9FAFB",
    "card":         "#FFFFFF",
    "border":       "#E5E7EB",
    "text":         "#111827",
    "muted":        "#6B7280",
    "accent":       "#1F4E78",
    "accent_soft":  "#EFF4F8",
    "accent_hover": "#154061",
    "green":        "#10B981",
    "green_soft":   "#D1FAE5",
    "green_text":   "#065F46",
    "amber":        "#F59E0B",
    "amber_soft":   "#FEF3C7",
    "amber_text":   "#92400E",
    "red":          "#EF4444",
    "red_soft":     "#FEE2E2",
    "red_text":     "#991B1B",
    "blue":         "#3B82F6",
    "blue_soft":    "#E0E7FF",
    "blue_text":    "#3730A3",
}


# ── Canonical stylesheet ──────────────────────────────────────────────────
#
# Shared across the UI-* HTML generators. Structured so:
# - CSS custom properties carry the palette — easy to theme
# - Layout primitives (.container, .card, .kpi-grid) are reusable
# - Table / badge / breadcrumb patterns are stable
# - No JavaScript-dependent styles (fallbacks for no-JS users still work)
BASE_CSS = f"""
:root {{
  --bg: {PALETTE['bg']};
  --card: {PALETTE['card']};
  --border: {PALETTE['border']};
  --text: {PALETTE['text']};
  --muted: {PALETTE['muted']};
  --accent: {PALETTE['accent']};
  --accent-soft: {PALETTE['accent_soft']};
  --accent-hover: {PALETTE['accent_hover']};
  --green: {PALETTE['green']};
  --green-soft: {PALETTE['green_soft']};
  --green-text: {PALETTE['green_text']};
  --amber: {PALETTE['amber']};
  --amber-soft: {PALETTE['amber_soft']};
  --amber-text: {PALETTE['amber_text']};
  --red: {PALETTE['red']};
  --red-soft: {PALETTE['red_soft']};
  --red-text: {PALETTE['red_text']};
  --blue: {PALETTE['blue']};
  --blue-soft: {PALETTE['blue_soft']};
  --blue-text: {PALETTE['blue_text']};
  --shadow-sm: 0 1px 2px rgba(17, 24, 39, 0.04);
  --shadow-md: 0 4px 12px rgba(17, 24, 39, 0.06);
  --radius: 10px;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Helvetica, Arial, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  font-feature-settings: "ss01", "cv11";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

body {{ padding: 2rem 1.5rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}

.skip-link {{
  position: absolute;
  left: 1rem;
  top: -3rem;
  background: var(--accent);
  color: #fff;
  padding: 0.6rem 0.9rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  z-index: 1000;
}}
.skip-link:focus {{
  top: 1rem;
}}

a:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
summary:focus-visible {{
  outline: 3px solid var(--blue);
  outline-offset: 2px;
}}

h1 {{
  color: var(--accent);
  margin: 0 0 0.4rem 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}}
h2 {{
  color: var(--accent);
  margin: 2rem 0 0.75rem 0;
  font-size: 1.15rem;
  font-weight: 600;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid var(--border);
}}
h3 {{ font-size: 1rem; font-weight: 600; margin: 0.75rem 0 0.4rem 0; }}
p {{ margin: 0.5rem 0; }}
.muted {{ color: var(--muted); }}
.subtitle {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }}
.sr-only {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}

/* ── Breadcrumb ── */
.breadcrumb {{
  margin-bottom: 1.25rem;
  font-size: 0.85rem;
}}
.breadcrumb a {{
  color: var(--accent); text-decoration: none;
  border-bottom: 1px dotted transparent;
  transition: border-color 0.15s;
}}
.breadcrumb a:hover {{ border-bottom-color: var(--accent); }}

/* ── Cards ── */
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-sm);
}}
.card h2 {{ margin-top: 0; border-bottom: none; padding-bottom: 0; }}

/* ── KPI grid ── */
.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}}
.kpi-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-sm);
}}
.kpi-value {{
  font-size: 1.6rem; font-weight: 700; line-height: 1.1;
  font-variant-numeric: tabular-nums; color: var(--text);
}}
.kpi-label {{
  font-size: 0.75rem; color: var(--muted); margin-top: 0.35rem;
  text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600;
}}

/* ── Tables ── */
table {{ width: 100%; border-collapse: collapse; }}
th, td {{
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.88rem;
}}
th {{
  text-align: left; color: var(--muted); font-weight: 600;
  background: #F3F4F6;
  text-transform: uppercase; font-size: 0.72rem;
  letter-spacing: 0.05em; white-space: nowrap;
}}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
tbody tr:hover {{ background: var(--accent-soft); }}
tbody tr:last-child td {{ border-bottom: none; }}

/* ── Badges ── */
.badge {{
  display: inline-block; padding: 2px 10px; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600;
  letter-spacing: 0.02em;
}}
.badge-green  {{ background: var(--green-soft);  color: var(--green-text); }}
.badge-amber  {{ background: var(--amber-soft);  color: var(--amber-text); }}
.badge-red    {{ background: var(--red-soft);    color: var(--red-text); }}
.badge-blue   {{ background: var(--blue-soft);   color: var(--blue-text); }}
.badge-muted  {{ background: #E5E7EB; color: #374151; }}

/* ── Semantic text colors (used by text_to_html glyph wrapping) ── */
.ok    {{ color: var(--green-text); font-weight: 600; }}
.warn  {{ color: var(--amber-text); font-weight: 600; }}
.err   {{ color: var(--red-text);   font-weight: 600; }}
.up    {{ color: var(--green); }}
.down  {{ color: var(--red);   }}
.flat  {{ color: var(--muted); }}
.info  {{ color: var(--blue);  }}

/* ── Pre blocks (for text wrapper) ── */
pre {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.25rem 1.5rem;
  overflow-x: auto; font-size: 0.88rem;
  font-family: "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  line-height: 1.55; color: var(--text); white-space: pre;
  box-shadow: var(--shadow-sm);
}}
pre a {{
  color: var(--accent); text-decoration: none;
  border-bottom: 1px dotted var(--accent);
}}
pre a:hover {{ border-bottom-style: solid; }}

/* ── Footer ── */
footer {{
  color: var(--muted); font-size: 0.78rem; margin-top: 3rem;
  text-align: center; border-top: 1px solid var(--border);
  padding-top: 1.5rem;
}}

/* Prompt 56: mobile-responsive breakpoints */
@media (max-width: 768px) {{
  body {{ padding: 1rem 0.75rem; font-size: 14px; }}
  .container {{ max-width: 100%; }}
  h1 {{ font-size: 1.4rem; }}
  .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
  .kpi-value {{ font-size: 1.3rem; }}
  table {{ display: block; overflow-x: auto; }}
  th, td {{ padding: 0.4rem 0.5rem; white-space: nowrap; }}
  .badge {{ font-size: 0.7rem; }}
}}
@media (min-width: 769px) and (max-width: 1024px) {{
  .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* Dark mode — respects OS preference */
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0F172A;
    --card: #1E293B;
    --border: #334155;
    --text: #F1F5F9;
    --muted: #94A3B8;
    --accent: #60A5FA;
    --accent-soft: #1E3A5F;
    --accent-hover: #93C5FD;
    --green: #34D399;
    --green-soft: #064E3B;
    --green-text: #6EE7B7;
    --amber: #FBBF24;
    --amber-soft: #78350F;
    --amber-text: #FCD34D;
    --red: #F87171;
    --red-soft: #7F1D1D;
    --red-text: #FCA5A5;
    --blue: #60A5FA;
    --blue-soft: #1E3A5F;
    --blue-text: #93C5FD;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
  }}
  th {{ background: #1E293B; }}
  .badge-muted {{ background: #334155; color: #CBD5E1; }}
  img, svg {{ opacity: 0.9; }}
}}

/* ── Toast notifications ────────────────────────────── */
.rcm-toast-container {{
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}}
.rcm-toast {{
  pointer-events: auto;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  animation: rcm-toast-in 0.3s ease, rcm-toast-out 0.3s ease 2.7s forwards;
  max-width: 360px;
}}
.rcm-toast--success {{ background: var(--green); color: white; }}
.rcm-toast--error {{ background: var(--red); color: white; }}
.rcm-toast--info {{ background: var(--accent); color: white; }}
@keyframes rcm-toast-in {{ from {{ opacity:0; transform: translateX(40px); }} to {{ opacity:1; transform: translateX(0); }} }}
@keyframes rcm-toast-out {{ from {{ opacity:1; }} to {{ opacity:0; transform: translateY(-10px); }} }}
"""


# ── Document shell ────────────────────────────────────────────────────────

def shell(
    body: str,
    title: str,
    *,
    back_href: Optional[str] = None,
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    generated: bool = True,
    omit_h1: bool = False,
) -> str:
    """Wrap ``body`` in the standard UI document.

    Delegates to shell_v2 for consistent SeekingChartis branding.

    Parameters
    ----------
    body
        Raw HTML to inject inside ``<div class="container">``.
    title
        Document ``<title>`` and the first ``<h1>`` (unless ``body`` already
        supplies its own heading, in which case the caller omits the title
        within the body).
    back_href
        If provided, renders a "← Back to index" breadcrumb link.
    subtitle
        Small muted line under the h1 — e.g., row count, generation date.
    extra_css
        Additional CSS concatenated after BASE_CSS. Use for one-off
        per-page rules (e.g. funnel bars). Keep extra_css minimal — the
        goal of the shared kit is to push styling into BASE_CSS.
    extra_js
        Optional ``<script>`` content appended before ``</body>``.
    generated
        If True, append a "Generated <timestamp> · rcm-mc" footer. Set
        False for pages that have their own footer treatment.
    """
    # Delegate to shell_v2 for consistent SeekingChartis branding
    try:
        from .shell_v2 import shell_v2
        v2_body = body
        if back_href:
            v2_body = (
                f'<nav class="breadcrumb" style="margin-bottom:12px;font-size:13px;">'
                f'<a href="{html.escape(back_href)}" style="color:var(--cad-link,#5b9bd5);'
                f'text-decoration:none;">\u2190 Back to index</a></nav>{body}'
            )
        return shell_v2(
            v2_body, title,
            subtitle=subtitle,
            extra_css=extra_css,
            extra_js=extra_js,
        )
    except Exception:
        pass  # Fall back to original shell if shell_v2 fails

    breadcrumb = ""
    if back_href:
        breadcrumb = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb">'
            f'<a href="{html.escape(back_href)}">← Back to index</a>'
            f'</nav>'
        )

    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="subtitle">{html.escape(subtitle)}</div>'

    footer_html = ""
    if generated:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        from rcm_mc import __version__ as _ver
        footer_html = f'<footer>Generated {ts} · rcm-mc v{_ver}</footer>'

    # B128: global CSRF patcher. Reads the rcm_csrf cookie set on login
    # and adds a hidden csrf_token input to every form on submit. Also
    # sets X-CSRF-Token on fetch() calls via a wrapper. Harmless if the
    # cookie is absent (open mode / HTTP-Basic clients).
    csrf_js = (
        "(function(){"
        "function c(n){var m=document.cookie.match("
        "new RegExp('(?:^|; )'+n+'=([^;]*)'));"
        "return m?decodeURIComponent(m[1]):null;}"
        "document.addEventListener('submit',function(e){"
        "var t=c('rcm_csrf');if(!t)return;"
        "var f=e.target;if(!f||f.tagName!=='FORM')return;"
        "if(f.method&&f.method.toLowerCase()!=='post')return;"
        "var x=f.querySelector('input[name=csrf_token]');"
        "if(!x){x=document.createElement('input');x.type='hidden';"
        "x.name='csrf_token';f.appendChild(x);}x.value=t;},true);"
        "var of=window.fetch;if(of){window.fetch=function(u,o){"
        "o=o||{};var t=c('rcm_csrf');"
        "if(t&&o.method&&o.method.toUpperCase()!=='GET'){"
        "o.headers=o.headers||{};"
        "if(!o.headers['X-CSRF-Token'])o.headers['X-CSRF-Token']=t;}"
        "return of(u,o);};}"
        "})();"
    )
    badge_js = (
        "(function(){"
        "fetch('/api/alerts/active-count').then(function(r){return r.json();})"
        ".then(function(d){var b=document.getElementById('rcm-nav-alert-badge');"
        "if(b&&d.count>0){b.textContent=d.count;b.style.display='inline';}}"
        ").catch(function(){});"
        "})();"
    )
    toast_js = (
        "window.rcmToast=function(msg,type){"
        "type=type||'info';"
        "var c=document.getElementById('rcm-toast-container');"
        "if(!c){c=document.createElement('div');c.id='rcm-toast-container';"
        "c.className='rcm-toast-container';document.body.appendChild(c);}"
        "var t=document.createElement('div');"
        "t.className='rcm-toast rcm-toast--'+type;"
        "t.textContent=msg;c.appendChild(t);"
        "setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},3200);"
        "};"
    )
    extra_js_full = csrf_js + badge_js + toast_js + (extra_js or "")
    script_html = f'<script>{extra_js_full}</script>'
    h1_html = "" if omit_h1 else f'<h1>{html.escape(title)}</h1>'

    # Global nav bar — consistent across all light-theme pages.
    nav_html = (
        '<nav style="display:flex;gap:16px;padding:8px 0;margin-bottom:12px;'
        'border-bottom:1px solid var(--border);font-size:0.82rem;" '
        'aria-label="Main navigation">'
        '<a href="/" style="color:var(--accent);text-decoration:none;font-weight:600;">Dashboard</a>'
        '<a href="/new-deal" style="color:var(--accent);text-decoration:none;">+ New Deal</a>'
        '<a href="/screen" style="color:var(--accent);text-decoration:none;">Screen</a>'
        '<a href="/source" style="color:var(--accent);text-decoration:none;">Source</a>'
        '<a href="/portfolio/heatmap" style="color:var(--accent);text-decoration:none;">Heatmap</a>'
        '<a href="/portfolio/map" style="color:var(--accent);text-decoration:none;">Map</a>'
        '<a href="/alerts" style="color:var(--accent);text-decoration:none;">'
        'Alerts <span id="rcm-nav-alert-badge" style="display:none;background:#ef4444;'
        'color:white;padding:1px 6px;border-radius:10px;font-size:0.7rem;'
        'font-weight:700;vertical-align:middle;"></span></a>'
        '<a href="/runs" style="color:var(--accent);text-decoration:none;">Runs</a>'
        '<a href="/scenarios" style="color:var(--accent);text-decoration:none;">Scenarios</a>'
        '<a href="/settings" style="color:var(--accent);text-decoration:none;">Settings</a>'
        '<a href="/api/docs" style="color:var(--accent);text-decoration:none;">API</a>'
        '</nav>'
    )
    return (
        '<!DOCTYPE html>\n'
        f'<html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{html.escape(title)}</title>'
        f'<link rel="manifest" href="/manifest.json">'
        f'<meta name="theme-color" content="#1F4E78">'
        f'<style>{BASE_CSS}{extra_css}</style>'
        f'</head><body>'
        f'<a class="skip-link" href="#main-content">Skip to content</a>'
        f'<div class="container">'
        f'{nav_html}'
        f'{breadcrumb}'
        f'<main id="main-content" tabindex="-1">'
        f'{h1_html}'
        f'{subtitle_html}'
        f'{body}'
        f'</main>'
        f'{footer_html}'
        f'</div>'
        f'{script_html}'
        f'</body></html>\n'
    )

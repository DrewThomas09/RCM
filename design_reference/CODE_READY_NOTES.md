# SeekingChartis — Chartis Kit Rework (code-ready snippets)

This is a drop-in refresh for `rcm_mc/ui/_chartis_kit.py` that shifts the
platform from the dark Bloomberg/Palantir aesthetic to the editorial
navy + teal + serif language shown in the mockup (see `SeekingChartis
Rework.html`).

**What changes**
- Palette (`P` dict): dark navy/ink/parchment with teal accent replaces the
  pure-black terminal palette.
- Type: Source Serif 4 for display, Inter Tight for UI, JetBrains Mono
  preserved for numeric cells.
- Shell: editorial top bar (wordmark + serif nav) replaces the fixed 36px
  dark bar. Sidebar drops in favor of horizontal nav with accent underline.
- Data panels: parchment page bg, white panels with navy header strip and
  `[CODE]` tag — density preserved; chrome refined.

**What stays the same**
- `_CORPUS_NAV` routes and legacy list: untouched.
- Public API of `chartis_shell`, `ck_table`, `ck_fmt_*`, `ck_signal_badge`,
  `ck_kpi_block`, `ck_section_header`: unchanged signatures so existing
  callers (278 pages) keep working.
- `ck_panel` CSS class names preserved where used by page templates.

---

## 1. Palette drop-in (`_chartis_kit.py`, replace the `P` dict)

```python
P = {
    # Surfaces
    "bg":          "#f5f1ea",   # parchment page bg
    "panel":       "#ffffff",   # white data panels
    "panel_alt":   "#eCe6db",   # bone tint
    "navy":        "#0b2341",   # primary dark
    "ink":         "#061626",   # deepest
    "border":      "#d6cfc3",   # hairline rule on parchment
    "border_dim":  "#eCe6db",
    "navy_3":      "#1d3c69",   # divider on navy

    # Text on light
    "text":        "#1a2332",
    "text_dim":    "#465366",
    "text_faint":  "#7a8699",

    # Text on navy
    "on_navy":     "#e9eef5",
    "on_navy_dim": "#a5b4ca",

    # Accent
    "accent":      "#0f5e5a",   # dark teal — links on parchment
    "accent_bright": "#2fb3ad", # teal for badges, charts

    # Status (desaturated, print-friendly)
    "positive":    "#0a8a5f",
    "negative":    "#b5321e",
    "warning":     "#b8732a",
    "critical":    "#8a1e0e",
    "row_stripe":  "#faf7f0",
}

_SERIF = "'Source Serif 4', 'Iowan Old Style', Georgia, serif"
_SANS  = "'Inter Tight', -apple-system, 'Segoe UI', sans-serif"
_MONO  = "'JetBrains Mono', 'SF Mono', Consolas, monospace"
```

## 2. Shell (`chartis_shell`) — replace the body generator

Key structural changes: add a top `<link>` for Google Fonts, render a
`<header class="ck-bar">` with wordmark + horizontal nav + CTA. Drop the
`.ck-sidebar`; flatten its groups into the nav's overflow menu.

```python
def chartis_shell(
    body: str,
    *, title: str,
    active_nav: str = "",
    subtitle: str = "",
    extra_css: str = "",
    extra_js: str = "",
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    nav_html = _render_top_nav(active_nav)
    crumbs = _render_breadcrumbs(active_nav, title)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<title>{_html.escape(title)} · SeekingChartis</title>
<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
<link href=\"https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap\" rel=\"stylesheet\">
<style>{_BASE_CSS}{extra_css}</style>
</head>
<body>
  <div class=\"ck-accent-bar\"></div>
  {nav_html}
  {crumbs}
  <main class=\"ck-main\">
    <header class=\"ck-page-head\">
      <div class=\"ck-eyebrow\">{_html.escape(subtitle)}</div>
      <h1 class=\"ck-title\">{_html.escape(title)}</h1>
      <div class=\"ck-page-meta\">{now}</div>
    </header>
    {body}
  </main>
  <footer class=\"ck-footer\">© 2026 SeekingChartis · v{_VERSION}</footer>
  <script>{extra_js}</script>
</body>
</html>
"""
```

## 3. CSS replacement (`_BASE_CSS`) — essentials

```css
:root {
  --ck-bg: #f5f1ea; --ck-panel: #fff; --ck-navy: #0b2341;
  --ck-ink: #061626; --ck-teal: #2fb3ad; --ck-teal-ink: #0f5e5a;
  --ck-text: #1a2332; --ck-text-dim: #465366; --ck-text-faint: #7a8699;
  --ck-rule: #d6cfc3; --ck-bone: #eCe6db;
  --ck-serif: 'Source Serif 4', Georgia, serif;
  --ck-sans:  'Inter Tight', -apple-system, sans-serif;
  --ck-mono:  'JetBrains Mono', Consolas, monospace;
}
*,*::before,*::after { box-sizing: border-box; margin:0; padding:0; }
body {
  background: var(--ck-bg); color: var(--ck-text);
  font-family: var(--ck-sans); font-size: 14px; line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--ck-teal-ink); text-decoration: none; }
a:hover { color: var(--ck-navy); }

.ck-accent-bar {
  height: 3px;
  background: linear-gradient(90deg, #2fb3ad 0%, #3a6fb0 40%, #5c3e8c 80%, #2fb3ad 100%);
}
.ck-bar {
  background: #fff; border-bottom: 1px solid var(--ck-rule);
  padding: 16px 32px; display: flex; align-items: center; gap: 32px;
}
.ck-logo {
  font-family: var(--ck-serif); font-size: 22px; font-weight: 600;
  letter-spacing: -0.01em; color: var(--ck-navy);
}
.ck-logo em { font-style: italic; font-weight: 500; }
.ck-nav { display: flex; gap: 4px; }
.ck-nav a {
  padding: 10px 14px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ck-text-dim);
  border-bottom: 2px solid transparent;
}
.ck-nav a.active { color: var(--ck-navy); border-bottom-color: var(--ck-teal); }

.ck-page-head {
  max-width: 1440px; margin: 32px auto 16px; padding: 0 32px;
}
.ck-eyebrow {
  font-size: 11px; font-weight: 600; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--ck-text-dim);
  padding-left: 36px; position: relative; margin-bottom: 14px;
}
.ck-eyebrow::before {
  content: ''; position: absolute; left: 0; top: 50%;
  width: 24px; height: 2px; background: var(--ck-teal);
  transform: translateY(-50%);
}
.ck-title {
  font-family: var(--ck-serif); font-weight: 400;
  font-size: 42px; line-height: 1.1;
  color: var(--ck-navy); letter-spacing: -0.01em;
}
.ck-page-meta {
  font-family: var(--ck-mono); font-size: 11px; letter-spacing: 0.08em;
  color: var(--ck-text-faint); margin-top: 8px;
}

.ck-main {
  max-width: 1440px; margin: 0 auto 48px; padding: 0 32px;
}

/* Data panels (preserve existing class names!) */
.ck-panel {
  background: var(--ck-panel); border: 1px solid var(--ck-rule);
  margin-bottom: 16px;
}
.ck-panel-title {
  background: var(--ck-navy); color: #e9eef5;
  padding: 10px 14px;
  font-family: var(--ck-mono); font-size: 10px;
  letter-spacing: 0.14em; text-transform: uppercase;
  display: flex; align-items: center; gap: 10px;
}
.ck-panel > div:nth-child(2) { padding: 14px 16px; }

/* KPI blocks */
.ck-kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 0; background: #fff; border: 1px solid var(--ck-rule);
  margin-bottom: 24px;
}
.ck-kpi {
  padding: 18px 20px; border-right: 1px solid var(--ck-rule);
  border-top: 3px solid var(--ck-teal);
}
.ck-kpi:last-child { border-right: 0; }
.ck-kpi-label {
  font-family: var(--ck-mono); font-size: 9px;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--ck-text-faint); margin-bottom: 10px;
}
.ck-kpi-value {
  font-family: var(--ck-serif); font-size: 30px; font-weight: 500;
  color: var(--ck-navy); letter-spacing: -0.01em; line-height: 1;
}
.ck-kpi-unit {
  font-size: 11px; color: var(--ck-text-dim); margin-top: 8px;
}
```

## 4. `ck_kpi_block` — update HTML class wrappers

```python
def ck_kpi_block(label: str, value: str, unit: str = "", delta: str = "") -> str:
    return (
        f'<div class="ck-kpi">'
        f'  <div class="ck-kpi-label">{_html.escape(label)}</div>'
        f'  <div class="ck-kpi-value">{_html.escape(str(value))}</div>'
        f'  <div class="ck-kpi-unit">{_html.escape(unit)}</div>'
        f'</div>'
    )
```

## 5. Wordmark helper (new)

```python
def ck_wordmark(inverted: bool = False) -> str:
    col = "var(--ck-text)" if not inverted else "#e9eef5"
    return (
        '<div class="ck-logo" style="color:' + col + ';">'
        '<svg width="28" height="28" viewBox="0 0 48 48" '
        'style="vertical-align:-6px;margin-right:10px;">'
        f'<circle cx="24" cy="24" r="22" fill="none" stroke="{col}" stroke-width="1.5"/>'
        f'<path d="M24 6 L19 15 L24 12 L29 15 Z" fill="{col}"/>'
        f'<path d="M42 24 L33 19 L36 24 L33 29 Z" fill="{col}"/>'
        f'<path d="M24 42 L29 33 L24 36 L19 33 Z" fill="{col}"/>'
        f'<path d="M6 24 L15 29 L12 24 L15 19 Z" fill="{col}"/>'
        '<circle cx="24" cy="24" r="3" fill="#2fb3ad"/>'
        '</svg>Seeking<em>Chartis</em></div>'
    )
```

## 6. Migration plan

1. Keep the legacy dark `_chartis_kit.py` renamed to `_chartis_kit_dark.py`
   so the `analysis_workbench` pages that are densely styled can opt in
   during transition.
2. Introduce `_chartis_kit.py` with the new palette + shell.
3. Update `rcm_mc/ui/chartis/home_page.py` first (the 7-panel landing) —
   it's the reference implementation that shows panels + KPIs + breadcrumbs.
4. Migrate `analysis_workbench.py` next; it's the density stress-test.
5. For any page whose panels render natively (color literals baked in),
   swap calls like `P["accent"]` → `P["accent_bright"]` and verify.

## 7. Marketing landing page

The public-facing `/` marketing surface doesn't exist yet in the codebase
(only `/home` serves the signed-in landing). Add `rcm_mc/ui/chartis/marketing_page.py`
implementing the full hero → capabilities → modules → stats → insights →
cases → team → CTA composition from `components/MarketingPage.jsx`. Mount
at `GET /` with redirect-to-`/home` if auth'd.

---

See `SeekingChartis Rework.html` (open in the preview pane) for the visual
truth. Tabs A/B/C toggle between marketing, signed-in home, and deal
workbench. Press `T` or toggle the Tweaks toolbar button to try accent
colors, hero imagery, and container density.

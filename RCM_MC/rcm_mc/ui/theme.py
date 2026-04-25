"""Theme toggle — dark / light mode with user preference.

The platform is dark-by-default (CLAUDE.md: 'Dark mode is the
default — pages should render cleanly on dark backgrounds'). The
directive asks for an explicit *option* — partners working long
hours sometimes prefer light, and either way the choice should
persist across sessions.

This module ships:

  • A **theme stylesheet** with CSS custom properties (variables)
    for both ``:root`` defaults (dark) and ``[data-theme="light"]``
    overrides. Drop into <head> on every page.
  • A **theme toggle button** the user clicks to switch. Vanilla
    JS reads/writes ``localStorage["rcm_theme"]`` and sets
    ``document.documentElement.dataset.theme``.
  • An **initial-theme inline script** that runs *before* the
    body renders so users don't see a dark→light flash on first
    paint. Detects:
      1. localStorage preference (explicit user choice).
      2. ``prefers-color-scheme: dark`` media query (OS pref).
      3. Default = dark.

Other components can opt in incrementally — every variable falls
back to the existing hard-coded hex codes when not overridden.

Public API::

    from rcm_mc.ui.theme import (
        theme_init_script,
        theme_stylesheet,
        theme_toggle,
        THEME_VARS,
    )

    head_html = theme_init_script() + theme_stylesheet()
    body_html = theme_toggle() + ...
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# Token → (dark_value, light_value). Used by theme_stylesheet to
# emit the cascade and exposed via THEME_VARS for callers needing
# the values directly (e.g., SVG renderers that can't use CSS vars).
_THEME_TOKENS: Dict[str, tuple] = {
    # Backgrounds
    "bg-primary":   ("#0f172a", "#f8fafc"),
    "bg-surface":   ("#1f2937", "#ffffff"),
    "bg-elevated":  ("#111827", "#f1f5f9"),
    # Text
    "text":         ("#f3f4f6", "#0f172a"),
    "text-dim":     ("#9ca3af", "#64748b"),
    "text-muted":   ("#6b7280", "#94a3b8"),
    # Borders
    "border":       ("#374151", "#e2e8f0"),
    "border-strong": ("#4b5563", "#cbd5e1"),
    # Accent (kept the same so semantic colors stay consistent)
    "accent":       ("#60a5fa", "#1e40af"),
    "accent-bg":    ("#1e3a8a", "#dbeafe"),
    "accent-fg":    ("#bfdbfe", "#1e3a8a"),
    # Semantic colors stay constant across themes — green for
    # positive, red for negative is universal.
    "positive":     ("#10b981", "#059669"),
    "negative":     ("#ef4444", "#dc2626"),
    "watch":        ("#f59e0b", "#d97706"),
}


# THEME_VARS exposes a dict mapping token names → CSS var
# expressions for callers that build inline styles.
THEME_VARS: Dict[str, str] = {
    name: f"var(--theme-{name})"
    for name in _THEME_TOKENS
}


# ── Initial-theme script (no flash on first paint) ──────────

# This must run synchronously *before* the <body> renders, so we
# emit it as a top-of-<head> inline script. setting
# documentElement.dataset.theme triggers the right CSS variables
# before the first render.
_INIT_SCRIPT = """
<script>
(function() {
  try {
    var saved = localStorage.getItem("rcm_theme");
    var theme = saved;
    if (!theme) {
      theme = (window.matchMedia &&
        window.matchMedia(
          "(prefers-color-scheme: light)").matches)
        ? "light" : "dark";
    }
    document.documentElement.dataset.theme = theme;
  } catch (e) {
    document.documentElement.dataset.theme = "dark";
  }
})();
</script>
"""


def theme_init_script() -> str:
    """Render the initial-theme inline script.

    Drop at the *top* of <head> so it runs before any body
    paint. Otherwise users with light-mode preference see a
    dark flash on first load.
    """
    return _INIT_SCRIPT


# ── Theme stylesheet ────────────────────────────────────────

def theme_stylesheet() -> str:
    """Render the CSS-variables stylesheet.

    Emits two cascades:
      :root (default + dark)
      [data-theme="light"] (light overrides)

    Components that opt in by referencing var(--theme-*) get
    automatic light/dark switching; components that hard-code
    hex values continue to render the dark theme regardless.
    """
    dark_decls = "\n  ".join([
        f"--theme-{name}: {dark};"
        for name, (dark, _light) in _THEME_TOKENS.items()
    ])
    light_decls = "\n  ".join([
        f"--theme-{name}: {light};"
        for name, (_dark, light) in _THEME_TOKENS.items()
    ])
    return (
        f'<style>\n'
        f':root, [data-theme="dark"] {{\n  {dark_decls}\n}}\n'
        f'[data-theme="light"] {{\n  {light_decls}\n}}\n'
        # Defaults that follow the theme automatically
        f'html {{ background: var(--theme-bg-primary); }}\n'
        f'body {{ color: var(--theme-text);\n'
        f'  background: var(--theme-bg-primary); }}\n'
        f'</style>'
    )


# ── Toggle button ───────────────────────────────────────────

# Inline JS reads the current theme, flips it, persists. Tied
# to a button by id so multiple toggles don't conflict.
_TOGGLE_JS = """
<script>
(function() {
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;
  function update() {
    var theme = document.documentElement.dataset.theme
      || "dark";
    btn.textContent = theme === "dark" ? "☀ Light" : "☾ Dark";
    btn.setAttribute("aria-pressed",
      theme === "light" ? "true" : "false");
  }
  btn.addEventListener("click", function() {
    var current = document.documentElement.dataset.theme
      || "dark";
    var next = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("rcm_theme", next);
    } catch (e) {}
    update();
  });
  update();
})();
</script>
"""


def theme_toggle(*, inject_css: bool = True) -> str:
    """Render the theme-toggle button + JS handler.

    Drop into the page header (next to other navigation
    controls). Renders 'Light' or 'Dark' depending on current
    theme.
    """
    css = (
        '<style>'
        '#theme-toggle{background:transparent;'
        'border:1px solid var(--theme-border, #374151);'
        'border-radius:6px;padding:6px 12px;'
        'color:var(--theme-text-dim, #9ca3af);'
        'font-size:12px;cursor:pointer;'
        'font-family:system-ui;transition:'
        'background 0.15s, color 0.15s;}'
        '#theme-toggle:hover{'
        'background:var(--theme-bg-elevated, #111827);'
        'color:var(--theme-text, #f3f4f6);}'
        '</style>'
    ) if inject_css else ""
    return (
        css
        + '<button id="theme-toggle" type="button" '
        'aria-label="Toggle dark / light theme" '
        'aria-pressed="false">☀ Light</button>'
        + _TOGGLE_JS
    )

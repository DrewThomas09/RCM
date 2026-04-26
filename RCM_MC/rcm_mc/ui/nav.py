"""Breadcrumb navigation + keyboard shortcuts.

Two cross-cutting UX features:

  1. **Breadcrumbs** — every page should show the path back to
     the dashboard. Partners click a deal, drill into a service
     line, drill into a metric — they need a one-click path back
     without browser-back relics.
  2. **Keyboard shortcuts** — Bloomberg-style g-prefix navigation
     (g d → dashboard, g m → models). Power users get them; the
     ``?`` key opens a help dialog showing every binding.

Both features are pure HTML+CSS+vanilla-JS, no dependencies. Drop
into any page that serves dark-theme HTML.

Public API::

    from rcm_mc.ui.nav import (
        breadcrumb,
        keyboard_shortcuts,
        SHORTCUTS,
    )

    html = (
        breadcrumb([
            ("Dashboard", "/?v3=1"),
            ("Deals", "/?v3=1#deals"),
            ("Aurora", None),     # current page, no link
        ])
        + page_body
        + keyboard_shortcuts())
"""
from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ── Default shortcut registry ────────────────────────────────
# 'g' is the leader key — partners type 'g' followed by a single
# letter to navigate. ESC always cancels a pending leader.

SHORTCUTS: List[Tuple[str, str, str]] = [
    # (binding, label, target_url)
    ("g d", "Dashboard (morning view)", "/?v3=1"),
    ("g c", "Data catalog", "/data/catalog"),
    ("g r", "Data refresh", "/data/refresh"),
    ("g m", "Model quality", "/models/quality"),
    ("g i", "Feature importance", "/models/importance"),
    ("g e", "Exports", "/exports"),
    ("g h", "Home (legacy dashboard)", "/"),
    ("?", "Show this help", "#help"),
    ("/", "Focus search (when present)", ""),
    ("Esc", "Cancel pending shortcut / close help", ""),
]


# ── Breadcrumb ───────────────────────────────────────────────

def breadcrumb(
    items: List[Tuple[str, Optional[str]]],
    *,
    inject_css: bool = True,
) -> str:
    """Render a breadcrumb trail.

    Args:
      items: list of (label, href) tuples. The final item should
        have href=None to indicate the current page (rendered
        non-clickable). Each preceding item is a clickable parent.
      inject_css: include the small stylesheet. Set False on
        pages that already render multiple breadcrumbs (rare).

    Returns: HTML snippet. Renders as a single line with chevron
    separators.
    """
    if not items:
        return ""
    css = (
        '<style>'
        '.bc{display:flex;align-items:center;gap:6px;'
        'flex-wrap:wrap;font-size:12px;color:var(--faint);'
        'margin-bottom:18px;}'
        '.bc a{color:var(--teal);text-decoration:none;'
        'transition:color 0.1s;}'
        '.bc a:hover{color:var(--blue-soft);}'
        '.bc .bc-current{color:var(--ink);font-weight:500;}'
        '.bc .bc-sep{color:var(--muted);font-size:11px;}'
        '</style>') if inject_css else ""

    parts: List[str] = []
    for i, (label, href) in enumerate(items):
        if i > 0:
            parts.append('<span class="bc-sep">›</span>')
        if href and i < len(items) - 1:
            parts.append(
                f'<a href="{_html.escape(href)}">'
                f'{_html.escape(label)}</a>')
        else:
            parts.append(
                f'<span class="bc-current">'
                f'{_html.escape(label)}</span>')
    return css + '<nav class="bc">' + "".join(parts) + '</nav>'


# ── Keyboard shortcuts ───────────────────────────────────────

# Inline JS — listens for shortcut sequences globally. Pure
# vanilla; survives in any page that hasn't claimed g/? as
# input keys.
_SHORTCUTS_JS = """
(function() {
  var shortcuts = %SHORTCUTS_JSON%;
  var pending = null;
  var pendingTimer = null;
  var helpOpen = false;

  function isTyping(e) {
    var t = e.target;
    if (!t) return false;
    var tag = (t.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" ||
        tag === "select") return true;
    if (t.isContentEditable) return true;
    return false;
  }

  function clearPending() {
    pending = null;
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
    var ind = document.getElementById("kbd-leader-ind");
    if (ind) ind.style.display = "none";
  }

  function showLeaderIndicator() {
    var ind = document.getElementById("kbd-leader-ind");
    if (!ind) return;
    ind.style.display = "block";
    ind.textContent = "g…";
  }

  function showHelp() {
    var help = document.getElementById("kbd-help");
    if (!help) return;
    help.style.display = "flex";
    helpOpen = true;
  }

  function hideHelp() {
    var help = document.getElementById("kbd-help");
    if (!help) return;
    help.style.display = "none";
    helpOpen = false;
  }

  function focusSearch() {
    // Find the first visible search input on the page
    var inputs = document.querySelectorAll(
      'input[type="search"]');
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].offsetParent !== null) {
        inputs[i].focus();
        inputs[i].select();
        return true;
      }
    }
    return false;
  }

  document.addEventListener("keydown", function(e) {
    if (helpOpen && e.key === "Escape") {
      e.preventDefault();
      hideHelp();
      return;
    }
    if (isTyping(e)) {
      // Allow Esc to blur from inputs
      if (e.key === "Escape") {
        try { e.target.blur(); } catch (_) {}
      }
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Escape") {
      clearPending();
      hideHelp();
      return;
    }
    if (e.key === "?") {
      e.preventDefault();
      showHelp();
      return;
    }
    if (e.key === "/") {
      if (focusSearch()) {
        e.preventDefault();
      }
      return;
    }
    if (pending === "g") {
      e.preventDefault();
      var match = shortcuts.find(function(s) {
        return s.binding === "g " + e.key;
      });
      clearPending();
      if (match && match.target) {
        window.location.href = match.target;
      }
      return;
    }
    if (e.key === "g") {
      pending = "g";
      showLeaderIndicator();
      pendingTimer = setTimeout(clearPending, 1500);
    }
  });
})();
"""


def keyboard_shortcuts(
    *,
    extra: Optional[List[Tuple[str, str, str]]] = None,
    inject_css: bool = True,
) -> str:
    """Render the keyboard-shortcut help overlay + JS handler.

    Args:
      extra: extra (binding, label, target_url) tuples to add to
        the page-specific shortcuts. Merged with the defaults.
      inject_css: include the stylesheet for the help dialog +
        leader indicator.

    Returns: HTML+CSS+JS snippet. Page renders the leader-key
    indicator (hidden by default) and a help dialog.
    """
    all_shortcuts = list(SHORTCUTS)
    if extra:
        all_shortcuts.extend(extra)

    rows = "".join([
        f'<tr><td style="padding:6px 14px;">'
        f'<kbd style="background:var(--border);color:var(--ink);'
        f'padding:2px 8px;border-radius:4px;font-family:'
        f'monospace;font-size:11px;border:1px solid var(--muted);">'
        f'{_html.escape(binding)}</kbd></td>'
        f'<td style="padding:6px 14px;color:var(--border);'
        f'font-size:13px;">{_html.escape(label)}</td>'
        f'</tr>' for binding, label, _ in all_shortcuts
    ])

    css = (
        '<style>'
        '#kbd-leader-ind{position:fixed;bottom:20px;'
        'left:20px;background:var(--paper-pure);border:1px solid '
        'var(--border);border-radius:6px;padding:6px 14px;'
        'color:var(--teal);font-family:monospace;font-size:12px;'
        'font-weight:600;display:none;z-index:1000;}'
        '#kbd-help{position:fixed;top:0;left:0;right:0;'
        'bottom:0;background:rgba(0,0,0,0.7);'
        'display:none;align-items:center;justify-content:'
        'center;z-index:2000;}'
        '#kbd-help-card{background:var(--bg);border:1px solid '
        'var(--border);border-radius:8px;padding:24px;'
        'max-width:540px;width:90%;'
        'box-shadow:0 12px 40px rgba(0,0,0,0.6);}'
        '#kbd-help-card h3{margin:0 0 12px 0;'
        'color:var(--ink);font-size:16px;}'
        '#kbd-help-card .kbd-hint{color:var(--faint);'
        'font-size:12px;margin-bottom:14px;}'
        '#kbd-help-card table{width:100%;'
        'border-collapse:collapse;}'
        '#kbd-help-card .kbd-close{display:block;'
        'margin-top:14px;background:var(--border);border:none;'
        'border-radius:6px;padding:8px 14px;color:var(--ink);'
        'font-size:12px;cursor:pointer;width:100%;}'
        '</style>') if inject_css else ""

    leader_ind = (
        '<div id="kbd-leader-ind" '
        'aria-live="polite">g…</div>')

    help_dialog = (
        '<div id="kbd-help" role="dialog" '
        'aria-modal="true" aria-labelledby="kbd-help-title">'
        '<div id="kbd-help-card">'
        '<h3 id="kbd-help-title">Keyboard Shortcuts</h3>'
        '<div class="kbd-hint">'
        'Press the keys in sequence. <kbd>g d</kbd> means '
        'press <kbd>g</kbd> then <kbd>d</kbd>. '
        '<kbd>Esc</kbd> closes this dialog.</div>'
        f'<table>{rows}</table>'
        '<button class="kbd-close" '
        'onclick="document.getElementById(\'kbd-help\')'
        '.style.display=\'none\';">Close (Esc)</button>'
        '</div></div>')

    js_payload = json.dumps([
        {"binding": b, "label": lbl, "target": t}
        for b, lbl, t in all_shortcuts
    ])
    js = (_SHORTCUTS_JS
          .replace("%SHORTCUTS_JSON%", js_payload))

    return (css + leader_ind + help_dialog
            + f'<script>{js}</script>')

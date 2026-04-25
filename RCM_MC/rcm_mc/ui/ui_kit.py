"""Shared UI kit — canonical button / card / input / form styles.

Audit of the recent UI sprint surfaced the same button styles
duplicated across 6+ files (power_table, power_chart,
global_search, theme, compare, etc.) — each with its own slight
inline-style tweaks that drifted apart over time. Same goes for
card surfaces, search inputs, section headers.

This module ships:

  • A single ``ui_kit_stylesheet()`` function emitting all
    canonical class definitions in one <style> block.
  • Helper functions for the common surface elements: button,
    card, input, section_header, kpi_card.
  • Class names namespaced under ``.ui-`` so they coexist with
    legacy inline styles during incremental migration.

Class registry:

  .ui-btn              — base button (secondary / outline)
  .ui-btn-primary      — accent fill
  .ui-btn-ghost        — transparent, hover surfaces
  .ui-card             — surface card with border + radius
  .ui-card-elevated    — darker bg for nested cards
  .ui-input            — text / search input
  .ui-section-h        — small uppercase heading above tables
  .ui-kpi              — KPI label/value pair

Public API::

    from rcm_mc.ui.ui_kit import (
        ui_kit_stylesheet,
        button, card, input_field, section_header,
        kpi_card,
    )
"""
from __future__ import annotations

import html as _html
from typing import Any, Optional


_KIT_CSS = """
<style>
/* ── Button ─────────────────────────────────── */
.ui-btn{display:inline-block;background:#1f2937;
  border:1px solid #374151;border-radius:6px;
  padding:6px 12px;color:#f3f4f6;font-size:13px;
  text-decoration:none;cursor:pointer;
  font-family:system-ui,-apple-system,sans-serif;
  line-height:1.4;transition:background 0.15s,
  border-color 0.15s;}
.ui-btn:hover{background:#374151;
  border-color:#4b5563;}
.ui-btn-primary{background:#1e3a8a;color:#bfdbfe;
  border-color:#1e3a8a;}
.ui-btn-primary:hover{background:#1e40af;
  border-color:#1e40af;}
.ui-btn-ghost{background:transparent;
  color:#9ca3af;border-color:transparent;}
.ui-btn-ghost:hover{background:#1f2937;
  color:#f3f4f6;}

/* ── Card ─────────────────────────────────── */
.ui-card{background:#1f2937;border:1px solid #374151;
  border-radius:8px;}
.ui-card-elevated{background:#111827;
  border:1px solid #374151;border-radius:8px;}

/* ── Input ─────────────────────────────────── */
.ui-input{background:#1f2937;border:1px solid #374151;
  border-radius:6px;padding:6px 12px;color:#f3f4f6;
  font-size:13px;font-family:system-ui;
  box-sizing:border-box;}
.ui-input::placeholder{color:#6b7280;}
.ui-input:focus{outline:none;border-color:#60a5fa;}

/* ── Section header ─────────────────────────── */
.ui-section-h{font-size:11px;text-transform:uppercase;
  letter-spacing:0.06em;color:#9ca3af;margin:0 0 8px 0;
  font-weight:600;}

/* ── KPI ─────────────────────────────────── */
.ui-kpi{background:#1f2937;border:1px solid #374151;
  border-radius:8px;padding:14px 18px;flex:1;
  min-width:170px;}
.ui-kpi-label{font-size:11px;text-transform:uppercase;
  letter-spacing:0.06em;color:#9ca3af;
  margin-bottom:6px;}
.ui-kpi-value{font-size:22px;font-weight:600;
  color:#f3f4f6;
  font-variant-numeric:tabular-nums;}
.ui-kpi-sub{font-size:11px;color:#6b7280;
  margin-top:4px;}
</style>"""


def ui_kit_stylesheet() -> str:
    """Single canonical stylesheet. Idempotent — pages can
    include it multiple times safely (class-based selectors)."""
    return _KIT_CSS


# ── Helper functions ────────────────────────────────────────

def button(
    label: str,
    *,
    href: Optional[str] = None,
    kind: str = "secondary",
    type_: str = "button",
    button_id: Optional[str] = None,
) -> str:
    """Render a canonical button.

    Args:
      label: visible text. HTML-escaped.
      href: when set, renders as <a>; otherwise <button>.
      kind: 'primary' / 'secondary' (default) / 'ghost'.
      type_: button type when not a link ('button' / 'submit').
      button_id: optional DOM id.

    Returns: HTML snippet using .ui-btn classes from
    ui_kit_stylesheet().
    """
    classes = ["ui-btn"]
    if kind == "primary":
        classes.append("ui-btn-primary")
    elif kind == "ghost":
        classes.append("ui-btn-ghost")
    elif kind != "secondary":
        raise ValueError(f"Unknown button kind: {kind}")

    cls_attr = " ".join(classes)
    id_attr = (f' id="{_html.escape(button_id)}"'
               if button_id else "")
    if href:
        return (
            f'<a class="{cls_attr}" '
            f'href="{_html.escape(href)}"{id_attr}>'
            f'{_html.escape(label)}</a>')
    return (
        f'<button class="{cls_attr}" '
        f'type="{_html.escape(type_)}"{id_attr}>'
        f'{_html.escape(label)}</button>')


def card(
    inner_html: str,
    *,
    elevated: bool = False,
    padding: str = "18px",
) -> str:
    """Render a card surface.

    Args:
      inner_html: contents (caller renders).
      elevated: use the darker elevated surface for nested cards.
      padding: CSS padding value.

    Returns: <div class="ui-card[-elevated]"> wrapper.
    """
    cls = "ui-card-elevated" if elevated else "ui-card"
    return (
        f'<div class="{cls}" style="padding:{padding};">'
        f'{inner_html}</div>')


def input_field(
    *,
    name: str = "",
    placeholder: str = "",
    type_: str = "text",
    input_id: Optional[str] = None,
    value: str = "",
    aria_label: Optional[str] = None,
) -> str:
    """Render a canonical text/search input.

    Args:
      name: form name attribute.
      placeholder: placeholder text. HTML-escaped.
      type_: 'text' / 'search' / 'email' / 'password'.
      input_id: optional DOM id.
      value: initial value. HTML-escaped.
      aria_label: accessibility label when no visible label.

    Returns: <input class="ui-input"> snippet.
    """
    if type_ not in {"text", "search", "email",
                     "password", "number", "tel"}:
        raise ValueError(f"Unknown input type: {type_}")
    parts = [
        f'class="ui-input"',
        f'type="{_html.escape(type_)}"',
    ]
    if name:
        parts.append(f'name="{_html.escape(name)}"')
    if input_id:
        parts.append(f'id="{_html.escape(input_id)}"')
    if placeholder:
        parts.append(
            f'placeholder="{_html.escape(placeholder)}"')
    if value:
        parts.append(f'value="{_html.escape(value)}"')
    if aria_label:
        parts.append(
            f'aria-label="{_html.escape(aria_label)}"')
    return f'<input {" ".join(parts)}>'


def section_header(label: str) -> str:
    """Small uppercase heading above tables / lists."""
    return (
        f'<h3 class="ui-section-h">'
        f'{_html.escape(label)}</h3>')


def kpi_card(
    label: str,
    value: str,
    *,
    sub: str = "",
) -> str:
    """One KPI card. Use inside a flex container with gap to
    build a KPI strip."""
    sub_html = (
        f'<div class="ui-kpi-sub">'
        f'{_html.escape(sub)}</div>' if sub else "")
    return (
        f'<div class="ui-kpi">'
        f'<div class="ui-kpi-label">'
        f'{_html.escape(label)}</div>'
        f'<div class="ui-kpi-value">'
        f'{_html.escape(value)}</div>'
        f'{sub_html}</div>')

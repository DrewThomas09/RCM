"""Empty states — never show nothing; tell the user what to do.

Recent UI surfaces handle empty states ad hoc — 'No deals' here,
'No backtest results' there. Each is fine in isolation but the
copy + visual treatment drift apart over time. This module ships
a unified helper plus pre-built variants for the cases that
recur across the platform:

  • No data loaded yet → point to /data/refresh.
  • No analysis packets built → point to the packet builder.
  • No models trained → explain how to train.
  • No filter results → suggest broadening.
  • No search hits → suggest different terms.
  • Feature disabled → explain the env var or flag.

Visual treatments:

  • ``empty_state(...)`` — full-width card with title +
    description + optional primary action button. Used as the
    body of a page when the whole thing has no data.
  • ``empty_inline(...)`` — small inline message for sections /
    table rows / sidebars. Subtle enough not to overwhelm a
    populated page.
  • ``empty_table_row(...)`` — colspan'd table row with the
    inline empty state. For power_table-style placeholders.

Public API::

    from rcm_mc.ui.empty_states import (
        empty_state, empty_inline, empty_table_row,
        no_data_loaded, no_packets_built,
        no_filter_results, no_search_results,
    )
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmptyAction:
    """One CTA on an empty state."""
    label: str
    url: str
    primary: bool = True


# Status colors come from the semantic palette so empty-state
# CTAs match the rest of the platform.
_BG_SURFACE = "#1f2937"
_BG_ELEVATED = "#111827"
_BORDER = "#374151"
_TEXT = "#f3f4f6"
_TEXT_DIM = "#9ca3af"
_ACCENT = "#60a5fa"
_ACCENT_BG = "#1e3a8a"


def _css(*, inject: bool = True) -> str:
    if not inject:
        return ""
    return (
        '<style>'
        '.es-card{background:#1f2937;border:1px solid '
        '#374151;border-radius:8px;padding:40px 24px;'
        'text-align:center;}'
        '.es-icon{font-size:32px;line-height:1;'
        'margin-bottom:14px;color:#60a5fa;'
        'font-weight:300;}'
        '.es-title{color:#f3f4f6;font-size:15px;'
        'font-weight:600;margin:0 0 6px 0;}'
        '.es-desc{color:#9ca3af;font-size:13px;'
        'line-height:1.5;margin:0 auto 18px auto;'
        'max-width:480px;}'
        '.es-actions{display:flex;justify-content:center;'
        'gap:10px;flex-wrap:wrap;}'
        '.es-btn{display:inline-block;text-decoration:none;'
        'padding:8px 16px;border-radius:6px;font-size:13px;'
        'font-weight:500;border:1px solid #374151;}'
        '.es-btn-primary{background:#1e3a8a;color:#bfdbfe;'
        'border-color:#1e3a8a;}'
        '.es-btn-primary:hover{background:#1e40af;}'
        '.es-btn-secondary{background:transparent;'
        'color:#d1d5db;}'
        '.es-btn-secondary:hover{background:#1f2937;}'
        '.es-inline{padding:18px 20px;color:#9ca3af;'
        'font-size:13px;line-height:1.5;text-align:center;'
        'background:#111827;border:1px solid #374151;'
        'border-radius:8px;}'
        '.es-inline a{color:#60a5fa;text-decoration:none;}'
        '.es-inline a:hover{text-decoration:underline;}'
        '</style>')


# ── Core helpers ─────────────────────────────────────────────

def empty_state(
    title: str,
    description: str,
    *,
    icon: str = "○",
    actions: Optional[list] = None,
    inject_css: bool = True,
) -> str:
    """Full-width empty-state card with title + description +
    optional CTA buttons.

    Args:
      title: short heading (e.g. "No analysis packets yet").
      description: 1-2 sentence explanation + nudge.
      icon: single-glyph icon (Unicode preferred over SVG for
        portability). Defaults to ○ (a generic 'empty' indicator).
      actions: list of EmptyAction. First is rendered primary,
        rest secondary.
      inject_css: include the stylesheet.

    Returns: HTML snippet for an empty-state card.
    """
    actions = actions or []
    btns_html = "".join([
        f'<a href="{_html.escape(a.url)}" '
        f'class="es-btn '
        f'{"es-btn-primary" if a.primary else "es-btn-secondary"}">'
        f'{_html.escape(a.label)}</a>'
        for a in actions
    ])
    actions_html = (
        f'<div class="es-actions">{btns_html}</div>'
        if btns_html else "")
    return (
        _css(inject=inject_css)
        + f'<div class="es-card" role="status">'
        f'<div class="es-icon" aria-hidden="true">'
        f'{_html.escape(icon)}</div>'
        f'<h3 class="es-title">{_html.escape(title)}</h3>'
        f'<p class="es-desc">{_html.escape(description)}</p>'
        f'{actions_html}'
        f'</div>')


def empty_inline(
    message: str,
    *,
    action_label: Optional[str] = None,
    action_url: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Small inline empty state for sections / sidebars.

    Renders as a subtle box that doesn't overwhelm a populated
    page. Use for individual sections that haven't been built
    yet on a page where other sections are populated.
    """
    action_html = ""
    if action_label and action_url:
        action_html = (
            f' <a href="{_html.escape(action_url)}">'
            f'{_html.escape(action_label)} →</a>')
    return (
        _css(inject=inject_css)
        + f'<div class="es-inline" role="status">'
        f'{_html.escape(message)}{action_html}</div>')


def empty_table_row(
    *,
    n_columns: int,
    message: str = "No rows.",
    action_label: Optional[str] = None,
    action_url: Optional[str] = None,
) -> str:
    """A `<tr>` rendering a colspan'd empty-state cell.

    For tables built outside the power_table component (which
    has its own empty state). Caller is responsible for placing
    this inside an existing `<tbody>`.
    """
    action_html = ""
    if action_label and action_url:
        action_html = (
            f' <a href="{_html.escape(action_url)}" '
            f'style="color:#60a5fa;text-decoration:none;">'
            f'{_html.escape(action_label)} →</a>')
    return (
        f'<tr><td colspan="{int(n_columns)}" '
        f'style="padding:24px;color:#9ca3af;'
        f'text-align:center;font-size:13px;">'
        f'{_html.escape(message)}{action_html}</td></tr>')


# ── Pre-built variants ──────────────────────────────────────

def no_data_loaded(*, inject_css: bool = True) -> str:
    """Generic 'data hasn't been loaded yet' empty state."""
    return empty_state(
        "No data loaded yet",
        "The platform needs public-data sources to populate "
        "metrics. Run a refresh to load CMS, Census, CDC, "
        "and APCD data — or load from a CSV.",
        icon="⛁",
        actions=[
            EmptyAction("Refresh data",
                        "/data/refresh"),
            EmptyAction(
                "View catalog",
                "/data/catalog", primary=False),
        ],
        inject_css=inject_css)


def no_packets_built(
    *, deal_id: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """No analysis packets exist for this deal / portfolio."""
    description = (
        "Analysis packets bundle every per-deal calculation "
        "(profile, comps, predictions, EBITDA bridge, "
        "scenarios). Build one to populate the dashboard.")
    actions = [
        EmptyAction("View deal list", "/?v3=1"),
    ]
    if deal_id:
        description = (
            f"No analysis packet found for {deal_id}. Build "
            f"one with the CLI command shown — every "
            f"downstream view depends on it.")
        actions = [
            EmptyAction(
                "View deal list", "/?v3=1",
                primary=False),
        ]
    return empty_state(
        "No analysis packets yet",
        description,
        icon="◳",
        actions=actions,
        inject_css=inject_css)


def no_models_trained(*, inject_css: bool = True) -> str:
    """No trained predictors yet."""
    return empty_state(
        "No models trained yet",
        "Trained predictors (denial rate, days-in-AR, "
        "collection rate, forward distress, ...) need a "
        "calibration set. Once you've ingested HCRIS + "
        "Hospital Compare data, the predictors auto-fit on "
        "first use.",
        icon="◇",
        actions=[
            EmptyAction("Refresh data",
                        "/data/refresh"),
            EmptyAction(
                "Model quality docs",
                "/models/quality", primary=False),
        ],
        inject_css=inject_css)


def no_filter_results(*, inject_css: bool = True) -> str:
    """User filtered the list down to nothing."""
    return empty_state(
        "No matches for current filters",
        "Try broadening the filter criteria — narrower "
        "filters tend to produce empty results when only "
        "one or two records match.",
        icon="◌",
        inject_css=inject_css)


def no_search_results(
    query: str = "", *, inject_css: bool = True,
) -> str:
    """Search returned nothing."""
    if query:
        description = (
            f"Nothing matched '{query}'. Try fewer words, a "
            f"different spelling, or a broader term.")
    else:
        description = (
            "Try fewer words, a different spelling, or a "
            "broader term.")
    return empty_state(
        "No search results",
        description,
        icon="⌕",
        inject_css=inject_css)


def feature_disabled(
    feature: str, *, env_var: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Feature gated by env var or flag."""
    description = (
        f"This page renders the {feature} surface, which "
        f"isn't enabled on this deployment.")
    if env_var:
        description += (
            f" Set the {env_var} environment variable to "
            f"enable it.")
    return empty_state(
        f"{feature} is disabled",
        description,
        icon="◔",
        inject_css=inject_css)

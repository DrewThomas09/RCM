"""SeekingChartis — Chartis Kit dispatcher.

Phase 1 of the UI v2 editorial rework. This module is a thin
dispatcher that routes every import through one of two concrete
implementations:

- ``_chartis_kit_legacy`` — the dark Bloomberg/Palantir shell that
  has been in production. **Default.** Unchanged from before Phase 1.
- ``_chartis_kit_v2`` — the editorial navy / teal / parchment rework
  that ships under the ``CHARTIS_UI_V2`` feature flag.

Set ``CHARTIS_UI_V2=1`` in the environment to opt into v2. The
dispatcher preserves every public symbol that `rcm_mc/ui/*.py` and
the page renderers import today, so no call site changes across
Phases 1–14. Phase 15 deletes this dispatcher + the legacy module.

Public contract (unchanged across flag values):

- ``P`` palette dict — keys may differ internally, but every key
  used by a page renderer is preserved via alias.
- ``_CORPUS_NAV`` / ``_CORPUS_NAV_LEGACY`` — navigation data.
- ``chartis_shell(body, title, *, ...)`` — the page shell.
- ``ck_fmt_num``, ``ck_fmt_pct``, ``ck_fmt_moic``, ``ck_fmt_currency``,
  ``ck_fmt_irr`` — legacy-named formatters.
- ``ck_fmt_number``, ``ck_fmt_percent`` — v2-named formatters (mapped
  to legacy ones when v2 is off).
- ``ck_signal_badge``, ``ck_grade_badge``, ``ck_regime_badge``.
- ``ck_table``, ``ck_kpi_block``, ``ck_section_header``.
- ``ck_panel`` — v2 primitive; a thin div wrapper in legacy mode.
- ``ck_command_palette`` — v2 primitive; returns "" in legacy mode.

Design rule for Phases 2–14: when a page is migrated to v2, its
renderer swaps visual choices (hex literals, class names) through
``P`` and the kit's helpers — NEVER by branching on
``UI_V2_ENABLED``. The flag exists to gate the SHELL, not per-page
code paths.
"""
from __future__ import annotations

import os as _os

# ── Feature flag ────────────────────────────────────────────────────
#
# Default "0" during Phases 1–14 so existing test behaviour is
# byte-for-byte unchanged. Phase 15 flips the default to "1" and
# removes this module, promoting _chartis_kit_v2 to the only
# implementation.
UI_V2_ENABLED = _os.environ.get("CHARTIS_UI_V2", "0") != "0"

# ── TEMPORARY: editorial port in progress (commits 1–4 of Phase 1) ──
#
# The previous _chartis_kit_v2.py held the OLD reverted reskin's
# palette (#0b2341 navy / #2fb3ad teal). It was deleted in commit 1.
# Its replacement, _chartis_kit_editorial.py, lands in commit 4.
#
# Between now and commit 4, CHARTIS_UI_V2=1 is silently a no-op —
# the dispatcher falls through to the legacy dark shell regardless.
# This warning surfaces during that window so a stray bisect or env
# config doesn't quietly chase a ghost. Removed in commit 4.
if UI_V2_ENABLED:
    import sys as _sys
    print(
        "[chartis_kit] CHARTIS_UI_V2 is currently a no-op "
        "(editorial port in progress, see docs/UI_REWORK_PLAN.md). "
        "Falling through to legacy dark shell.",
        file=_sys.stderr,
    )
    UI_V2_ENABLED = False  # force legacy path until commit 4 rewires


# ── PHI posture banner ─────────────────────────────────────────────
#
# Controlled by env var ``RCM_MC_PHI_MODE``:
#   "disallowed" → green "no PHI" banner — public-data-only deployments
#   "restricted" → amber "PHI under BAA" banner — compliant hosts only
#   (unset)      → no banner (dev / unconfigured)
#
# Inlined CSS: shell templates vary across v2/legacy, and a separate
# stylesheet would need wiring through both. Inline is additive +
# self-contained + immune to shell-CSS accidentally overriding it.

def _phi_banner_html() -> str:
    mode = _os.environ.get("RCM_MC_PHI_MODE", "").strip().lower()
    if mode == "disallowed":
        return (
            '<div style="background:#064e3b;color:#d1fae5;padding:8px 16px;'
            'text-align:center;font-size:12px;font-weight:500;'
            'font-family:system-ui,-apple-system,sans-serif;'
            'border-bottom:1px solid #047857;letter-spacing:0.02em;"'
            ' data-testid="phi-banner" data-phi-mode="disallowed">'
            '🛡️ Public data only — no PHI permitted on this instance.'
            '</div>'
        )
    if mode == "restricted":
        return (
            '<div style="background:#78350f;color:#fef3c7;padding:8px 16px;'
            'text-align:center;font-size:12px;font-weight:600;'
            'font-family:system-ui,-apple-system,sans-serif;'
            'border-bottom:1px solid #92400e;letter-spacing:0.02em;"'
            ' data-testid="phi-banner" data-phi-mode="restricted">'
            '⚠️ PHI-eligible deployment — access audit-logged. '
            'Do not export outside BAA scope.'
            '</div>'
        )
    return ""


if UI_V2_ENABLED:
    # ── v2 editorial shell ──────────────────────────────────────────
    from ._chartis_kit_v2 import (  # noqa: F401
        P,
        _CORPUS_NAV,
        _LEGACY_NAV as _CORPUS_NAV_LEGACY,
        ck_command_palette,
        ck_fmt_currency,
        ck_fmt_number,
        ck_fmt_percent,
        ck_kpi_block,
        ck_panel,
        ck_section_header,
        ck_signal_badge as _v2_signal_badge,
        ck_table,
        chartis_shell as _v2_chartis_shell,
    )

    # --- Compat shims: legacy-named functions callers still use ----

    from ._chartis_kit_legacy import (  # noqa: F401
        ck_fmt_moic,
        ck_fmt_irr,
        ck_grade_badge,
        ck_regime_badge,
        _MONO,
        _SANS,
    )

    def ck_fmt_num(value, decimals: int = 1, suffix: str = "",
                   na: str = "—") -> str:
        """Legacy-named wrapper around ``ck_fmt_number``."""
        if value is None:
            return na
        try:
            return ck_fmt_number(float(value), precision=decimals) + suffix
        except (TypeError, ValueError):
            return na

    def ck_fmt_pct(value, decimals: int = 1, signed: bool = False) -> str:
        """Legacy-named wrapper around ``ck_fmt_percent``.

        ``signed`` prepends '+' to positive values — the legacy
        behaviour many pages rely on for signed variance displays.
        """
        if value is None:
            return "—"
        try:
            out = ck_fmt_percent(float(value), precision=decimals)
        except (TypeError, ValueError):
            return "—"
        if signed and float(value) > 0 and not out.startswith(("+", "-")):
            out = "+" + out
        return out

    def ck_signal_badge(signal, *, tone: str | None = None) -> str:
        """Compat wrapper: accepts either the legacy single-arg form
        (``ck_signal_badge("OK")``) or the v2 tone-keyword form
        (``ck_signal_badge("Priority", tone="positive")``).
        """
        text = "" if signal is None else str(signal)
        resolved_tone = tone
        if resolved_tone is None:
            # Legacy call: signal IS the tone label, typically one of
            # POSITIVE / NEGATIVE / WARNING / NEUTRAL.
            up = text.upper()
            if up in ("POSITIVE", "BUY", "STRONG"):
                resolved_tone = "positive"
            elif up in ("NEGATIVE", "SELL", "WEAK"):
                resolved_tone = "negative"
            elif up in ("WARNING", "CAUTION"):
                resolved_tone = "warning"
            elif up in ("CRITICAL", "BLOCKER"):
                resolved_tone = "critical"
            else:
                resolved_tone = "neutral"
        return _v2_signal_badge(text, tone=resolved_tone)

    def chartis_shell(body, title, *, active_nav=None, subtitle: str = "",
                      breadcrumbs=None, code: str | None = None,
                      extra_css: str = "", extra_js: str = "",
                      **kwargs) -> str:
        """Compat shell: accepts both the legacy kwargs
        (``subtitle``, ``extra_css``, ``extra_js``) and the v2 kwargs
        (``breadcrumbs``, ``code``, ``user_initials``, etc.). Unknown
        kwargs pass through to the v2 shell.

        ``subtitle`` is stashed into the v2 page-head eyebrow row;
        ``extra_css`` and ``extra_js`` are appended to the body. This
        keeps the dozens of existing callers working without a
        simultaneous rewrite of every page.
        """
        # Route subtitle to the v2 eyebrow by threading through the
        # body. Future cleanup (Phase 15) can drop this shim.
        if subtitle and not breadcrumbs:
            breadcrumbs = [{"label": str(subtitle)}]
        wrapped_body = _phi_banner_html() + body
        if extra_css:
            wrapped_body = f'<style>{extra_css}</style>{wrapped_body}'
        if extra_js:
            wrapped_body = f'{wrapped_body}<script>{extra_js}</script>'
        # Note: the v2 shell also has its own Cmd-K handler
        # (_chartis_kit_v2.py:487). We don't inject a duplicate
        # palette here for the same reason as the legacy branch —
        # two handlers binding to Cmd-K would both fire.
        return _v2_chartis_shell(
            wrapped_body, title,
            active_nav=active_nav, breadcrumbs=breadcrumbs, code=code,
            **kwargs,
        )

else:
    # ── Legacy dark shell ───────────────────────────────────────────
    from ._chartis_kit_legacy import (  # noqa: F401
        P,
        _CORPUS_NAV,
        _CORPUS_NAV_LEGACY,
        _MONO,
        _SANS,
        chartis_shell as _legacy_chartis_shell,
        ck_fmt_currency,
        ck_fmt_irr,
        ck_fmt_moic,
        ck_fmt_num,
        ck_fmt_pct,
        ck_grade_badge,
        ck_kpi_block,
        ck_regime_badge,
        ck_section_header,
        ck_signal_badge,
        ck_table,
    )

    # PHI banner wrapper — prepended to body before the legacy shell
    # renders. Preserves the exact kwarg surface of the legacy shell.
    # The legacy shell already ships its own Cmd-K palette (see
    # _chartis_kit_legacy.py::_palette_html), so we DO NOT inject
    # our own here — doing so would create two #wc-cmdk modals
    # alongside the existing #ck-palette-bd, both binding to Cmd-K,
    # both opening on keystroke. The legacy palette's entries are
    # extended via _PALETTE_ENTRIES in the legacy module instead.
    def chartis_shell(body: str, title: str, **kwargs) -> str:  # type: ignore[misc]
        return _legacy_chartis_shell(
            _phi_banner_html() + body, title, **kwargs,
        )

    # v2-named helpers that callers may start using in Phase 2+
    # renderers. In legacy mode they delegate to the legacy helpers
    # so a mixed-phase page still renders.
    def ck_fmt_number(value, *, precision: int = 0, dash: str = "—") -> str:
        """v2-named wrapper; legacy mode uses ``ck_fmt_num``."""
        if value is None:
            return dash
        return ck_fmt_num(value, decimals=precision)

    def ck_fmt_percent(value, *, precision: int = 1, dash: str = "—") -> str:
        """v2-named wrapper; legacy mode uses ``ck_fmt_pct``."""
        if value is None:
            return dash
        return ck_fmt_pct(value, decimals=precision)

    def ck_panel(body_html: str, *, title=None, code=None) -> str:
        """v2 primitive; legacy mode renders a minimal div wrapper."""
        head = ""
        if title:
            head = (
                f'<div class="ck-panel-title" '
                f'style="padding:10px 14px;background:{P.get("panel_alt", "#0f172a")};'
                f'color:{P.get("text_dim", "#94a3b8")};font-size:10px;'
                f'letter-spacing:.14em;text-transform:uppercase;">{title}</div>'
            )
        return (
            f'<section class="ck-panel" '
            f'style="background:{P.get("panel", "#111827")};'
            f'border:1px solid {P.get("border", "#1e293b")};'
            f'margin-bottom:16px;">'
            f'{head}<div class="ck-panel-body" style="padding:14px 16px;">'
            f'{body_html}</div></section>'
        )

    def ck_command_palette(modules) -> str:
        """v2 primitive; legacy mode emits nothing (⌘K not wired)."""
        return ""


def ck_related_views(items):
    """Render a "related pages" strip as a list of links.

    Accepts a list of (label, href) tuples. The editorial reskin
    introduced this helper; the revert to the legacy shell dropped
    the implementation but left the callers in place, so this is
    a minimal compat shim that works in both shells.
    """
    import html as _h
    if not items:
        return ""
    chips = []
    for item in items:
        try:
            label, href = item
        except (TypeError, ValueError):
            continue
        chips.append(
            f'<a href="{_h.escape(str(href))}" '
            f'style="display:inline-block;margin:0 10px 6px 0;padding:4px 10px;'
            f'border:1px solid {P.get("border", "#1e293b")};'
            f'border-radius:4px;color:{P.get("text_dim", "#94a3b8")};'
            f'font-size:11px;text-decoration:none;">'
            f'{_h.escape(str(label))}</a>'
        )
    return (
        f'<section style="margin:18px 0;padding:12px 14px;'
        f'background:{P.get("panel_alt", "#0f172a")};'
        f'border:1px solid {P.get("border", "#1e293b")};">'
        f'<div style="font-size:10px;color:{P.get("text_dim", "#94a3b8")};'
        f'letter-spacing:.14em;text-transform:uppercase;'
        f'margin-bottom:8px;">Related</div>'
        + "".join(chips) + '</section>'
    )


__all__ = [
    "UI_V2_ENABLED",
    "P",
    "_CORPUS_NAV",
    "_CORPUS_NAV_LEGACY",
    "_MONO",
    "_SANS",
    "chartis_shell",
    "ck_command_palette",
    "ck_fmt_currency",
    "ck_fmt_irr",
    "ck_fmt_moic",
    "ck_fmt_num",
    "ck_fmt_number",
    "ck_fmt_pct",
    "ck_fmt_percent",
    "ck_grade_badge",
    "ck_kpi_block",
    "ck_panel",
    "ck_regime_badge",
    "ck_related_views",
    "ck_section_header",
    "ck_signal_badge",
    "ck_table",
]

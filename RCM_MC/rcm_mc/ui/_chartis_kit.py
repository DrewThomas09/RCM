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
# CHARTIS_UI_V2 (or RCM_MC_UI_VERSION=v3) opts the env into the
# editorial shell from _chartis_kit_editorial. Default "0" so existing
# behaviour is byte-for-byte unchanged. Phase 4 flips the default; Phase
# 5 cleanup deletes _chartis_kit_legacy and this dispatcher.
#
# Per-request override via ?ui=v3 query param lands in commit 5 — the
# request-time flag overrides the env, so a partner can preview the
# editorial render without changing server config.
def _ui_flag_on() -> bool:
    v2 = _os.environ.get("CHARTIS_UI_V2", "")
    v3 = _os.environ.get("RCM_MC_UI_VERSION", "").lower()
    return v2 not in ("", "0") or v3 in ("v3", "editorial", "1", "true")


UI_V2_ENABLED = _ui_flag_on()


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
    # ── editorial shell (Phase 1+ port) ─────────────────────────────
    #
    # Pure passthrough — the editorial module's chartis_shell already
    # matches the legacy kwargs (subtitle, extra_css, extra_js,
    # active_nav) so existing callers in rcm_mc/ui/chartis/*.py and
    # rcm_mc/ui/*.py work unchanged. Editorial-only kwargs
    # (breadcrumbs, code, show_chrome, show_phi_banner) are accepted
    # but optional. The PHI banner is rendered inside chartis_shell
    # itself, NOT injected here — avoids the double-banner that the
    # old compat shim caused.
    from ._chartis_kit_editorial import (  # noqa: F401
        P,
        _CORPUS_NAV,
        _LEGACY_NAV as _CORPUS_NAV_LEGACY,
        _MONO,
        _SANS,
        chartis_shell,
        ck_command_palette,
        ck_fmt_currency,
        ck_fmt_irr,
        ck_fmt_moic,
        ck_fmt_num,
        ck_fmt_number,
        ck_fmt_pct,
        ck_fmt_percent,
        ck_grade_badge,
        ck_kpi_block,
        ck_panel,
        ck_regime_badge,
        ck_section_header,
        ck_signal_badge,
        ck_table,
        # Editorial-only helpers
        covenant_pill,
        editorial_crumbs,
        editorial_page_head,
        editorial_topbar,
        number_maybe,
        pair_block,
        phi_banner,
        sparkline_svg,
        stage_pill,
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
    # Flag + palette
    "UI_V2_ENABLED",
    "P",
    "_CORPUS_NAV",
    "_CORPUS_NAV_LEGACY",
    "_MONO",
    "_SANS",
    # Shell
    "chartis_shell",
    # Helpers (legacy + editorial both expose)
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
    # Editorial-only (re-exported when UI_V2_ENABLED; importing through
    # the dispatcher means callers get an AttributeError under the
    # legacy shell, which is the intended signal — these helpers
    # produce editorial markup that doesn't fit the dark theme).
    "covenant_pill",
    "editorial_crumbs",
    "editorial_page_head",
    "editorial_topbar",
    "number_maybe",
    "pair_block",
    "phi_banner",
    "sparkline_svg",
]

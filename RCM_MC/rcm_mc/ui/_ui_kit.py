"""Compatibility shim — re-exports ``shell`` as chartis_shell.

Historically this module held a light-theme ``BASE_CSS`` + ``shell()``
renderer. Both are dead code after the unify-on-chartis migration
(chore/ui-polish-and-sanity-guards). The legacy ``shell()`` function
is kept as a thin wrapper so callers that still import
``from rcm_mc.ui._ui_kit import shell`` continue to work — they now
render through ``chartis_shell`` like everything else.

Callers that still use this shim:
  - rcm_mc/server.py (top-level import)
  - rcm_mc/ui/csv_to_html.py
  - rcm_mc/ui/text_to_html.py
  - rcm_mc/ui/sensitivity_dashboard.py
  - rcm_mc/ui/json_to_html.py
  - rcm_mc/infra/output_index.py
  - rcm_mc/reports/lp_update.py

Once those migrate to `from rcm_mc.ui._chartis_kit import chartis_shell`
directly, this module can be deleted entirely.
"""
from __future__ import annotations

from typing import Optional

from ._chartis_kit import chartis_shell


def shell(
    body: str,
    title: str,
    *,
    back_href: Optional[str] = None,
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    generated: bool = True,  # noqa: ARG001 — kept for signature parity
    omit_h1: bool = False,  # noqa: ARG001 — kept for signature parity
) -> str:
    """Legacy ``shell()`` — routes through ``chartis_shell``.

    Historically this function wrapped a body in a light-theme document
    and later delegated to ``shell_v2``. After the chartis unification
    it just calls ``chartis_shell`` with a compatible signature. The
    ``back_href`` argument is rendered as a small breadcrumb link above
    the body content; the ``generated`` and ``omit_h1`` arguments are
    accepted for backward compat but ignored.
    """
    import html as _html
    if back_href:
        body = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb" '
            f'style="margin-bottom:12px;font-size:11px;">'
            f'<a href="{_html.escape(back_href)}" '
            f'style="color:var(--ck-accent);text-decoration:none;">'
            f'&larr; Back to index</a></nav>{body}'
        )
    return chartis_shell(
        body,
        title,
        subtitle=subtitle or "",
        extra_css=extra_css,
        extra_js=extra_js,
    )

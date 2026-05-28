"""Honest placeholder for a deal surface that hasn't been built yet.

Renders inside the shared shell so navigation works (the sub-nav tab is
highlighted, identity header is real), but the body is a plain "under
construction" panel describing what this surface will be. Nothing is
fabricated.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict

from ._shell import SURFACE_BY_PATH, deal_shell


def render_surface_stub(
    ccn: str, slug: str, hospital: Dict[str, Any],
) -> str:
    surface = SURFACE_BY_PATH.get(slug)
    label = surface.label if surface else slug.title()
    blurb = surface.description if surface else "Surface under construction."
    group = surface.group if surface else ""
    body = (
        '<section class="ds-stub" style="max-width:780px;margin:32px auto 0;'
        'background:#faf6ec;border:1px solid #c9c1ac;padding:36px 32px;'
        'border-radius:2px;">'
        '<span style="font-family:var(--sc-mono);font-size:10.5px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        f'{_html.escape(group)} &middot; surface {surface.number if surface else "?"}'
        '</span>'
        f'<h2 style="font-family:var(--sc-serif);font-weight:400;font-size:30px;'
        f'line-height:1.1;margin:8px 0 10px;color:#15202b;">{_html.escape(label)}</h2>'
        f'<p style="font-family:var(--sc-serif);font-size:15px;line-height:1.55;'
        f'color:#2a3a4a;margin:0 0 18px;">{_html.escape(blurb)}</p>'
        '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        'color:#6a7480;margin:0 0 6px;font-style:italic;">'
        'Under construction. The underlying analytics already exist in the '
        'service layer; this surface wires them into the deal-lens shell in '
        'an upcoming PR. Until then, no data is shown here rather than '
        'fabricated.'
        '</p>'
        '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        'color:#2a3a4a;margin:14px 0 0;">'
        f'For now, return to <a href="/deals/{_html.escape(ccn, quote=True)}/profile" '
        'style="color:#1f7a5a;">Profile</a> for what is live.'
        '</p>'
        '</section>'
    )
    return deal_shell(
        ccn, hospital, active_slug=slug, body_html=body,
        page_title=f"{label} · coming soon",
    )

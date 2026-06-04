"""Shared 'demo mode active' banner.

Rendered at the top of the partner landing surfaces (``/home`` and the ``/app``
command center) whenever the curated KKR demo portfolio is loaded, so a partner
always knows they're looking at demo data — not their own deals — and can reach
the demo controls (including unload) in one click.

Detection keys off the demo profile marker (``"demo": "kkr"``) rather than a
deal id, so a partner who happens to hold a real Cotiviti deal never sees a
spurious 'unload the demo' prompt. Returns an empty string when no demo deals
are present, so callers can unconditionally concatenate it into the page body.
"""
from __future__ import annotations

from typing import Any


def demo_banner(store: Any) -> str:
    """Return the demo-mode banner HTML, or '' when the demo isn't loaded."""
    try:
        with store.connect() as con:
            n = con.execute(
                "SELECT COUNT(*) FROM deals WHERE profile_json LIKE ?",
                ('%"demo": "kkr"%',),
            ).fetchone()[0]
    except Exception:  # noqa: BLE001
        n = 0
    if not n:
        return ""
    return (
        '<div style="display:flex;align-items:center;gap:10px;background:#eef4fb;'
        'border:1px solid #b9cde6;border-left:4px solid #0b2341;border-radius:4px;'
        'padding:9px 14px;margin:10px 0 4px;font-size:12px;color:#1a2332;">'
        '<span style="font-family:JetBrains Mono,monospace;font-size:10px;'
        'letter-spacing:.1em;text-transform:uppercase;background:#0b2341;color:#fff;'
        'padding:2px 7px;border-radius:2px;white-space:nowrap;">Demo mode</span>'
        f'<span>Showing the curated <b>KKR healthcare portfolio</b> '
        f'({int(n)} deals) — real investments, modeled operating metrics. '
        'These are not your deals.</span>'
        '<a href="/demo" style="margin-left:auto;color:#155752;text-decoration:none;'
        'font-weight:600;white-space:nowrap;">Demo controls &amp; unload &rarr;</a>'
        '</div>'
    )

"""Reusable export-menu component.

Drops a consistent "Download as…" cluster into any result page. One
helper produces the HTML; result pages call it with the relevant
deal_id (or direct URLs for pages that aren't packet-driven).

Two entry points:
    export_menu_for_deal(deal_id: str) -> str
        The standard ``/api/analysis/<deal>/export?format=X`` links:
        HTML · PDF · XLSX · PPTX · CSV · JSON · ZIP package

    export_menu(label: str, links: list[tuple[str, str]]) -> str
        Generic variant for pages that aren't packet-driven — caller
        supplies (label, href) pairs. Used by EBITDA bridge page,
        the dashboard's corpus exports, etc.

The markup is deliberately self-contained: inline CSS, no external
stylesheet, no JS. Survives any shell theme; renders identically in
both v2 + legacy chartis_kit branches.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from typing import List, Tuple


def _button(href: str, label: str, *, primary: bool = False) -> str:
    bg = "var(--sc-navy)" if primary else "#fff"
    fg = "#fff" if primary else "var(--sc-navy)"
    border = "1px solid var(--sc-navy)"
    return (
        f'<a href="{_html.escape(href)}" '
        f'style="display:inline-block;padding:6px 14px;margin:0 6px 6px 0;'
        f'background:{bg};color:{fg};{border};border-radius:4px;'
        f'text-decoration:none;font-size:12px;font-weight:500;'
        f'font-family:system-ui,-apple-system,sans-serif;"'
        f' class="no-print">{_html.escape(label)}</a>'
    )


def export_menu(label: str, links: List[Tuple[str, str]]) -> str:
    """Generic export cluster.

    Args:
        label: Heading shown above the buttons ("Export this report" etc.)
        links: list of (button_label, href) tuples. First is primary-styled.
    """
    if not links:
        return ""
    buttons = []
    for i, (btn_label, href) in enumerate(links):
        buttons.append(_button(href, btn_label, primary=(i == 0)))
    return (
        '<div class="no-print" style="margin:16px 0;padding:12px;'
        'background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;'
        'font-family:system-ui,-apple-system,sans-serif;">'
        f'<div style="font-size:11px;text-transform:uppercase;color:#6b7280;'
        f'letter-spacing:0.05em;margin-bottom:8px;">{_html.escape(label)}</div>'
        + "".join(buttons) +
        '</div>'
    )


def export_menu_for_deal(deal_id: str, *, label: str = "Download") -> str:
    """Standard menu for packet-driven deal pages.

    Wraps ``/api/analysis/<deal_id>/export?format=X`` with the 7 formats
    currently supported (HTML, PDF, XLSX, PPTX, CSV, JSON, ZIP package).
    PDF uses the HTML-with-auto-print path; no new runtime deps required.

    The deal_id is URL-encoded (not HTML-escaped) here since it becomes
    a path segment; _button() applies the HTML-escape on final render.
    That keeps us at exactly one layer of encoding per-layer.
    """
    safe = _urlparse.quote(deal_id, safe="")
    base = f"/api/analysis/{safe}/export"
    links = [
        ("HTML memo", f"{base}?format=html"),
        ("PDF (print)", f"{base}?format=pdf"),
        ("Excel (XLSX)", f"{base}?format=xlsx"),
        ("PowerPoint", f"{base}?format=pptx"),
        ("Raw data (CSV)", f"{base}?format=csv"),
        ("JSON", f"{base}?format=json"),
        ("ZIP package", f"{base}?format=package"),
    ]
    return export_menu(label, links)

"""Internal Open-Data Integrations lab — /tools/open-data (+ /<id> detail).

Backend staging surface for the open-source healthcare datasets/APIs in
``rcm_mc.data_public.open_data_registry``. Deliberately INTERNAL: it lives
under the Tools tab and is reachable by direct URL, but it is NOT added to the
top nav (``_CORPUS_NAV``) or the section sub-nav, and every screen is badged
work-in-progress. The point is to track, link, and stage the integration work
before anything graduates to a front-facing feature.

Pure presentation over the registry; no network calls happen here (the loaders
that actually fetch live where credentials/outbound access exist).
"""
from __future__ import annotations

import html as _html
from typing import Optional

from rcm_mc.ui._chartis_kit import chartis_shell, ck_page_title, P
from rcm_mc.data_public import open_data_registry as reg

# Access-model badge colors (semantic, desaturated to fit the palette).
_ACCESS = {
    "open": (P["positive"], "OPEN"),
    "api": (P["accent"], "API"),
    "credentialed": (P["warning"], "CREDENTIALED"),
    "self-host": (P["navy"], "SELF-HOST"),
    "model": ("#6d5bd0", "MODEL"),
}
_STATUS = {
    "registered": (P["text_faint"], "Registered"),
    "wired": (P["positive"], "Wired"),
}


def _badge(color: str, label: str) -> str:
    return (f'<span style="font-family:var(--sc-mono);font-size:9px;'
            f'letter-spacing:.1em;text-transform:uppercase;color:#fff;'
            f'background:{color};padding:2px 7px;border-radius:10px">'
            f'{_html.escape(label)}</span>')


def _access_badge(access: str) -> str:
    color, label = _ACCESS.get(access, (P["text_faint"], access.upper()))
    return _badge(color, label)


def _status_badge(status: str) -> str:
    color, label = _STATUS.get(status, (P["text_faint"], status))
    return (f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'color:{color}">&#9679; {_html.escape(label)}</span>')


def _wip_banner() -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin:14px 0 6px;'
        f'padding:10px 14px;border:1px solid {P["warning"]};border-radius:3px;'
        f'background:rgba(184,115,42,.07)">'
        f'<span style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
        f'text-transform:uppercase;color:#fff;background:{P["warning"]};'
        f'padding:3px 8px;border-radius:3px">Internal &middot; WIP</span>'
        f'<span style="font-family:var(--sc-sans);font-size:12.5px;color:{P["text_dim"]}">'
        f'Staging area for open-data integrations. Cataloged + linked, not yet '
        f'wired into the product, and intentionally kept out of the main nav '
        f'until each is built out.</span></div>')


def _card(s: dict) -> str:
    sid = s["id"]
    return (
        f'<div style="border:1px solid {P["border"]};border-radius:3px;'
        f'padding:13px 15px;background:{P["panel"]};display:flex;'
        f'flex-direction:column;gap:7px">'
        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
        f'<a href="/tools/open-data/{_html.escape(sid)}" '
        f'style="font-family:var(--sc-serif);font-size:15px;color:{P["text"]};'
        f'text-decoration:none;font-weight:600">{_html.escape(s["name"])}</a>'
        f'{_access_badge(s["access"])}</div>'
        f'<div style="font-family:var(--sc-sans);font-size:12.5px;line-height:1.5;'
        f'color:{P["text_dim"]}">{_html.escape(s["blurb"])}</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'gap:10px;margin-top:2px">{_status_badge(s["status"])}'
        f'<a href="{_html.escape(s["url"])}" target="_blank" rel="noopener" '
        f'style="font-family:var(--sc-mono);font-size:10px;color:{P["accent"]};'
        f'text-decoration:none">source &#8599;</a></div></div>')


def render_open_data_lab() -> str:
    title = ck_page_title(
        "Open-data integrations",
        eyebrow="INTERNAL · TOOLS LAB",
        meta=f"{len(reg.all_sources())} sources staged · backend, not in the nav",
    )
    counts = reg.status_counts()
    summary = (
        f'<div style="font-family:var(--sc-mono);font-size:11px;color:{P["text_dim"]};'
        f'margin:4px 0 0"><b style="color:{P["text"]}">{len(reg.all_sources())}</b> '
        f'sources &middot; <b style="color:{P["positive"]}">{counts.get("wired", 0)}</b> '
        f'wired &middot; <b style="color:{P["text"]}">{counts.get("registered", 0)}</b> '
        f'registered (linked, loader pending)</div>')
    sections = []
    for cid, label, items in reg.by_category():
        cards = "".join(_card(s) for s in items)
        sections.append(
            f'<section style="margin:22px 0 0">'
            f'<div style="font-family:var(--sc-sans);font-size:12px;font-weight:600;'
            f'letter-spacing:.06em;text-transform:uppercase;color:{P["text_dim"]};'
            f'border-bottom:1px solid {P["border"]};padding-bottom:6px;margin:0 0 12px">'
            f'{_html.escape(label)} '
            f'<span style="color:{P["text_faint"]};font-weight:400">'
            f'&middot; {len(items)}</span></div>'
            f'<div style="display:grid;'
            f'grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">'
            f'{cards}</div></section>')
    body = title + _wip_banner() + summary + "".join(sections)
    return chartis_shell(body, title="Open-data integrations",
                         active_nav="/tools")


def render_open_data_source(source_id: str) -> str:
    s = reg.get(source_id)
    if not s:
        body = ck_page_title("Source not found", eyebrow="INTERNAL · TOOLS LAB")
        body += (f'<p style="font-family:var(--sc-sans);color:{P["text_dim"]}">'
                 f'No registered source with that id. '
                 f'<a href="/tools/open-data" style="color:{P["accent"]}">'
                 f'Back to the lab &rarr;</a></p>')
        return chartis_shell(body, title="Open-data integrations",
                             active_nav="/tools")
    rows = [
        ("Category", reg.category_label(s["category"])),
        ("Access model", s["access"]),
        ("License", s.get("license", "—")),
        ("Integration shape", s.get("integration", "—")),
        ("Status", _STATUS.get(s["status"], (None, s["status"]))[1]),
    ]
    meta_rows = "".join(
        f'<tr><td style="padding:5px 16px 5px 0;font-family:var(--sc-mono);'
        f'font-size:10px;letter-spacing:.08em;text-transform:uppercase;'
        f'color:{P["text_faint"]};vertical-align:top;white-space:nowrap">'
        f'{_html.escape(k)}</td>'
        f'<td style="padding:5px 0;font-family:var(--sc-sans);font-size:13px;'
        f'color:{P["text"]}">{_html.escape(str(v))}</td></tr>'
        for k, v in rows)
    title = ck_page_title(
        s["name"], eyebrow="INTERNAL · TOOLS LAB",
        meta="staged integration · not front-facing")
    body = (
        title + _wip_banner()
        + f'<p style="font-family:var(--sc-serif);font-size:16px;line-height:1.55;'
        f'color:{P["text_dim"]};max-width:70ch;margin:14px 0 4px">'
        f'{_html.escape(s["blurb"])}</p>'
        + f'<p style="font-family:var(--sc-sans);font-size:13px;line-height:1.55;'
        f'color:{P["text_dim"]};max-width:70ch;margin:8px 0 18px">'
        f'<b style="color:{P["text"]}">Why it matters: </b>'
        f'{_html.escape(s.get("relevance", ""))}</p>'
        + f'<table style="border-collapse:collapse;margin:0 0 18px">{meta_rows}</table>'
        + f'<p><a href="{_html.escape(s["url"])}" target="_blank" rel="noopener" '
        f'style="font-family:var(--sc-mono);font-size:12px;color:{P["accent"]};'
        f'text-decoration:none">Open source &#8599;</a>'
        f'<span style="color:{P["text_faint"]};margin:0 10px">·</span>'
        f'<a href="/tools/open-data" style="font-family:var(--sc-mono);font-size:12px;'
        f'color:{P["text_dim"]};text-decoration:none">&larr; back to the lab</a></p>')
    return chartis_shell(body, title=s["name"], active_nav="/tools")

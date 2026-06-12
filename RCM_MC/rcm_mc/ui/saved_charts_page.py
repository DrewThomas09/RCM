"""Saved Charts library — reopen named Chart Builder / Exhibit configs.

A saved chart is a route + query string (the chart IS its URL), so the
library is a thin list: open relinks to the live page, delete posts to
the owner-scoped store. Saving happens on the chart pages themselves
via a small POST form that snapshots ``location.search``.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell, ck_empty_state, ck_page_title

_ROUTE_LABELS = {"/chart-builder": "Chart", "/exhibit": "Exhibit"}


def save_chart_form(route: str) -> str:
    """The "save this chart" strip the two chart pages embed — a name
    box + POST. The hidden query_params field is snapshotted from
    ``location.search`` at submit so what's saved is exactly the URL
    being looked at (the CSRF shim patches the POST automatically)."""
    r = html.escape(route, quote=True)
    return (
        f'<form method="post" action="/api/charts/save" '
        f'onsubmit="this.query_params.value='
        f'window.location.search.slice(1);" '
        f'style="display:flex;gap:8px;justify-content:center;'
        f'align-items:center;margin-top:10px;">'
        f'<input type="hidden" name="route" value="{r}">'
        f'<input type="hidden" name="query_params" value="">'
        f'<input type="text" name="title" placeholder="Name this chart…" '
        f'maxlength="160" required style="height:28px;border:1px solid '
        f'#c9c1ac;border-radius:5px;padding:0 8px;width:220px;'
        f'font-size:12px;">'
        f'<button type="submit" style="padding:6px 13px;border:1px solid '
        f'#c9c1ac;border-radius:5px;background:#fff;color:#0b2341;'
        f'font-size:12px;font-weight:600;cursor:pointer;">★ Save to '
        f'library</button>'
        f'<a href="/charts" style="font-size:11.5px;color:#1F7A75;">'
        f'My saved charts →</a></form>')


def render_saved_charts_page(
    charts: List[Dict[str, Any]],
    owner: str = "",
    qs: "Optional[Dict[str, Any]]" = None,
) -> str:
    rows = ""
    for c in charts:
        qp = c.get("query_params", "")
        href = c["route"] + (f"?{qp}" if qp else "")
        kind = _ROUTE_LABELS.get(c["route"], "Chart")
        when = (c.get("created_at", "") or "")[:10]
        rows += (
            f'<tr>'
            f'<td style="padding:9px 12px;font-family:var(--sc-serif,serif);'
            f'font-weight:600;"><a href="{html.escape(href, quote=True)}" '
            f'style="color:#0b2341;text-decoration:none;">'
            f'{html.escape(c["title"])}</a></td>'
            f'<td style="padding:9px 12px;"><span style="font-size:10.5px;'
            f'padding:2px 9px;border-radius:10px;border:1px solid #9bc1bc;'
            f'color:#155752;">{kind}</span></td>'
            f'<td style="padding:9px 12px;font-size:11.5px;color:#7a8699;" '
            f'class="num">{html.escape(when)}</td>'
            f'<td style="padding:9px 12px;text-align:right;">'
            f'<a href="{html.escape(href, quote=True)}" '
            f'style="font-size:11.5px;color:#1F7A75;margin-right:12px;">'
            f'Open</a>'
            f'<form method="post" action="/api/charts/delete" '
            f'style="display:inline;">'
            f'<input type="hidden" name="id" value="{int(c["id"])}">'
            f'<button type="submit" style="border:none;background:none;'
            f'color:#b5321e;font-size:11.5px;cursor:pointer;padding:0;">'
            f'Delete</button></form></td></tr>')

    if not owner:
        content = ck_empty_state(
            "Sign in to keep a chart library",
            "Saved charts are per-user. Sign in, configure a chart on "
            "Chart Builder or Exhibit Composer, and click “★ Save to "
            "library”.")
    elif not charts:
        content = ck_empty_state(
            "No saved charts yet",
            "Configure a chart on Chart Builder or Exhibit Composer and "
            "click “★ Save to library” — it reopens from here exactly as "
            "you left it.")
    else:
        content = (
            '<div style="border:1px solid #d6cfc0;border-radius:8px;'
            'background:#fff;overflow:hidden;">'
            '<table style="width:100%;border-collapse:collapse;'
            'font-size:13px;">'
            '<thead><tr style="background:#efe9dd;font-size:10.5px;'
            'letter-spacing:0.06em;color:#465366;">'
            '<th style="padding:8px 12px;text-align:left;">NAME</th>'
            '<th style="padding:8px 12px;text-align:left;">KIND</th>'
            '<th style="padding:8px 12px;text-align:left;">SAVED</th>'
            '<th></th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')

    body = (
        ck_page_title(
            "Saved Charts",
            eyebrow="UTILITY · CHART LIBRARY",
            meta="Named Chart Builder and Exhibit Composer configurations "
                 "— reopen any of them exactly as saved.",
        )
        + '<div class="ts-wrap" style="max-width:920px;">'
        + content
        + '<div style="font-size:12px;color:#465366;margin-top:14px;">'
          'Build something new: <a href="/chart-builder" '
          'style="color:#1F7A75;">Chart Builder</a> · '
          '<a href="/exhibit" style="color:#1F7A75;">Exhibit Composer</a>'
          '</div></div>')
    return chartis_shell(
        body, "Saved Charts", active_nav="/research",
        subtitle="Chart library")

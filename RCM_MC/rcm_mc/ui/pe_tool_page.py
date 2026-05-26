"""Deal-driven PE Intelligence tool runner — /diligence/pe-tool.

Runs a pe_intelligence analytic tool against a *real* deal's analysis packet
and renders its output, with a deal picker at the top so an analyst can swap
the demonstration deal for the one they're actually working. This is the
"bring the dark tools to life on real data" path the user asked for: the page
looks filled out (defaulting to a loaded deal) but every figure traces to that
deal's PartnerReview — no fabricated inputs.

First cluster wired: the tools that compute purely from a single
``PartnerReview`` (built via the same pipeline as /deal/<id>/partner-review).
More clusters (tools needing extra typed inputs) light up over later passes;
the registry below is the extension point.
"""
from __future__ import annotations

import html as _html
import importlib
import re
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import (
    P,
    chartis_shell,
    ck_empty_state,
    ck_page_title,
    ck_source_purpose,
)

# slug → how to run it. ``mode`` "review": render_fn(review) directly;
# "report": render_fn(builder(review)). Only single-PartnerReview tools that
# run clean against a real packet are listed (verified before wiring).
PE_TOOL_REGISTRY: Dict[str, Dict[str, str]] = {
    "analyst_cheatsheet": {
        "title": "Analyst Cheatsheet",
        "builder": "build_cheatsheet", "render": "render_cheatsheet_markdown",
        "mode": "review",
    },
    "hundred_day_plan": {
        "title": "100-Day Plan",
        "builder": "generate_plan", "render": "render_plan_markdown",
        "mode": "report",
    },
    "red_team_review": {
        "title": "Red-Team Review",
        "builder": "build_red_team_report", "render": "render_red_team_markdown",
        "mode": "report",
    },
    "partner_discussion": {
        "title": "Partner Discussion",
        "builder": "build_discussion", "render": "render_discussion_markdown",
        "mode": "report",
    },
    "negotiation_position": {
        "title": "Negotiation Position",
        "builder": "derive_negotiation_position",
        "render": "render_negotiation_markdown", "mode": "report",
    },
}


def _inline(s: str) -> str:
    s = _html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    return s


def _md_to_html(md: str) -> str:
    """Compact markdown → Chartis-styled HTML for tool output (headings,
    pipe tables, bullet lists, bold/italic, paragraphs). Self-contained so the
    page carries no cross-package CSS dependency."""
    th = (f'padding:6px 10px;font-family:var(--ck-mono);font-size:9.5px;'
          f'letter-spacing:0.06em;text-transform:uppercase;color:{P["text_faint"]};'
          f'text-align:left;border-bottom:2px solid {P["border"]};')
    td = (f'padding:6px 10px;font-size:12px;color:{P["text"]};'
          f'border-bottom:1px solid {P["border_dim"]};vertical-align:top;')
    out: List[str] = []
    table: List[str] = []
    in_list = False

    def flush_table() -> None:
        rows = [r.strip() for r in table if r.strip()]
        table.clear()
        if len(rows) < 2:
            return
        header = [c.strip() for c in rows[0].strip("|").split("|")]
        body_start = 2 if "---" in rows[1] else 1
        html = [f'<table style="width:100%;border-collapse:collapse;margin:10px 0;">'
                f'<thead><tr>'
                + "".join(f'<th style="{th}">{_inline(c)}</th>' for c in header)
                + '</tr></thead><tbody>']
        for r in rows[body_start:]:
            cells = [c.strip() for c in r.strip("|").split("|")]
            html.append("<tr>" + "".join(f'<td style="{td}">{_inline(c)}</td>'
                                          for c in cells) + "</tr>")
        html.append("</tbody></table>")
        out.append("".join(html))

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in md.split("\n"):
        if line.startswith("|"):
            table.append(line)
            continue
        if table:
            flush_table()
        if line.startswith("# "):
            close_list()
            out.append(f'<h2 style="font-family:var(--sc-serif);color:{P["text"]};'
                       f'font-size:19px;margin:14px 0 6px;">{_inline(line[2:])}</h2>')
        elif line.startswith("## "):
            close_list()
            out.append(f'<h3 style="font-family:var(--sc-serif);color:{P["text"]};'
                       f'font-size:15px;margin:12px 0 5px;">{_inline(line[3:])}</h3>')
        elif line.startswith("### "):
            close_list()
            out.append(f'<h4 style="font-family:var(--ck-mono);font-size:11px;'
                       f'letter-spacing:0.06em;text-transform:uppercase;'
                       f'color:{P["text_dim"]};margin:10px 0 4px;">'
                       f'{_inline(line[4:])}</h4>')
        elif line.startswith(("- ", "* ")):
            if not in_list:
                out.append('<ul style="margin:6px 0 6px 18px;padding:0;">')
                in_list = True
            out.append(f'<li style="font-size:12.5px;line-height:1.55;'
                       f'color:{P["text"]};margin:2px 0;">{_inline(line[2:])}</li>')
        elif line.strip() == "":
            close_list()
        else:
            close_list()
            out.append(f'<p style="font-size:12.5px;line-height:1.6;'
                       f'color:{P["text"]};margin:6px 0;">{_inline(line)}</p>')
    if table:
        flush_table()
    close_list()
    return "\n".join(out)


def run_review_tool(slug: str, review: Any) -> Tuple[str, Optional[str]]:
    """Run a registered review-driven tool. Returns (markdown, error)."""
    spec = PE_TOOL_REGISTRY.get(slug)
    if spec is None:
        return "", f"Tool '{slug}' is not yet wired for inline run."
    try:
        mod = importlib.import_module(f"..pe_intelligence.{slug}", __package__)
        render = getattr(mod, spec["render"])
        if spec["mode"] == "review":
            md = render(review)
        else:
            builder = getattr(mod, spec["builder"])
            md = render(builder(review))
        if not isinstance(md, str) or not md.strip():
            return "", "Tool produced no output for this deal."
        return md, None
    except Exception as exc:  # noqa: BLE001
        return "", f"{type(exc).__name__}: {exc}"


def _deal_picker(slug: str, deal_id: str,
                 deals: List[Tuple[str, str]]) -> str:
    opts = []
    for did, name in deals:
        sel = " selected" if did == deal_id else ""
        label = f"{name} ({did})" if name and name != did else did
        opts.append(f'<option value="{_html.escape(did)}"{sel}>'
                    f'{_html.escape(label)}</option>')
    tool_opts = []
    for s, spec in PE_TOOL_REGISTRY.items():
        sel = " selected" if s == slug else ""
        tool_opts.append(f'<option value="{_html.escape(s)}"{sel}>'
                         f'{_html.escape(spec["title"])}</option>')
    sty = (f'padding:7px 10px;font-size:12.5px;border:1px solid {P["border"]};'
           f'border-radius:3px;background:{P["panel"]};color:{P["text"]};'
           f'font-family:var(--sc-sans);margin-right:8px;')
    return (
        f'<form method="get" action="/diligence/pe-tool" '
        f'style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
        f'margin:10px 0 14px;">'
        f'<span style="font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:{P["text_faint"]};">'
        f'Tool</span>'
        f'<select name="tool" style="{sty}">{"".join(tool_opts)}</select>'
        f'<span style="font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:{P["text_faint"]};">'
        f'Deal</span>'
        f'<select name="deal" style="{sty}">{"".join(opts)}</select>'
        f'<button type="submit" style="padding:7px 16px;font-size:12px;'
        f'font-family:var(--ck-mono);border:1px solid {P["accent"]};'
        f'background:{P["accent"]};color:#fff;border-radius:3px;cursor:pointer;">'
        f'Run</button>'
        f'<a href="/diligence/pe-library" style="font-size:11.5px;'
        f'color:{P["accent"]};margin-left:4px;">← all tools</a>'
        f'</form>'
    )


def render_pe_tool_page(
    slug: str = "",
    review: Any = None,
    deal_id: str = "",
    deal_name: str = "",
    deals: Optional[List[Tuple[str, str]]] = None,
    error: str = "",
) -> str:
    """Render a deal-driven tool run. ``deals`` is [(deal_id, name), …]."""
    deals = deals or []
    spec = PE_TOOL_REGISTRY.get(slug)
    title = spec["title"] if spec else "PE Intelligence Tool"

    picker = _deal_picker(slug, deal_id, deals) if deals else ""

    if not deals:
        inner = ck_empty_state(
            "No deal loaded",
            "These tools compute from a real deal's analysis packet. Load or "
            "create a deal (Pipeline → New Deal), then return here to run it.",
        )
    elif spec is None:
        inner = ck_empty_state(
            "Pick a tool",
            "Choose a tool above to run it against the selected deal, or browse "
            "the full toolkit in the PE Intelligence Library.",
        )
    elif error:
        inner = (
            f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-left:3px solid {P["negative"]};border-radius:3px;'
            f'padding:14px;"><div style="font-family:var(--ck-mono);font-size:10px;'
            f'letter-spacing:0.1em;text-transform:uppercase;color:{P["negative"]};'
            f'margin-bottom:5px;">Could not run on this deal</div>'
            f'<div style="color:{P["text_dim"]};font-size:12px;line-height:1.55;">'
            f'{_html.escape(error)}<br>Try another deal, or run a simulation on '
            f'this one first so its analysis packet is complete.</div></div>'
        )
    else:
        md, run_err = run_review_tool(slug, review)
        if run_err:
            inner = (
                f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
                f'border-left:3px solid {P["negative"]};border-radius:3px;padding:14px;'
                f'color:{P["text_dim"]};font-size:12px;line-height:1.55;">'
                f'{_html.escape(run_err)}</div>'
            )
        else:
            inner = (
                f'<div class="ck-panel"><div style="padding:8px 16px 16px;">'
                f'{_md_to_html(md)}</div></div>'
            )

    sp = ck_source_purpose(
        purpose=(
            f"Run the {title} against a real deal's analysis packet. Switch the "
            "deal above to your live deal — every figure is computed from that "
            "deal's PartnerReview, not fabricated."
        ),
        universe="user-deals",
        confidence="derived",
        source="pe_intelligence." + (slug or "—")
               + " · computed from the selected deal's analysis packet",
        next_action="All tools",
        next_href="/diligence/pe-library",
    )

    meta = (f"{title} · {_html.escape(deal_name or deal_id)}"
            if spec and deal_id else "select a tool + deal")
    body = (
        ck_page_title(title, eyebrow="DILIGENCE · PE INTELLIGENCE", meta=meta)
        + sp + picker + inner
    )
    return chartis_shell(body, title=title, active_nav="/diligence")

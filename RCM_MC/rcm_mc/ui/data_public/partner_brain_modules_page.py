"""Partner Brain module directory + auto-detail pages.

Routes:
    /partner-brain/modules                — directory of all 264 catalogued
                                            pe_intelligence modules, grouped
                                            by category with filter chips.
    /partner-brain/module?name=<slug>     — auto-rendered detail page for a
                                            single module: docstring, exported
                                            dataclasses/functions, and the
                                            compute output when Input has
                                            defaults.

This is the load-bearing connection page for Phase 2+: every
orphaned pe_intelligence module becomes reachable through a uniform
flow without hand-crafting a page per module.
"""
from __future__ import annotations

import html as _html
import json as _json
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_section_header
from ._pe_module_introspect import (
    PEModuleEntry,
    catalog_pe_intelligence,
    find_entry,
    run_module_default,
)


_CATEGORY_LABELS = {
    "valuation": "Valuation & M&A",
    "ic-decision": "IC Decision",
    "sniff": "Sniff Test & Archetype",
    "100-day": "100-Day & Integration",
    "regulatory": "Regulatory",
    "failures": "Named Failures",
    "wc": "Working Capital",
    "team": "Management & Team",
    "synthesis": "Synthesis & Analysis",
    "rcm-payer": "RCM / Payer Mix",
    "process": "Deal Process",
    "business-model": "Business Model",
    "debt": "Debt & LBO",
    "lp-ops": "LP / Portfolio Ops",
    "opportunity": "Opportunity / White Space",
    "hold": "Hold / Syndication",
    "quality-esg": "Quality / ESG",
    "vcp": "Value-Creation Plan",
    "exit": "Exit",
    "other": "Other",
}


# ── Shared helpers ─────────────────────────────────────────────────


def _kpi_tile(label: str, value: str, color: Optional[str] = None) -> str:
    val_color = color or P["text"]
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'padding:12px 14px;min-width:120px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};letter-spacing:0.08em;'
        f'text-transform:uppercase;margin-bottom:4px">{_html.escape(label)}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{val_color};'
        f'font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace">'
        f"{_html.escape(value)}</div></div>"
    )


def _back_link(target: str, label: str) -> str:
    return (
        f'<div style="margin-bottom:16px">'
        f'<a href="{target}" style="color:{P["accent"]};font-size:11px;text-decoration:none">'
        f"← {_html.escape(label)}</a></div>"
    )


# ── Directory page ────────────────────────────────────────────────


def _directory_rows(entries: List[PEModuleEntry], active_cat: str) -> str:
    """Render the module rows grouped by category."""
    # Group
    by_cat: Dict[str, List[PEModuleEntry]] = {}
    for e in entries:
        for c in e.categories:
            by_cat.setdefault(c, []).append(e)

    if active_cat and active_cat in by_cat:
        groups = [(active_cat, by_cat[active_cat])]
    else:
        # Sort groups by preferred order then module count
        pref = list(_CATEGORY_LABELS.keys())
        groups = sorted(
            by_cat.items(),
            key=lambda kv: (pref.index(kv[0]) if kv[0] in pref else 99, -len(kv[1])),
        )

    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]
    pos = P["positive"]
    warn = P["warning"]

    blocks = []
    for cat, items in groups:
        label = _CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        rows = []
        for i, e in enumerate(items):
            rb = panel_alt if i % 2 == 0 else bg
            status_color = pos if (e.compute_fn and e.input_class) else (warn if e.compute_fn else text_dim)
            status_text = (
                "AUTO-RUN" if (e.compute_fn and e.input_class) else
                ("FN-ONLY" if e.compute_fn else "INFO-ONLY")
            )
            rows.append(
                f'<tr style="background:{rb};vertical-align:top">'
                f'<td style="padding:6px 12px;width:90px;text-align:center">'
                f'<span style="font-size:9px;color:{status_color};border:1px solid {status_color};'
                f'padding:2px 6px;letter-spacing:0.06em;font-family:JetBrains Mono,monospace">'
                f"{status_text}</span></td>"
                f'<td style="padding:6px 12px">'
                f'<a href="/partner-brain/module?name={_html.escape(e.name)}" '
                f'style="font-size:11px;font-weight:700;color:{acc};text-decoration:none;'
                f'font-family:JetBrains Mono,monospace">{_html.escape(e.name)}</a>'
                f'<div style="font-size:10px;color:{text_dim};margin-top:2px;line-height:1.5">'
                f"{_html.escape(e.first_line)}</div></td>"
                f"</tr>"
            )
        blocks.append(
            f'<div style="margin-top:20px">'
            f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;'
            f'text-transform:uppercase;padding-bottom:6px;border-bottom:1px solid {border};'
            f'margin-bottom:8px">{_html.escape(label)} <span style="color:{text_dim}">({len(items)})</span></div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )
    return "".join(blocks)


def _category_chips(entries: List[PEModuleEntry], active: str) -> str:
    counts: Dict[str, int] = {}
    for e in entries:
        for c in e.categories:
            counts[c] = counts.get(c, 0) + 1
    pref = list(_CATEGORY_LABELS.keys())
    ordered = sorted(counts.items(), key=lambda kv: (pref.index(kv[0]) if kv[0] in pref else 99))

    chips = []
    all_active = "" if active else f"background:{P['accent']};color:{P['bg']};border-color:{P['accent']}"
    chips.append(
        f'<a href="/partner-brain/modules" '
        f'style="display:inline-block;padding:4px 10px;font-size:10px;'
        f'font-family:JetBrains Mono,monospace;color:{P["text"]};'
        f'border:1px solid {P["border"]};text-decoration:none;margin:2px;'
        f'letter-spacing:0.06em;{all_active}">ALL ({len(entries)})</a>'
    )
    for cat, count in ordered:
        label = _CATEGORY_LABELS.get(cat, cat)
        is_active = cat == active
        style = (
            f"background:{P['accent']};color:{P['bg']};border-color:{P['accent']}"
            if is_active else ""
        )
        chips.append(
            f'<a href="/partner-brain/modules?cat={cat}" '
            f'style="display:inline-block;padding:4px 10px;font-size:10px;'
            f'font-family:JetBrains Mono,monospace;color:{P["text"]};'
            f'border:1px solid {P["border"]};text-decoration:none;margin:2px;'
            f'letter-spacing:0.06em;{style}">{_html.escape(label)} ({count})</a>'
        )
    return f'<div style="margin-top:12px;margin-bottom:12px">{"".join(chips)}</div>'


def render_partner_brain_modules_directory(qp: Dict[str, str] | None = None) -> str:
    qp = qp or {}
    active_cat = qp.get("cat", "").strip().lower()

    entries = catalog_pe_intelligence()
    auto_runnable = sum(1 for e in entries if e.compute_fn and e.input_class)
    fn_only = sum(1 for e in entries if e.compute_fn and not e.input_class)

    text = P["text"]
    text_dim = P["text_dim"]

    kpi_strip = (
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px">'
        f"{_kpi_tile('Total modules', str(len(entries)))}"
        f"{_kpi_tile('Auto-runnable', str(auto_runnable), P['positive'])}"
        f"{_kpi_tile('Fn-only', str(fn_only), P['warning'])}"
        f"{_kpi_tile('Info-only', str(len(entries) - auto_runnable - fn_only), P['text_dim'])}"
        f"{_kpi_tile('Categories', str(len(_CATEGORY_LABELS)))}"
        f"</div>"
    )

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'{_back_link("/partner-brain", "Partner Brain hub")}'
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f"Partner Brain · Module Directory</h1>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"Every catalogued <code>rcm_mc.pe_intelligence</code> module — "
        f"name, docstring, and a link to its auto-generated detail page. "
        f"<span style=\"color:{P['positive']}\">AUTO-RUN</span> modules "
        f"have a default-constructible Input so the detail page computes "
        f"and renders a report. "
        f"<span style=\"color:{P['warning']}\">FN-ONLY</span> modules have "
        f"a compute function but a required Input; details show the signature "
        f"and docstring. "
        f"<span style=\"color:{P['text_dim']}\">INFO-ONLY</span> modules "
        f"are libraries / registries surfaced for discovery.</p>"
        f"{kpi_strip}"
        f'{_category_chips(entries, active_cat)}'
        f"{_directory_rows(entries, active_cat)}"
        f"</div>"
    )
    return chartis_shell(
        body=body, title="Partner Brain · Module Directory", active_nav="/partner-brain"
    )


# ── Module-detail page ────────────────────────────────────────────


def _render_json_block(d: Any, max_depth: int = 4) -> str:
    """Render a nested dict/list as a pretty-printed JSON block."""
    try:
        text = _json.dumps(d, indent=2, default=str, sort_keys=False)
    except Exception:  # noqa: BLE001
        text = str(d)
    # Truncate for safety
    if len(text) > 50_000:
        text = text[:50_000] + "\n... (truncated)"
    return (
        f'<pre style="background:{P["panel_alt"]};border:1px solid {P["border"]};'
        f'padding:12px 16px;font-size:10px;color:{P["text"]};line-height:1.5;'
        f'overflow-x:auto;font-family:JetBrains Mono,monospace;'
        f'max-height:600px;overflow-y:auto;white-space:pre-wrap;word-break:break-word">'
        f"{_html.escape(text)}</pre>"
    )


def _render_markdown_block(md: str) -> str:
    """Very lightweight markdown rendering — enough for the module-
    supplied ``render_*_markdown`` output to look readable."""
    if not md:
        return ""
    escaped = _html.escape(md)
    return (
        f'<pre style="background:{P["panel_alt"]};border:1px solid {P["border"]};'
        f'padding:12px 16px;font-size:11px;color:{P["text"]};line-height:1.6;'
        f'overflow-x:auto;font-family:JetBrains Mono,monospace;'
        f'max-height:600px;overflow-y:auto;white-space:pre-wrap;word-break:break-word">'
        f"{escaped}</pre>"
    )


def _shape_table(entry: PEModuleEntry) -> str:
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    rows = [
        ("Module name", f'<code style="color:{acc}">{_html.escape(entry.name)}</code>'),
        ("Source file", f'<code style="color:{text_dim}">{_html.escape(entry.file_path)}</code>'),
        ("Input class", f'<code style="color:{acc}">{_html.escape(entry.input_class or "—")}</code>'),
        ("Compute fn", f'<code style="color:{acc}">{_html.escape(entry.compute_fn or "—")}</code>'),
        ("Report class", f'<code style="color:{acc}">{_html.escape(entry.report_class or "—")}</code>'),
        ("Render fn", f'<code style="color:{acc}">{_html.escape(entry.render_fn or "—")}</code>'),
        ("Categories", ", ".join(
            f'<a href="/partner-brain/modules?cat={c}" style="color:{acc}">{_html.escape(c)}</a>'
            for c in entry.categories
        )),
        (
            "All classes",
            ", ".join(f'<code style="color:{text_dim}">{_html.escape(c)}</code>' for c in entry.all_classes) or "—",
        ),
        (
            "All functions",
            ", ".join(f'<code style="color:{text_dim}">{_html.escape(f)}</code>' for f in entry.all_functions) or "—",
        ),
    ]
    body = "".join(
        f'<tr><td style="padding:5px 10px;font-size:10px;color:{text_dim};'
        f'letter-spacing:0.06em;width:140px;border-bottom:1px dashed {border}">'
        f'{_html.escape(k)}</td><td style="padding:5px 10px;font-size:11px;color:{text};'
        f'border-bottom:1px dashed {border}">{v}</td></tr>'
        for k, v in rows
    )
    return (
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tbody>{body}</tbody></table>'
    )


def render_partner_brain_module_detail(qp: Dict[str, str] | None = None) -> str:
    qp = qp or {}
    name = qp.get("name", "").strip()
    if not name:
        body = (
            f'<div style="padding:40px;max-width:900px;margin:0 auto">'
            f'{_back_link("/partner-brain/modules", "Module directory")}'
            f'<h1 style="color:{P["text"]};font-size:18px">Missing module name</h1>'
            f'<p style="font-size:12px;color:{P["text_dim"]};margin-top:8px">'
            f"Pass <code>?name=&lt;module_name&gt;</code> in the URL. "
            f"Return to the <a href=\"/partner-brain/modules\" style=\"color:{P['accent']}\">"
            f"directory</a>.</p></div>"
        )
        return chartis_shell(body=body, title="Partner Brain · Module", active_nav="/partner-brain")

    entry = find_entry(name)
    if entry is None:
        body = (
            f'<div style="padding:40px;max-width:900px;margin:0 auto">'
            f'{_back_link("/partner-brain/modules", "Module directory")}'
            f'<h1 style="color:{P["text"]};font-size:18px">Module not found</h1>'
            f'<p style="font-size:12px;color:{P["text_dim"]};margin-top:8px">'
            f'No catalogued module named <code>{_html.escape(name)}</code>. '
            f"Return to the <a href=\"/partner-brain/modules\" style=\"color:{P['accent']}\">"
            f"directory</a>.</p></div>"
        )
        return chartis_shell(body=body, title="Partner Brain · Module", active_nav="/partner-brain")

    # Attempt auto-run.
    result = run_module_default(entry.name) if entry.compute_fn else {
        "ok": False, "reason": "no compute function detected",
        "report_dict": None, "markdown": None, "report_type": None,
    }

    text = P["text"]
    text_dim = P["text_dim"]
    panel = P["panel"]
    border = P["border"]

    status_badge_html = ""
    if entry.compute_fn and entry.input_class:
        status_badge_html = (
            f'<span style="font-size:10px;color:{P["positive"]};border:1px solid {P["positive"]};'
            f'padding:3px 8px;letter-spacing:0.06em;font-family:JetBrains Mono,monospace">AUTO-RUN</span>'
        )
    elif entry.compute_fn:
        status_badge_html = (
            f'<span style="font-size:10px;color:{P["warning"]};border:1px solid {P["warning"]};'
            f'padding:3px 8px;letter-spacing:0.06em;font-family:JetBrains Mono,monospace">FN-ONLY</span>'
        )
    else:
        status_badge_html = (
            f'<span style="font-size:10px;color:{P["text_dim"]};border:1px solid {P["text_dim"]};'
            f'padding:3px 8px;letter-spacing:0.06em;font-family:JetBrains Mono,monospace">INFO-ONLY</span>'
        )

    # Result section.
    result_html = ""
    if result["ok"]:
        # Highlight partner_note if the report has one.
        partner_note = ""
        if isinstance(result["report_dict"], dict):
            partner_note = str(result["report_dict"].get("partner_note") or "")
        if partner_note:
            result_html += (
                f'<div style="background:{panel};border:1px solid {border};'
                f'border-left:3px solid {P["accent"]};padding:14px 16px;margin-bottom:16px">'
                f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;'
                f'text-transform:uppercase;margin-bottom:6px;font-weight:600">Partner note</div>'
                f'<div style="font-size:12px;color:{text};line-height:1.6">'
                f"{_html.escape(partner_note)}</div></div>"
            )
        result_html += (
            ck_section_header(
                f"Report — {result['report_type']}",
                "auto-run on default inputs · all fields",
                None,
            )
            + _render_json_block(result["report_dict"])
        )
        if result["markdown"]:
            result_html += (
                '<div style="margin-top:20px"></div>'
                + ck_section_header("Markdown render", f"output of {entry.render_fn}", None)
                + _render_markdown_block(result["markdown"])
            )
    else:
        reason = str(result.get("reason", ""))
        result_html = (
            f'<div style="background:{panel};border:1px solid {P["warning"]};'
            f'border-left:3px solid {P["warning"]};padding:14px 16px">'
            f'<div style="font-size:10px;color:{P["warning"]};letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-bottom:6px;font-weight:600">Auto-run unavailable</div>'
            f'<div style="font-size:11px;color:{text};line-height:1.6">{_html.escape(reason)}</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:8px;line-height:1.5">'
            f"Module is importable and callable from Python; this page just "
            f"can't auto-construct its Input with defaults. Future phase "
            f"will add per-module demo input builders.</div></div>"
        )

    docstring_html = (
        f'<pre style="background:{panel};border:1px solid {border};padding:14px 16px;'
        f'font-size:11px;color:{text_dim};line-height:1.6;white-space:pre-wrap;'
        f'word-break:break-word;font-family:JetBrains Mono,monospace">'
        f'{_html.escape(entry.docstring or "(no module docstring)")}</pre>'
    )

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'{_back_link("/partner-brain/modules", "Module directory")}'
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em;'
        f'font-family:JetBrains Mono,monospace">{_html.escape(entry.name)}</h1>'
        f'{status_badge_html}'
        f"</div>"
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"{_html.escape(entry.first_line or '(no one-line summary)')}</p>"
        f'<div style="margin-top:20px"></div>'
        f'{ck_section_header("Module docstring", "", None)}'
        f'<div style="margin-top:8px">{docstring_html}</div>'
        f'<div style="margin-top:20px"></div>'
        f'{ck_section_header("Module shape", "detected exports + wiring signature", None)}'
        f'<div style="margin-top:8px">{_shape_table(entry)}</div>'
        f'<div style="margin-top:28px"></div>'
        f"{result_html}"
        f"</div>"
    )
    return chartis_shell(
        body=body, title=f"Partner Brain · {entry.name}", active_nav="/partner-brain"
    )

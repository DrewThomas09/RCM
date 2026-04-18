"""VDR / Diligence Tracker — /vdr-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _status_color(status: str) -> str:
    return {
        "complete": P["positive"],
        "in progress": P["accent"],
        "overdue": P["negative"],
        "pending": P["warning"],
        "scheduled": P["text_dim"],
        "pre-final": P["text_dim"],
    }.get(status, P["text_dim"])


def _priority_color(priority: str) -> str:
    return {
        "critical": P["negative"],
        "high": P["warning"],
        "standard": P["text_dim"],
        "medium": P["accent"],
        "low": P["text_dim"],
    }.get(priority, P["text_dim"])


def _mat_color(m: str) -> str:
    return {
        "critical": P["negative"],
        "material": P["warning"],
        "high": P["warning"],
        "medium": P["accent"],
        "low": P["text_dim"],
    }.get(m, P["text_dim"])


def _requests_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID","left"),("Workstream","left"),("Category","left"),("Request","left"),
            ("Status","center"),("Priority","center"),("Requested","right"),("Response","right"),
            ("Days Out","right"),("Complete %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(r.status)
        p_c = _priority_color(r.priority)
        d_c = P["negative"] if r.days_outstanding > 20 else (P["warning"] if r.days_outstanding > 10 else text_dim)
        c_c = pos if r.completeness_pct >= 0.95 else (acc if r.completeness_pct >= 0.70 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.request_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(r.workstream)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:340px">{_html.escape(r.request)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.status)}</span></td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{p_c};font-weight:700">{_html.escape(r.priority)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.requested_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.response_date) if r.response_date else "—"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{r.days_outstanding if r.days_outstanding else "—"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{r.completeness_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _workstreams_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Workstream","left"),("Total","right"),("Complete","right"),("In Progress","right"),
            ("Outstanding","right"),("Overdue","right"),("Completeness %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if w.completeness_pct >= 0.95 else (acc if w.completeness_pct >= 0.80 else P["warning"])
        o_c = neg if w.overdue > 0 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(w.workstream)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{w.total_requests}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{w.complete}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{w.in_progress}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{w.outstanding}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{w.overdue}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{w.completeness_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _qa_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Q&A ID","left"),("Topic","left"),("Response Quality","center"),("Days to Answer","right"),
            ("Follow-Up","center"),("Materiality","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    q_c = {"thorough": pos, "partial": P["warning"], "deflected": neg}
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        qc = q_c.get(q.seller_response_quality, text_dim)
        f_c = P["warning"] if q.follow_up_required else pos
        m_c = _mat_color(q.materiality)
        d_c = neg if q.answered_within_days > 5 else (P["warning"] if q.answered_within_days > 3 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(q.qa_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:400px">{_html.escape(q.topic)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{qc};font-weight:700">{_html.escape(q.seller_response_quality).upper()}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:600">{q.answered_within_days}d</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"YES" if q.follow_up_required else "NO"}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{m_c};border:1px solid {m_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(q.materiality)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _documents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Section","left"),("Uploaded","right"),("Expected","right"),("Completeness %","right"),
            ("Last Updated","right"),("Seller Notes","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if d.completeness_pct >= 0.90 else (acc if d.completeness_pct >= 0.80 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.section)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{d.documents_uploaded}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.total_expected}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{d.completeness_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(d.last_updated)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.seller_notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _critical_path_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Item","left"),("Owner","left"),("Dependency","left"),("Needed By","right"),
            ("Status","center"),("Risk to Close","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.current_status)
        r_c = neg if c.risk_to_close.startswith("critical") or c.risk_to_close.startswith("high") else (P["warning"] if c.risk_to_close.startswith("medium") else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.item)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.owner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.dependency)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_html.escape(c.needed_by)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.current_status)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{r_c}">{_html.escape(c.risk_to_close)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _materiality_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Finding","left"),("Workstream","left"),("Materiality","center"),
            ("SPA Impact","left"),("Disposition","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    disp_c = {"resolved": P["positive"], "disclosed, mitigated": P["positive"], "disclosed": P["accent"],
              "in remediation": P["warning"], "in progress": P["accent"], "in negotiation": P["warning"],
              "open": P["negative"]}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = _mat_color(m.materiality)
        d_c = disp_c.get(m.disposition, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:380px">{_html.escape(m.finding)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.workstream)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{m_c};border:1px solid {m_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.materiality)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(m.spa_impact)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{d_c};font-weight:600">{_html.escape(m.disposition)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_vdr_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.vdr_tracker import compute_vdr_tracker
    r = compute_vdr_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    overdue_delta_color = neg if r.overdue_count > 0 else pos
    kpi_strip = (
        ck_kpi_block("Days Open", str(r.days_since_vdr_open), "d", "") +
        ck_kpi_block("Total Requests", str(r.total_requests), "", "") +
        ck_kpi_block("Completion", f"{r.completion_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Overdue", str(r.overdue_count), "", "") +
        ck_kpi_block("Material Findings", str(r.material_findings_count), "", "") +
        ck_kpi_block("Workstreams", str(len(r.workstreams)), "", "") +
        ck_kpi_block("Q&A Items", str(len(r.qa_log)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    req_tbl = _requests_table(r.requests)
    ws_tbl = _workstreams_table(r.workstreams)
    qa_tbl = _qa_table(r.qa_log)
    doc_tbl = _documents_table(r.documents)
    cp_tbl = _critical_path_table(r.critical_path)
    mat_tbl = _materiality_table(r.materiality)

    total_docs_up = sum(d.documents_uploaded for d in r.documents)
    total_docs_exp = sum(d.total_expected for d in r.documents)
    doc_complete_pct = total_docs_up / total_docs_exp * 100 if total_docs_exp else 0

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">VDR / Diligence Request Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{_html.escape(r.deal_name)} · {r.days_since_vdr_open} days since VDR open · {r.total_requests} requests across {len(r.workstreams)} workstreams · {r.overdue_count} overdue · {r.material_findings_count} material findings — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Workstream Completion Summary</div>{ws_tbl}</div>
  <div style="{cell}"><div style="{h3}">Critical-Path Items to Close</div>{cp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Materiality Findings / SPA Exposure</div>{mat_tbl}</div>
  <div style="{cell}"><div style="{h3}">Document Room — Section Coverage ({total_docs_up:,} / {total_docs_exp:,} · {doc_complete_pct:.1f}%)</div>{doc_tbl}</div>
  <div style="{cell}"><div style="{h3}">Full Diligence Request List ({r.total_requests} items)</div>{req_tbl}</div>
  <div style="{cell}"><div style="{h3}">Management Q&A Log</div>{qa_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">VDR Status Summary:</strong> {r.days_since_vdr_open} days since VDR opened — {r.total_requests} requests total with {r.completion_pct * 100:.1f}% average completeness.
    {r.overdue_count} overdue items (cyber incident history + Phase I environmental) are blocking critical-path workstreams; escalation to seller CFO required by end of week.
    Document room at {doc_complete_pct:.1f}% complete across 12 sections; IT/Cyber (77.3%), Tax (80.0%), and Deal Structure (73.3%) remain weakest.
    Q&A log shows {sum(1 for q in r.qa_log if q.follow_up_required)} open follow-ups across {len(r.qa_log)} items; seller response quality skews to "thorough" on financial/regulatory, "partial" on IT/HR.
    Material findings count of {r.material_findings_count} is elevated but all tractable — two critical items (cyber disclosure + MD rollover) drive remaining deal risk.
    SPA first draft timeline: 2026-04-30; confirmatory QoE close-out: 2026-05-15 — remains on track for target close.
  </div>
</div>"""

    return chartis_shell(body, "VDR Tracker", active_nav="/vdr-tracker")

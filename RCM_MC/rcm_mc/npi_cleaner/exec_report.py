"""Executive data-quality one-pager — the artifact that goes in the deck.

A self-contained, print-ready HTML page (inline styles only, no app shell,
no JS) built from a run's scorecard: the grade, the five dimensions, the
top findings with plain-English descriptions and remediation guidance from
the rule registry, payer clusters, denial mix, and the emptiest columns.
Teams forward this to the source-system owner; it has to stand alone in an
email, which is why it deliberately does not use the app's chartis shell.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

from . import rules as _rules

_CSS = """
body{font-family:Georgia,'Times New Roman',serif;color:#1a2332;margin:40px auto;
     max-width:820px;padding:0 24px;line-height:1.45}
h1{font-size:26px;margin:0 0 2px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;
   border-bottom:2px solid #155752;padding-bottom:4px;margin:28px 0 10px}
.small{color:#5b6770;font-size:12.5px}
.grade{font-size:56px;font-weight:700;line-height:1}
.grid{display:flex;gap:26px;align-items:center;margin:14px 0 4px}
table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
   color:#5b6770;border-bottom:1px solid #d2ddd7;padding:4px 8px}
td{border-bottom:1px solid #eceff1;padding:5px 8px;vertical-align:top}
.num{text-align:right;font-variant-numeric:tabular-nums}
.sev-critical{color:#b5321e;font-weight:700}
.sev-warning{color:#b8732a;font-weight:700}
.sev-info{color:#5b6770}
.bar{height:8px;background:#eceff1;border-radius:4px;overflow:hidden;width:180px;
     display:inline-block;vertical-align:middle;margin-right:8px}
.bar>i{display:block;height:100%}
@media print{body{margin:10mm auto}}
"""


def _esc(v: object) -> str:
    return _html.escape(str(v if v is not None else ""))


def _dim_color(v: float) -> str:
    return "#0a8a5f" if v >= 85 else ("#b8732a" if v >= 70 else "#b5321e")


def build_exec_report(sc: Dict[str, object], file_name: str,
                      generated: str) -> str:
    """Render the one-pager from an as_scorecard() dict. ``generated`` is an
    ISO timestamp string supplied by the caller (keeps this module pure)."""
    q = sc.get("quality") or {}
    dims: Dict[str, float] = dict(q.get("dimensions") or {})
    score = q.get("score", "—")
    letter = q.get("letter", "—")
    tone = _dim_color(float(score) if isinstance(score, (int, float)) else 0)

    parts: List[str] = []
    parts.append(f"<style>{_CSS}</style>")
    parts.append("<h1>Claims data-quality report</h1>")
    parts.append(f"<div class='small'>{_esc(file_name)} · generated "
                 f"{_esc(generated)} · PE&nbsp;Desk claims cleaner</div>")

    # Headline grade + core counts.
    parts.append("<div class='grid'>")
    parts.append(f"<div class='grade' style='color:{tone}'>{_esc(letter)}"
                 f"<span style='font-size:22px;color:#5b6770'> · "
                 f"{_esc(score)}/100</span></div>")
    parts.append(
        "<div class='small'>"
        f"{int(sc.get('rows_in') or 0):,} rows in · "
        f"{int(sc.get('rows_out') or 0):,} rows out · "
        f"{int(sc.get('duplicates_removed') or 0):,} exact duplicates removed"
        f"<br>{int(sc.get('repairs_total') or 0):,} safe repairs applied · "
        f"{int(sc.get('changes_logged') or 0):,} cells changed "
        "(full audit trail available)</div>")
    parts.append("</div>")

    # Dimensions.
    parts.append("<h2>Quality dimensions</h2><table>")
    for k in ("completeness", "validity", "consistency",
              "uniqueness", "conformity"):
        v = float(dims.get(k, 0.0))
        parts.append(
            f"<tr><td style='width:130px'>{k.title()}</td>"
            f"<td><span class='bar'><i style='width:{max(2, min(100, v))}%;"
            f"background:{_dim_color(v)}'></i></span>"
            f"<span class='num'>{v:.1f}%</span></td></tr>")
    parts.append("</table>")

    # Top findings with rule-registry descriptions.
    sanity: Dict[str, int] = dict(sc.get("sanity") or {})
    if sanity:
        parts.append("<h2>Findings (reported, never auto-changed)</h2>")
        parts.append("<table><tr><th>Severity</th><th>Finding</th>"
                     "<th class='num'>Rows</th><th>What to do</th></tr>")
        ordered = sorted(sanity.items(), key=lambda kv: -kv[1])
        sev_rank = {"critical": 0, "warning": 1, "info": 2}
        ordered.sort(key=lambda kv: sev_rank.get(
            _rules.describe(kv[0])["severity"], 3))
        for rule_id, n in ordered[:14]:
            d = _rules.describe(rule_id)
            parts.append(
                f"<tr><td class='sev-{_esc(d['severity'])}'>"
                f"{_esc(d['severity'])}</td>"
                f"<td><strong>{_esc(d['title'])}</strong><br>"
                f"<span class='small'>{_esc(d['description'])}</span></td>"
                f"<td class='num'>{n:,}</td>"
                f"<td class='small'>{_esc(d['remediation'])}</td></tr>")
        parts.append("</table>")

    # Payer clusters.
    payer = sc.get("payer") or {}
    multi = payer.get("multi_spelling") or []
    if multi:
        parts.append("<h2>Payer spellings to reconcile</h2><table>"
                     "<tr><th>Payer group</th><th class='num'>Rows</th>"
                     "<th>Spellings seen</th></tr>")
        for c in multi[:8]:
            variants = " · ".join(
                f"{_esc(v['value'])} ({int(v['count']):,})"
                for v in c.get("variants", []))
            parts.append(f"<tr><td>{_esc(c['canonical'])}</td>"
                         f"<td class='num'>{int(c['total']):,}</td>"
                         f"<td class='small'>{variants}</td></tr>")
        parts.append("</table>")

    # Denial mix.
    denials = sc.get("denials") or {}
    top = denials.get("top") or []
    if top:
        try:
            from . import refdata as _rd
        except Exception:  # noqa: BLE001
            _rd = None
        parts.append("<h2>Top denial / adjustment reasons</h2><table>"
                     "<tr><th>Code</th><th>Meaning</th>"
                     "<th class='num'>Rows</th></tr>")
        for d in top[:10]:
            desc = (_rd.carc_description(str(d["code"])) if _rd else None) or ""
            parts.append(f"<tr><td>{_esc(d['code'])}</td>"
                         f"<td class='small'>{_esc(desc)}</td>"
                         f"<td class='num'>{int(d['count']):,}</td></tr>")
        parts.append("</table>")

    # Who is in this file — credential + specialty mix (report-only).
    creds: Dict[str, int] = dict(sc.get("credentials") or {})
    if creds:
        try:
            from . import refdata as _rd2
        except Exception:  # noqa: BLE001
            _rd2 = None
        parts.append("<h2>Credential mix</h2><table>"
                     "<tr><th>Credential</th><th>Meaning</th>"
                     "<th class='num'>Cells</th></tr>")
        for c, n in sorted(creds.items(), key=lambda kv: -kv[1])[:10]:
            meaning = (_rd2.credential_meaning(c) if _rd2 else None) or ""
            parts.append(f"<tr><td>{_esc(c)}</td>"
                         f"<td class='small'>{_esc(meaning)}</td>"
                         f"<td class='num'>{int(n):,}</td></tr>")
        parts.append("</table>")

    specs = sc.get("specialties") or []
    if specs:
        parts.append("<h2>Specialty mix (provider taxonomy)</h2><table>"
                     "<tr><th>Taxonomy</th><th>Specialty</th>"
                     "<th class='num'>Rows</th></tr>")
        for s in specs[:10]:
            parts.append(
                f"<tr><td>{_esc(s.get('code'))}</td>"
                f"<td class='small'>{_esc(s.get('name') or '—')}</td>"
                f"<td class='num'>{int(s.get('n') or 0):,}</td></tr>")
        parts.append("</table>")

    # Emptiest columns.
    fills = [f for f in (sc.get("fill_rates") or [])
             if float(f.get("pct", 100)) < 100.0]
    if fills:
        fills.sort(key=lambda f: float(f["pct"]))
        parts.append("<h2>Columns with blanks</h2><table>"
                     "<tr><th>Column</th><th class='num'>% filled</th></tr>")
        for f in fills[:10]:
            parts.append(f"<tr><td>{_esc(f['column'])}</td>"
                         f"<td class='num'>{float(f['pct']):.1f}%</td></tr>")
        parts.append("</table>")

    parts.append(
        "<p class='small' style='margin-top:26px'>Grades are deterministic "
        "ratios of the counts shown — no model, no sampling. Findings are "
        "reported and never auto-changed; safe formatting repairs are "
        "itemized in the run's change-log download.</p>")
    return "".join(parts)

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
import re as _re
from typing import Dict, List

from . import rules as _rules

# Remit exports often prefix the CARC with its group code ("CO-45", "PR1");
# descriptions and playbooks key on the bare code, so lookups strip a
# leading CO/OA/PI/PR/CR when the raw token misses. Display keeps the raw.
_CARC_PREFIX_RE = _re.compile(r"^(?:CO|OA|PI|PR|CR)[-\s]?(?=[A-Z]?\d)")

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


def _fmt_money(v: object) -> str:
    try:
        return f"${float(v):,.2f}"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(v: object) -> str:
    try:
        return f"{float(v):.1f}%"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"


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

    # Trend banner — regression/recovery vs the previous run of this file.
    # This page is the artifact that gets forwarded; a quality drop the web
    # UI knew about must not vanish from the emailed copy.
    trend = sc.get("trend_alerts") or []
    if trend:
        parts.append(
            "<div style='border-left:4px solid #b8732a;background:#faf3ea;"
            "padding:8px 12px;margin:10px 0'>")
        parts.append("<strong style='font-size:13px'>Change vs the "
                     "previous run of this file</strong>")
        for a in trend[:6]:
            parts.append(f"<div class='small'>• {_esc(a)}</div>")
        parts.append("</div>")

    # De-identification confirmation — one line, but the difference between
    # "safe to forward" and not.
    deid = sc.get("deid") or {}
    if deid:
        cols = ", ".join(str(c) for c in (deid.get("columns") or [])[:8])
        parts.append(
            f"<p class='small'>De-identified: {int(deid.get('cells') or 0):,}"
            f" patient-identifier cells masked"
            + (f" ({_esc(cols)})" if cols else "") + ".</p>")

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

    # Compliance screens (OIG LEIE + PECOS). A file with excluded billing
    # NPIs is direct fraud exposure — the one thing a one-pager must not
    # stay silent about.
    comp = sc.get("compliance") or []
    if comp:
        parts.append("<h2>Compliance (OIG LEIE · PECOS)</h2><table>"
                     "<tr><th>Screen</th><th class='num'>Checked</th>"
                     "<th class='num'>Hits</th><th>Result</th></tr>")
        for s in comp:
            if not isinstance(s, dict) or s.get("id") == "error":
                continue
            hits = int(s.get("excluded") or 0) + int(s.get("not_enrolled")
                                                     or 0)
            tone = ("sev-critical" if int(s.get("excluded") or 0) > 0
                    else ("sev-warning" if hits else "sev-info"))
            avail = ("" if s.get("available")
                     else " <span class='small'>(not available)</span>")
            parts.append(
                f"<tr><td>{_esc(s.get('label') or s.get('id'))}{avail}</td>"
                f"<td class='num'>{int(s.get('checked') or 0):,}</td>"
                f"<td class='num {tone}'>{hits:,}</td>"
                f"<td class='small'>{_esc(s.get('note') or '')}</td></tr>")
            for m in (s.get("matches") or [])[:6]:
                who = " ".join(str(m.get(k)) for k in ("npi", "name")
                               if m.get(k))
                extra = " · ".join(
                    str(m.get(k)) for k in ("excl_type", "excl_date")
                    if m.get(k))
                billed = (f" · billed {_fmt_money(m['billed'])}"
                          if m.get("billed") is not None else "")
                parts.append(
                    f"<tr><td colspan='4' class='small sev-critical'>"
                    f"&nbsp;&nbsp;⚠ excluded: {_esc(who)}"
                    + (f" ({_esc(extra)})" if extra else "")
                    + _esc(billed) + "</td></tr>")
        parts.append("</table>")

    # Dollar exposure — the v49 engine sizes each issue in billed dollars;
    # this is the dollars-at-risk narrative of the whole page.
    adv = sc.get("advanced") or {}
    adv_issues = [it for it in (adv.get("issues") or [])
                  if isinstance(it, dict)]
    if adv_issues:
        adv_issues = sorted(
            adv_issues,
            key=lambda it: -(float(it.get("dollars") or 0.0)))
        parts.append("<h2>Dollar exposure by issue</h2><table>"
                     "<tr><th>Issue</th><th class='num'>Rows</th>"
                     "<th class='num'>$ exposure</th>"
                     "<th class='num'>% of file $</th></tr>")
        for it in adv_issues[:8]:
            parts.append(
                f"<tr><td>{_esc(it.get('issue'))}</td>"
                f"<td class='num'>{int(it.get('rows') or 0):,}</td>"
                f"<td class='num'>{_fmt_money(it.get('dollars'))}</td>"
                f"<td class='num'>{_fmt_pct(it.get('pct_dollars'))}"
                "</td></tr>")
        parts.append("</table>")

    # NPPES cross-check — verified/deactivated counts + recovered NPIs.
    nppes = sc.get("nppes") or {}
    nv = (nppes.get("verify") or {}) if isinstance(nppes, dict) else {}
    nr = (nppes.get("recover") or {}) if isinstance(nppes, dict) else {}
    if nv or nr:
        bits2: List[str] = []
        if nv:
            bits2.append(f"{int(nv.get('checked') or 0):,} NPIs checked "
                         f"against NPPES — {int(nv.get('active') or 0):,} "
                         f"active, {int(nv.get('not_found') or 0):,} not "
                         "found / deactivated")
        rec_n = (len(nr.get("matches") or [])
                 if isinstance(nr, dict) else 0)
        if rec_n:
            bits2.append(f"{rec_n} row(s) with recovered candidate NPIs")
        if int(sc.get("recovered_written") or 0):
            bits2.append(f"{int(sc['recovered_written']):,} recovered NPIs "
                         "written into the cleaned file")
        if bits2:
            parts.append("<h2>NPPES verification</h2>"
                         f"<p class='small'>{_esc(' · '.join(bits2))}</p>")

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
        _ppct = denials.get("preventable_pct")
        if _ppct is not None:
            parts.append(f"<p class='small'><strong>{_ppct}% of the "
                         "classified denial volume was preventable</strong> "
                         "by a pre-submission screen.</p>")
        parts.append("<h2>Top denial / adjustment reasons</h2><table>"
                     "<tr><th>Code</th><th>Meaning</th>"
                     "<th class='num'>Rows</th><th>Playbook</th></tr>")
        for d in top[:10]:
            code = str(d["code"]).strip().upper()
            bare = _CARC_PREFIX_RE.sub("", code)
            desc = ""
            if _rd:
                desc = (_rd.carc_description(code)
                        or _rd.carc_description(bare) or "")
            _pb = ""
            if d.get("category"):
                _pb = f"[{d['category']}] {d.get('action', '')}"
            elif _rd and bare != code:
                # Group-code-prefixed tokens (CO-45) miss the engine-side
                # playbook join; recover it here from the bare code.
                pb2 = _rd.carc_playbook(bare)
                if pb2:
                    _pb = f"[{pb2['category']}] {pb2.get('action', '')}"
            parts.append(f"<tr><td>{_esc(d['code'])}</td>"
                         f"<td class='small'>{_esc(desc)}</td>"
                         f"<td class='num'>{int(d['count']):,}</td>"
                         f"<td class='small'>{_esc(_pb)}</td></tr>")
        parts.append("</table>")

    # Population marts (analytics.py) — what the file MEANS: care-setting
    # mix, visit counts, readmissions, condition burden, data-loss alerts.
    pop = sc.get("population") or {}
    if pop:
        parts.append("<h2>Population profile</h2>")
        mix = pop.get("service_mix") or {}
        cats = mix.get("categories") or []
        if cats:
            parts.append("<table><tr><th>Care setting</th>"
                         "<th class='num'>Lines</th>"
                         "<th class='num'>% of file</th>"
                         "<th class='num'>Charges</th></tr>")
            for c in cats[:8]:
                parts.append(
                    f"<tr><td>{_esc(c['category'])} — "
                    f"<span class='small'>{_esc(c['subcategory'])}</span>"
                    f"</td><td class='num'>{int(c['rows']):,}</td>"
                    f"<td class='num'>{c['pct']}%</td>"
                    f"<td class='num'>${float(c['charges']):,.2f}</td></tr>")
            parts.append("</table>")
        bits: List[str] = []
        enc = pop.get("encounters") or {}
        if enc:
            bits.append(f"{int(enc.get('n_encounters') or 0):,} encounters "
                        f"across {int(enc.get('n_patients') or 0):,} "
                        "patients")
            readm = enc.get("readmissions") or {}
            if readm:
                bits.append(
                    f"30-day inpatient readmissions: "
                    f"{int(readm.get('readmissions_30d') or 0):,} of "
                    f"{int(readm.get('inpatient_stays') or 0):,} stays "
                    f"({readm.get('rate_pct')}%)")
        vol = pop.get("volume") or {}
        if vol.get("median_observed_pmpm") is not None:
            bits.append("median observed PMPM "
                        f"${float(vol['median_observed_pmpm']):,.2f}")
        if bits:
            parts.append(f"<p class='small'>{_esc(' · '.join(bits))}</p>")
        for a in (vol.get("alerts") or [])[:4]:
            parts.append(f"<p class='small sev-critical'>⚠ {_esc(a)}</p>")
        cond = pop.get("conditions") or {}
        prev = cond.get("prevalence") or []
        if prev:
            top_c = " · ".join(
                f"{_esc(p['condition'])} {p['pct']}%" for p in prev[:6])
            # Without a patient column those percentages are shares of
            # ROWS — calling them "prevalence" in the deck artifact would
            # misstate the denominator.
            if cond.get("patient_grouping") is False:
                parts.append(
                    "<p class='small'><strong>Chronic condition mentions "
                    "(% of rows — no patient column detected):</strong> "
                    f"{top_c}</p>")
            else:
                parts.append(f"<p class='small'><strong>Chronic conditions "
                             f"(prevalence):</strong> {top_c}</p>")
        ci = pop.get("coding_intensity") or {}
        if ci:
            _line = (f"E&amp;M coding intensity: "
                     f"{int(ci.get('established_visits') or 0):,} "
                     f"established visits, file average level "
                     f"{ci.get('file_avg_level')}")
            _nat = ci.get("national_mix") or {}
            if _nat:
                try:
                    _tot = sum(float(v) for v in _nat.values())
                    _nat_avg = (sum(int(str(k)[-1]) * float(v)
                                    for k, v in _nat.items()) / _tot
                                if _tot else None)
                except (TypeError, ValueError):
                    _nat_avg = None
                if _nat_avg is not None:
                    _line += (f" vs national avg level {_nat_avg:.2f} "
                              "(Medicare established-visit mix)")
            if ci.get("provider_basis"):
                _line += f" (per-{ci['provider_basis']}-provider basis)"
            outs = ci.get("outliers") or []
            if outs:
                _line += (f" — {len(outs)} provider(s) code materially "
                          "hotter than the file")
            parts.append(f"<p class='small'>{_esc(_line)}</p>")

    # Charge outliers — per-HCPCS statistical outliers (3×IQR), previously
    # web-UI-only.
    outl = sc.get("outliers") or []
    if outl:
        parts.append("<h2>Charge outliers (per HCPCS)</h2><table>"
                     "<tr><th>Code</th><th class='num'>Lines</th>"
                     "<th class='num'>Outliers</th>"
                     "<th class='num'>Median</th>"
                     "<th class='num'>Max</th></tr>")
        for o in outl[:8]:
            parts.append(
                f"<tr><td>{_esc(o.get('code'))}</td>"
                f"<td class='num'>{int(o.get('n') or 0):,}</td>"
                f"<td class='num'>{int(o.get('outliers') or 0):,}</td>"
                f"<td class='num'>{_fmt_money(o.get('median'))}</td>"
                f"<td class='num'>{_fmt_money(o.get('max'))}</td></tr>")
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

    pq = sc.get("payer_quality") or []
    if pq:
        parts.append("<h2>Quality by payer</h2><table>"
                     "<tr><th>Payer</th><th class='num'>Rows</th>"
                     "<th class='num'>Flagged</th><th class='num'>Clean %"
                     "</th><th>Top rules</th></tr>")
        for p in pq[:10]:
            rules_txt = ", ".join(
                f"{t['rule']} ({t['n']})" for t in (p.get("top_rules") or []))
            parts.append(f"<tr><td>{_esc(p['payer'])}</td>"
                         f"<td class='num'>{int(p['rows']):,}</td>"
                         f"<td class='num'>{int(p['flagged']):,}</td>"
                         f"<td class='num'>{p['clean_pct']}%</td>"
                         f"<td class='small'>{_esc(rules_txt)}</td></tr>")
        parts.append("</table>")

    claims = sc.get("claims") or {}
    if claims.get("n_claims"):
        ch = claims.get("charge") or {}
        parts.append("<h2>Claim rollup</h2><table>"
                     "<tr><th>Metric</th><th class='num'>Value</th></tr>"
                     f"<tr><td>Distinct claims ({_esc(claims.get('column'))})"
                     f"</td><td class='num'>{int(claims['n_claims']):,}"
                     "</td></tr>"
                     f"<tr><td>Lines per claim (avg / max)</td>"
                     f"<td class='num'>{claims.get('avg_lines')} / "
                     f"{claims.get('max_lines')}</td></tr>")
        if ch:
            parts.append(
                f"<tr><td>Per-claim charge (median / mean / max)</td>"
                f"<td class='num'>${ch.get('median'):,.2f} / "
                f"${ch.get('mean'):,.2f} / ${ch.get('max'):,.2f}</td></tr>")
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

"""Five-step guided onboarding wizard (Prompt 26).

An associate opens ``/new-deal``, types a hospital name, drag-drops
seller files, and lands on the Bloomberg workbench three minutes
later. All five steps are server-rendered HTML pages — no SPA, no
framework, same stdlib pattern as every other RCM-MC UI.

State flow between steps:

- **Step 1 → 2**: `POST /api/deals/wizard/select` with the chosen CCN;
  the server runs ``auto_populate`` and stores the result in a
  process-local session map keyed by ``deal_id``. Redirect to Step 2
  with ``?deal_id=...``.
- **Step 2 → 3**: Continue button carries the ``deal_id`` forward.
- **Step 3**: files are uploaded to ``/api/deals/<id>/upload``
  (already wired in Prompt 25); the results are merged into the same
  session map so Step 4 can render totals.
- **Step 4 → 5**: `POST /api/deals/wizard/launch` triggers
  `build_analysis_packet` (with ``auto_populated`` + extracted
  metrics threaded through). Redirect to ``/analysis/<deal_id>``.

The in-memory session map is a deliberate choice: the whole wizard
takes under 10 minutes of associate time, and a process restart
during onboarding is an edge case. A Redis-style store would be
warranted when multi-process deployments become real.
"""
from __future__ import annotations

import html
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── In-process wizard session ──────────────────────────────────────

@dataclass
class WizardSession:
    """Per-deal state accumulated across the five steps."""
    deal_id: str
    name: str = ""
    ccn: str = ""
    state: str = ""
    profile: Dict[str, Any] = field(default_factory=dict)
    financials: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    utilization: Dict[str, Any] = field(default_factory=dict)
    benchmark_metrics: Dict[str, float] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    coverage_pct: float = 0.0
    summary: str = ""
    # Accumulated extracted metrics from uploaded files. Keyed by
    # metric_key → latest value the analyst confirmed.
    extracted: Dict[str, float] = field(default_factory=dict)
    uploaded_files: List[str] = field(default_factory=list)


# Process-local session store. Lock gates writes so concurrent
# browsers on the same deal_id don't stomp on each other's state.
_SESSIONS: Dict[str, WizardSession] = {}
_SESSIONS_LOCK = threading.Lock()


def save_session(session: WizardSession) -> None:
    with _SESSIONS_LOCK:
        _SESSIONS[session.deal_id] = session


def load_session(deal_id: str) -> Optional[WizardSession]:
    with _SESSIONS_LOCK:
        return _SESSIONS.get(deal_id)


def clear_session(deal_id: str) -> None:
    with _SESSIONS_LOCK:
        _SESSIONS.pop(deal_id, None)


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


# ── Shared wizard chrome ───────────────────────────────────────────

_WIZARD_CSS = """
body.wizard { margin:0; padding:0; background:#f5f1ea; color:#1a2332;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
  font-size: 14px; line-height: 1.5; }
.wizard .skip-link { position:absolute; left:16px; top:-48px; z-index:1000;
  background:#0b2341; color:#fff; padding:10px 14px; border-radius:4px;
  text-decoration:none; font-weight:600; }
.wizard .skip-link:focus { top:16px; }
.wizard .wrap { max-width:960px; margin:0 auto; padding:32px 24px; }
.wizard .steps { display:flex; gap:6px; margin-bottom:24px;
  font-size: 11px; text-transform:uppercase; letter-spacing:.08em; }
.wizard .steps .step { padding:6px 12px; border:1px solid #d6cfc3;
  border-radius:3px; color:#7a8699; }
.wizard .steps .step.active { background:#0b2341; color:#fff;
  border-color:#0b2341; }
.wizard h1 { font-size: 22px; font-weight:600; margin: 0 0 6px; }
.wizard .sub { color:#465366; margin-bottom: 24px; font-size: 13px; }
.wizard .card { background:#ffffff; border:1px solid #d6cfc3;
  padding:18px; border-radius:4px; margin-bottom:16px; }
.wizard .match-card { background:#f5f1ea; border:1px solid #d6cfc3;
  padding:12px 14px; margin-bottom:8px; cursor:pointer;
  border-radius:3px; transition:border-color 0.1s; }
.wizard .match-card:hover { border-color:#2fb3ad; }
.wizard .match-card:focus-visible { border-color:#2fb3ad; outline:3px solid #2fb3ad; outline-offset:2px; }
.wizard .match-name { font-weight:600; }
.wizard .match-meta { color:#465366; font-size:12px; margin-top:2px; }
.wizard .match-conf { float:right; color:#0a8a5f;
  font-family: "JetBrains Mono", monospace; }
.wizard input[type=text], .wizard input[type=number], .wizard input[type=search] {
  background:#ffffff; color:#1a2332; border:1px solid #d6cfc3;
  padding:8px 12px; font-size:14px; border-radius:3px;
  font-family:inherit; width:100%; box-sizing:border-box; }
.wizard input[type=file] { color:#1a2332; padding:8px 0; }
.wizard .btn { background:#0b2341; color:#fff; border:none;
  padding:10px 18px; border-radius:3px; cursor:pointer;
  font-weight:600; font-size:13px; }
.wizard .btn.secondary { background:#ffffff; border:1px solid #d6cfc3;
  color:#1a2332; }
.wizard .btn:hover { background:#132e53; }
.wizard .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.wizard .field-row { display:grid; grid-template-columns:180px 1fr auto;
  gap:8px; padding:4px 0; border-bottom:1px solid #d6cfc3;
  font-size:13px; align-items:baseline; }
.wizard .source-pill { background:#d6cfc3; color:#465366;
  font-size:10px; padding:1px 6px; border-radius:2px;
  font-family: "JetBrains Mono", monospace; text-transform: uppercase;
  letter-spacing:.04em; }
.wizard .gap-row { display:grid; grid-template-columns:40px 1fr;
  gap:10px; padding:6px 0; border-bottom:1px solid #d6cfc3;
  font-size:12px; }
.wizard .gap-rank { color:#b8732a; font-family: "JetBrains Mono", monospace; }
.wizard .gap-why { color:#465366; font-size:11px; margin-top:2px; }
.wizard .bar { background:#ece6db; height:6px; border-radius:3px;
  overflow:hidden; margin-top:6px; }
.wizard .bar > div { background:#0a8a5f; height:100%; }
.wizard .grade-A { color:#0a8a5f; }
.wizard .grade-B { color:#2fb3ad; }
.wizard .grade-C { color:#b8732a; }
.wizard .grade-D { color:#b5321e; }
.wizard .pill { display:inline-block; padding:2px 8px;
  font-size:11px; border-radius:2px; background:#d6cfc3;
  color:#465366; margin-right:6px; text-transform:uppercase;
  letter-spacing: 0.04em; }
.wizard .empty-hint { color:#465366; padding:8px; font-size:12px; }
.wizard hr { border:none; border-top:1px solid #d6cfc3; margin:16px 0; }
.wizard a:focus-visible, .wizard button:focus-visible,
.wizard input:focus-visible { outline:3px solid #2fb3ad; outline-offset:2px; }
"""


def _render_step_nav(current: int) -> str:
    labels = [
        "Find hospital", "Pre-fill", "Upload files",
        "Review", "Launch",
    ]
    parts = []
    for i, label in enumerate(labels, start=1):
        cls = "step active" if i == current else "step"
        parts.append(f'<div class="{cls}">{i}. {label}</div>')
    return f'<nav class="steps" aria-label="Wizard progress">{"".join(parts)}</nav>'


def _shell(body: str, *, title: str = "New Deal", step: int = 1) -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{_esc(title)} · RCM-MC</title>'
        f'<style>{_WIZARD_CSS}</style></head>'
        '<body class="wizard"><a class="skip-link" href="#main-content">'
        'Skip to content</a><div class="wrap">'
        + _render_step_nav(step)
        + '<main id="main-content" tabindex="-1">' + body + '</main>'
        + '</div></body></html>'
    )


# ── Step 1 — find ──────────────────────────────────────────────────

def render_step1(query: str = "") -> str:
    """Search box + live results rendered via ``fetch()`` to
    ``/api/data/hospitals``."""
    prefill_query = _esc(query)
    body = f"""
    <h1>Step 1 — Find your hospital</h1>
    <div class="sub">Type a hospital name, a 6-digit CCN, or "Name, ST".
      We'll look it up in HCRIS + Care Compare + IRS 990.</div>
    <div class="card">
      <input type="search" id="wiz-search" placeholder="e.g. Mercy Regional, CA"
             autocomplete="off" value="{prefill_query}"/>
      <div id="wiz-matches" style="margin-top:12px;" aria-live="polite"
           aria-busy="false" aria-label="Search results"></div>
      <div class="empty-hint" id="wiz-hint" role="status"
           aria-live="polite" aria-atomic="true">Type at least 3 characters to search.</div>
    </div>
    <form method="POST" action="/new-deal/manual" class="card">
      <div style="font-weight:600;margin-bottom:8px;">Don't see your hospital?</div>
      <div class="grid2">
        <label>Name<input type="text" name="name" required></label>
        <label>State (2-letter)<input type="text" name="state" maxlength="2"></label>
        <label>Bed count<input type="number" name="bed_count" min="1"></label>
        <label>Medicare %<input type="number" step="0.01" name="medicare_pct"></label>
        <label>Medicaid %<input type="number" step="0.01" name="medicaid_pct"></label>
        <label>Commercial %<input type="number" step="0.01" name="commercial_pct"></label>
      </div>
      <div style="margin-top:12px;">
        <button class="btn secondary" type="submit">Continue with manual entry →</button>
      </div>
    </form>
    <script>
      (function() {{
        const input = document.getElementById('wiz-search');
        const out = document.getElementById('wiz-matches');
        const hint = document.getElementById('wiz-hint');
        let timer = null;
        function fmtCard(m) {{
          const safe = (s) => (s == null ? '' :
            String(s).replace(/[&<>"']/g, c =>
              ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])));
          return `<div class="match-card" data-ccn="${{safe(m.ccn)}}"
                      role="button" tabindex="0"
                      aria-label="Select ${{safe(m.name)}} in ${{safe(m.city)}} ${{safe(m.state)}}">
                    <span class="match-conf">${{(m.confidence*100).toFixed(0)}}%</span>
                    <div class="match-name">${{safe(m.name)}}</div>
                    <div class="match-meta">CCN ${{safe(m.ccn)}} · ${{safe(m.city)}} ${{safe(m.state)}}
                      · ${{(m.bed_count||0)}} beds
                      ${{m.system_affiliation ? '· ' + safe(m.system_affiliation) : ''}}</div>
                  </div>`;
        }}
        function submitSelection(card) {{
          const ccn = card.dataset.ccn;
          const form = document.createElement('form');
          form.method = 'POST';
          form.action = '/api/deals/wizard/select';
          const input = document.createElement('input');
          input.type = 'hidden'; input.name = 'ccn'; input.value = ccn;
          form.appendChild(input);
          document.body.appendChild(form); form.submit();
        }}
        function search() {{
          const q = input.value.trim();
          if (q.length < 3) {{
            out.innerHTML = '';
            out.setAttribute('aria-busy', 'false');
            hint.textContent = 'Type at least 3 characters to search.';
            return;
          }}
          out.setAttribute('aria-busy', 'true');
          fetch('/api/data/hospitals?q=' + encodeURIComponent(q) + '&limit=5')
            .then(r => r.json())
            .then(d => {{
              const ms = d.matches || [];
              out.setAttribute('aria-busy', 'false');
              if (!ms.length) {{ out.innerHTML = ''; hint.textContent = 'No matches — try a different spelling or CCN.'; return; }}
              hint.textContent = 'Found ' + ms.length + ' match' + (ms.length === 1 ? '' : 'es') + '. Click a match to pre-fill this deal.';
              out.innerHTML = ms.map(fmtCard).join('');
              out.querySelectorAll('.match-card').forEach(card => {{
                card.addEventListener('click', () => submitSelection(card));
                card.addEventListener('keydown', (e) => {{
                  if (e.key === 'Enter' || e.key === ' ') {{
                    e.preventDefault();
                    submitSelection(card);
                  }}
                }});
              }});
            }})
            .catch(() => {{
              out.innerHTML = '';
              out.setAttribute('aria-busy', 'false');
              hint.textContent = 'Search failed — try again.';
            }});
        }}
        input.addEventListener('input', () => {{
          if (timer) clearTimeout(timer);
          timer = setTimeout(search, 300);
        }});
        if (input.value) search();
      }})();
    </script>
    """
    return _shell(body, title="Find Hospital", step=1)


# ── Step 2 — pre-fill ──────────────────────────────────────────────

def render_step2(session: WizardSession) -> str:
    """Two-column "populated" / "still needed" summary."""
    populated_groups = [
        ("Profile", session.profile),
        ("Financial", session.financials),
        ("Quality", session.quality),
        ("Utilization", session.utilization),
    ]
    populated_html: List[str] = []
    source_by_field: Dict[str, Dict[str, Any]] = {
        s["field"]: s for s in session.sources
    }
    for label, bucket in populated_groups:
        if not bucket:
            continue
        rows: List[str] = []
        for k, v in sorted(bucket.items()):
            src = source_by_field.get(k)
            src_pill = (
                f'<span class="source-pill">{_esc(src["source"])}'
                + (f' · {_esc(src["period"])}' if src and src.get("period") else '')
                + '</span>'
            ) if src else ''
            value_str = (
                f"{float(v):,.2f}" if isinstance(v, (int, float))
                else _esc(v)
            )
            rows.append(
                f'<div class="field-row">'
                f'<div>{_esc(k)}</div>'
                f'<div style="font-family:\'JetBrains Mono\',monospace;">'
                f'{value_str}</div>'
                f'<div>{src_pill}</div></div>'
            )
        populated_html.append(
            f'<div style="margin-bottom:14px;">'
            f'<div style="font-weight:600;margin-bottom:6px;color:#0a8a5f;">'
            f'✓ {_esc(label)} ({len(bucket)})</div>'
            + "".join(rows) + '</div>'
        )
    populated_block = (
        "".join(populated_html)
        or '<div class="empty-hint">Nothing populated from public sources.</div>'
    )

    gap_rows: List[str] = []
    for g in session.gaps[:20]:
        gap_rows.append(
            f'<div class="gap-row">'
            f'<div class="gap-rank">#{g["ebitda_sensitivity_rank"]}</div>'
            f'<div><div>{_esc(g["display_name"])}</div>'
            f'<div class="gap-why">{_esc(g.get("why_it_matters") or "")}</div>'
            f'</div></div>'
        )
    gaps_block = (
        "".join(gap_rows)
        or '<div class="empty-hint">No gaps — every registry metric is populated.</div>'
    )

    pct = max(0.0, min(100.0, float(session.coverage_pct)))
    body = f"""
    <h1>Step 2 — Here's what we found</h1>
    <div class="sub">Populated {pct:.1f}% of the 38-metric registry from
      public sources. Review, then keep going.</div>
    <div class="grid2">
      <div class="card">
        <div style="font-weight:600;margin-bottom:10px;">
          Populated fields
        </div>
        {populated_block}
      </div>
      <div class="card">
        <div style="font-weight:600;margin-bottom:10px;">
          Still needed ({len(session.gaps)})
        </div>
        <div style="font-size:12px;color:#465366;margin-bottom:8px;">
          Sorted by EBITDA sensitivity. Top gaps are the highest-value
          things to ask the seller for.
        </div>
        {gaps_block}
      </div>
    </div>
    <div class="card">
      <div>Coverage: <span style="font-family:'JetBrains Mono',monospace;">{pct:.1f}%</span></div>
      <div class="bar"><div style="width:{pct:.1f}%;"></div></div>
    </div>
    <form method="GET" action="/new-deal/step3" style="display:inline;">
      <input type="hidden" name="deal_id" value="{_esc(session.deal_id)}"/>
      <button class="btn" type="submit">Continue — upload seller files →</button>
    </form>
    <form method="GET" action="/new-deal/step4" style="display:inline;margin-left:8px;">
      <input type="hidden" name="deal_id" value="{_esc(session.deal_id)}"/>
      <button class="btn secondary" type="submit">Skip to Review →</button>
    </form>
    """
    return _shell(body, title="Pre-fill Review", step=2)


# ── Step 3 — upload ────────────────────────────────────────────────

def render_step3(session: WizardSession) -> str:
    uploaded_html: List[str] = []
    for fn in session.uploaded_files:
        uploaded_html.append(f'<div class="pill">{_esc(fn)}</div>')
    extracted_count = len(session.extracted)
    deal_id = _esc(session.deal_id)
    body = f"""
    <h1>Step 3 — Upload seller data</h1>
    <div class="sub">Drag and drop the files you got from the seller —
      Excel, CSV, or TSV. We'll extract denial rates, AR aging, payer
      mix, and collections automatically.</div>
    <form method="POST" enctype="multipart/form-data"
          action="/new-deal/upload?deal_id={deal_id}" class="card">
      <input type="file" name="file" multiple
             accept=".xlsx,.xls,.xlsm,.csv,.tsv,.txt"/>
      <div style="margin-top:12px;">
        <button class="btn" type="submit">Upload &amp; extract</button>
      </div>
    </form>
    <div class="card">
      <div style="font-weight:600;margin-bottom:8px;">
        Files processed so far ({len(session.uploaded_files)})
      </div>
      <div>{''.join(uploaded_html) or '<div class="empty-hint">No uploads yet.</div>'}</div>
      <div style="margin-top:8px;font-size:12px;color:#465366;">
        Extracted {extracted_count} metric(s) total.
      </div>
    </div>
    <form method="GET" action="/new-deal/step4" style="display:inline;">
      <input type="hidden" name="deal_id" value="{deal_id}"/>
      <button class="btn" type="submit">Continue to Review →</button>
    </form>
    """
    return _shell(body, title="Upload Data", step=3)


# ── Step 4 — review + override ────────────────────────────────────

def _grade_for(coverage: float, extracted_count: int) -> str:
    """Coarse grade forecast: A ≥ 80% coverage, B ≥ 60%, C ≥ 40%, else D.
    Extracted metrics boost coverage effectively."""
    adjusted = coverage + (extracted_count * 2.5)
    if adjusted >= 80:
        return "A"
    if adjusted >= 60:
        return "B"
    if adjusted >= 40:
        return "C"
    return "D"


def render_step4(session: WizardSession) -> str:
    deal_id = _esc(session.deal_id)
    grade = _grade_for(session.coverage_pct, len(session.extracted))

    # Up to 10 editable fields — the top gaps + any auto-populated
    # metric with a registered RCM key.
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        registry = RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        registry = {}
    override_candidates: List[Dict[str, Any]] = []
    # First: anything we extracted — the analyst probably wants to
    # confirm those.
    for k, v in session.extracted.items():
        override_candidates.append({
            "metric_key": k, "value": v,
            "display_name": (registry.get(k) or {}).get("display_name", k),
            "rank": (registry.get(k) or {}).get(
                "ebitda_sensitivity_rank", 99,
            ),
        })
    # Then: top gaps by EBITDA sensitivity.
    existing_keys = {c["metric_key"] for c in override_candidates}
    for g in session.gaps:
        if g["metric_key"] in existing_keys:
            continue
        override_candidates.append({
            "metric_key": g["metric_key"],
            "value": None,
            "display_name": g["display_name"],
            "rank": g["ebitda_sensitivity_rank"],
        })
    override_candidates.sort(key=lambda c: c["rank"])
    override_candidates = override_candidates[:10]

    rows: List[str] = []
    for c in override_candidates:
        val = c["value"]
        val_str = f"{float(val):.2f}" if isinstance(val, (int, float)) else ""
        rows.append(
            f'<div class="field-row">'
            f'<div>{_esc(c["display_name"])}</div>'
            f'<input type="number" step="0.01" name="override_{_esc(c["metric_key"])}" '
            f'value="{val_str}"/>'
            f'<div style="color:#7a8699;font-size:11px;">#{c["rank"]}</div>'
            f'</div>'
        )
    overrides_block = "".join(rows) or (
        '<div class="empty-hint">No editable fields.</div>'
    )

    n_observed = len(session.extracted)
    n_auto = len(session.benchmark_metrics) + len(session.financials)
    coverage_pct = max(0.0, min(100.0, float(session.coverage_pct)))

    body = f"""
    <h1>Step 4 — Review &amp; Launch</h1>
    <div class="sub">Confirm the numbers, pick a confidence level, and
      build your analysis.</div>

    <div class="card">
      <div style="display:flex;align-items:center;gap:20px;">
        <div>
          <div style="font-size:42px;font-weight:700;"
               class="grade-{grade}">{grade}</div>
          <div class="empty-hint">projected grade</div>
        </div>
        <div style="flex:1;">
          <div><strong>{_esc(session.name or session.deal_id)}</strong>
            <span class="pill">{_esc(session.ccn or "manual")}</span>
            <span class="pill">{_esc(session.state or "??")}</span></div>
          <div class="empty-hint" style="margin-top:4px;">
            {n_observed} extracted · {n_auto} auto-populated · coverage
            {coverage_pct:.1f}% of 38-metric registry
          </div>
          <div class="bar" style="margin-top:6px;">
            <div style="width:{coverage_pct:.1f}%"></div>
          </div>
        </div>
      </div>
    </div>

    <form method="POST" action="/api/deals/wizard/launch" class="card">
      <input type="hidden" name="deal_id" value="{deal_id}"/>
      <div style="font-weight:600;margin-bottom:10px;">
        Editable overrides (top {len(override_candidates)})
      </div>
      <div style="font-size:12px;color:#465366;margin-bottom:10px;">
        Adjust any pre-filled value; leave blank to keep the
        auto-populated / registry default.
      </div>
      {overrides_block}
      <hr/>
      <label style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" name="run_mc" {'checked' if grade in ('A','B') else ''}/>
        Run Monte Carlo simulation
        <span class="empty-hint">
          (~30 s with MC, ~5 s without)
        </span>
      </label>
      <div style="margin-top:16px;">
        <button class="btn" type="submit">Build analysis →</button>
      </div>
    </form>
    """
    return _shell(body, title="Review & Launch", step=4)


# ── Step 5 — launched ─────────────────────────────────────────────

def render_step5(session: WizardSession) -> str:
    deal_id = _esc(session.deal_id)
    body = f"""
    <h1>Step 5 — Your analysis is ready</h1>
    <div class="sub">Packet built from {len(session.extracted)} extracted,
      {len(session.benchmark_metrics)} auto-populated metrics + the 38-metric
      registry. Click any number in the workbench to see where it came from.
    </div>
    <div class="card">
      <a class="btn" href="/analysis/{deal_id}">Open the workbench →</a>
    </div>
    <script>
      // Auto-redirect after a short pause for feel-of-speed.
      setTimeout(function() {{
        window.location.href = "/analysis/{deal_id}";
      }}, 600);
    </script>
    """
    return _shell(body, title="Analysis Ready", step=5)


# ── Handler-side helpers ─────────────────────────────────────────

def start_session_from_auto_populate(
    deal_id: str, auto_populate_result,
) -> WizardSession:
    """Seed a :class:`WizardSession` from an ``AutoPopulateResult``.

    Used by the ``/api/deals/wizard/select`` route after the server
    calls ``auto_populate``. Stores the session in the module map
    and returns it for the caller to inspect.
    """
    sel = auto_populate_result.selected
    session = WizardSession(
        deal_id=deal_id,
        name=(sel.name if sel else ""),
        ccn=(sel.ccn if sel else ""),
        state=(sel.state if sel else ""),
        profile=dict(auto_populate_result.profile),
        financials=dict(auto_populate_result.financials),
        quality=dict(auto_populate_result.quality),
        utilization=dict(auto_populate_result.utilization),
        benchmark_metrics=dict(auto_populate_result.benchmark_metrics),
        sources=[s.to_dict() for s in auto_populate_result.sources],
        gaps=[g.to_dict() for g in auto_populate_result.gaps],
        coverage_pct=float(auto_populate_result.coverage_pct),
        summary=auto_populate_result.summary,
    )
    save_session(session)
    return session


def start_session_manual(
    deal_id: str, *, name: str, state: str = "",
    bed_count: Optional[int] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> WizardSession:
    """Seed a session from manual Step-1 entry (no HCRIS hit)."""
    profile: Dict[str, Any] = {"name": name}
    if state:
        profile["state"] = state
    if bed_count:
        profile["bed_count"] = bed_count
    if payer_mix:
        profile["payer_mix"] = payer_mix
    session = WizardSession(
        deal_id=deal_id, name=name, state=state or "",
        profile=profile,
    )
    save_session(session)
    return session


def merge_extraction(
    deal_id: str, extraction_dict: Dict[str, Any], filename: str,
) -> Optional[WizardSession]:
    """Merge an ``ExtractionResult.to_dict()`` into the session.

    Keeps the latest-period value per metric. Appends the filename
    to ``uploaded_files`` so Step 3 can show what's been processed.
    """
    session = load_session(deal_id)
    if session is None:
        return None
    session.uploaded_files.append(filename)
    for metric_key, extractions in (extraction_dict.get("metrics") or {}).items():
        if not extractions:
            continue
        # Prefer the latest period (sort descending).
        sorted_ex = sorted(
            extractions,
            key=lambda ex: str(ex.get("period") or ""),
            reverse=True,
        )
        val = sorted_ex[0].get("value")
        if val is None:
            continue
        try:
            session.extracted[metric_key] = float(val)
        except (TypeError, ValueError):
            continue
    save_session(session)
    return session

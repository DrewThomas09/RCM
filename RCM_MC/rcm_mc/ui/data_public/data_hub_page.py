"""Data Hub — `/data-hub`, the central CMS / public-API research console.

This is the front door for the "reliable place of information and CMS data"
mission: one console that shows **every** data source the desk can pull,
whether it is cached locally right now, how fresh that cache is, and — the
part that used to only be possible from a terminal — a one-click way to
*fill* it.

Two data worlds are unified here (see ``ARCHITECTURE.md`` /
``docs`` for the full split):

* **Public-API estate** — the repo-root ``connectors/`` estate (openFDA,
  CMS Coverage, NPI Registry, CMS Open Data, Provider Data, Open Payments,
  Medicaid, Healthcare.gov, CDC, HRSA, Census ACS, NIH RePORTER, OIG LEIE,
  BLS QCEW, healthdata.gov, ICD-10). Read-only through
  ``data_public.connector_estate``; every count/vintage is computed live
  from the ingested SQLite files — nothing here is illustrative.
* **In-app CMS benchmark cache** — the seven ``data.data_refresh`` sources
  (HCRIS, Care Compare, utilization, IRS 990, POS, general, HRRP) cached in
  the portfolio DB. Freshness read from ``data_source_status``.

Everything degrades to an honest empty state when the estate is absent
(wheel installs don't ship it) — never a 500, never a fake number.

Filling data (``can_warm=True``, admin only) posts to
``/api/data-hub/warm/<connector>`` which runs the estate refresh as a
background job; the page polls ``/api/jobs/<id>`` and reloads when done.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROUTE = "/data-hub"


# ── freshness ────────────────────────────────────────────────────────
def _parse_ts(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    # Vintages come back as ``ingested_at`` / ``fetched_at`` — usually full
    # ISO, occasionally just a date. Try both without raising.
    for parser in (
        lambda x: datetime.fromisoformat(x),
        lambda x: datetime.strptime(x[:10], "%Y-%m-%d"),
    ):
        try:
            ts = parser(s)
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _freshness_chip(raw: Optional[str], *, empty_label: str = "not cached") -> str:
    ts = _parse_ts(raw)
    if ts is None:
        return (
            '<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
            'background:#ece5d6;color:#7a8699;font-size:11px;font-family:'
            f'JetBrains Mono,monospace;">{_html.escape(empty_label)}</span>'
        )
    days = (datetime.now(timezone.utc) - ts).days
    if days <= 7:
        bg, fg, word = "#d9ece2", "#0a6a48", "fresh"
    elif days <= 45:
        bg, fg, word = "#f2e7d1", "#7a4c16", "aging"
    else:
        bg, fg, word = "#f2ded7", "#8a2a1a", "stale"
    label = "today" if days <= 0 else f"{days}d ago"
    return (
        f'<span title="{word} · last ingested {_html.escape(ts.date().isoformat())}" '
        f'style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{bg};color:{fg};font-size:11px;font-weight:500;'
        f'font-family:JetBrains Mono,monospace;">{label}</span>'
    )


def _num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


# ── estate (public-API) section ──────────────────────────────────────
def _estate_row(summary: Dict[str, Any], rows: int, vintage: Optional[str],
                hint: Dict[str, Any], can_warm: bool) -> str:
    name = str(summary.get("connector", ""))
    label = str(summary.get("label", name))
    n_ds = int(summary.get("n_datasets", 0) or 0)
    base = ""
    urls = summary.get("base_urls") or []
    if urls:
        base = str(urls[0])
    warm = rows > 0
    status_dot = (
        '<span style="color:#0a8a5f;">●</span> cached' if warm
        else '<span style="color:#b58a3a;">○</span> empty'
    )
    # Action cell: a Warm button for admins, else the copy-ready command.
    if can_warm and hint.get("planned"):
        action = (
            f'<button class="dh-warm" data-conn="{_html.escape(name)}" '
            'style="background:var(--sc-navy,#0b2341);color:#fff;border:none;'
            'padding:5px 12px;border-radius:4px;font-size:12px;cursor:pointer;">'
            f'{"Refresh" if warm else "Warm"}</button>'
        )
    else:
        cmd = str(hint.get("command", "")) or (
            f"python -m connectors.{name}.cli")
        action = (
            f'<code style="font-size:10.5px;color:#5a6472;white-space:nowrap;">'
            f'{_html.escape(cmd)}</code>'
        )
    return (
        f'<tr data-conn="{_html.escape(name)}">'
        f'<td style="font-weight:600;">{_html.escape(label)}'
        f'<div style="font-size:10.5px;color:#8a94a3;font-family:'
        f'JetBrains Mono,monospace;">{_html.escape(base)}</div></td>'
        f'<td style="text-align:right;font-variant-numeric:tabular-nums;'
        f'color:#5a6472;">{n_ds}</td>'
        f'<td style="text-align:right;font-variant-numeric:tabular-nums;'
        f'font-weight:600;">{_num(rows) if warm else "—"}</td>'
        f'<td>{_freshness_chip(vintage)}</td>'
        f'<td style="font-size:12px;color:#5a6472;">{status_dot}</td>'
        f'<td class="dh-job" style="font-size:12px;color:#7a8699;">—</td>'
        f'<td style="text-align:right;">{action}</td>'
        f'</tr>'
    )


def _estate_section(can_warm: bool) -> str:
    from ...data_public import connector_estate as ce

    if not ce.estate_available():
        from rcm_mc.ui._chartis_kit import ck_empty_state
        why = ce.load_failure()
        body = (
            f"The connectors/ estate failed to load: {why}."
            if why else
            "This deployment has no repo-root connectors/ estate on disk. "
            "Check out the full repository (the estate lives beside RCM_MC), "
            "then fill it: python -m connectors.cli refresh --db var/connectors."
        )
        return (
            '<section style="margin-top:26px;">'
            + _section_head("Public-API estate",
                            "16 healthcare data connectors — unavailable")
            + ck_empty_state("Public-API estate not available", body,
                             eyebrow="PUBLIC DATA", icon="⛁", tone="warning")
            + '</section>'
        )

    summaries = ce.connectors_summary()
    ingested = ce.ingested_counts()
    vintages = ce.connector_vintages()
    # Sort cached-first, then by dataset breadth — the warm sources are what
    # a researcher reaches for, so they lead.
    summaries.sort(key=lambda s: (
        -(ingested.get(str(s.get("connector")), 0) > 0),
        -int(s.get("n_datasets", 0) or 0),
        str(s.get("label", "")),
    ))
    rows_html = []
    for s in summaries:
        name = str(s.get("connector", ""))
        rows_html.append(_estate_row(
            s, int(ingested.get(name, 0) or 0), vintages.get(name),
            ce.ingest_hint(name), can_warm))

    warm_all = ""
    if can_warm:
        warm_all = (
            '<button class="dh-warm" data-conn="all" '
            'style="background:#155752;color:#fff;border:none;padding:7px 16px;'
            'border-radius:5px;font-size:13px;font-weight:600;cursor:pointer;'
            'margin-bottom:12px;">Warm every connector</button> '
            '<span style="font-size:12px;color:#7a8699;">polls in the '
            'background · max 1 warm per source per hour</span>'
        )
    else:
        warm_all = (
            '<p style="font-size:12px;color:#7a8699;margin:0 0 12px;">'
            'Sign in as an admin to warm sources from here, or run the '
            'per-connector command shown in the Action column.</p>'
        )

    table = (
        '<div style="overflow-x:auto;">'
        '<table class="wc-table" style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:2px solid #d8cfbf;text-align:left;'
        'font-size:11px;text-transform:uppercase;letter-spacing:0.05em;'
        'color:#7a8699;">'
        '<th style="padding:6px 8px;">API / connector</th>'
        '<th style="padding:6px 8px;text-align:right;">Datasets</th>'
        '<th style="padding:6px 8px;text-align:right;">Rows cached</th>'
        '<th style="padding:6px 8px;">Freshness</th>'
        '<th style="padding:6px 8px;">Status</th>'
        '<th style="padding:6px 8px;">Job</th>'
        '<th style="padding:6px 8px;text-align:right;">Action</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    return (
        '<section style="margin-top:26px;">'
        + _section_head("Public-API estate",
                        f"{len(summaries)} healthcare data connectors · "
                        "cached-first")
        + warm_all + table
        + '</section>'
    )


# ── in-app CMS benchmark cache (World A) ──────────────────────────────
def _world_a_section(db_path: Optional[str]) -> str:
    from rcm_mc.ui._chartis_kit import ck_empty_state
    try:
        from ...data.data_refresh import KNOWN_SOURCES, get_status
        from ...portfolio.store import PortfolioStore
        store = PortfolioStore(db_path) if db_path else None
        existing = {r["source_name"]: r for r in get_status(store)} if store else {}
    except Exception:  # noqa: BLE001
        return (
            '<section style="margin-top:26px;">'
            + _section_head("In-app CMS benchmark cache",
                            "HCRIS · Care Compare · utilization · IRS 990 + more")
            + ck_empty_state(
                "Benchmark status not loaded yet",
                "Run rcm-mc data refresh once (or use the Data refresh page) "
                "to populate the data_source_status table.",
                eyebrow="PUBLIC DATA",
                cta_label="Open data refresh", cta_href="/data/refresh")
            + '</section>'
        )
    rows_html = []
    for name in KNOWN_SOURCES:
        st = existing.get(name, {})
        last = st.get("last_refresh_at")
        records = int(st.get("record_count") or 0)
        state = str(st.get("status") or "—")
        rows_html.append(
            f'<tr><td style="font-weight:600;">{_html.escape(name)}</td>'
            f'<td>{_freshness_chip(last, empty_label="never")}</td>'
            f'<td style="text-align:right;font-variant-numeric:tabular-nums;">'
            f'{_num(records)}</td>'
            f'<td style="font-size:12px;color:#5a6472;">{_html.escape(state)}</td>'
            f'</tr>'
        )
    table = (
        '<div style="overflow-x:auto;">'
        '<table class="wc-table" style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:2px solid #d8cfbf;text-align:left;'
        'font-size:11px;text-transform:uppercase;letter-spacing:0.05em;'
        'color:#7a8699;">'
        '<th style="padding:6px 8px;">Source</th>'
        '<th style="padding:6px 8px;">Freshness</th>'
        '<th style="padding:6px 8px;text-align:right;">Rows</th>'
        '<th style="padding:6px 8px;">Status</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
        '<p style="font-size:12px;color:#7a8699;margin-top:10px;">'
        'Refresh these from the dedicated '
        '<a href="/data/refresh" style="color:#155752;">Data refresh</a> page.</p>'
    )
    return (
        '<section style="margin-top:26px;">'
        + _section_head("In-app CMS benchmark cache",
                        f"{len(KNOWN_SOURCES)} sources cached in the portfolio DB")
        + table + '</section>'
    )


# ── research tools ───────────────────────────────────────────────────
_TOOLS = [
    ("National Data Catalog", "/national-data",
     "Every major U.S. national health database — HCUP/NEDS, MEPS, NHANES, "
     "SAMHSA, USRDS, SEER — with access model + how to get it."),
    ("Connector Estate", "/connector-estate",
     "Browse every dataset, search by id/table, sample rows + copy-ready queries."),
    ("NPI Cleaner", "/npi-cleaner",
     "Clean & enrich provider/claims files — Luhn checks, NPPES recovery, exports."),
    ("Market Scan", "/market-scan",
     "One-input county/state market brief off cached Census · CDC · HRSA · CMS."),
    ("Data Quality", "/data-quality",
     "Live certification: connected sources, row counts, null rates, freshness."),
    ("CMS Sources", "/cms-sources",
     "The public-source catalog: what each dataset is and where it comes from."),
    ("Data APIs", "/data-apis",
     "Reference table of every public API — auth, rate limits, docs links."),
]


def _tools_section() -> str:
    cards = []
    for title, href, desc in _TOOLS:
        cards.append(
            f'<a href="{href}" style="display:block;text-decoration:none;'
            'border:1px solid #ddd3c2;border-radius:8px;padding:14px 16px;'
            'background:#fbf8f1;color:inherit;transition:border-color .12s;">'
            f'<div style="font-weight:700;color:#0b2341;font-size:14px;">'
            f'{_html.escape(title)} <span style="color:#155752;">→</span></div>'
            f'<div style="font-size:12.5px;color:#5a6472;margin-top:4px;'
            f'line-height:1.4;">{_html.escape(desc)}</div>'
            f'<div style="font-size:10.5px;color:#8a94a3;margin-top:6px;'
            f'font-family:JetBrains Mono,monospace;">{_html.escape(href)}</div>'
            '</a>'
        )
    grid = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,'
        'minmax(240px,1fr));gap:12px;">' + "".join(cards) + '</div>'
    )
    return (
        '<section style="margin-top:26px;">'
        + _section_head("Research tools",
                        "jump into the real-data surfaces")
        + grid + '</section>'
    )


def _search_box() -> str:
    """Find-the-data entry point. GETs into the Connector Estate search
    (``/connector-estate?q=``), which resolves a query against every
    registered dataset id / table / endpoint across the estate — so a
    partner can go from "I need X" to the dataset in one step.
    """
    return (
        '<form action="/connector-estate" method="get" '
        'style="margin:16px 0 4px;display:flex;gap:8px;max-width:560px;">'
        '<input type="search" name="q" '
        'placeholder="Search all datasets — e.g. hospital, drug spending, NPI, wages…" '
        'aria-label="Search CMS and public datasets" '
        'style="flex:1;padding:9px 12px;border:1px solid #d8cfbf;border-radius:6px;'
        'font-size:13px;background:#fff;color:#1a2332;">'
        '<button type="submit" '
        'style="background:#155752;color:#fff;border:none;padding:9px 18px;'
        'border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">'
        'Find data</button></form>'
    )


def _section_head(title: str, sub: str) -> str:
    return (
        f'<div style="margin-bottom:10px;">'
        f'<h2 style="font-size:17px;color:#0b2341;margin:0;'
        f'font-family:Source Serif 4,Georgia,serif;">{_html.escape(title)}</h2>'
        f'<div style="font-size:12px;color:#7a8699;margin-top:2px;">'
        f'{_html.escape(sub)}</div></div>'
    )


# ── inline JS (warm submit + poll) ───────────────────────────────────
_WARM_JS = r"""
(function(){
  function poll(jobId, row){
    fetch('/api/jobs/'+encodeURIComponent(jobId),{credentials:'same-origin'})
      .then(function(r){return r.json();})
      .then(function(j){
        var cell = row ? row.querySelector('.dh-job') : null;
        function set(h){ if(cell) cell.innerHTML = h; }
        if(j.status==='queued'){ set('<span style="color:#7a8699;">● queued</span>'); setTimeout(function(){poll(jobId,row);},2500); }
        else if(j.status==='running'){ set('<span style="color:#b8732a;">● warming…</span>'); setTimeout(function(){poll(jobId,row);},2500); }
        else if(j.status==='done'){
          var res=j.result||{}; var w=res.rows_written; var msg = (typeof w==='number') ? ('✓ '+w.toLocaleString()+' rows') : '✓ done';
          set('<span style="color:#0a8a5f;">'+msg+'</span>');
          setTimeout(function(){window.location.reload();},1400);
        }
        else if(j.status==='failed'){ set('<span style="color:#b5321e;" title="'+((j.error||'').slice(0,120).replace(/"/g,'&quot;'))+'">✗ failed</span>'); reEnable(row); }
        else { set('<span style="color:#7a8699;">'+j.status+'</span>'); setTimeout(function(){poll(jobId,row);},2500); }
      })
      .catch(function(){ reEnable(row); });
  }
  function reEnable(row){ if(!row) return; var b=row.querySelector('.dh-warm'); if(b){ b.disabled=false; b.style.opacity='1'; } }
  document.addEventListener('click', function(e){
    var btn = e.target.closest('.dh-warm'); if(!btn || btn.disabled) return;
    var conn = btn.getAttribute('data-conn'); if(!conn) return;
    var row = btn.closest('tr');
    btn.disabled=true; btn.style.opacity='0.6';
    var cell = row ? row.querySelector('.dh-job') : null;
    if(cell) cell.innerHTML = '<span style="color:#7a8699;">● submitting…</span>';
    fetch('/api/data-hub/warm/'+encodeURIComponent(conn),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'}})
      .then(function(r){return r.json().then(function(j){return {status:r.status,body:j};});})
      .then(function(o){
        if(o.status===202 && o.body.job_id){ poll(o.body.job_id, row); }
        else if(o.status===429){ if(cell) cell.innerHTML='<span style="color:#b8732a;">rate limited ('+((o.body.detail||{}).retry_after_seconds||'?')+'s)</span>'; reEnable(row); }
        else if(o.status===403){ if(cell) cell.innerHTML='<span style="color:#b5321e;">admin only</span>'; reEnable(row); }
        else { if(cell) cell.innerHTML='<span style="color:#b5321e;">'+(o.body.error||'error')+'</span>'; reEnable(row); }
      })
      .catch(function(){ if(cell) cell.innerHTML='<span style="color:#b5321e;">network error</span>'; reEnable(row); });
  });
})();
"""


# ── public entry ─────────────────────────────────────────────────────
def render_data_hub(params: Optional[Dict[str, Any]] = None, *,
                    db_path: Optional[str] = None,
                    can_warm: bool = False) -> str:
    """Render the Data Hub console.

    ``can_warm`` gates the in-UI warm buttons (admin only — set by the
    server from the session role). ``db_path`` is the portfolio DB used to
    read in-app benchmark freshness; ``None`` degrades to an honest note.
    """
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_kpi_block, ck_page_explainer, ck_page_title,
    )
    from ...data_public import connector_estate as ce

    params = params or {}

    # ── live summary numbers (all real; degrade to 0 when estate absent) ──
    estate_ok = ce.estate_available()
    summaries = ce.connectors_summary() if estate_ok else []
    ingested = ce.ingested_counts() if estate_ok else {}
    n_conn = len(summaries)
    n_datasets = sum(int(s.get("n_datasets", 0) or 0) for s in summaries)
    n_warm = sum(1 for v in ingested.values() if v > 0)
    n_rows = sum(int(v) for v in ingested.values())

    meta = (f"{n_conn} public APIs · {n_datasets} datasets · "
            f"{n_warm} cached locally · {n_rows:,} rows")

    def _mn(v: str) -> str:
        return f'<span class="mn">{v}</span>'

    kpis = (
        ck_kpi_block("Public APIs", _mn(str(n_conn)),
                     "healthcare data connectors") +
        ck_kpi_block("Cached now", _mn(f"{n_warm}/{n_conn}"),
                     "warmed on this machine") +
        ck_kpi_block("Rows cached", _mn(_num(n_rows)),
                     "rows ingested locally") +
        ck_kpi_block("Datasets", _mn(str(n_datasets)),
                     "registered across the estate")
    )

    explainer = ck_page_explainer(
        "The central place to find and pull the CMS &amp; public-health data "
        "a model needs — before touching a single deal.",
        "Every source below is real: counts and freshness are computed live "
        "from what is cached on this machine, and nothing is illustrative. "
        "Warm a source to pull a polite slice from its public API, then "
        "browse or query it from the tools at the bottom.",
        source="connectors/ estate + portfolio benchmark cache",
    )

    body = (
        ck_page_title("Data Hub", eyebrow="Research · CMS & Public APIs",
                      meta=meta)
        + explainer
        + f'<div class="ck-kpi-grid" style="margin-top:14px;">{kpis}</div>'
        + _search_box()
        + _estate_section(can_warm)
        + _world_a_section(db_path)
        + _tools_section()
    )
    return chartis_shell(
        body, "Data Hub",
        active_nav=_ROUTE,
        subtitle=f"CMS & public-API research hub · {meta}",
        extra_js=_WARM_JS,
    )

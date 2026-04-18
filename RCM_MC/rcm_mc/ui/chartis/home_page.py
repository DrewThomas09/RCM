"""SeekingChartis Home — seven-panel partner landing.

Panels: pipeline funnel, active alerts, portfolio health distribution,
recent deals, upcoming deadlines, PE intelligence highlights (top-3
partner-review verdicts across the portfolio), corpus insights
(recent additions + top vintages).

Every panel is defensive: if a backend query fails the panel degrades
to an empty state rather than crashing the whole page.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
    ck_signal_badge,
)
from ._helpers import render_page_explainer
from ._sanity import render_number

_STAGES = ("Sourcing", "Screened", "IOI", "LOI", "Diligence", "IC", "Closed")


def _panel(title: str, body: str, *, code: str = "") -> str:
    code_html = (
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};'
        f'margin-left:8px;">{_html.escape(code)}</span>'
        if code else ""
    )
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">'
        f'{_html.escape(title)}{code_html}'
        f'</div>'
        f'<div style="padding:10px 12px;">{body}</div>'
        f'</div>'
    )


def _empty(msg: str) -> str:
    return (
        f'<div style="color:{P["text_faint"]};font-size:11px;'
        f'font-style:italic;padding:6px 0;">{_html.escape(msg)}</div>'
    )


def _pipeline_funnel(store: Any) -> str:
    try:
        deals = store.list_deals()
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else list(deals or [])
    except Exception:
        rows = []
    counts: Dict[str, int] = {s: 0 for s in _STAGES}
    other = 0
    for r in rows:
        stage = str(r.get("stage") or "").strip()
        if not stage:
            counts["Sourcing"] += 1
            continue
        matched = False
        for s in _STAGES:
            if stage.lower() == s.lower() or stage.lower().startswith(s.lower()):
                counts[s] += 1
                matched = True
                break
        if not matched:
            other += 1
    if not rows:
        return _empty("No deals in portfolio yet. Import from /new-deal.")
    total = sum(counts.values()) + other
    cells = []
    for s in _STAGES:
        n = counts[s]
        pct = (n / total * 100.0) if total else 0.0
        bar_w = max(2, int(pct))
        col = P["accent"] if n else P["border"]
        cells.append(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:4px 0;font-family:var(--ck-mono);font-size:11px;">'
            f'<span style="width:80px;color:{P["text_dim"]};">{s}</span>'
            f'<span style="width:36px;text-align:right;color:{P["text"]};'
            f'font-variant-numeric:tabular-nums;">{n}</span>'
            f'<span style="flex:1;height:6px;background:{P["border_dim"]};'
            f'border-radius:1px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{bar_w}%;'
            f'background:{col};"></span></span>'
            f'<span style="width:44px;text-align:right;color:{P["text_faint"]};'
            f'font-variant-numeric:tabular-nums;">{pct:.1f}%</span>'
            f'</div>'
        )
    return "".join(cells)


def _alerts(db_path: str) -> str:
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT deal_id, severity, kind, message, fired_at "
            "FROM alerts WHERE acked_at IS NULL "
            "ORDER BY fired_at DESC LIMIT 6"
        ).fetchall()
        con.close()
    except Exception:
        rows = []
    if not rows:
        return _empty("No active alerts.")
    out = []
    for r in rows:
        sev = str(r["severity"] or "").lower()
        col = {"critical": P["critical"], "high": P["negative"],
               "medium": P["warning"], "low": P["text_dim"]}.get(sev, P["text_dim"])
        did = _html.escape(str(r["deal_id"] or ""))
        kind = _html.escape(str(r["kind"] or ""))
        msg = _html.escape(str(r["message"] or "")[:120])
        fired = _html.escape(str(r["fired_at"] or ""))
        out.append(
            f'<div style="padding:5px 0;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11px;">'
            f'<div style="display:flex;gap:8px;align-items:center;">'
            f'<span style="color:{col};font-family:var(--ck-mono);font-size:9px;'
            f'font-weight:700;letter-spacing:0.10em;text-transform:uppercase;">'
            f'{_html.escape(sev or "—")}</span>'
            f'<span style="color:{P["text_dim"]};font-family:var(--ck-mono);'
            f'font-size:10px;">{kind}</span>'
            f'<a href="/deal/{did}" style="color:{P["accent"]};'
            f'font-family:var(--ck-mono);font-size:10px;margin-left:auto;">'
            f'{did}</a></div>'
            f'<div style="color:{P["text"]};margin-top:2px;">{msg}</div>'
            f'<div style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:9px;margin-top:1px;">{fired}</div>'
            f'</div>'
        )
    out.append(
        f'<div style="margin-top:8px;"><a href="/alerts" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;">'
        f'ALL ALERTS →</a></div>'
    )
    return "".join(out)


def _health_distribution(db_path: str) -> str:
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT score FROM deal_health_scores "
            "WHERE score IS NOT NULL"
        ).fetchall()
        con.close()
    except Exception:
        rows = []
    if not rows:
        return _empty("No health scores computed yet.")
    green = sum(1 for r in rows if r["score"] >= 70)
    amber = sum(1 for r in rows if 40 <= r["score"] < 70)
    red = sum(1 for r in rows if r["score"] < 40)
    total = green + amber + red
    cells = []
    for label, n, col in (
        ("Healthy (≥70)", green, P["positive"]),
        ("Watchlist (40-69)", amber, P["warning"]),
        ("At Risk (<40)", red, P["negative"]),
    ):
        pct = (n / total * 100.0) if total else 0.0
        cells.append(
            f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;'
            f'font-family:var(--ck-mono);font-size:11px;">'
            f'<span style="width:140px;color:{col};">{_html.escape(label)}</span>'
            f'<span style="width:36px;text-align:right;color:{P["text"]};'
            f'font-variant-numeric:tabular-nums;">{n}</span>'
            f'<span style="flex:1;height:6px;background:{P["border_dim"]};'
            f'border-radius:1px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{max(2, int(pct))}%;'
            f'background:{col};"></span></span>'
            f'<span style="width:44px;text-align:right;color:{P["text_faint"]};'
            f'font-variant-numeric:tabular-nums;">{pct:.1f}%</span>'
            f'</div>'
        )
    return "".join(cells)


def _recent_deals(store: Any) -> str:
    try:
        deals = store.list_deals()
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else list(deals or [])
    except Exception:
        rows = []
    if not rows:
        return _empty("No deals yet.")
    rows_sorted = sorted(
        rows,
        key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""),
        reverse=True,
    )[:6]
    out = []
    for r in rows_sorted:
        did = str(r.get("deal_id") or "")
        name = str(r.get("name") or did)
        stage = str(r.get("stage") or "—")
        out.append(
            f'<div style="display:flex;gap:8px;align-items:center;padding:4px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11px;">'
            f'<a href="/deal/{_html.escape(did)}" style="color:{P["accent"]};'
            f'flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{_html.escape(name)}</a>'
            f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;">{_html.escape(stage)}</span>'
            f'<a href="/deal/{_html.escape(did)}/partner-review" '
            f'style="color:{P["warning"]};font-family:var(--ck-mono);'
            f'font-size:9px;letter-spacing:0.10em;">PR</a>'
            f'</div>'
        )
    return "".join(out)


def _deadlines(db_path: str) -> str:
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        today = date.today().isoformat()
        week_out = (date.today() + timedelta(days=7)).isoformat()
        rows = con.execute(
            "SELECT deal_id, title, due_date, owner "
            "FROM deal_deadlines "
            "WHERE completed_at IS NULL AND due_date <= ? "
            "ORDER BY due_date ASC LIMIT 6",
            (week_out,),
        ).fetchall()
        con.close()
    except Exception:
        rows = []
    if not rows:
        return _empty("No deadlines within 7 days.")
    out = []
    today_str = date.today().isoformat()
    for r in rows:
        did = _html.escape(str(r["deal_id"] or ""))
        title = _html.escape(str(r["title"] or "")[:80])
        due = str(r["due_date"] or "")
        owner = _html.escape(str(r["owner"] or "—"))
        overdue = due < today_str
        col = P["negative"] if overdue else P["warning"]
        out.append(
            f'<div style="display:flex;gap:8px;align-items:baseline;padding:4px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11px;">'
            f'<span style="color:{col};font-family:var(--ck-mono);font-size:10px;'
            f'width:90px;">{_html.escape(due)}</span>'
            f'<a href="/deal/{did}" style="color:{P["accent"]};flex:1;'
            f'min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f'{title}</a>'
            f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;">{owner}</span>'
            f'</div>'
        )
    return "".join(out)


def _pe_highlights(store: Any, db_path: str) -> str:
    """Top-3 partner-review verdicts across the portfolio.

    Wraps partner_review() in try/except per-deal; a single bad packet
    must not kill the panel.
    """
    try:
        deals = store.list_deals()
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else list(deals or [])
    except Exception:
        rows = []
    if not rows:
        return _empty("Import a deal to see PE intelligence highlights.")
    try:
        from ...analysis.analysis_store import get_or_build_packet
        from ...pe_intelligence import partner_review
    except Exception as exc:
        return _empty(f"PE intelligence unavailable: {exc!r}")

    verdicts: List[Tuple[str, str, str, int, str]] = []
    for r in rows[:15]:
        did = str(r.get("deal_id") or "")
        name = str(r.get("name") or did)
        if not did:
            continue
        try:
            pkt = get_or_build_packet(store, did, skip_simulation=True)
            rv = partner_review(pkt)
            rec = str(rv.narrative.recommendation or "—")
            crit = sum(1 for h in rv.heuristic_hits if h.severity == "CRITICAL")
            headline = rv.narrative.headline or ""
            verdicts.append((did, name, rec, crit, headline[:140]))
        except Exception:
            continue
    if not verdicts:
        return _empty("No partner reviews yet — open a deal to build one.")
    # Rank: critical flags first, then PASS recs, then PROCEED.
    priority = {"PASS": 0, "PROCEED_WITH_CAVEATS": 1, "PROCEED": 2, "STRONG_PROCEED": 3}
    verdicts.sort(key=lambda t: (-t[3], priority.get(t[2], 9)))
    out = []
    for did, name, rec, crit, headline in verdicts[:3]:
        col = {
            "PASS": P["negative"],
            "PROCEED_WITH_CAVEATS": P["warning"],
            "PROCEED": P["text"],
            "STRONG_PROCEED": P["positive"],
        }.get(rec, P["text_dim"])
        out.append(
            f'<div style="padding:6px 0;border-bottom:1px solid {P["border_dim"]};'
            f'font-size:11px;">'
            f'<div style="display:flex;gap:8px;align-items:center;">'
            f'<a href="/deal/{_html.escape(did)}/partner-review" '
            f'style="color:{P["accent"]};flex:1;min-width:0;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">{_html.escape(name)}</a>'
            f'<span style="color:{col};font-family:var(--ck-mono);font-size:9px;'
            f'font-weight:700;letter-spacing:0.10em;">{_html.escape(rec)}</span>'
            f'</div>'
            + (
                f'<div style="color:{P["negative"]};font-family:var(--ck-mono);'
                f'font-size:9px;margin-top:1px;">'
                f'{crit} critical flag{"s" if crit != 1 else ""}</div>'
                if crit else ""
            )
            + (
                f'<div style="color:{P["text_dim"]};margin-top:2px;">'
                f'{_html.escape(headline)}</div>' if headline else ""
            )
            + f'</div>'
        )
    out.append(
        f'<div style="margin-top:8px;"><a href="/pe-intelligence" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;">'
        f'PE INTELLIGENCE BRAIN →</a></div>'
    )
    return "".join(out)


def _load_all_seed_deals() -> List[Dict[str, Any]]:
    """Mirror of deals_library_page._get_all_seed_deals — corpus access."""
    try:
        from ...data_public.deals_corpus import _SEED_DEALS
        from ...data_public.extended_seed import EXTENDED_SEED_DEALS
    except Exception:
        return []
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = __import__(
                f"rcm_mc.data_public.extended_seed_{i}",
                fromlist=[f"EXTENDED_SEED_DEALS_{i}"],
            )
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _corpus_insights() -> str:
    corpus = _load_all_seed_deals()
    if not corpus:
        return _empty("No corpus loaded.")

    def _deal_year(d: Any) -> Optional[int]:
        for key in ("entry_year", "vintage_year", "year"):
            val = getattr(d, key, None) if not isinstance(d, dict) else d.get(key)
            try:
                if val is not None:
                    return int(val)
            except (TypeError, ValueError):
                continue
        return None

    def _deal_moic(d: Any) -> Optional[float]:
        for key in ("realized_moic", "moic"):
            val = getattr(d, key, None) if not isinstance(d, dict) else d.get(key)
            try:
                if val is not None:
                    return float(val)
            except (TypeError, ValueError):
                continue
        return None

    def _deal_name(d: Any) -> str:
        for key in ("name", "deal_name", "target_name"):
            val = getattr(d, key, None) if not isinstance(d, dict) else d.get(key)
            if val:
                return str(val)
        return "—"

    # Recent: last 6 by entry year.
    recent = sorted(
        (d for d in corpus if _deal_year(d)),
        key=lambda d: _deal_year(d) or 0, reverse=True,
    )[:6]
    # Top vintages: aggregate mean realized MOIC by entry year.
    from collections import defaultdict
    by_year: Dict[int, List[float]] = defaultdict(list)
    for d in corpus:
        y = _deal_year(d)
        m = _deal_moic(d)
        if y and m is not None:
            by_year[y].append(m)
    vintage_rows = sorted(
        ((y, sum(ms) / len(ms), len(ms)) for y, ms in by_year.items() if len(ms) >= 3),
        key=lambda t: t[1], reverse=True,
    )[:5]

    left = [
        f'<div style="color:{P["text_faint"]};font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.12em;margin-bottom:4px;">RECENT ENTRIES</div>'
    ]
    for d in recent:
        y = _deal_year(d) or 0
        left.append(
            f'<div style="display:flex;gap:8px;padding:3px 0;font-size:11px;'
            f'border-bottom:1px solid {P["border_dim"]};">'
            f'<span style="font-family:var(--ck-mono);color:{P["text_faint"]};'
            f'width:40px;">{y}</span>'
            f'<span style="color:{P["text"]};overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{_html.escape(_deal_name(d))}</span>'
            f'</div>'
        )
    right = [
        f'<div style="color:{P["text_faint"]};font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.12em;margin-bottom:4px;">TOP VINTAGES</div>'
    ]
    for y, mean_moic, n in vintage_rows:
        right.append(
            f'<div style="display:flex;gap:8px;padding:3px 0;font-size:11px;'
            f'border-bottom:1px solid {P["border_dim"]};">'
            f'<span style="font-family:var(--ck-mono);color:{P["text_faint"]};'
            f'width:40px;">{y}</span>'
            f'<span style="flex:1;">{render_number(mean_moic, "moic")}</span>'
            f'<span style="font-family:var(--ck-mono);color:{P["text_faint"]};'
            f'font-size:9px;">n={n}</span>'
            f'</div>'
        )
    return (
        f'<div style="display:flex;gap:12px;">'
        f'<div style="flex:1;min-width:0;">{"".join(left)}</div>'
        f'<div style="flex:1;min-width:0;">{"".join(right)}</div>'
        f'</div>'
        f'<div style="margin-top:8px;"><a href="/library" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;">'
        f'BROWSE CORPUS →</a></div>'
    )


def _kpi_strip(store: Any, db_path: str) -> str:
    try:
        deals = store.list_deals()
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else list(deals or [])
        n_deals = len(rows)
    except Exception:
        n_deals = 0
    n_alerts = 0
    try:
        con = sqlite3.connect(db_path)
        (n_alerts,) = con.execute(
            "SELECT COUNT(*) FROM alerts WHERE acked_at IS NULL"
        ).fetchone()
        con.close()
    except Exception:
        n_alerts = 0
    n_corpus = len(_load_all_seed_deals())
    tiles = (
        ck_kpi_block("Active Deals", f"{n_deals}", "in portfolio")
        + ck_kpi_block("Unacked Alerts", f"{n_alerts}", "across portfolio")
        + ck_kpi_block("Corpus Deals", f"{n_corpus}", "benchmarkable comps")
        + ck_kpi_block("PE Intel Modules", "278", "partner reflexes codified")
    )
    return f'<div class="ck-kpi-grid">{tiles}</div>'


def render_home(store: Any, db_path: str, current_user: Optional[str] = None) -> str:
    """Render the seven-panel home landing page."""
    explainer = render_page_explainer(
        what=(
            "Seven-panel partner landing: pipeline funnel, active alerts, "
            "portfolio-health distribution, recent deals, upcoming "
            "deadlines (7 days), top partner-review verdicts across the "
            "portfolio, and corpus insights."
        ),
        page_key="home",
    )
    kpi = _kpi_strip(store, db_path)
    panels = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
        f'{_panel("Pipeline Funnel", _pipeline_funnel(store), code="FNL")}'
        f'{_panel("Active Alerts", _alerts(db_path), code="ALR")}'
        f'{_panel("Portfolio Health", _health_distribution(db_path), code="HLT")}'
        f'{_panel("Recent Deals", _recent_deals(store), code="DLS")}'
        f'{_panel("Upcoming Deadlines (7d)", _deadlines(db_path), code="DDL")}'
        f'{_panel("PE Intelligence Highlights", _pe_highlights(store, db_path), code="PRV")}'
        f'</div>'
        + _panel("Corpus Insights", _corpus_insights(), code="CPS")
    )
    subtitle = (
        f"Signed in as {_html.escape(current_user)}"
        if current_user else "Partner landing — pipeline, alerts, PE brain verdicts"
    )
    return chartis_shell(
        explainer + kpi + panels,
        title="Home",
        active_nav="/home",
        subtitle=subtitle,
    )

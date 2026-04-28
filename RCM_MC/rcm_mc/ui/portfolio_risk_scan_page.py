"""`/portfolio/risk-scan` — morning portfolio risk scan.

The partner's Monday-morning question: "which of my 12 hold-period
deals needs attention today?" Currently the answer requires opening
each deal individually. This page answers it in one screen.

Each deal is scanned against five risk dimensions:

  1. **Health score** — current composite score + band, with a
     90-day trend sparkline showing direction.
  2. **Covenant headroom** — TRIPPED / TIGHT / SAFE status read from
     the portfolio snapshot. A TRIPPED deal needs work TODAY.
  3. **Active alerts** — count of unacked alerts for the deal. Any
     deal with >0 open alerts surfaces amber; ≥3 surfaces red.
  4. **Snapshot freshness** — days since the latest portfolio
     snapshot. A deal stale >30 days is rendering on old data.
  5. **Pending deadlines** — count of open deadlines where the
     user is the owner, plus count of overdue deadlines.

Everything is best-effort — a missing table or a failing compute
on a single deal falls through to "—" for that cell, not a page
crash. The goal is to always render SOMETHING, even on a fresh
deploy or a partially-populated DB.

The page respects the same filterable/sortable contract as the
dashboard's tables (`_web_components.sortable_table` with
`filterable=True`) so a partner with 50 deals can type "sector"
or "covenant" and filter in place.

Public API:
    render_portfolio_risk_scan(db_path: str) -> str
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def _safe_status_str(v: object) -> str:
    """Coerce a possibly-NaN covenant_status to a string safely.
    Same shape as dashboard_page._safe_status_str — pandas converts
    NULL covenant_status DB values to NaN (float), which is truthy so
    the `(v or "")` idiom doesn't catch it; .upper() then crashes.
    Surfaced 2026-04-26 by the seeded-DB integration test.
    """
    if v is None:
        return ""
    if isinstance(v, float) and v != v:  # NaN check
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except (TypeError, ValueError):
        return None


def _cell_chip(label: str, *, bg: str, fg: str) -> str:
    return (
        f'<span style="display:inline-block;padding:1px 8px;'
        f'background:{bg};color:{fg};border-radius:9999px;'
        f'font-size:11px;font-weight:600;'
        f'font-variant-numeric:tabular-nums;">{_html.escape(label)}</span>'
    )


# ── Per-dimension cell renderers ───────────────────────────────────

def _health_cell(score: Optional[int], band: Optional[str]) -> str:
    """Score chip color-coded by band."""
    if score is None:
        return _cell_chip("—", bg="#f3f4f6", fg="#6b7280")
    band_l = (band or "").lower()
    if band_l in ("excellent", "good"):
        return _cell_chip(str(score), bg="#d1fae5", fg="#065f46")
    if band_l == "fair":
        return _cell_chip(str(score), bg="#fef3c7", fg="#92400e")
    if band_l in ("poor", "critical"):
        return _cell_chip(str(score), bg="#fee2e2", fg="#991b1b")
    return _cell_chip(str(score), bg="#e0e7ff", fg="#3730a3")


def _covenant_cell(status: Optional[str]) -> str:
    s = (status or "").upper()
    if s == "TRIPPED":
        return _cell_chip("TRIPPED", bg="#fee2e2", fg="#991b1b")
    if s == "TIGHT":
        return _cell_chip("TIGHT", bg="#fef3c7", fg="#92400e")
    if s in ("SAFE", "OK"):
        return _cell_chip("SAFE", bg="#d1fae5", fg="#065f46")
    return _cell_chip("—", bg="#f3f4f6", fg="#6b7280")


def _alerts_cell(count: int) -> str:
    if count <= 0:
        return _cell_chip("0", bg="#f3f4f6", fg="#6b7280")
    if count >= 3:
        return _cell_chip(str(count), bg="#fee2e2", fg="#991b1b")
    return _cell_chip(str(count), bg="#fef3c7", fg="#92400e")


def _freshness_cell(days: Optional[int]) -> str:
    if days is None:
        return _cell_chip("never", bg="#f3f4f6", fg="#6b7280")
    if days < 7:
        return _cell_chip(f"{days}d", bg="#d1fae5", fg="#065f46")
    if days < 30:
        return _cell_chip(f"{days}d", bg="#fef3c7", fg="#92400e")
    return _cell_chip(f"{days}d", bg="#fee2e2", fg="#991b1b")


def _hrrp_cell(pct: Optional[float]) -> str:
    """HRRP penalty as a percentage of Medicare IPPS revenue.
    None for non-hospitals or hospitals not in the file. 0% =
    no penalty (green); ≥2% = high penalty (red); cap is 3%.
    """
    if pct is None:
        return _cell_chip("—", bg="#f3f4f6", fg="#6b7280")
    if pct == 0:
        return _cell_chip("0%", bg="#d1fae5", fg="#065f46")
    if pct >= 2.0:
        return _cell_chip(f"{pct:.1f}%", bg="#fee2e2", fg="#991b1b")
    if pct >= 1.0:
        return _cell_chip(f"{pct:.1f}%", bg="#fef3c7", fg="#92400e")
    return _cell_chip(f"{pct:.1f}%", bg="#e0e7ff", fg="#3730a3")


def _quality_cell(rating: Optional[int]) -> str:
    """CMS overall hospital rating, 1-5 stars. None for facilities
    not in the CMS General Info file (or non-hospital deals)."""
    if rating is None:
        return _cell_chip("—", bg="#f3f4f6", fg="#6b7280")
    if rating >= 4:
        return _cell_chip(f"{rating}★", bg="#d1fae5", fg="#065f46")
    if rating == 3:
        return _cell_chip(f"{rating}★", bg="#e0e7ff", fg="#3730a3")
    if rating == 2:
        return _cell_chip(f"{rating}★", bg="#fef3c7", fg="#92400e")
    return _cell_chip(f"{rating}★", bg="#fee2e2", fg="#991b1b")


def _deadlines_cell(open_count: int, overdue_count: int) -> str:
    if overdue_count > 0:
        return _cell_chip(
            f"{open_count} ({overdue_count} overdue)",
            bg="#fee2e2", fg="#991b1b",
        )
    if open_count > 0:
        return _cell_chip(str(open_count), bg="#e0e7ff", fg="#3730a3")
    return _cell_chip("0", bg="#f3f4f6", fg="#6b7280")


# ── Data gathering ──────────────────────────────────────────────────

def _gather_per_deal(db_path: str) -> List[Dict[str, Any]]:
    """One dict per deal. Every field is best-effort."""
    try:
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        deals_df = store.list_deals(include_archived=False)
    except Exception:  # noqa: BLE001
        return []

    if deals_df.empty:
        return []

    # Pull latest snapshot per deal once (cheap) — gives
    # covenant_status + snapshot freshness cheaply.
    try:
        from ..portfolio.portfolio_snapshots import latest_per_deal
        snap_df = latest_per_deal(store)
        snap_by_id: Dict[str, Dict[str, Any]] = {
            str(r["deal_id"]): r.to_dict()
            for _, r in snap_df.iterrows()
        } if not snap_df.empty else {}
    except Exception:  # noqa: BLE001
        snap_by_id = {}

    # Pre-load deadlines in one pass — avoids N round-trips.
    # `list_deadlines` and `overdue` both return pandas DataFrames,
    # so iterate via iterrows() rather than `for dl in df` (which
    # would iterate column names).
    open_deadlines: Dict[str, int] = {}
    overdue_deadlines: Dict[str, int] = {}
    try:
        from ..deals.deal_deadlines import list_deadlines, overdue
        # list_deadlines defaults to include_completed=False so it
        # returns OPEN deadlines — exactly what we want here.
        od_df = list_deadlines(store)
        if od_df is not None and not od_df.empty:
            for _, dl in od_df.iterrows():
                did = str(dl.get("deal_id") or "")
                if did:
                    open_deadlines[did] = open_deadlines.get(did, 0) + 1
        ov_df = overdue(store)
        if ov_df is not None and not ov_df.empty:
            for _, dl in ov_df.iterrows():
                did = str(dl.get("deal_id") or "")
                if did:
                    overdue_deadlines[did] = overdue_deadlines.get(did, 0) + 1
    except Exception:  # noqa: BLE001
        pass

    # Active-alerts-per-deal in one pass.
    alerts_per_deal: Dict[str, int] = {}
    try:
        from ..alerts.alerts import evaluate_active
        for a in evaluate_active(store):
            did = str(getattr(a, "deal_id", "") or "")
            alerts_per_deal[did] = alerts_per_deal.get(did, 0) + 1
    except Exception:  # noqa: BLE001
        pass

    out: List[Dict[str, Any]] = []
    for _, row in deals_df.iterrows():
        deal_id = str(row.get("deal_id") or "")
        if not deal_id:
            continue
        name = str(row.get("name") or deal_id)
        snap = snap_by_id.get(deal_id, {})

        # Health score — compute_health is pricey on a real DB; do
        # it lazily with try/except so one failed compute doesn't
        # crash the whole page.
        score: Optional[int] = None
        band: Optional[str] = None
        try:
            from ..deals.health_score import compute_health
            h = compute_health(store, deal_id)
            score = h.get("score")
            band = h.get("band")
        except Exception:  # noqa: BLE001
            pass

        # Snapshot freshness — age of the latest snapshot row.
        snap_age = _days_since(snap.get("snapshot_at")
                               or snap.get("created_at"))

        # Chain lookup via CMS POS — best-effort. Treats the deal_id
        # as a CCN (which it is for HCRIS-anchored deals); non-CCN
        # deal_ids just get empty chain strings.
        chain_name = ""
        chain_size = 0
        try:
            from ..data.cms_pos import get_facility_by_ccn, count_facilities_in_chain
            fac = get_facility_by_ccn(store, deal_id)
            if fac:
                chain_name = fac.get("chain_identifier") or ""
                chain_size = count_facilities_in_chain(store, deal_id)
        except Exception:  # noqa: BLE001
            pass

        # CMS Hospital General Information — overall 5-star rating.
        # Same best-effort pattern: returns None if the table isn't
        # populated yet or the CCN doesn't match.
        quality_rating: Optional[int] = None
        try:
            from ..data.cms_hospital_general import get_quality_by_ccn
            q = get_quality_by_ccn(store, deal_id)
            if q:
                quality_rating = q.get("overall_rating")
        except Exception:  # noqa: BLE001
            pass

        # CMS HRRP — readmission penalty as a percentage of Medicare
        # IPPS payments. Best-effort.
        hrrp_pct: Optional[float] = None
        try:
            from ..data.cms_hrrp import get_penalty_by_ccn
            h = get_penalty_by_ccn(store, deal_id)
            if h:
                hrrp_pct = h.get("payment_adjustment_pct")
        except Exception:  # noqa: BLE001
            pass

        out.append({
            "deal_id": deal_id,
            "name": name,
            "sector": str(row.get("sector") or "") or "—",
            "stage": str(row.get("stage") or "") or "—",
            "score": score,
            "band": band,
            "covenant_status": snap.get("covenant_status"),
            "alerts": alerts_per_deal.get(deal_id, 0),
            "snap_age_days": snap_age,
            "open_deadlines": open_deadlines.get(deal_id, 0),
            "overdue_deadlines": overdue_deadlines.get(deal_id, 0),
            "chain": chain_name,
            "chain_size": chain_size,
            "quality_rating": quality_rating,
            "hrrp_pct": hrrp_pct,
        })

    return out


# ── Row-level priority ranker ──────────────────────────────────────
#
# Puts "needs attention today" rows at the top without requiring the
# partner to click the Covenant or Alerts column header. Priority is
# a simple weighted sum — TRIPPED covenant and overdue deadlines
# dominate; low health scores and unacked alerts pile on.

def _priority_rank(deal: Dict[str, Any]) -> int:
    score = 0
    if _safe_status_str(deal.get("covenant_status")).upper() == "TRIPPED":
        score += 100
    elif _safe_status_str(deal.get("covenant_status")).upper() == "TIGHT":
        score += 30
    score += 20 * int(deal.get("overdue_deadlines") or 0)
    score += 5 * int(deal.get("alerts") or 0)
    h = deal.get("score")
    if isinstance(h, int):
        if h < 40:
            score += 40
        elif h < 60:
            score += 15
    if deal.get("snap_age_days") is not None:
        days = deal["snap_age_days"]
        if days > 60:
            score += 20
        elif days > 30:
            score += 10
    return score


# ── Page renderer ──────────────────────────────────────────────────

def render_portfolio_risk_scan(db_path: str) -> str:
    from . import _web_components as _wc
    from ._chartis_kit import chartis_shell

    deals = _gather_per_deal(db_path)

    header = _wc.page_header(
        "Portfolio risk scan",
        subtitle=(
            "One-screen scan across every active deal — health score, "
            "covenant, alerts, snapshot freshness, deadlines. Rows "
            "sorted highest-priority first so attention-required "
            "deals surface without clicking a column."
        ),
        crumbs=[("Dashboard", "/dashboard"),
                ("Portfolio risk scan", None)],
    )

    if not deals:
        empty = (
            '<p>No active deals in the portfolio store yet. '
            'Add deals via the <a href="/new-deal" '
            'style="color:var(--sc-navy);">new deal wizard</a> or import '
            'via <a href="/import" style="color:var(--sc-navy);">Quick '
            'import</a>, then this scan will populate.</p>'
        )
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header + _wc.section_card("No deals yet", empty))
        )
        return chartis_shell(body, "Portfolio risk scan",
                             active_nav="/portfolio/risk-scan")

    # Priority-sort so the worst deals float to the top
    deals.sort(key=_priority_rank, reverse=True)

    # Color legend — tells a first-time user what each chip means
    # before they have to hover or click to discover it.
    legend = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;'
        'margin:12px 0 4px;padding:10px 12px;background:#fafbfc;'
        'border:1px solid #f3f4f6;border-radius:6px;'
        'font-size:11px;color:#6b7280;">'
        '<span style="font-weight:600;color:#374151;'
        'text-transform:uppercase;letter-spacing:0.05em;">Key</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;'
        'background:#10b981;border-radius:50%;margin-right:6px;'
        'vertical-align:middle;"></span>safe / fresh / excellent</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;'
        'background:#f59e0b;border-radius:50%;margin-right:6px;'
        'vertical-align:middle;"></span>tight / stale / fair</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;'
        'background:#ef4444;border-radius:50%;margin-right:6px;'
        'vertical-align:middle;"></span>tripped / cold / poor / overdue</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;'
        'background:#d1d5db;border-radius:50%;margin-right:6px;'
        'vertical-align:middle;"></span>no data / zero</span>'
        '</div>'
    )

    # Summary strip: counts across the portfolio for the 3
    # most-actionable categories.
    tripped = sum(1 for d in deals
                  if _safe_status_str(d.get("covenant_status")).upper() == "TRIPPED")
    any_alerts = sum(1 for d in deals if (d.get("alerts") or 0) > 0)
    any_overdue = sum(1 for d in deals
                      if (d.get("overdue_deadlines") or 0) > 0)

    def _summary_chip(label: str, n: int, *, level: str) -> str:
        colors = {
            "ok": ("#d1fae5", "#065f46"),
            "warn": ("#fef3c7", "#92400e"),
            "alert": ("#fee2e2", "#991b1b"),
        }
        bg, fg = colors.get(level, colors["ok"])
        return (
            f'<div style="padding:10px 14px;background:{bg};color:{fg};'
            f'border-radius:8px;flex:1;min-width:180px;">'
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.05em;opacity:0.85;">{_html.escape(label)}</div>'
            f'<div style="font-size:22px;font-weight:700;margin-top:2px;'
            f'font-variant-numeric:tabular-nums;">{n}</div>'
            f'</div>'
        )

    summary_strip = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:16px 0;">'
        + _summary_chip("Covenant TRIPPED", tripped,
                        level="alert" if tripped else "ok")
        + _summary_chip("Deals with open alerts", any_alerts,
                        level="warn" if any_alerts else "ok")
        + _summary_chip("Deals with overdue deadlines", any_overdue,
                        level="alert" if any_overdue else "ok")
        + _summary_chip("Active deals scanned", len(deals), level="ok")
        + "</div>"
    )

    # Row construction — each cell is a colored chip so the scan
    # reads visually, not by reading numbers.
    rows: List[List[str]] = []
    for d in deals:
        deal_id = d["deal_id"]
        name_link = (
            f'<a href="/deal/{_html.escape(deal_id)}" '
            f'style="color:var(--sc-navy);font-weight:500;text-decoration:none;">'
            f'{_html.escape(d["name"])}</a>'
            f'<div style="font-family:monospace;font-size:10px;'
            f'color:#6b7280;margin-top:2px;text-transform:uppercase;">'
            f'{_html.escape(deal_id)}</div>'
        )
        # Chain cell — shows the chain identifier + count of
        # facilities. Independent → "—". Small chain (2-3) → neutral.
        # Large chain (4+) → amber (concentration heads-up).
        if d.get("chain"):
            cs = d.get("chain_size") or 1
            if cs >= 4:
                chain_cell = _cell_chip(
                    f'{_html.escape(d["chain"])} · {cs}',
                    bg="#fef3c7", fg="#92400e",
                )
            else:
                chain_cell = _cell_chip(
                    f'{_html.escape(d["chain"])} · {cs}',
                    bg="#e0e7ff", fg="#3730a3",
                )
        else:
            chain_cell = _cell_chip("—", bg="#f3f4f6", fg="#6b7280")

        rows.append([
            name_link,
            f'<span style="color:#4b5563;">{_html.escape(d["sector"])}</span>',
            chain_cell,
            _quality_cell(d.get("quality_rating")),
            _hrrp_cell(d.get("hrrp_pct")),
            _health_cell(d["score"], d["band"]),
            _covenant_cell(d["covenant_status"]),
            _alerts_cell(d["alerts"]),
            _freshness_cell(d["snap_age_days"]),
            _deadlines_cell(d["open_deadlines"], d["overdue_deadlines"]),
        ])

    table = _wc.sortable_table(
        ["Deal", "Sector", "Chain", "Quality", "HRRP", "Health",
         "Covenant", "Alerts", "Snap age", "Deadlines"],
        rows, id="portfolio-risk-scan",
        hide_columns_sm=[1, 2, 8],
        filterable=True,
        filter_placeholder=(
            "Filter by deal, sector, chain, or stage…"),
    )

    # One-click CSV export — saves a partner from copy-paste-and-
    # reformat-into-PowerPoint when they need to share the scan.
    csv_link = (
        '<a href="/api/portfolio/risk-scan.csv" '
        'download style="display:inline-block;margin:0 0 12px;'
        'padding:6px 12px;background:#fff;border:1px solid #d0e3f0;'
        'color:var(--sc-navy);border-radius:4px;font-size:12px;'
        'font-weight:500;text-decoration:none;'
        'transition:background 0.1s;" '
        'onmouseover="this.style.background=\'#f0f6fc\';" '
        'onmouseout="this.style.background=\'#fff\';" '
        'title="Download today\'s scan as CSV — paste into PowerPoint, '
        'email, or Excel">'
        '⬇ Export CSV</a>'
    )

    inner = (
        header
        + summary_strip
        + legend
        + csv_link
        + _wc.section_card(
            f"Per-deal scan ({len(deals)} active deals)",
            table, pad=False,
        )
    )

    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
    )
    return chartis_shell(body, "Portfolio risk scan",
                         active_nav="/portfolio/risk-scan")

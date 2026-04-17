"""Composite deal health score + trend history (Bricks 135, 138).

Partners want a one-number summary: is this deal green/amber/red?
Individual signals exist (covenant status, EBITDA variance, alert
counts) but a scalar that rolls them up is what ends up on the
committee page.

Design:

- Score starts at 100 and is subtracted from based on component
  severities. Not additive from zero — that way a deal with *no*
  signals defaults to healthy, which matches intuition.
- Every deduction is transparent: the ``components`` list in the
  returned dict names each hit + its impact. Partners who don't
  trust opaque scores can trace every point.
- Bands:
    green  ≥ 80
    amber  50–79
    red    < 50
- Stateless: never mutates the store. Safe to call on every page
  view.

Public API::

    compute_health(store, deal_id) -> dict
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from ..portfolio.store import PortfolioStore


def _band(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 50:
        return "amber"
    return "red"


def _ensure_history_table(store: PortfolioStore) -> None:
    """B138: daily history table for health trends."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_health_history (
                deal_id TEXT NOT NULL,
                at_date TEXT NOT NULL,
                score INTEGER NOT NULL,
                band TEXT NOT NULL,
                PRIMARY KEY (deal_id, at_date)
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_health_history_date "
            "ON deal_health_history(deal_id, at_date DESC)"
        )
        con.commit()


def _record_history(
    store: PortfolioStore,
    deal_id: str,
    score: int,
    band: str,
    today: Optional[date] = None,
) -> None:
    """Upsert today's score for a deal. Idempotent within the day."""
    _ensure_history_table(store)
    d = (today or date.today()).isoformat()
    with store.connect() as con:
        con.execute(
            "INSERT INTO deal_health_history (deal_id, at_date, score, band) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(deal_id, at_date) DO UPDATE SET "
            "score = excluded.score, band = excluded.band",
            (deal_id, d, int(score), band),
        )
        con.commit()


def history_series(
    store: PortfolioStore,
    deal_id: str,
    *,
    days: int = 90,
) -> list:
    """Return [(at_date, score)] for a deal, oldest-first.

    Sparkline source for /deal/<id>. Capped at ``days`` most-recent
    entries so long-running deals don't balloon the chart.
    """
    _ensure_history_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT at_date, score FROM deal_health_history "
            "WHERE deal_id = ? ORDER BY at_date DESC LIMIT ?",
            (deal_id, int(days)),
        ).fetchall()
    series = [(r["at_date"], int(r["score"])) for r in rows]
    series.reverse()  # oldest-first for a left-to-right chart
    return series


def _prior_score(
    store: PortfolioStore,
    deal_id: str,
    today: Optional[date] = None,
) -> Optional[int]:
    """Most recent history score strictly before ``today``."""
    _ensure_history_table(store)
    d = (today or date.today()).isoformat()
    with store.connect() as con:
        row = con.execute(
            "SELECT score FROM deal_health_history "
            "WHERE deal_id = ? AND at_date < ? "
            "ORDER BY at_date DESC LIMIT 1",
            (deal_id, d),
        ).fetchone()
    return int(row["score"]) if row else None


def compute_health(store: PortfolioStore, deal_id: str) -> Dict[str, Any]:
    """Return ``{score, band, components}`` for a single deal.

    ``components`` is a list of ``{label, impact, detail}`` so the UI
    can show exactly why the score is what it is.
    """
    from ..alerts.alerts import evaluate_active
    from ..pe.hold_tracking import variance_report
    from ..portfolio.portfolio_snapshots import latest_per_deal

    score = 100
    components = []

    df = latest_per_deal(store)
    row = df[df["deal_id"] == deal_id] if not df.empty else df
    if row.empty:
        return {
            "deal_id": deal_id,
            "score": None,
            "band": "unknown",
            "components": [{
                "label": "No snapshot",
                "impact": 0,
                "detail": "Deal has not been registered yet.",
            }],
        }
    r = row.iloc[0]

    # ── Covenant contribution (largest single factor) ──
    cov = r.get("covenant_status")
    if cov == "TRIPPED":
        components.append({
            "label": "Covenant TRIPPED",
            "impact": -40,
            "detail": "Leverage exceeds maximum allowed.",
        })
        score -= 40
    elif cov == "TIGHT":
        components.append({
            "label": "Covenant TIGHT",
            "impact": -15,
            "detail": "Within 1 turn of maximum.",
        })
        score -= 15

    # ── Concerning-signal contribution ──
    # B146 fix: use pd.isna so numpy NaN and pandas NA both round to 0.
    # The old `nc == nc` trick worked for Python float NaN but not all
    # nullables the upstream pipeline can produce.
    import pandas as _pd
    nc = r.get("concerning_signals")
    nc_int = 0 if nc is None or _pd.isna(nc) else int(nc)
    if nc_int >= 5:
        components.append({
            "label": f"{nc_int} concerning signals",
            "impact": -15,
            "detail": "Multiple trend metrics moving in concerning direction.",
        })
        score -= 15
    elif nc_int >= 3:
        components.append({
            "label": f"{nc_int} concerning signals",
            "impact": -8,
            "detail": "Cluster of concerning trends.",
        })
        score -= 8
    elif nc_int >= 1:
        components.append({
            "label": f"{nc_int} concerning signal",
            "impact": -3,
            "detail": "At least one concerning trend.",
        })
        score -= 3

    # ── EBITDA variance (latest quarter) ──
    vdf = variance_report(store, deal_id)
    if not vdf.empty:
        ebitda = vdf[vdf["kpi"] == "ebitda"].sort_values("quarter")
        if not ebitda.empty:
            latest = ebitda.iloc[-1]
            vp = latest.get("variance_pct")
            if vp is not None and not (isinstance(vp, float) and vp != vp):
                vp = float(vp)
                if vp <= -0.15:
                    components.append({
                        "label": f"EBITDA miss {vp*100:+.1f}%",
                        "impact": -25,
                        "detail": f"Quarter {latest.get('quarter')}: "
                                  f"missing plan by ≥15%.",
                    })
                    score -= 25
                elif vp <= -0.10:
                    components.append({
                        "label": f"EBITDA miss {vp*100:+.1f}%",
                        "impact": -15,
                        "detail": f"Quarter {latest.get('quarter')}: "
                                  f"missing plan by 10-15%.",
                    })
                    score -= 15
                elif vp <= -0.05:
                    components.append({
                        "label": f"EBITDA miss {vp*100:+.1f}%",
                        "impact": -5,
                        "detail": f"Quarter {latest.get('quarter')}: "
                                  f"lagging plan by 5-10%.",
                    })
                    score -= 5

    # ── Active alerts (catch-all for evaluator signals we missed) ──
    try:
        active = [a for a in evaluate_active(store) if a.deal_id == deal_id]
    except Exception:  # noqa: BLE001
        active = []
    n_red = sum(1 for a in active if a.severity == "red")
    n_amber = sum(1 for a in active if a.severity == "amber")
    # Deduct only for alerts *not* already counted above (covenant +
    # variance alerts would double-count). Use deadline + cluster +
    # stage_regress as the "residual" alert categories.
    residual = [a for a in active
                if a.kind in ("deadline_overdue", "concerning_cluster",
                              "stage_regress")]
    for a in residual:
        hit = 5 if a.severity == "amber" else 10
        components.append({
            "label": a.kind,
            "impact": -hit,
            "detail": a.title,
        })
        score -= hit

    score = max(0, min(100, score))
    band = _band(score)

    # B138: record today's score + compute trend vs most-recent prior day
    today = date.today()
    prior = _prior_score(store, deal_id, today=today)
    try:
        _record_history(store, deal_id, score, band, today=today)
    except Exception:  # noqa: BLE001 — history must never break scoring
        pass
    if prior is None:
        trend = "flat"
        delta = 0
    else:
        delta = score - prior
        trend = "up" if delta > 0 else ("down" if delta < 0 else "flat")

    return {
        "deal_id": deal_id,
        "score": score,
        "band": band,
        "components": components,
        "trend": trend,
        "delta": delta,
    }

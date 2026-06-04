"""KKR healthcare-portfolio demo seed.

Why this exists
---------------
Demo mode turns the partner-ops console into a *fully populated, credible*
showcase: a partner clicks "Load KKR demo" and the command center, portfolio
map, alerts, cohorts, deal pages, variance, health scores and PE math all light
up with **real KKR healthcare deals** instead of an empty database. Everything
that reads the portfolio (``PortfolioStore``) is driven from one curated set,
so the whole surface is internally consistent and links resolve to these deals.

Credibility discipline
-----------------------
- The **deals are real** — every entry is an actual KKR healthcare investment
  that is also in the source-cited ``verified_deals`` corpus (``source_url``
  carried through for provenance).
- **Enterprise values are the real, publicly-reported figures** where one was
  disclosed (Envision ~$9.9B, Cotiviti ~$4.9B, BrightSpring ~$1.3B, Therapy
  Brands ~$1.2B); the rest are modeled at sector-typical entry multiples and
  clearly flagged as illustrative (the chartis shell's per-route illustrative
  banner already discloses modeled figures).
- Operating metrics (RCM KPIs), leverage/covenant headroom, MOIC/IRR and
  quarterly actuals are **modeled** from a per-deal performance tier — they are
  realistic and internally consistent, not represented as audited returns.
- The portfolio deliberately includes the **honest downside**: KKR's Envision
  Healthcare (a documented ~$10B write-off / 2023 Chapter 11) seeds as a
  covenant-tripped, distressed red deal — a real track record contains losses.

Seeding mirrors the proven recipe in the repo's ``demo.py`` (upsert_deal +
staged PE artifacts + register_snapshot + quarterly actuals + tags/owners +
health history), so the command center renders identically to the shipped demo.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


# --- The KKR healthcare portfolio (real deals; EV real where disclosed) -----
# Compact spec; the seeder derives RCM KPIs / actuals from ``tier`` so the
# 13×(many) numbers stay consistent and maintainable.
#   ev_mm        : enterprise value ($M); real where publicly reported
#   ev_real      : True if ev_mm is the disclosed figure (else modeled)
#   mult         : entry EV / EBITDA multiple (sector-typical)
#   tier         : "red" | "amber" | "green" — drives KPIs, headroom, variance
KKR_DEMO_DEALS: List[Dict[str, Any]] = [
    {"id": "envision", "name": "Envision Healthcare", "sector": "physician_practices",
     "year": 2018, "ev_mm": 9900, "ev_real": True, "mult": 10.0, "tier": "red",
     "moic": 0.0, "irr": -1.00, "leverage": 7.6, "headroom": -0.8,
     "exit_mult": 0.0, "hold": 5.0, "outcome": "bankrupt", "owner": "AT",
     "tags": ["fund_7", "watch", "distressed"],
     "note": "KKR's ~$9.9B 2018 buyout; filed Chapter 11 in 2023 — equity written off. The portfolio's honest downside case.",
     "src": "https://www.envisionhealth.com/"},
    {"id": "cotiviti", "name": "Cotiviti", "sector": "rcm_healthtech",
     "year": 2018, "ev_mm": 4900, "ev_real": True, "mult": 15.0, "tier": "green",
     "moic": 2.6, "irr": 0.22, "leverage": 5.0, "headroom": 2.6,
     "exit_mult": 16.0, "hold": 6.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_7", "core", "comp"],
     "note": "Payment-integrity + analytics for health plans; KKR acquired Verscend/Cotiviti 2018.",
     "src": "https://www.cotiviti.com/"},
    {"id": "brightspring", "name": "BrightSpring Health Services", "sector": "home_health_hospice",
     "year": 2019, "ev_mm": 1300, "ev_real": True, "mult": 11.0, "tier": "green",
     "moic": 2.1, "irr": 0.17, "leverage": 5.4, "headroom": 1.9,
     "exit_mult": 12.0, "hold": 5.0, "outcome": "exited", "owner": "SB",
     "tags": ["fund_7", "core", "exited"],
     "note": "Home & community health + pharmacy; KKR (from Onex 2019), IPO'd 2024.",
     "src": "https://www.brightspringhealth.com/"},
    {"id": "petvet", "name": "PetVet Care Centers", "sector": "veterinary",
     "year": 2018, "ev_mm": 2000, "ev_real": False, "mult": 16.0, "tier": "green",
     "moic": 2.3, "irr": 0.19, "leverage": 5.8, "headroom": 1.5,
     "exit_mult": 17.0, "hold": 6.0, "outcome": "active", "owner": "JD",
     "tags": ["fund_7", "roll-up"],
     "note": "General-practice + specialty veterinary hospitals; KKR acquired 2018.",
     "src": "https://www.petvetcarecenters.com/"},
    {"id": "ivirma", "name": "IVIRMA Global", "sector": "physician_practices",
     "year": 2017, "ev_mm": 1100, "ev_real": False, "mult": 11.0, "tier": "green",
     "moic": 2.4, "irr": 0.21, "leverage": 5.0, "headroom": 2.0,
     "exit_mult": 12.0, "hold": 5.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_6", "core"],
     "note": "Global fertility / IVF network; KKR acquired 2017.",
     "src": "https://www.ivirma.com/"},
    {"id": "covenant", "name": "Covenant Physician Partners", "sector": "asc",
     "year": 2017, "ev_mm": 700, "ev_real": False, "mult": 13.0, "tier": "green",
     "moic": 2.6, "irr": 0.23, "leverage": 5.2, "headroom": 1.6,
     "exit_mult": 14.0, "hold": 5.0, "outcome": "exited", "owner": "JD",
     "tags": ["fund_6", "exited"],
     "note": "Ambulatory surgery centers + physician practices; KKR 2017, exited.",
     "src": "https://www.covenantphysicianpartners.com/"},
    {"id": "heartland", "name": "Heartland Dental", "sector": "dental",
     "year": 2018, "ev_mm": 2800, "ev_real": False, "mult": 14.0, "tier": "amber",
     "moic": 1.7, "irr": 0.11, "leverage": 6.2, "headroom": 0.7,
     "exit_mult": 14.0, "hold": 6.0, "outcome": "active", "owner": "AT",
     "tags": ["fund_7", "roll-up", "watch"],
     "note": "Largest US dental support organization; KKR acquired 2018 (levered DSO).",
     "src": "https://www.heartland.com/"},
    {"id": "gmr", "name": "Global Medical Response", "sector": "ems",
     "year": 2017, "ev_mm": 2400, "ev_real": False, "mult": 8.0, "tier": "amber",
     "moic": 1.5, "irr": 0.09, "leverage": 6.8, "headroom": 0.4,
     "exit_mult": 8.0, "hold": 7.0, "outcome": "active", "owner": "AT",
     "tags": ["fund_6", "watch"],
     "note": "Air + ground medical transport (AMR/Air Methods); KKR 2017 — capital-intensive, levered.",
     "src": "https://www.globalmedicalresponse.com/"},
    {"id": "therapy_brands", "name": "Therapy Brands", "sector": "rcm_healthtech",
     "year": 2021, "ev_mm": 1200, "ev_real": True, "mult": 20.0, "tier": "amber",
     "moic": 1.6, "irr": 0.12, "leverage": 6.0, "headroom": 0.6,
     "exit_mult": 19.0, "hold": 4.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_7", "software"],
     "note": "Behavioral-health practice-management + EHR SaaS; KKR acquired 2021 (~$1.2B).",
     "src": "https://therapybrands.com/"},
    {"id": "headlands", "name": "Headlands Research", "sector": "other_services",
     "year": 2018, "ev_mm": 400, "ev_real": False, "mult": 14.0, "tier": "amber",
     "moic": 1.5, "irr": 0.08, "leverage": 5.0, "headroom": 0.8,
     "exit_mult": 13.0, "hold": 6.0, "outcome": "active", "owner": "JD",
     "tags": ["fund_7", "de_novo"],
     "note": "Clinical-trial site network; KKR-built platform (2018).",
     "src": "https://www.headlandsresearch.com/"},
    {"id": "bluesprig", "name": "BlueSprig Pediatrics", "sector": "behavioral_health",
     "year": 2017, "ev_mm": 500, "ev_real": False, "mult": 14.0, "tier": "amber",
     "moic": 1.6, "irr": 0.09, "leverage": 5.5, "headroom": 0.5,
     "exit_mult": 13.0, "hold": 6.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_6", "autism", "watch"],
     "note": "Autism / ABA therapy for children; KKR-backed platform (2017).",
     "src": "https://www.bluesprigpediatrics.com/"},
    {"id": "geode", "name": "Geode Health", "sector": "behavioral_health",
     "year": 2021, "ev_mm": 300, "ev_real": False, "mult": 18.0, "tier": "amber",
     "moic": 1.4, "irr": 0.10, "leverage": 4.5, "headroom": 1.0,
     "exit_mult": 18.0, "hold": 4.0, "outcome": "active", "owner": "JD",
     "tags": ["fund_7", "de_novo"],
     "note": "Outpatient mental-health platform; KKR-formed (2021), early growth.",
     "src": "https://geodehealth.com/"},
    {"id": "infinx", "name": "Infinx", "sector": "rcm_healthtech",
     "year": 2024, "ev_mm": 500, "ev_real": False, "mult": 16.0, "tier": "green",
     "moic": 1.2, "irr": 0.18, "leverage": 4.0, "headroom": 2.2,
     "exit_mult": 17.0, "hold": 1.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_8", "software", "new"],
     "note": "AI-driven revenue-cycle automation; KKR growth investment (2024).",
     "src": "https://www.infinx.com/"},
]


# Per-tier RCM KPI baselines (percent metrics on a 0-100 scale, matching the
# RCM_METRIC_REGISTRY benchmark scale used by demo.py). Worse tiers -> higher
# denial / AR / cost-to-collect; better tiers -> cleaner.
_TIER_RCM = {
    "red":   {"denial_rate": 14.2, "final_denial_rate": 6.1, "days_in_ar": 58.4,
              "ar_over_90_pct": 22.4, "clean_claim_rate": 84.2, "net_collection_rate": 91.8,
              "dnfb_days": 7.8, "charge_lag_days": 4.2, "cost_to_collect": 4.1},
    "amber": {"denial_rate": 11.2, "final_denial_rate": 4.2, "days_in_ar": 51.0,
              "ar_over_90_pct": 17.2, "clean_claim_rate": 88.6, "net_collection_rate": 94.0,
              "dnfb_days": 6.0, "charge_lag_days": 3.4, "cost_to_collect": 3.3},
    "green": {"denial_rate": 7.4, "final_denial_rate": 2.1, "days_in_ar": 41.2,
              "ar_over_90_pct": 11.0, "clean_claim_rate": 93.0, "net_collection_rate": 96.5,
              "dnfb_days": 4.0, "charge_lag_days": 2.3, "cost_to_collect": 2.5},
}
# Quarterly EBITDA actual / plan factor by tier (variance showcase).
_TIER_ACTUAL = {"red": 0.70, "amber": 0.93, "green": 1.05}


def _rcm_for(tier: str, idx: int) -> Dict[str, Dict[str, Any]]:
    """RCM observed-metrics block for a deal, with small deterministic per-deal
    jitter so cards aren't identical. Wrapped in the ObservedMetric shape
    (value + quality_flags) the packet builder expects."""
    base = _TIER_RCM.get(tier, _TIER_RCM["amber"])
    out: Dict[str, Dict[str, Any]] = {}
    for j, (k, v) in enumerate(base.items()):
        jitter = ((idx * 7 + j * 3) % 5 - 2) * 0.1  # -0.2..+0.2, deterministic
        out[k] = {"value": round(v + jitter, 2), "quality_flags": []}
    return out


def entry_ebitda_mm(spec: Dict[str, Any]) -> int:
    """Entry EBITDA ($M) implied by EV / entry multiple."""
    return int(round(spec["ev_mm"] / spec["mult"]))


def seed_kkr_demo(store: Any, run_dir: Optional[str] = None) -> int:
    """Seed the KKR demo portfolio into ``store`` (idempotent upserts).

    Mirrors ``demo.py``'s seeding so the command center / portfolio map / alerts
    / deal pages render fully. ``run_dir`` holds the staged PE artifacts the
    snapshot reader consumes; a temp dir is created if not supplied.

    Returns the number of deals seeded.
    """
    from ..portfolio.portfolio_snapshots import register_snapshot
    from ..pe.hold_tracking import record_quarterly_actuals
    from ..deals.deal_tags import add_tag
    from ..deals.deal_owners import assign_owner
    from ..deals.health_score import compute_health
    try:
        from ..deals.health_score import _record_history
    except Exception:  # noqa: BLE001
        _record_history = None
    try:
        from ..deals.watchlist import star_deal
    except Exception:  # noqa: BLE001
        star_deal = None

    if run_dir is None:
        run_dir = tempfile.mkdtemp(prefix="kkr_demo_")
    os.makedirs(run_dir, exist_ok=True)
    today = date.today()

    for idx, spec in enumerate(KKR_DEMO_DEALS):
        did = spec["id"]
        ebitda = entry_ebitda_mm(spec) * 1e6
        ev = spec["ev_mm"] * 1e6
        # Deal record + RCM observed metrics + light provenance profile.
        store.upsert_deal(
            did, name=spec["name"],
            profile={
                "observed_metrics": _rcm_for(spec["tier"], idx),
                "sector": spec["sector"],
                "sponsor": "KKR",
                "vintage": spec["year"],
                "source_url": spec["src"],
                "ev_disclosed": bool(spec["ev_real"]),
                "demo": "kkr",
            },
        )
        # Stage PE artifacts the snapshot reader consumes (demo.py format).
        ddir = os.path.join(run_dir, did + "_run")
        os.makedirs(ddir, exist_ok=True)
        with open(os.path.join(ddir, "pe_bridge.json"), "w") as f:
            json.dump({"entry_ebitda": ebitda, "entry_ev": ev,
                       "entry_multiple": spec["mult"], "exit_multiple": spec["exit_mult"],
                       "hold_years": spec["hold"]}, f)
        with open(os.path.join(ddir, "pe_returns.json"), "w") as f:
            json.dump({"moic": spec["moic"], "irr": spec["irr"]}, f)
        with open(os.path.join(ddir, "pe_covenant.json"), "w") as f:
            json.dump({"actual_leverage": spec["leverage"],
                       "covenant_headroom_turns": spec["headroom"]}, f)
        # Concerning trend signals for the stressed deals (drives clustering).
        n_concern = {"red": 5, "amber": 2, "green": 0}[spec["tier"]]
        if n_concern:
            try:
                import pandas as pd
                pd.DataFrame({"severity": ["concerning"] * n_concern + ["neutral"]}
                             ).to_csv(os.path.join(ddir, "trend_signals.csv"), index=False)
            except Exception:  # noqa: BLE001
                pass
        register_snapshot(store, did, "hold", run_dir=ddir,
                          notes=f"{spec['year']} KKR entry · {spec['name']}")

        # Quarterly actuals vs plan (variance + alerts).
        q_plan = round(ebitda / 4 * 1.05)
        q_actual = round(q_plan * _TIER_ACTUAL[spec["tier"]])
        record_quarterly_actuals(store, did, "2026Q1",
                                  actuals={"ebitda": q_actual}, plan={"ebitda": q_plan})

        for t in spec["tags"]:
            add_tag(store, deal_id=did, tag=t)
        assign_owner(store, deal_id=did, owner=spec["owner"])
        if star_deal and spec["tier"] in ("red", "amber"):
            try:
                star_deal(store, did)
            except Exception:  # noqa: BLE001
                pass

    # Health-score history so trend arrows render.
    if _record_history is not None:
        for spec in KKR_DEMO_DEALS:
            try:
                h = compute_health(store, spec["id"])
                if h.get("score") is not None:
                    _record_history(store, spec["id"], min(100, h["score"] + 8),
                                    h["band"], today=today - timedelta(days=1))
            except Exception:  # noqa: BLE001
                pass
    return len(KKR_DEMO_DEALS)


def demo_deal_rows() -> List[Dict[str, Any]]:
    """Flat, JSON/CSV-friendly rows for the downloadable demo-ingestion files
    (and a quick programmatic view of the portfolio)."""
    rows = []
    for s in KKR_DEMO_DEALS:
        rows.append({
            "deal_id": s["id"], "name": s["name"], "sponsor": "KKR",
            "sector": s["sector"], "vintage": s["year"],
            "entry_ev_mm": s["ev_mm"], "ev_disclosed": bool(s["ev_real"]),
            "entry_ebitda_mm": entry_ebitda_mm(s),
            "entry_multiple": s["mult"], "exit_multiple": s["exit_mult"],
            "hold_years": s["hold"], "leverage_turns": s["leverage"],
            "covenant_headroom_turns": s["headroom"],
            "moic": s["moic"], "irr": s["irr"], "outcome": s["outcome"],
            "performance_tier": s["tier"], "source_url": s["src"],
        })
    return rows

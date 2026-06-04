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
    {"id": "gland_pharma", "name": "Gland Pharma", "sector": "other_services",
     "year": 2017, "ev_mm": 1100, "ev_real": False, "mult": 12.0, "tier": "green",
     "moic": 4.0, "irr": 0.40, "leverage": 3.0, "headroom": 2.6,
     "exit_mult": 18.0, "hold": 3.0, "outcome": "exited", "owner": "JD",
     "tags": ["fund_6", "exited", "pharma"],
     "note": "Injectable-generics CDMO; KKR 2017, exited via 2020 IPO — a ~4x KKR win (the upside bookend to Envision).",
     "src": "https://www.glandpharma.com/"},
    {"id": "one_call", "name": "One Call", "sector": "other_services",
     "year": 2019, "ev_mm": 2000, "ev_real": False, "mult": 9.0, "tier": "amber",
     "moic": 1.3, "irr": 0.07, "leverage": 6.5, "headroom": 0.5,
     "exit_mult": 9.0, "hold": 6.0, "outcome": "active", "owner": "AT",
     "tags": ["fund_7", "watch"],
     "note": "Workers'-comp specialized-care management; KKR + Blackstone Credit principal shareholders via 2019 recap.",
     "src": "https://onecallcm.com/"},
    {"id": "contacts1800", "name": "1-800 Contacts", "sector": "ophthalmology",
     "year": 2020, "ev_mm": 3000, "ev_real": False, "mult": 11.0, "tier": "green",
     "moic": 1.9, "irr": 0.14, "leverage": 5.5, "headroom": 1.7,
     "exit_mult": 12.0, "hold": 4.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_7", "consumer"],
     "note": "Direct-to-consumer contact-lens retail + vision tech; KKR acquired from AEA Investors 2020.",
     "src": "https://www.1800contacts.com/"},
    {"id": "clarify_health", "name": "Clarify Health", "sector": "rcm_healthtech",
     "year": 2018, "ev_mm": 300, "ev_real": False, "mult": 0.0, "tier": "green",
     "moic": 1.5, "irr": 0.16, "leverage": 0.5, "headroom": 3.0,
     "exit_mult": 0.0, "hold": 6.0, "outcome": "active", "owner": "SB",
     "tags": ["fund_growth", "software", "vbc"],
     "note": "Value-based-care analytics / patient-journey intelligence; KKR-led growth financing (2018+).",
     "src": "https://clarifyhealth.com/"},
]


# Per-tier RCM KPI baselines (percent metrics on a 0-100 scale, matching the
# RCM_METRIC_REGISTRY benchmark scale used by demo.py). Worse tiers -> higher
# denial / AR / cost-to-collect; better tiers -> cleaner. Calibrated so the
# derived RCM EBITDA-bridge opportunity lands in a *credible* band (red ~5%,
# amber ~4%, green ~2.4% of net revenue) rather than the implausible double-
# digit figure that an exaggerated gap-to-benchmark would imply. The dramatic
# red/amber/green health spread comes from covenant + variance signals (see
# health_score.py), not these KPIs, so a tight, believable RCM spread here
# doesn't flatten the command center.
_TIER_RCM = {
    "red":   {"denial_rate": 8.6, "final_denial_rate": 3.3, "days_in_ar": 46.0,
              "ar_over_90_pct": 14.0, "clean_claim_rate": 90.8, "net_collection_rate": 94.7,
              "dnfb_days": 5.2, "charge_lag_days": 3.0, "cost_to_collect": 3.0},
    "amber": {"denial_rate": 8.0, "final_denial_rate": 2.9, "days_in_ar": 44.5,
              "ar_over_90_pct": 13.2, "clean_claim_rate": 91.8, "net_collection_rate": 95.4,
              "dnfb_days": 4.8, "charge_lag_days": 2.7, "cost_to_collect": 2.85},
    "green": {"denial_rate": 7.4, "final_denial_rate": 2.1, "days_in_ar": 41.2,
              "ar_over_90_pct": 11.0, "clean_claim_rate": 93.0, "net_collection_rate": 96.5,
              "dnfb_days": 4.0, "charge_lag_days": 2.3, "cost_to_collect": 2.5},
}
# Quarterly EBITDA actual / plan factor by tier (variance showcase). This is
# the *latest* quarter's headline variance — the health score reads it, so it
# must stay put.
_TIER_ACTUAL = {"red": 0.70, "amber": 0.93, "green": 1.05}

# Operating history: the trailing quarters we seed actuals-vs-plan for so the
# EBITDA trajectory chart, the variance drill-down and the health-trend
# sparkline all have a real time series instead of a single point. Ends at
# 2026Q1 (the latest), whose variance equals _TIER_ACTUAL above so the health
# bands are unchanged from the single-quarter seed.
_HIST_QUARTERS = ["2024Q3", "2024Q4", "2025Q1", "2025Q2",
                  "2025Q3", "2025Q4", "2026Q1"]
# (start, end) actual/plan ratio across the history window, per tier. ``end``
# equals _TIER_ACTUAL. The arc tells each deal's story: greens compound a
# beat, ambers drift from on-plan into a miss, reds slide toward distress.
_TIER_TRAJECTORY = {"red": (0.96, 0.70), "amber": (1.02, 0.93), "green": (1.00, 1.05)}
_PLAN_QOQ_GROWTH = 1.02  # underwritten plan steps up ~2%/quarter


def _seed_quarterly_history(record_fn, store: Any, deal_id: str, tier: str,
                            entry_ebitda: float, net_revenue: float) -> None:
    """Record ``_HIST_QUARTERS`` of EBITDA + NPSR actuals-vs-plan for a deal.

    The plan steps up ~2%/quarter; the actual/plan ratio walks linearly from
    the tier's start factor to its end factor (== _TIER_ACTUAL), so the latest
    quarter is identical to the prior single-quarter seed (health unchanged)
    while the earlier quarters give the trajectory + variance surfaces a real
    series to draw. Best-effort per quarter so one bad row can't abort seeding.
    """
    n = len(_HIST_QUARTERS)
    start, end = _TIER_TRAJECTORY.get(tier, _TIER_TRAJECTORY["amber"])
    last_plan_eb = round(entry_ebitda / 4 * 1.05)
    last_plan_npsr = round(net_revenue / 4 * 1.05)
    for i, q in enumerate(_HIST_QUARTERS):
        frac = i / (n - 1) if n > 1 else 1.0
        factor = start + (end - start) * frac
        grow = _PLAN_QOQ_GROWTH ** (n - 1 - i)   # plan was lower earlier
        plan_eb = round(last_plan_eb / grow)
        plan_npsr = round(last_plan_npsr / grow)
        try:
            record_fn(store, deal_id, q,
                      actuals={"ebitda": round(plan_eb * factor),
                               "net_patient_revenue": round(plan_npsr * factor)},
                      plan={"ebitda": plan_eb, "net_patient_revenue": plan_npsr})
        except Exception:  # noqa: BLE001
            pass


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
    """Entry EBITDA ($M) implied by EV / entry multiple. Returns 0 for
    growth-equity deals carried at ``mult == 0`` (pre-profit SaaS, e.g. a
    value-based-care analytics platform) where an EBITDA multiple doesn't apply."""
    mult = spec.get("mult") or 0
    if mult <= 0:
        return 0
    return int(round(spec["ev_mm"] / mult))


# Headquarters US state for the geographic portfolio map (/portfolio/map shades
# states by deal count). Real HQ where disclosed; otherwise the company's
# principal US location. Gland Pharma is India-based (Hyderabad) so it carries
# no US state and is honestly omitted from the US map rather than faked.
_HQ_STATE = {
    "envision": "TN", "cotiviti": "GA", "brightspring": "KY", "petvet": "CT",
    "ivirma": "NJ", "covenant": "TN", "heartland": "IL", "gmr": "CO",
    "therapy_brands": "AL", "headlands": "CA", "bluesprig": "TX", "geode": "IL",
    "infinx": "CA", "gland_pharma": "", "one_call": "FL", "contacts1800": "UT",
    "clarify_health": "CA",
}

# Sector-typical EBITDA margin used only to back into an illustrative net
# revenue base for the RCM EBITDA-bridge dollar math (the platform's core
# value lever). Software/health-tech run richer margins than capital-intensive
# services. Default 0.15 for clinical-services roll-ups.
_SECTOR_MARGIN = {"rcm_healthtech": 0.30, "ems": 0.12, "other_services": 0.13}
# Blended net revenue per patient encounter / claim ($), to size claims volume.
_REV_PER_CLAIM = 300.0


def bridge_financials(spec: Dict[str, Any]) -> Dict[str, float]:
    """Illustrative net-revenue base + claims volume for the RCM EBITDA bridge.

    Backed into from entry EBITDA at a sector-typical margin so the bridge's
    dollar opportunity (denial-rate / AR / cost-to-collect uplift) is non-zero
    and scaled to the deal — worse-tier deals carry worse RCM KPIs and so a
    larger improvement opportunity. Modeled, not disclosed; seeded as analyst
    overrides so the figure survives the server's packet rebuilds."""
    eb_mm = entry_ebitda_mm(spec)
    if eb_mm <= 0:
        # Growth-equity / pre-profit (e.g. a VBC analytics platform): use an
        # EV-implied revenue proxy rather than an EBITDA-margin back-in.
        net_rev_mm = round(spec["ev_mm"] * 0.30)
    else:
        margin = _SECTOR_MARGIN.get(spec["sector"], 0.15)
        net_rev_mm = round(eb_mm / margin)
    net_rev = float(net_rev_mm) * 1e6
    return {"net_revenue": net_rev, "claims_volume": float(int(net_rev / _REV_PER_CLAIM))}


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
    # Optional: seed an analysis packet per deal so the packet-driven surfaces
    # (geographic /portfolio/map, /portfolio/heatmap, the analysis workbench
    # cache) light up — list_packets() only returns *persisted* packets, and
    # nothing in the base seed builds one. Built with the same args the server
    # uses (skip_simulation=True) so the seeded row is a warm cache hit later.
    try:
        from ..analysis.analysis_store import get_or_build_packet
        from ..analysis.deal_overrides import set_override
    except Exception:  # noqa: BLE001
        get_or_build_packet = None
        set_override = None

    if run_dir is None:
        run_dir = tempfile.mkdtemp(prefix="kkr_demo_")
    os.makedirs(run_dir, exist_ok=True)
    today = date.today()

    for idx, spec in enumerate(KKR_DEMO_DEALS):
        did = spec["id"]
        ebitda = entry_ebitda_mm(spec) * 1e6
        ev = spec["ev_mm"] * 1e6
        # Deal record + RCM observed metrics + light provenance profile.
        profile = {
            "observed_metrics": _rcm_for(spec["tier"], idx),
            "sector": spec["sector"],
            "sponsor": "KKR",
            "vintage": spec["year"],
            "source_url": spec["src"],
            "ev_disclosed": bool(spec["ev_real"]),
            "demo": "kkr",
        }
        # HQ state powers the geographic /portfolio/map (it shades states by
        # deal count). Only set when known — Gland Pharma (India) stays off the
        # US map rather than being placed in a fake state.
        st = _HQ_STATE.get(did, "")
        if st:
            profile["state"] = st
        store.upsert_deal(did, name=spec["name"], profile=profile)
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

        # Quarterly actuals vs plan across a trailing history window (variance
        # drill-down + EBITDA trajectory + health-trend sparkline). The latest
        # quarter preserves the tier's headline variance so health is unchanged.
        _seed_quarterly_history(record_quarterly_actuals, store, did,
                                spec["tier"], ebitda,
                                bridge_financials(spec)["net_revenue"])

        for t in spec["tags"]:
            add_tag(store, deal_id=did, tag=t)
        assign_owner(store, deal_id=did, owner=spec["owner"])
        if star_deal and spec["tier"] in ("red", "amber"):
            try:
                star_deal(store, did)
            except Exception:  # noqa: BLE001
                pass

        # Illustrative revenue base → non-zero RCM EBITDA-bridge opportunity.
        # Seeded as bridge-namespace overrides so the figure persists through
        # the server's packet rebuilds (overrides are part of the cache key).
        if set_override is not None:
            try:
                fin = bridge_financials(spec)
                set_override(store, did, "bridge.net_revenue",
                             fin["net_revenue"], set_by="demo",
                             reason="KKR demo — illustrative net revenue base")
                set_override(store, did, "bridge.claims_volume",
                             fin["claims_volume"], set_by="demo",
                             reason="KKR demo — illustrative claims volume")
            except Exception:  # noqa: BLE001
                pass
        # Persist the analysis packet (warms the cache; lights up the map /
        # heatmap / workbench). Best-effort: never let it break the seed.
        if get_or_build_packet is not None:
            try:
                get_or_build_packet(store, did, skip_simulation=True)
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

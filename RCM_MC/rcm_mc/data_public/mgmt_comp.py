"""Management Compensation Analyzer — rollover equity, options, MIP economics.

PE healthcare deals typically feature:
- Management rollover equity (5-15% of deal equity)
- Stock option pool (7-12% of fully diluted equity, multi-year vesting)
- Performance-based restricted stock
- Sale bonus / earnout pool
- Executive-specific carry
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Benchmark compensation data by size bucket
# ---------------------------------------------------------------------------

_COMP_BENCHMARKS = {
    "<$100M": {
        "ceo_base_k": 425, "ceo_bonus_pct": 0.45, "ceo_rollover_pct": 0.08,
        "cfo_base_k": 280, "cfo_bonus_pct": 0.35, "cfo_rollover_pct": 0.015,
        "option_pool_pct": 0.10, "mip_pct_of_gain": 0.08,
    },
    "$100-250M": {
        "ceo_base_k": 550, "ceo_bonus_pct": 0.55, "ceo_rollover_pct": 0.06,
        "cfo_base_k": 340, "cfo_bonus_pct": 0.40, "cfo_rollover_pct": 0.012,
        "option_pool_pct": 0.10, "mip_pct_of_gain": 0.08,
    },
    "$250-500M": {
        "ceo_base_k": 725, "ceo_bonus_pct": 0.65, "ceo_rollover_pct": 0.05,
        "cfo_base_k": 420, "cfo_bonus_pct": 0.45, "cfo_rollover_pct": 0.010,
        "option_pool_pct": 0.09, "mip_pct_of_gain": 0.075,
    },
    "$500M-1B": {
        "ceo_base_k": 925, "ceo_bonus_pct": 0.75, "ceo_rollover_pct": 0.04,
        "cfo_base_k": 525, "cfo_bonus_pct": 0.50, "cfo_rollover_pct": 0.008,
        "option_pool_pct": 0.08, "mip_pct_of_gain": 0.07,
    },
    ">$1B": {
        "ceo_base_k": 1200, "ceo_bonus_pct": 0.85, "ceo_rollover_pct": 0.03,
        "cfo_base_k": 685, "cfo_bonus_pct": 0.60, "cfo_rollover_pct": 0.006,
        "option_pool_pct": 0.07, "mip_pct_of_gain": 0.065,
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExecutiveComp:
    role: str
    base_salary_k: float
    target_bonus_pct: float
    target_bonus_k: float
    total_cash_k: float
    rollover_equity_pct: float
    rollover_value_mm: float
    options_pct: float
    options_fair_value_mm: float
    total_at_risk_mm: float


@dataclass
class MIPTranche:
    tranche: str                 # "Time Vest", "Performance Vest 2x MOIC", etc.
    allocation_pct: float
    vesting_type: str
    hurdle: str
    expected_payout_moic2: float    # at 2x MOIC exit
    expected_payout_moic3: float    # at 3x MOIC exit


@dataclass
class ExitScenarioPayout:
    scenario: str                # "2x MOIC", "3x MOIC", "4x MOIC"
    exit_equity_mm: float
    lp_net_mm: float
    gp_carry_mm: float
    mgmt_rollover_payout_mm: float
    mgmt_options_payout_mm: float
    mip_pool_payout_mm: float
    total_mgmt_payout_mm: float
    pct_going_to_mgmt: float


@dataclass
class MgmtCompResult:
    ev_mm: float
    equity_mm: float
    size_bucket: str
    executives: List[ExecutiveComp]
    mip_tranches: List[MIPTranche]
    exit_scenarios: List[ExitScenarioPayout]
    total_rollover_mm: float
    total_option_pool_mm: float
    total_mip_pool_mm: float
    blended_alignment_score: float     # 0-100
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 60):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _size_bucket(ev_mm: float) -> str:
    if ev_mm < 100: return "<$100M"
    if ev_mm < 250: return "$100-250M"
    if ev_mm < 500: return "$250-500M"
    if ev_mm < 1000: return "$500M-1B"
    return ">$1B"


def _build_executives(ev_mm: float, equity_mm: float, bucket: str) -> List[ExecutiveComp]:
    b = _COMP_BENCHMARKS[bucket]

    # CEO
    ceo_base = b["ceo_base_k"]
    ceo_bonus = ceo_base * b["ceo_bonus_pct"]
    ceo_cash = ceo_base + ceo_bonus
    ceo_roll_pct = b["ceo_rollover_pct"]
    ceo_roll_mm = equity_mm * ceo_roll_pct
    # CEO options ~ 30% of option pool
    ceo_opt_pct = b["option_pool_pct"] * 0.30
    ceo_opt_fv = equity_mm * ceo_opt_pct * 0.35   # Black-Scholes FV ~ 35% of underlying
    ceo_total_risk = ceo_roll_mm + ceo_opt_fv

    # CFO
    cfo_base = b["cfo_base_k"]
    cfo_bonus = cfo_base * b["cfo_bonus_pct"]
    cfo_cash = cfo_base + cfo_bonus
    cfo_roll_pct = b["cfo_rollover_pct"]
    cfo_roll_mm = equity_mm * cfo_roll_pct
    cfo_opt_pct = b["option_pool_pct"] * 0.12
    cfo_opt_fv = equity_mm * cfo_opt_pct * 0.35
    cfo_total_risk = cfo_roll_mm + cfo_opt_fv

    # Other executives (COO, CMO, VP aggregate)
    other_roll_pct = b["option_pool_pct"] * 0.25 * 0.5   # rollover portion
    other_roll_mm = equity_mm * other_roll_pct
    other_opt_pct = b["option_pool_pct"] * 0.58    # remaining option pool
    other_opt_fv = equity_mm * other_opt_pct * 0.35

    return [
        ExecutiveComp(
            role="CEO",
            base_salary_k=round(ceo_base, 0),
            target_bonus_pct=round(b["ceo_bonus_pct"], 2),
            target_bonus_k=round(ceo_bonus, 0),
            total_cash_k=round(ceo_cash, 0),
            rollover_equity_pct=round(ceo_roll_pct, 4),
            rollover_value_mm=round(ceo_roll_mm, 2),
            options_pct=round(ceo_opt_pct, 4),
            options_fair_value_mm=round(ceo_opt_fv, 2),
            total_at_risk_mm=round(ceo_total_risk, 2),
        ),
        ExecutiveComp(
            role="CFO",
            base_salary_k=round(cfo_base, 0),
            target_bonus_pct=round(b["cfo_bonus_pct"], 2),
            target_bonus_k=round(cfo_bonus, 0),
            total_cash_k=round(cfo_cash, 0),
            rollover_equity_pct=round(cfo_roll_pct, 4),
            rollover_value_mm=round(cfo_roll_mm, 2),
            options_pct=round(cfo_opt_pct, 4),
            options_fair_value_mm=round(cfo_opt_fv, 2),
            total_at_risk_mm=round(cfo_total_risk, 2),
        ),
        ExecutiveComp(
            role="Other Execs (COO, CMO, VPs)",
            base_salary_k=round(b["cfo_base_k"] * 0.75 * 4, 0),    # 4 combined
            target_bonus_pct=round(b["cfo_bonus_pct"] * 0.80, 2),
            target_bonus_k=round(b["cfo_base_k"] * 0.75 * 4 * b["cfo_bonus_pct"] * 0.80, 0),
            total_cash_k=round(b["cfo_base_k"] * 0.75 * 4 * (1 + b["cfo_bonus_pct"] * 0.80), 0),
            rollover_equity_pct=round(other_roll_pct, 4),
            rollover_value_mm=round(other_roll_mm, 2),
            options_pct=round(other_opt_pct, 4),
            options_fair_value_mm=round(other_opt_fv, 2),
            total_at_risk_mm=round(other_roll_mm + other_opt_fv, 2),
        ),
    ]


def _build_mip_tranches(bucket: str) -> List[MIPTranche]:
    b = _COMP_BENCHMARKS[bucket]
    mip_total_pct = b["mip_pct_of_gain"]
    return [
        MIPTranche(
            tranche="Time-Vest (5-yr)",
            allocation_pct=round(mip_total_pct * 0.30, 4),
            vesting_type="Ratable",
            hurdle="Continued employment",
            expected_payout_moic2=round(mip_total_pct * 0.30 * 100, 2),
            expected_payout_moic3=round(mip_total_pct * 0.30 * 200, 2),
        ),
        MIPTranche(
            tranche="Perf-Vest 2x MOIC",
            allocation_pct=round(mip_total_pct * 0.35, 4),
            vesting_type="Cliff + threshold",
            hurdle="2.0x MOIC to sponsor",
            expected_payout_moic2=round(mip_total_pct * 0.35 * 100, 2),
            expected_payout_moic3=round(mip_total_pct * 0.35 * 200, 2),
        ),
        MIPTranche(
            tranche="Perf-Vest 3x MOIC",
            allocation_pct=round(mip_total_pct * 0.25, 4),
            vesting_type="Cliff + threshold",
            hurdle="3.0x MOIC to sponsor",
            expected_payout_moic2=0.0,    # threshold not met
            expected_payout_moic3=round(mip_total_pct * 0.25 * 200, 2),
        ),
        MIPTranche(
            tranche="IRR Kicker (25% IRR)",
            allocation_pct=round(mip_total_pct * 0.10, 4),
            vesting_type="Cliff",
            hurdle="25% IRR to sponsor",
            expected_payout_moic2=0.0,
            expected_payout_moic3=round(mip_total_pct * 0.10 * 200, 2),
        ),
    ]


def _build_exit_scenarios(
    equity_mm: float,
    executives: List[ExecutiveComp],
    mip_tranches: List[MIPTranche],
    bucket: str,
) -> List[ExitScenarioPayout]:
    scenarios = []
    total_rollover = sum(e.rollover_value_mm for e in executives)
    total_option_pct = sum(e.options_pct for e in executives)

    for label, moic in [("2x MOIC", 2.0), ("3x MOIC", 3.0), ("4x MOIC", 4.0)]:
        exit_equity = equity_mm * moic
        gain = exit_equity - equity_mm
        # LP/GP split: 20% carry above 8% hurdle
        hurdle = equity_mm * ((1.08 ** 5) - 1)    # assume 5-yr hold
        carry_base = max(0, gain - hurdle)
        gp_carry = carry_base * 0.20
        lp_net = exit_equity - gp_carry

        # Mgmt payouts
        # Rollover: grows with exit, net of carry
        rollover_payout = total_rollover * moic * 0.90    # net of carry friction
        # Options: (exit value - strike) × option pool; strike ≈ entry
        option_gain_per_share = max(0, moic - 1.0)
        option_payout = equity_mm * total_option_pct * option_gain_per_share
        # MIP pool
        if moic >= 3.0:
            mip_pool = sum(t.expected_payout_moic3 for t in mip_tranches) / 100 * gain
        elif moic >= 2.0:
            mip_pool = sum(t.expected_payout_moic2 for t in mip_tranches) / 100 * gain
        else:
            mip_pool = 0.0

        total_mgmt = rollover_payout + option_payout + mip_pool
        pct_to_mgmt = total_mgmt / exit_equity if exit_equity else 0

        scenarios.append(ExitScenarioPayout(
            scenario=label,
            exit_equity_mm=round(exit_equity, 1),
            lp_net_mm=round(lp_net, 1),
            gp_carry_mm=round(gp_carry, 1),
            mgmt_rollover_payout_mm=round(rollover_payout, 2),
            mgmt_options_payout_mm=round(option_payout, 2),
            mip_pool_payout_mm=round(mip_pool, 2),
            total_mgmt_payout_mm=round(total_mgmt, 2),
            pct_going_to_mgmt=round(pct_to_mgmt, 4),
        ))
    return scenarios


def _alignment_score(executives: List[ExecutiveComp], equity_mm: float) -> float:
    """0-100 score of management alignment with sponsor."""
    if not executives or equity_mm <= 0:
        return 50.0
    ceo = executives[0]
    # Rollover as % of CEO total cash compensation (proxy for skin in game)
    ceo_cash_mm = ceo.total_cash_k / 1000
    rollover_to_cash = ceo.rollover_value_mm / ceo_cash_mm if ceo_cash_mm else 0
    # 3x multiple = good alignment; 10x = excellent
    ratio_score = min(100, rollover_to_cash * 10)

    # Total mgmt at-risk as % of equity (higher = better)
    total_at_risk = sum(e.total_at_risk_mm for e in executives)
    risk_pct = total_at_risk / equity_mm if equity_mm else 0
    # 10% = great, 5% = OK, 2% = weak
    risk_score = min(100, risk_pct * 1000)

    blended = (ratio_score * 0.55 + risk_score * 0.45)
    return round(min(max(blended, 0), 100), 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_mgmt_comp(
    ev_mm: float = 300.0,
    equity_pct: float = 0.45,
) -> MgmtCompResult:
    corpus = _load_corpus()
    bucket = _size_bucket(ev_mm)
    equity_mm = ev_mm * equity_pct

    executives = _build_executives(ev_mm, equity_mm, bucket)
    mip_tranches = _build_mip_tranches(bucket)
    scenarios = _build_exit_scenarios(equity_mm, executives, mip_tranches, bucket)

    total_rollover = sum(e.rollover_value_mm for e in executives)
    total_opt = sum(e.options_fair_value_mm for e in executives)
    total_mip = _COMP_BENCHMARKS[bucket]["mip_pct_of_gain"] * equity_mm
    score = _alignment_score(executives, equity_mm)

    return MgmtCompResult(
        ev_mm=round(ev_mm, 1),
        equity_mm=round(equity_mm, 1),
        size_bucket=bucket,
        executives=executives,
        mip_tranches=mip_tranches,
        exit_scenarios=scenarios,
        total_rollover_mm=round(total_rollover, 2),
        total_option_pool_mm=round(total_opt, 2),
        total_mip_pool_mm=round(total_mip, 2),
        blended_alignment_score=score,
        corpus_deal_count=len(corpus),
    )

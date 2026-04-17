from __future__ import annotations

from typing import Any, Dict, Tuple, List

import numpy as np
import pandas as pd

from ..infra.logger import logger
from ..infra.profile import align_benchmark_to_actual
from .distributions import sample_dirichlet, sample_dist, sample_sum_iid_as_gamma
from ..rcm.claim_distribution import build_lognormal_claim_buckets, denial_rate_by_bucket
from ..infra.capacity import assign_bucket_wait_days, compute_capacity


def _logit(p: float) -> float:
    p = float(np.clip(p, 1e-9, 1 - 1e-9))
    return float(np.log(p / (1 - p)))


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _normalize_probs(d: Dict[str, float]) -> Dict[str, float]:
    keys = list(d.keys())
    vals = np.array([max(float(d[k]), 0.0) for k in keys], dtype=float)
    s = float(vals.sum())
    if s <= 0:
        vals = np.ones(len(keys), dtype=float) / len(keys)
    else:
        vals = vals / s
    return {k: float(vals[i]) for i, k in enumerate(keys)}


def _apply_stage_bias(stage_mix: Dict[str, float], bias: Dict[str, float]) -> Dict[str, float]:
    """Apply additive stage bias; subtract mass proportionally from non-biased stages."""
    mix = {k: float(v) for k, v in stage_mix.items()}
    bias = bias or {}
    add_mass = 0.0
    biased_keys = set()
    for k, dv in bias.items():
        if k in mix:
            mix[k] = mix[k] + float(dv)
            add_mass += float(dv)
            biased_keys.add(k)
    if add_mass > 0:
        others = [k for k in mix.keys() if k not in biased_keys]
        if not others:
            others = list(mix.keys())
        tot_other = sum(max(mix[k], 0.0) for k in others)
        if tot_other > 1e-12:
            for k in others:
                frac = max(mix[k], 0.0) / tot_other
                mix[k] -= add_mass * frac
        else:
            mix[others[0]] -= add_mass
    return _normalize_probs(mix)


def _apply_backlog_stage_shift(
    stage_mix: Dict[str, float],
    shift: float,
    l2_share: float = 0.70,
) -> Dict[str, float]:
    """Shift a fraction of L1 into L2/L3 as backlog grows.

    l2_share controls what fraction of the shifted mass goes to L2 vs L3
    (default 0.70, i.e. 70/30 split). Configurable via
    config backlog.stage_shift_l2_share.
    """
    shift = float(np.clip(shift, 0.0, 0.80))
    l2_share = float(np.clip(l2_share, 0.0, 1.0))
    mix = _normalize_probs({k: float(v) for k, v in stage_mix.items()})

    p1 = mix.get("L1", 0.0)
    shift_mass = p1 * shift
    mix["L1"] = p1 - shift_mass

    mix["L2"] = mix.get("L2", 0.0) + l2_share * shift_mass
    mix["L3"] = mix.get("L3", 0.0) + (1.0 - l2_share) * shift_mass
    return _normalize_probs(mix)


def _expected_stage_mix_with_type_biases(
    *,
    stage_mix_base: Dict[str, float],
    type_mix: Dict[str, float],
    denial_types: Dict[str, Any],
) -> Dict[str, float]:
    acc = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    for t, t_share in (type_mix or {}).items():
        t_share = float(t_share)
        bias = {}
        if isinstance(denial_types, dict) and t in denial_types and isinstance(denial_types[t], dict):
            bias = denial_types[t].get("stage_bias", {}) or {}
        mix_t = _apply_stage_bias(stage_mix_base, bias)
        for s in ("L1", "L2", "L3"):
            acc[s] += t_share * float(mix_t.get(s, 0.0))
    return _normalize_probs(acc)


def _simulate_payer_pass1(cfg: Dict[str, Any], payer: str, rng: np.random.Generator) -> Dict[str, Any]:
    pconf = cfg["payers"][payer]
    R_total = float(cfg["hospital"]["annual_revenue"])
    R_p = R_total * float(pconf["revenue_share"])
    avg_claim = float(pconf["avg_claim_dollars"])

    dar_clean = float(sample_dist(rng, pconf["dar_clean_days"], size=None)[0])

    out: Dict[str, Any] = {
        "payer": payer,
        "revenue": R_p,
        "avg_claim": avg_claim,
        "dar_clean": dar_clean,
        "include_denials": bool(pconf.get("include_denials", False)),
        "include_underpayments": bool(pconf.get("include_underpayments", False)) and bool(cfg.get("underpayments", {}).get("enabled", True)),
    }

    # Denials
    if out["include_denials"]:
        d = pconf["denials"]
        idr = float(sample_dist(rng, d["idr"], size=None)[0])
        fwr_base = float(sample_dist(rng, d["fwr"], size=None)[0])

        base_type_shares = {t: float(tv.get("share", 0.0)) for t, tv in d["denial_types"].items()}
        conc = float(d.get("denial_mix_concentration", 120))
        type_mix = sample_dirichlet(rng, base_type_shares, concentration=conc)

        stage_mix_base = {k: float(v) for k, v in d["stage_mix"].items()}
        denial_types = d["denial_types"]

        # Leap 5: Claim-size buckets (optional)
        cd = pconf.get("claim_distribution", {}) or {}
        cd_enabled = bool(cd.get("enabled", False))
        denial_buckets: List[Dict[str, Any]] = []

        # Estimate annual claim count
        claim_count_est = (R_p / avg_claim) if avg_claim > 0 else 0.0

        if cd_enabled and claim_count_est > 0:
            cv = float(cd.get("cv", 1.25))
            qs = cd.get("bucket_quantiles", [0.0, 0.70, 0.90, 0.97, 1.0])
            beta = float(cd.get("size_denial_odds_beta", 0.60))
            _bucket_seed = int(rng.integers(0, 2**31))
            buckets = build_lognormal_claim_buckets(mean=avg_claim, cv=cv, quantiles=qs, seed=_bucket_seed)

            mean_amounts = [b.mean_amount for b in buckets]
            claim_weights = [max(b.share_claims, 0.0) for b in buckets]
            # Use claim weights for solving alpha so avg denial probability matches idr
            idr_b = denial_rate_by_bucket(
                idr_base=idr,
                bucket_mean_amounts=mean_amounts,
                avg_claim=avg_claim,
                beta=beta,
                bucket_weights=claim_weights,
            )

            for b, p_b in zip(buckets, idr_b):
                cc = claim_count_est * float(b.share_claims)
                lam = cc * float(p_b)
                cases = int(rng.poisson(lam)) if lam > 0 else 0
                dollars = float(cases) * float(b.mean_amount)
                denial_buckets.append(
                    {
                        "bucket_idx": int(b.idx),
                        "q_low": float(b.q_low),
                        "q_high": float(b.q_high),
                        "share_claims": float(b.share_claims),
                        "share_dollars": float(b.share_dollars),
                        "mean_amount": float(b.mean_amount),
                        "claim_count_est": float(cc),
                        "idr_bucket": float(p_b),
                        "denial_cases": int(cases),
                        "denied_dollars": float(dollars),
                        "x_log_size": float(np.log(float(b.mean_amount) / float(avg_claim))),
                    }
                )
        else:
            # Legacy: single bucket approximated by avg claim size
            lam = claim_count_est * idr
            cases = int(rng.poisson(lam)) if lam > 0 else 0
            dollars = float(cases) * avg_claim
            denial_buckets.append(
                {
                    "bucket_idx": 0,
                    "q_low": 0.0,
                    "q_high": 1.0,
                    "share_claims": 1.0,
                    "share_dollars": 1.0,
                    "mean_amount": float(avg_claim),
                    "claim_count_est": float(claim_count_est),
                    "idr_bucket": float(idr),
                    "denial_cases": int(cases),
                    "denied_dollars": float(dollars),
                    "x_log_size": 0.0,
                }
            )

        denial_cases = int(sum(int(b["denial_cases"]) for b in denial_buckets))
        denied_dollars = float(sum(float(b["denied_dollars"]) for b in denial_buckets))

        # Leap 4+: work-equivalent touches per case for capacity/queue math.
        cap = cfg.get("operations", {}).get("denial_capacity", {}) or {}
        touches_per_case_cfg = cap.get("touches_per_case", {"L1": 1.0, "L2": 3.0, "L3": 8.0})
        stage_mix_expected = _expected_stage_mix_with_type_biases(
            stage_mix_base=stage_mix_base,
            type_mix=type_mix,
            denial_types=denial_types,
        )
        touches_per_case = 0.0
        for s in ("L1", "L2", "L3"):
            touches_per_case += float(stage_mix_expected.get(s, 0.0)) * float(touches_per_case_cfg.get(s, 1.0))
        touches_per_case = float(max(touches_per_case, 0.10))

        out.update(
            {
                "idr": idr,
                "fwr_base": fwr_base,
                "type_mix": type_mix,
                "denied_dollars": denied_dollars,
                "denial_cases": denial_cases,
                "denial_buckets": denial_buckets,
                "stage_mix_base": stage_mix_base,
                "denial_types": denial_types,
                "touches_per_case": touches_per_case,
                "size_fwr_odds_beta": float(cd.get("size_fwr_odds_beta", -0.10)) if cd_enabled else 0.0,
            }
        )
    else:
        out.update(
            {
                "idr": 0.0,
                "fwr_base": 0.0,
                "type_mix": {},
                "denied_dollars": 0.0,
                "denial_cases": 0,
                "denial_buckets": [],
                "stage_mix_base": {},
                "denial_types": {},
                "touches_per_case": 0.0,
                "size_fwr_odds_beta": 0.0,
            }
        )

    # Underpayments (kept intentionally simple)
    if out["include_underpayments"]:
        u = pconf.get("underpayments", {})
        upr = float(sample_dist(rng, u["upr"], size=None)[0])
        sev = float(sample_dist(rng, u["severity"], size=None)[0])
        rec = float(sample_dist(rng, u["recovery"], size=None)[0])

        claims_est = R_p / avg_claim if avg_claim > 0 else 0.0
        upr_lambda = claims_est * upr
        underpay_cases = int(rng.poisson(upr_lambda)) if upr_lambda > 0 else 0
        underpaid_dollars = float(underpay_cases) * avg_claim * sev if underpay_cases > 0 else 0.0

        out.update(
            {
                "upr": upr,
                "underpay_severity": sev,
                "underpay_recovery": rec,
                "underpaid_dollars": underpaid_dollars,
                "underpay_cases": underpay_cases,
                "underpay_followup_cost_spec": u["followup_cost"],
                "underpay_resolution_days_spec": u["resolution_days"],
            }
        )
    else:
        out.update(
            {
                "upr": 0.0,
                "underpay_severity": 0.0,
                "underpay_recovery": 0.0,
                "underpaid_dollars": 0.0,
                "underpay_cases": 0,
                "underpay_followup_cost_spec": None,
                "underpay_resolution_days_spec": None,
            }
        )

    return out


def _simulate_payer_pass2(
    cfg: Dict[str, Any],
    payer_state: Dict[str, Any],
    rng: np.random.Generator,
    backlog_x: float,
    queue_wait_days_base: float,
) -> Dict[str, Any]:
    payer = payer_state["payer"]
    R_p = payer_state["revenue"]

    appeals = cfg["appeals"]["stages"]
    wacc = float(cfg["economics"]["wacc_annual"])

    cap = cfg["operations"]["denial_capacity"]
    backlog = cap.get("backlog", {})
    shift_per_x = float(backlog.get("stage_shift_per_x", 0.20))
    fwr_logit_penalty_per_x = float(backlog.get("fwr_logit_penalty_per_x", 0.60))
    days_mult_per_x = float(backlog.get("days_multiplier_per_x", 0.15))
    backlog_l2_share = float(backlog.get("stage_shift_l2_share", 0.70))

    stage_shift = shift_per_x * backlog_x
    fwr_logit_penalty = fwr_logit_penalty_per_x * backlog_x
    days_multiplier = 1.0 + days_mult_per_x * backlog_x

    qconf = cap.get("queue", {}) if isinstance(cap.get("queue", {}), dict) else {}
    mode = str(cap.get("mode", "annual_backlog")).strip().lower()
    priority = str(qconf.get("priority", "fifo")).strip().lower()
    max_fwr = float(cfg.get("analysis", {}).get("max_fwr", 0.98))

    # Denials
    denial_writeoff = 0.0
    fwr_weighted_num = 0.0
    fwr_weighted_den = 0.0
    fwr_realized = float(payer_state.get("fwr_base", 0.0))
    denial_rework_cost = 0.0
    denial_addl_days_sum = 0.0
    collectible_denied = 0.0

    denial_writeoff_by_type: Dict[str, float] = {}
    denial_cases_by_stage = {"L1": 0, "L2": 0, "L3": 0}
    denial_rework_cost_by_type: Dict[str, float] = {}
    denial_cases_by_type: Dict[str, int] = {}
    denial_rework_cost_by_stage = {"L1": 0.0, "L2": 0.0, "L3": 0.0}

    denied_dollars_total = float(payer_state.get("denied_dollars", 0.0))
    denial_cases_total = int(payer_state.get("denial_cases", 0))
    idr = float(payer_state.get("idr", 0.0))

    denial_buckets: List[Dict[str, Any]] = payer_state.get("denial_buckets", []) or []
    # Assign bucket-specific wait days (Leap 5)
    if mode == "queue" and bool(qconf.get("enabled", True)) and queue_wait_days_base > 0:
        assign_bucket_wait_days(denial_buckets, queue_wait_days_base=float(queue_wait_days_base), priority=priority)
    else:
        for b in denial_buckets:
            b["queue_wait_days"] = float(queue_wait_days_base)

    # Dollar-weighted queue delay (useful for IC / working-capital story)
    q_wait_dollar_wtd = 0.0
    if denied_dollars_total > 0:
        q_wait_dollar_wtd = float(sum(float(b.get("denied_dollars", 0.0)) * float(b.get("queue_wait_days", 0.0)) for b in denial_buckets) / denied_dollars_total)

    if payer_state.get("include_denials", False) and denial_buckets:
        type_keys = list(payer_state["type_mix"].keys())
        type_probs = np.array([payer_state["type_mix"][k] for k in type_keys], dtype=float)
        _tp_sum = type_probs.sum()
        if _tp_sum <= 0:
            logger.warning("type_mix sums to 0 for payer %s; using uniform", payer_state.get("payer", "?"))
            type_probs = np.ones(len(type_keys), dtype=float) / max(len(type_keys), 1)
        else:
            type_probs = type_probs / _tp_sum

        fwr_base = float(payer_state["fwr_base"])
        size_fwr_beta = float(payer_state.get("size_fwr_odds_beta", 0.0))

        for bucket in denial_buckets:
            b_cases = int(bucket.get("denial_cases", 0))
            if b_cases <= 0:
                continue

            dollars_per_case = float(bucket.get("mean_amount", payer_state["avg_claim"]))
            b_wait_days = float(bucket.get("queue_wait_days", 0.0))
            b_x = float(bucket.get("x_log_size", 0.0))

            # Age penalty from queue delay (Leap 4/5)
            age_penalty = 0.0
            if mode == "queue" and bool(qconf.get("enabled", True)) and b_wait_days > 0:
                slope = float(qconf.get("fwr_age_logit_slope_per_30d", 0.25))
                cap_pen = float(qconf.get("max_age_logit_penalty", 2.0))
                age_penalty = slope * (b_wait_days / 30.0)
                age_penalty = float(np.clip(age_penalty, 0.0, cap_pen))

            type_counts = rng.multinomial(b_cases, type_probs)

            for t, t_cases in zip(type_keys, type_counts):
                if t_cases <= 0:
                    continue

                denial_cases_by_type[t] = denial_cases_by_type.get(t, 0) + int(t_cases)
                t_rework_cost = 0.0

                type_denied_dollars = dollars_per_case * float(t_cases)
                tconf = payer_state["denial_types"][t]
                odds_mult = float(tconf.get("fwr_odds_mult", 1.0))
                stage_bias = tconf.get("stage_bias", {}) or {}

                # Larger claims often get more attention; allow modest size tilt on write-off odds.
                fwr_type = _sigmoid(
                    _logit(fwr_base)
                    + np.log(max(odds_mult, 1e-6))
                    + fwr_logit_penalty
                    + age_penalty
                    + (size_fwr_beta * b_x)
                )
                fwr_type = float(np.clip(fwr_type, 0.0, max_fwr))

                wo = type_denied_dollars * fwr_type
                fwr_weighted_num += fwr_type * type_denied_dollars
                fwr_weighted_den += type_denied_dollars
                denial_writeoff += wo
                denial_writeoff_by_type[t] = denial_writeoff_by_type.get(t, 0.0) + wo
                collectible_denied += (type_denied_dollars - wo)

                stage_mix = dict(payer_state["stage_mix_base"])
                stage_mix = _apply_stage_bias(stage_mix, stage_bias)
                stage_mix = _apply_backlog_stage_shift(stage_mix, stage_shift, l2_share=backlog_l2_share)

                stage_keys = list(stage_mix.keys()) if stage_mix else ["L1", "L2", "L3"]
                stage_probs = np.array([stage_mix.get(k, 0.0) for k in stage_keys], dtype=float)
                _sp_sum = stage_probs.sum()
                if _sp_sum <= 0:
                    logger.warning("stage_probs sums to 0 for payer %s; using uniform", payer_state.get("payer", "?"))
                    stage_probs = np.ones(len(stage_keys), dtype=float) / max(len(stage_keys), 1)
                else:
                    stage_probs = stage_probs / _sp_sum
                stage_counts = rng.multinomial(int(t_cases), stage_probs)

                for sk, scount in zip(stage_keys, stage_counts):
                    if scount <= 0:
                        continue
                    denial_cases_by_stage[sk] += int(scount)

                    c_cost = sample_sum_iid_as_gamma(rng, appeals[sk]["cost"], n=float(scount))
                    denial_rework_cost += c_cost
                    t_rework_cost += c_cost
                    denial_rework_cost_by_stage[sk] = denial_rework_cost_by_stage.get(sk, 0.0) + float(c_cost)
                    denial_addl_days_sum += sample_sum_iid_as_gamma(rng, appeals[sk]["days"], n=float(scount)) * days_multiplier

                    if b_wait_days > 0:
                        denial_addl_days_sum += float(scount) * b_wait_days

                denial_rework_cost_by_type[t] = denial_rework_cost_by_type.get(t, 0.0) + float(t_rework_cost)

    avg_denial_addl_days = (denial_addl_days_sum / denial_cases_total) if denial_cases_total > 0 else 0.0
    if fwr_weighted_den > 1e-12:
        fwr_realized = float(fwr_weighted_num / fwr_weighted_den)

    # Underpayments
    underpaid_dollars = float(payer_state["underpaid_dollars"])
    underpay_cases = int(payer_state["underpay_cases"])
    upr = float(payer_state["upr"])
    sev = float(payer_state["underpay_severity"])
    rec = float(payer_state["underpay_recovery"])

    underpay_recovered = 0.0
    underpay_leakage = 0.0
    underpay_cost = 0.0
    underpay_addl_days_sum = 0.0

    if payer_state["include_underpayments"] and underpaid_dollars > 0:
        underpay_recovered = underpaid_dollars * rec
        underpay_leakage = underpaid_dollars - underpay_recovered
        if underpay_cases > 0:
            underpay_cost = sample_sum_iid_as_gamma(rng, payer_state["underpay_followup_cost_spec"], n=float(underpay_cases))
            underpay_addl_days_sum = sample_sum_iid_as_gamma(rng, payer_state["underpay_resolution_days_spec"], n=float(underpay_cases)) * days_multiplier
            if mode == "queue" and queue_wait_days_base > 0:
                spill = float(cfg.get("operations", {}).get("underpay_delay_spillover", 0.35))
                underpay_addl_days_sum += float(underpay_cases) * float(queue_wait_days_base) * spill

    avg_underpay_addl_days = (underpay_addl_days_sum / underpay_cases) if underpay_cases > 0 else 0.0

    net_collectible = R_p - denial_writeoff - underpay_leakage
    net_collectible = float(max(net_collectible, 0.0))

    dar_clean = float(payer_state["dar_clean"])
    ar_base = (net_collectible / 365.0) * dar_clean if net_collectible > 0 else 0.0
    ar_denials_addl = (collectible_denied / 365.0) * avg_denial_addl_days if net_collectible > 0 else 0.0
    ar_underpay_addl = (underpay_recovered / 365.0) * avg_underpay_addl_days if net_collectible > 0 else 0.0
    ar_total = ar_base + ar_denials_addl + ar_underpay_addl

    dar_total = (ar_total / (net_collectible / 365.0)) if net_collectible > 0 else 0.0
    economic_cost = ar_total * wacc

    return {
        "payer": payer,
        "revenue": R_p,
        "net_collectible": net_collectible,

        # sampled KPI primitives
        "idr": idr,
        "fwr_base": float(payer_state.get("fwr_base", 0.0)),
        "fwr_realized": fwr_realized,
        "dar_clean": dar_clean,
        "upr": upr,
        "underpay_severity": sev,
        "underpay_recovery": rec,

        # denials
        "denied_dollars": denied_dollars_total,
        "denial_cases": denial_cases_total,
        "denial_writeoff": denial_writeoff,
        "denial_rework_cost": denial_rework_cost,
        "avg_denial_addl_days": avg_denial_addl_days,

        # underpayments
        "underpaid_dollars": underpaid_dollars,
        "underpay_cases": underpay_cases,
        "underpay_recovered": underpay_recovered,
        "underpay_leakage": underpay_leakage,
        "underpay_cost": underpay_cost,
        "avg_underpay_addl_days": avg_underpay_addl_days,

        # A/R + economics
        "ar_total_dollars": ar_total,
        "dar_total": dar_total,
        "economic_cost": economic_cost,

        # explainability
        "denial_cases_L1": denial_cases_by_stage["L1"],
        "denial_cases_L2": denial_cases_by_stage["L2"],
        "denial_cases_L3": denial_cases_by_stage["L3"],
        "denial_writeoff_by_type": denial_writeoff_by_type,
        "denial_rework_cost_by_type": denial_rework_cost_by_type,
        "denial_cases_by_type": denial_cases_by_type,
        "denial_rework_cost_by_stage": denial_rework_cost_by_stage,
        "backlog_x": backlog_x,
        "queue_wait_days": float(queue_wait_days_base),
        "queue_wait_days_dollar_weighted": float(q_wait_dollar_wtd),
        "touches_per_case": float(payer_state.get("touches_per_case", 0.0)),
    }


def simulate_one(cfg: Dict[str, Any], rng: np.random.Generator) -> Dict[str, Any]:
    payer_names = list(cfg["payers"].keys())
    payer_states = [_simulate_payer_pass1(cfg, p, rng) for p in payer_names]

    total_denial_touches = 0.0
    total_denial_cases = 0
    for ps in payer_states:
        if ps.get("include_denials", False):
            total_denial_cases += int(ps.get("denial_cases", 0))
            total_denial_touches += float(ps.get("denial_cases", 0)) * float(ps.get("touches_per_case", 0.0))

    cap_res = compute_capacity(cfg, float(total_denial_touches), int(total_denial_cases))
    backlog_x = float(cap_res["backlog_x"])
    queue_wait_days = float(cap_res["queue_wait_days"])
    backlog_months_avg = float(cap_res["backlog_months_avg"])
    backlog_months_max = float(cap_res["backlog_months_max"])
    capacity_touches = cap_res["capacity_touches"]
    outsourced_cost = float(cap_res.get("outsourced_cost", 0.0))

    payer_results = [
        _simulate_payer_pass2(cfg, ps, rng, backlog_x=backlog_x, queue_wait_days_base=queue_wait_days) for ps in payer_states
    ]

    rev_sum = sum(float(r["revenue"]) for r in payer_results)
    if rev_sum > 1e-9:
        qw_port = sum(
            float(r.get("queue_wait_days_dollar_weighted", 0.0)) * float(r["revenue"])
            for r in payer_results
        ) / rev_sum
    else:
        qw_port = float(np.nanmean([r.get("queue_wait_days_dollar_weighted", np.nan) for r in payer_results]))

    totals = {
        "revenue": sum(r["revenue"] for r in payer_results),
        "net_collectible": sum(r["net_collectible"] for r in payer_results),

        "denial_writeoff": sum(r["denial_writeoff"] for r in payer_results),
        "denial_rework_cost": sum(r["denial_rework_cost"] for r in payer_results),

        "underpay_leakage": sum(r["underpay_leakage"] for r in payer_results),
        "underpay_cost": sum(r["underpay_cost"] for r in payer_results),

        "economic_cost": sum(r["economic_cost"] for r in payer_results),

        "total_denial_cases": sum(r["denial_cases"] for r in payer_results),
        "total_underpay_cases": sum(r["underpay_cases"] for r in payer_results),

        # Capacity explainability
        "total_denial_touches": float(total_denial_touches),
        "capacity_touches": float(capacity_touches if np.isfinite(capacity_touches) else 0.0),
        "backlog_x": float(backlog_x),
        "outsourced_cost": outsourced_cost,

        # Queue explainability (revenue-weighted portfolio queue delay)
        "queue_wait_days": float(queue_wait_days),
        "backlog_months_avg": float(backlog_months_avg),
        "backlog_months_max": float(backlog_months_max),
        "queue_wait_days_dollar_weighted": float(qw_port),
    }

    totals["leakage_total"] = totals["denial_writeoff"] + totals["underpay_leakage"]
    totals["rework_total"] = totals["denial_rework_cost"] + totals["underpay_cost"]
    # Core RCM + outsourced vendor cost; working-capital (WACC) cost stays in economic_cost for reporting
    totals["rcm_ebitda_impact"] = totals["leakage_total"] + totals["rework_total"] + outsourced_cost
    totals["rcm_ebitda_impact_incl_wc"] = totals["rcm_ebitda_impact"] + totals["economic_cost"]

    net = totals["net_collectible"]
    if net > 0:
        ar_total = sum(r["ar_total_dollars"] for r in payer_results)
        totals["dar_total"] = (ar_total / (net / 365.0))
    else:
        totals["dar_total"] = 0.0

    return {"payers": payer_results, "totals": totals}


def simulate(
    cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    include_payer_drivers: bool = True,
    progress_callback: Any = None,
    early_stop: bool = True,
    registry: Any = None,
) -> pd.DataFrame:
    """Run n_sims Monte Carlo iterations.

    Args:
        progress_callback: Optional callable(iteration, n_sims) called every 1000 iters (Step 49)
        early_stop: If True, check convergence every 5000 iters and stop early if stable (Step 52)
        registry: Optional ``ProvenanceRegistry``. When supplied, each
            summary metric (p50 denial rate, p50 EBITDA impact, etc.)
            is recorded as a Monte Carlo DataPoint so the partner can
            trace numbers back to the sim that produced them.
    """
    import time
    t_start = time.perf_counter()

    rng = np.random.default_rng(int(seed))
    rows = []
    ebitda_values: List[float] = []
    converged_at = None

    for i in range(int(n_sims)):
        out = simulate_one(cfg, rng)
        t = out["totals"]

        row = {"sim": i, **t}

        if include_payer_drivers:
            for pr in out["payers"]:
                p = pr["payer"]
                row[f"idr_{p}"] = pr["idr"]
                row[f"fwr_{p}"] = pr["fwr_base"]
                row[f"fwr_base_{p}"] = pr["fwr_base"]
                row[f"fwr_realized_{p}"] = pr.get("fwr_realized", pr["fwr_base"])
                row[f"dar_clean_{p}"] = pr["dar_clean"]
                row[f"upr_{p}"] = pr["upr"]

        rows.append(row)
        ebitda_values.append(float(t.get("rcm_ebitda_impact", 0)))

        # Step 49: Progress callback
        if progress_callback and (i + 1) % 1000 == 0:
            try:
                progress_callback(i + 1, n_sims)
            except Exception:
                pass

        # Step 52: Convergence detection
        if early_stop and (i + 1) >= 10000 and (i + 1) % 5000 == 0:
            recent = ebitda_values[-5000:]
            prior = ebitda_values[-10000:-5000]
            if len(prior) >= 5000:
                mean_recent = float(np.mean(recent))
                mean_prior = float(np.mean(prior))
                p90_recent = float(np.percentile(recent, 90))
                p90_prior = float(np.percentile(prior, 90))
                mean_abs = abs(mean_recent - mean_prior)
                p90_abs = abs(p90_recent - p90_prior)
                if mean_prior != 0 and p90_prior != 0:
                    mean_pct = mean_abs / abs(mean_prior)
                    p90_pct = p90_abs / abs(p90_prior)
                    stable = mean_pct < 0.005 and p90_pct < 0.005
                else:
                    stable = mean_abs < 1000.0 and p90_abs < 1000.0
                if stable:
                    converged_at = i + 1
                    logger.info(
                        "Converged at iteration %d (mean delta %.4g, P90 delta %.4g)",
                        converged_at, mean_abs, p90_abs,
                    )
                    break

    # Step 50: Timing
    elapsed = time.perf_counter() - t_start
    iters_completed = len(rows)
    rate = iters_completed / elapsed if elapsed > 0 else 0
    logger.info("Simulation: %d iterations in %.1fs (%.0f iter/s)%s",
                iters_completed, elapsed, rate,
                f" [converged at {converged_at}]" if converged_at else "")

    df = pd.DataFrame(rows)
    num_cols = df.select_dtypes(include=[np.number]).columns
    if len(num_cols):
        n_inf = int(np.isinf(df[num_cols].to_numpy()).sum())
        n_nan = int(np.isnan(df[num_cols].to_numpy()).sum())
        if n_inf or n_nan:
            logger.warning("Simulation output contained %d inf and %d nan; coercing to finite values", n_inf, n_nan)
            df[num_cols] = df[num_cols].replace([np.inf, -np.inf], 0.0).fillna(0.0)

    # B163: opt-in provenance capture. Record the canonical MC p50s
    # for each summary metric so downstream consumers (pe_math,
    # partner UI) can trace them back to this simulate() call.
    if registry is not None:
        try:
            _record_simulate_metrics(registry, df, n_sims=iters_completed)
        except Exception:  # noqa: BLE001 — never break a sim on audit failure
            pass
    return df


def _record_simulate_metrics(registry, df: "pd.DataFrame",
                              n_sims: int) -> None:
    """Record p50 + stddev of each numeric summary column as a MC
    DataPoint. Private helper — callers pass a ``ProvenanceRegistry``
    to ``simulate(registry=...)``."""
    # Focus on the top-line metrics a partner cares about. The
    # per-payer driver columns (idr_Medicare, fwr_BCBS, etc.) are
    # noisy and rarely referenced in explanations.
    TOPLINE = (
        "rcm_ebitda_impact", "revenue_lift", "collection_lift",
        "npsr_lift", "cost_to_collect_delta",
        "idr_blended", "fwr_blended", "dar_clean_blended",
    )
    for col in df.columns:
        if col not in TOPLINE:
            continue
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        try:
            p50 = float(series.quantile(0.5))
            sd = float(series.std()) if len(series) > 1 else 0.0
        except Exception:  # noqa: BLE001
            continue
        registry.record_mc(
            value=p50, metric_name=col,
            n_sims=int(n_sims), percentile=50, stddev=sd,
        )


def simulate_compare(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> pd.DataFrame:
    if align_profile:
        actual_cfg, benchmark_cfg = align_benchmark_to_actual(actual_cfg, benchmark_cfg, deepcopy_inputs=True)

    df_a = simulate(actual_cfg, n_sims=n_sims, seed=seed, include_payer_drivers=True)
    df_b = simulate(benchmark_cfg, n_sims=n_sims, seed=seed + 1, include_payer_drivers=True)

    df = pd.DataFrame({"sim": df_a["sim"]})

    out_cols = [
        "denial_writeoff",
        "underpay_leakage",
        "denial_rework_cost",
        "underpay_cost",
        "economic_cost",
        "dar_total",
        "rcm_ebitda_impact",
        "rcm_ebitda_impact_incl_wc",
        "outsourced_cost",
        # Queue explainability
        "queue_wait_days",
        "queue_wait_days_dollar_weighted",
        "backlog_x",
    ]
    for col in out_cols:
        if col not in df_a.columns or col not in df_b.columns:
            continue
        df[f"actual_{col}"] = df_a[col].values
        df[f"bench_{col}"] = df_b[col].values
        df[f"drag_{col}"] = df[f"actual_{col}"] - df[f"bench_{col}"]

    df["ebitda_drag"] = df["drag_rcm_ebitda_impact"]
    df["economic_drag"] = df["drag_economic_cost"]

    driver_cols = [c for c in df_a.columns if c.startswith(("idr_", "fwr_", "dar_clean_", "upr_"))]
    for c in driver_cols:
        df[f"actual_{c}"] = df_a[c].values
        df[f"bench_{c}"] = df_b[c].values

    return df


# ── Step 54: Per-payer simulation summary ──────────────────────────────────

def payer_simulation_summary(
    cfg: Dict[str, Any],
    n_sims: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Run simulation and return per-payer summary statistics."""
    rng = np.random.default_rng(int(seed))
    payer_data: Dict[str, List[Dict[str, float]]] = {}

    for _ in range(n_sims):
        out = simulate_one(cfg, rng)
        for pr in out["payers"]:
            p = pr["payer"]
            if p not in payer_data:
                payer_data[p] = []
            payer_data[p].append({
                "idr": pr["idr"],
                "fwr_base": pr["fwr_base"],
                "dar_clean": pr["dar_clean"],
                "denial_writeoff": pr["denial_writeoff"],
                "underpay_leakage": pr["underpay_leakage"],
                "denial_cases": pr["denial_cases"],
            })

    rows = []
    for payer, records in payer_data.items():
        df_p = pd.DataFrame(records)
        row = {"payer": payer}
        for col in df_p.columns:
            row[f"{col}_mean"] = float(df_p[col].mean())
            row[f"{col}_p10"] = float(df_p[col].quantile(0.10))
            row[f"{col}_p90"] = float(df_p[col].quantile(0.90))
        rows.append(row)

    return pd.DataFrame(rows)


# ── Step 56: Batch comparison mode ─────────────────────────────────────────

def batch_compare(
    actual_cfgs: List[Dict[str, Any]],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> pd.DataFrame:
    """Compare multiple actual configs against one benchmark."""
    results = []
    for i, actual_cfg in enumerate(actual_cfgs):
        df = simulate_compare(actual_cfg, benchmark_cfg, n_sims=n_sims, seed=seed, align_profile=align_profile)
        hospital_name = actual_cfg.get("hospital", {}).get("name", f"Site_{i+1}")
        ebitda = df["ebitda_drag"]
        results.append({
            "site": hospital_name,
            "ebitda_drag_mean": float(ebitda.mean()),
            "ebitda_drag_p10": float(ebitda.quantile(0.10)),
            "ebitda_drag_p90": float(ebitda.quantile(0.90)),
            "n_sims": len(df),
        })
    return pd.DataFrame(results)


# ── Step 58: Warm-start from prior simulation ──────────────────────────────

def warm_start_simulate(
    cfg: Dict[str, Any],
    prior_csv: str,
    target_n_sims: int,
    seed: int,
) -> pd.DataFrame:
    """Load prior results and run additional iterations to reach target."""
    prior = pd.read_csv(prior_csv)
    existing = len(prior)
    remaining = target_n_sims - existing

    if remaining <= 0:
        logger.info("Prior run has %d iterations, target is %d; no additional iterations needed", existing, target_n_sims)
        return prior

    logger.info("Warm-starting: %d existing + %d new = %d target", existing, remaining, target_n_sims)
    new_df = simulate(cfg, n_sims=remaining, seed=seed + existing, early_stop=False)
    new_df["sim"] = new_df["sim"] + existing
    return pd.concat([prior, new_df], ignore_index=True)

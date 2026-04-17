from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .logger import logger


# Step 31: Kept for backward compatibility but no longer enforced
MANDATORY_PAYERS = ("Medicare", "Medicaid", "Commercial", "SelfPay")

CURRENT_SCHEMA_VERSION = "1.0"


class ConfigError(ValueError):
    pass


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge override into base. Override values win."""
    result = deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = deepcopy(val)
    return result


def _resolve_env_vars(obj: Any) -> Any:
    """Replace ${ENV_VAR} and ${ENV_VAR:default} patterns with environment values (Step 38)."""
    if isinstance(obj, str):
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")
        def _replacer(m: re.Match) -> str:
            var_name = m.group(1)
            default = m.group(2)
            val = os.environ.get(var_name)
            if val is not None:
                return val
            if default is not None:
                return default
            logger.warning("Environment variable %s not set and no default provided", var_name)
            return m.group(0)
        return pattern.sub(_replacer, obj)
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


def load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML with support for _extends inheritance (Step 34) and env var substitution (Step 38)."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level YAML must be a dict, got {type(data)}")

    # Step 34: Config inheritance
    if "_extends" in data:
        base_path = data.pop("_extends")
        if not os.path.isabs(base_path):
            base_path = os.path.join(os.path.dirname(os.path.abspath(path)), base_path)
        logger.info("Loading base config: %s", base_path)
        base_data = load_yaml(base_path)
        data = _deep_merge(base_data, data)

    # Step 38: Environment variable resolution
    data = _resolve_env_vars(data)

    return data


def canonical_payer_name(name: str) -> str:
    n = str(name).strip()
    lower = n.lower().replace("-", "").replace(" ", "")
    if lower in ("selfpay", "self"):
        return "SelfPay"
    if lower == "medicare":
        return "Medicare"
    if lower == "medicaid":
        return "Medicaid"
    if lower in ("commercial", "private", "phi"):
        return "Commercial"
    # passthrough for any additional payer segments
    return n


# Backwards-compatible alias (kept to avoid breaking any external imports)
_canonical_payer_name = canonical_payer_name


def _require(condition: bool, msg: str) -> None:
    if not condition:
        raise ConfigError(msg)


_VALID_DIST_TYPES = {"fixed", "beta", "normal", "normal_trunc", "gaussian", "triangular", "lognormal", "gamma", "empirical"}

_DIST_REQUIRED_FIELDS = {
    "fixed": ["value"],
    "beta": ["mean", "sd"],
    "normal": ["mean", "sd"],
    "normal_trunc": ["mean", "sd"],
    "gaussian": ["mean", "sd"],
    "lognormal": ["mean", "sd"],
    "gamma": ["mean", "sd"],
    "triangular": ["low", "mode", "high"],
    "empirical": ["values"],
}


def _validate_dist_spec(spec: Any, name: str) -> None:
    """Validate a distribution specification dict has the correct structure."""
    if not isinstance(spec, dict):
        raise ConfigError(f"{name}: distribution spec must be a dict, got {type(spec).__name__}")
    dist_type = str(spec.get("dist", "fixed")).lower()
    if dist_type not in _VALID_DIST_TYPES:
        raise ConfigError(f"{name}: unknown distribution type '{dist_type}'; valid types: {sorted(_VALID_DIST_TYPES)}")
    required = _DIST_REQUIRED_FIELDS.get(dist_type, [])
    for fld in required:
        if fld not in spec:
            raise ConfigError(f"{name}: distribution type '{dist_type}' requires field '{fld}'")
        if fld == "values":
            continue  # validated separately for empirical
        try:
            float(spec[fld])
        except (TypeError, ValueError):
            raise ConfigError(f"{name}: field '{fld}' must be numeric, got {spec[fld]!r}")
    if dist_type in ("beta", "normal", "normal_trunc", "gaussian", "lognormal", "gamma"):
        sd = float(spec["sd"])
        if sd < 0:
            raise ConfigError(f"{name}: sd must be >= 0, got {sd}")
    if dist_type == "empirical":
        vals = spec.get("values", [])
        if not isinstance(vals, list) or len(vals) < 1:
            raise ConfigError(f"{name}: empirical distribution requires non-empty 'values' list")


def _sum_to_one(d: Dict[str, float], tol: float = 1e-6) -> bool:
    s = sum(float(v) for v in d.values())
    return abs(s - 1.0) <= tol


def _validate_deal_section(deal: Dict[str, Any]) -> None:
    """Validate the optional PE `deal` config block.

    Every field is optional individually; the block simply enforces that
    anything present has a sensible range. Downstream consumers degrade
    to defaults when fields are missing.
    """
    if not isinstance(deal, dict):
        raise ConfigError("`deal` section must be a mapping")

    pairs_positive = [
        ("entry_ebitda", True),
        ("entry_multiple", True),
        ("exit_multiple", True),
        ("hold_years", True),
        ("covenant_max_leverage", True),
    ]
    for key, must_be_positive in pairs_positive:
        if key in deal and deal[key] is not None:
            v = float(deal[key])
            if must_be_positive and v <= 0:
                raise ConfigError(f"deal.{key} must be > 0 (got {v})")

    # Bounded-range fields
    for key, lo, hi in [
        ("equity_pct",         0.0, 1.0),
        ("organic_growth_pct", -0.5, 1.0),   # -50% crash to 100% bubble
        ("interest_rate",      0.0, 0.50),
    ]:
        if key in deal and deal[key] is not None:
            v = float(deal[key])
            if not (lo <= v <= hi):
                raise ConfigError(f"deal.{key} must be in [{lo}, {hi}] (got {v})")

    # Portfolio auto-registration fields (Brick 51). Both must be present
    # together — an ID without a stage or vice versa is ambiguous.
    if "portfolio_deal_id" in deal and deal["portfolio_deal_id"] is not None:
        if not isinstance(deal["portfolio_deal_id"], str) or not deal["portfolio_deal_id"].strip():
            raise ConfigError("deal.portfolio_deal_id must be a non-empty string")
    if "portfolio_stage" in deal and deal["portfolio_stage"] is not None:
        # Import locally to avoid circular (portfolio_snapshots imports from portfolio.store)
        from ..portfolio.portfolio_snapshots import DEAL_STAGES
        if deal["portfolio_stage"] not in DEAL_STAGES:
            raise ConfigError(
                f"deal.portfolio_stage must be one of {DEAL_STAGES} "
                f"(got {deal['portfolio_stage']!r})"
            )


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and also normalizes payer keys (e.g., 'Self-Pay' -> 'SelfPay').
    Returns a normalized config dict.
    """
    cfg = dict(cfg)  # shallow copy

    _require("hospital" in cfg and isinstance(cfg["hospital"], dict), "Missing 'hospital' section.")
    _require("annual_revenue" in cfg["hospital"], "hospital.annual_revenue is required.")
    annual_revenue = float(cfg["hospital"]["annual_revenue"])
    _require(annual_revenue > 0, "hospital.annual_revenue must be > 0.")

    # Optional `deal` section — PE deal structure (Brick 46). Validated only
    # when present so every config pre-dating this brick keeps working.
    if "deal" in cfg and cfg["deal"] is not None:
        _validate_deal_section(cfg["deal"])

    _require("payers" in cfg and isinstance(cfg["payers"], dict), "Missing 'payers' section.")
    payers_raw: Dict[str, Any] = cfg["payers"]

    # Canonicalize payer keys
    payers: Dict[str, Any] = {}
    for k, v in payers_raw.items():
        ck = _canonical_payer_name(k)
        if ck in payers:
            raise ConfigError(f"Duplicate payer after canonicalization: {ck}")
        payers[ck] = v
    cfg["payers"] = payers

    # Step 31: No longer enforce mandatory payers. Just require at least one payer
    # with revenue_share > 0 and include_denials = True.
    # Step 39: Schema versioning
    cfg.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    sv = str(cfg.get("schema_version", CURRENT_SCHEMA_VERSION))
    if sv != CURRENT_SCHEMA_VERSION:
        logger.warning("Config schema_version %s differs from current %s; proceeding but check for compatibility",
                        sv, CURRENT_SCHEMA_VERSION)

    # Step 32: Payer alias mapping
    payer_aliases = cfg.get("payer_aliases", {})
    if payer_aliases:
        new_payers: Dict[str, Any] = {}
        for k, v in payers.items():
            ck = payer_aliases.get(k, k)
            ck = canonical_payer_name(ck)
            if ck in new_payers:
                logger.warning("Payer alias collision: %s -> %s (merging not supported, keeping first)", k, ck)
            else:
                new_payers[ck] = v
        payers = new_payers
        cfg["payers"] = payers

    has_denial_payer = any(
        float(pconf.get("revenue_share", 0)) > 0 and pconf.get("include_denials", True)
        for pconf in payers.values() if isinstance(pconf, dict)
    )
    _require(len(payers) >= 1, "At least one payer is required")
    _require(has_denial_payer, "At least one payer must have revenue_share > 0 and include_denials enabled")

    # Validate payer shares
    shares = {}
    for p, pconf in payers.items():
        _require(isinstance(pconf, dict), f"payer '{p}' must be a dict")
        _require("revenue_share" in pconf, f"payer '{p}' missing revenue_share")
        rs = float(pconf["revenue_share"])
        _require(rs >= 0, f"payer '{p}' revenue_share must be >= 0")
        shares[p] = rs

        # include flags default
        pconf.setdefault("include_denials", p != "SelfPay")
        pconf.setdefault("include_underpayments", p != "SelfPay")

        # Step 35: Per-payer working_days (falls back to global)
        # Not set here; simulator reads payer-level first, then global

        # avg_claim used to translate dollars -> volumes for capacity + rework economics
        _require("avg_claim_dollars" in pconf, f"payer '{p}' missing avg_claim_dollars")
        _require(float(pconf["avg_claim_dollars"]) > 0, f"payer '{p}' avg_claim_dollars must be >0")

        # dar_clean_days distribution required (baseline clean-claim A/R days)
        _require("dar_clean_days" in pconf, f"payer '{p}' missing dar_clean_days distribution spec")
        _validate_dist_spec(pconf["dar_clean_days"], f"payer '{p}' dar_clean_days")

        # Leap 5: Optional claim size distribution (enables large-claim tail + dollar-priority queue).
        pconf.setdefault("claim_distribution", {})
        cd = pconf["claim_distribution"]
        if cd is None:
            cd = {}
            pconf["claim_distribution"] = cd
        _require(isinstance(cd, dict), f"payer '{p}' claim_distribution must be a dict")
        cd.setdefault("enabled", False)
        cd.setdefault("cv", 1.25)  # coefficient of variation for lognormal claim sizes
        cd.setdefault("bucket_quantiles", [0.0, 0.70, 0.90, 0.97, 1.0])
        # Denial probability tilt by claim size: logistic(beta * log(size/mean)).
        cd.setdefault("size_denial_odds_beta", 0.60)
        # Optional: larger claims are fought harder (slightly lower write-off odds).
        cd.setdefault("size_fwr_odds_beta", -0.10)

        if bool(cd.get("enabled", False)):
            qs = cd.get("bucket_quantiles", [0.0, 0.7, 0.9, 0.97, 1.0])
            _require(isinstance(qs, list) and len(qs) >= 3, f"payer '{p}' claim_distribution.bucket_quantiles must be a list with >=3 entries")
            qsf = [float(x) for x in qs]
            _require(abs(qsf[0] - 0.0) <= 1e-9, f"payer '{p}' claim_distribution.bucket_quantiles must start at 0.0")
            _require(abs(qsf[-1] - 1.0) <= 1e-9, f"payer '{p}' claim_distribution.bucket_quantiles must end at 1.0")
            _require(all(qsf[i] <= qsf[i+1] for i in range(len(qsf)-1)), f"payer '{p}' claim_distribution.bucket_quantiles must be non-decreasing")
            _require(float(cd.get("cv", 1.25)) > 0, f"payer '{p}' claim_distribution.cv must be > 0")


        if pconf.get("include_denials", False):
            _require("denials" in pconf, f"payer '{p}' include_denials=true but denials section missing")
            d = pconf["denials"]
            _require("idr" in d and isinstance(d["idr"], dict), f"payer '{p}' denials.idr distribution missing")
            _validate_dist_spec(d["idr"], f"payer '{p}' denials.idr")
            _require("fwr" in d and isinstance(d["fwr"], dict), f"payer '{p}' denials.fwr distribution missing")
            _validate_dist_spec(d["fwr"], f"payer '{p}' denials.fwr")
            _require("stage_mix" in d and isinstance(d["stage_mix"], dict), f"payer '{p}' denials.stage_mix missing")
            _require(_sum_to_one(d["stage_mix"], tol=1e-3), f"payer '{p}' denials.stage_mix must sum to 1")
            _require("denial_types" in d and isinstance(d["denial_types"], dict), f"payer '{p}' denials.denial_types missing")
            _require(len(d["denial_types"]) >= 1, f"payer '{p}' denials.denial_types must have at least one entry")
            type_shares = {}
            for t_name, t_val in d["denial_types"].items():
                _require(isinstance(t_val, dict), f"payer '{p}' denials.denial_types.{t_name} must be a dict")
                _require("share" in t_val, f"payer '{p}' denials.denial_types.{t_name} missing 'share'")
                share_v = float(t_val["share"])
                _require(share_v >= 0, f"payer '{p}' denials.denial_types.{t_name}.share must be >= 0")
                type_shares[t_name] = share_v
                if "fwr_odds_mult" in t_val:
                    _require(isinstance(t_val["fwr_odds_mult"], (int, float)),
                             f"payer '{p}' denials.denial_types.{t_name}.fwr_odds_mult must be numeric")
                if "stage_bias" in t_val and t_val["stage_bias"]:
                    _require(isinstance(t_val["stage_bias"], dict),
                             f"payer '{p}' denials.denial_types.{t_name}.stage_bias must be a dict")
            _require(_sum_to_one(type_shares, tol=1e-3), f"payer '{p}' denials.denial_types.*.share must sum to 1")
            d.setdefault("denial_mix_concentration", 120)

    _require(abs(sum(shares.values()) - 1.0) <= 1e-3, f"Sum of payer revenue_share must be 1.0; got {sum(shares.values()):.4f}")

    # Global sections
    cfg.setdefault("analysis", {})
    cfg["analysis"].setdefault("n_sims", 30000)
    cfg["analysis"].setdefault("seed", 42)
    cfg["analysis"].setdefault("working_days", 250)

    cfg.setdefault("economics", {})
    cfg["economics"].setdefault("wacc_annual", 0.12)

    # Step 41: Configurable appeal stages (not hardcoded to L1/L2/L3)
    _require("appeals" in cfg and isinstance(cfg["appeals"], dict), "Missing global 'appeals' section.")
    stages = cfg["appeals"].get("stages")
    _require(isinstance(stages, dict), "appeals.stages must be a dict")
    _require(len(stages) >= 1, "appeals.stages must have at least one stage")
    for stage_name, stage_conf in stages.items():
        _require(isinstance(stage_conf, dict), f"appeals.stages.{stage_name} must be a dict")
        _require("cost" in stage_conf and isinstance(stage_conf["cost"], dict), f"appeals.stages.{stage_name}.cost missing")
        _validate_dist_spec(stage_conf["cost"], f"appeals.stages.{stage_name}.cost")
        _require("days" in stage_conf and isinstance(stage_conf["days"], dict), f"appeals.stages.{stage_name}.days missing")
        _validate_dist_spec(stage_conf["days"], f"appeals.stages.{stage_name}.days")

    cfg.setdefault("operations", {})
    cfg["operations"].setdefault("denial_capacity", {})
    cap = cfg["operations"]["denial_capacity"]
    cap.setdefault("fte", 12)
    cap.setdefault("denials_per_fte_per_day", 12)
    cap.setdefault("enabled", True)

    # Capacity modeling mode: "annual_backlog" (legacy) or "queue" (Leap 4+).
    cap.setdefault("mode", "annual_backlog")

    # Touch-equivalent work per denial case by appeal stage (used in queue/backlog math).
    cap.setdefault("touches_per_case", {"L1": 1.0, "L2": 3.0, "L3": 8.0})

    # Queue model settings (used when denial_capacity.mode == "queue").
    cap.setdefault("queue", {})
    q = cap["queue"]
    q.setdefault("enabled", True)
    q.setdefault("months", 12)
    q.setdefault("days_per_month", 30.0)
    # Additional write-off risk as denials age in backlog (log-odds per 30 days of wait).
    q.setdefault("fwr_age_logit_slope_per_30d", 0.25)
    q.setdefault("max_age_logit_penalty", 2.0)
    # Optional: prioritize by dollars (requires claim distribution in Leap 5).
    q.setdefault("priority", "fifo")  # fifo | high_dollar_first

    # Step 42: Normalize and validate capacity mode (extended: unlimited, outsourced)
    mode = str(cap.get("mode", "annual_backlog")).strip().lower()
    if mode in ("queue", "workqueue", "dynamic_queue", "dynamic"):
        mode = "queue"
    elif mode in ("unlimited", "none", "no_cap"):
        mode = "unlimited"
    elif mode in ("outsourced", "outsource", "vendor"):
        mode = "outsourced"
        cap.setdefault("cost_per_case", 35.0)
    else:
        mode = "annual_backlog"
    cap["mode"] = mode

    # touches_per_case must include all defined appeal stages with positive values
    tpc = cap.get("touches_per_case", {})
    _require(isinstance(tpc, dict), "operations.denial_capacity.touches_per_case must be a dict")
    appeal_stage_names = list(cfg["appeals"]["stages"].keys())
    for s in appeal_stage_names:
        if s not in tpc:
            tpc[s] = 1.0  # default touch weight for undefined stages
        _require(float(tpc[s]) > 0, f"operations.denial_capacity.touches_per_case.{s} must be > 0")
    cap["touches_per_case"] = tpc

    if mode == "queue":
        _require(bool(q.get("enabled", True)), "operations.denial_capacity.queue.enabled must be true when mode==queue")
        _require(int(q.get("months", 12)) >= 1, "operations.denial_capacity.queue.months must be >= 1")
        _require(float(q.get("days_per_month", 30.0)) > 0, "operations.denial_capacity.queue.days_per_month must be > 0")
        pr = str(q.get("priority", "fifo")).strip().lower()
        if pr not in ("fifo", "high_dollar_first"):
            raise ConfigError("operations.denial_capacity.queue.priority must be fifo or high_dollar_first")
        q["priority"] = pr



    cap.setdefault("backlog", {})
    backlog = cap["backlog"]
    backlog.setdefault("enabled", True)
    backlog.setdefault("stage_shift_per_x", 0.20)          # per 1.0x over capacity
    backlog.setdefault("stage_shift_l2_share", 0.70)       # fraction of shifted mass going to L2 vs L3
    backlog.setdefault("fwr_logit_penalty_per_x", 0.60)    # per 1.0x over capacity
    backlog.setdefault("days_multiplier_per_x", 0.15)      # +15% days per 1.0x over capacity
    backlog.setdefault("max_over_capacity_x", 3.0)         # cap sensitivity to avoid crazy tails

    # Underpayment delay spillover: fraction of queue wait applied to underpayment resolution days
    cfg["operations"].setdefault("underpay_delay_spillover", 0.35)

    # Underpayments: optional global enable
    cfg.setdefault("underpayments", {})
    cfg["underpayments"].setdefault("enabled", True)

    return cfg


def load_and_validate(path: str) -> Dict[str, Any]:
    return validate_config(load_yaml(path))


# ── Step 36: Config diff tool ──────────────────────────────────────────────

def diff_configs(cfg_a: Dict[str, Any], cfg_b: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    """Return a structured diff between two configs."""
    diffs: List[Dict[str, Any]] = []
    all_keys = sorted(set(list(cfg_a.keys()) + list(cfg_b.keys())))
    for key in all_keys:
        full_key = f"{prefix}.{key}" if prefix else key
        in_a = key in cfg_a
        in_b = key in cfg_b
        val_a = cfg_a.get(key)
        val_b = cfg_b.get(key)

        if not in_a:
            diffs.append({"key": full_key, "change": "added_in_b", "value_b": val_b})
        elif not in_b:
            diffs.append({"key": full_key, "change": "removed_in_b", "value_a": val_a})
        elif isinstance(val_a, dict) and isinstance(val_b, dict):
            diffs.extend(diff_configs(val_a, val_b, prefix=full_key))
        elif val_a != val_b:
            entry: Dict[str, Any] = {"key": full_key, "change": "modified", "value_a": val_a, "value_b": val_b}
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                entry["delta"] = float(val_b) - float(val_a)
            diffs.append(entry)
    return diffs


# ── Step 37: Validation-only mode ──────────────────────────────────────────

def validate_config_from_path(path: str) -> Tuple[bool, List[str]]:
    """Validate a config file. Returns (is_valid, list_of_issues)."""
    issues: List[str] = []
    try:
        load_and_validate(path)
        return True, []
    except ConfigError as e:
        issues.append(str(e))
        return False, issues
    except Exception as e:
        issues.append(f"Unexpected error: {e}")
        return False, issues


# ── Step 43: Multi-site support ────────────────────────────────────────────

def is_multi_site(cfg: Dict[str, Any]) -> bool:
    """Check if config has multi-site structure."""
    return "sites" in cfg and isinstance(cfg["sites"], list) and len(cfg["sites"]) > 0


def expand_multi_site(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand a multi-site config into individual site configs.

    Each site inherits global settings and can override payers,
    annual_revenue, capacity, and name.
    """
    if not is_multi_site(cfg):
        return [cfg]

    site_cfgs = []
    base = {k: v for k, v in cfg.items() if k != "sites"}
    for site in cfg["sites"]:
        site_cfg = _deep_merge(base, site)
        site_cfg.setdefault("hospital", {})
        if "name" in site:
            site_cfg["hospital"]["name"] = site["name"]
        site_cfgs.append(site_cfg)
    return site_cfgs


# ── Step 45: Config export/import ──────────────────────────────────────────

def export_config_json(cfg: Dict[str, Any], path: str) -> None:
    """Export config as JSON."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, default=str)


def import_config_json(path: str) -> Dict[str, Any]:
    """Import config from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"JSON config must be a dict, got {type(data)}")
    return data


def flatten_config(cfg: Dict[str, Any], prefix: str = "") -> List[Dict[str, str]]:
    """Flatten config into a table of key-value pairs for spreadsheet review."""
    rows: List[Dict[str, str]] = []
    for key, val in cfg.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            rows.extend(flatten_config(val, prefix=full_key))
        elif isinstance(val, list):
            rows.append({"parameter": full_key, "value": str(val), "type": "list"})
        else:
            rows.append({"parameter": full_key, "value": str(val), "type": type(val).__name__})
    return rows
"""
Scenario overlay: apply parameter shocks to config.
Pure function; does not modify Monte Carlo kernel math.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List

import numpy as np
import yaml


def _shock_mean(d: Dict[str, Any], mult: float = 1.0, add: float = 0.0) -> None:
    """Apply multiplicative and additive shock to distribution mean."""
    if "mean" not in d:
        return
    m = float(d["mean"])
    m2 = m * mult + add
    d["mean"] = float(np.clip(m2, 0.0, 1.0)) if "min" not in d and "max" not in d else float(m2)
    if "min" in d:
        d["mean"] = max(d["mean"], float(d["min"]))
    if "max" in d:
        d["mean"] = min(d["mean"], float(d["max"]))


def _shock_stage_mix(sm: Dict[str, float], delta_L1: float = 0, delta_L2: float = 0, delta_L3: float = 0) -> Dict[str, float]:
    """Apply additive deltas to stage mix and renormalize."""
    out = {
        "L1": float(sm.get("L1", 0.7)) + delta_L1,
        "L2": float(sm.get("L2", 0.2)) + delta_L2,
        "L3": float(sm.get("L3", 0.1)) + delta_L3,
    }
    s = sum(out.values())
    if s > 0:
        out = {k: v / s for k, v in out.items()}
    return out


def apply_scenario(config: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply scenario shocks to config. Pure function; returns new config.
    Scenario schema: { name: str, shocks: [ { payer, param, type: "mult"|"add"|"replace", value } ] }
    Supported params: idr, fwr, underpay_rate, ar_days, appeal_stage_mix, underpay_recovery.
    Aliases: upr->underpay_rate, dar_clean_days->ar_days
    """
    _PARAM_ALIASES = {"upr": "underpay_rate", "dar_clean_days": "ar_days"}
    cfg = copy.deepcopy(config)
    shocks = scenario.get("shocks", [])
    if not shocks:
        return cfg

    payers = cfg.get("payers", {})

    for sh in shocks:
        payer = sh.get("payer")
        if not payer or payer not in payers:
            continue
        param = _PARAM_ALIASES.get(sh.get("param"), sh.get("param"))
        typ = sh.get("type", "mult")
        val_obj = sh.get("value")
        val = float(val_obj) if isinstance(val_obj, (int, float)) else 0.0

        p = payers[payer]

        if param == "idr" and p.get("include_denials") and "denials" in p:
            d = p["denials"].get("idr", {})
            if typ == "mult":
                _shock_mean(d, mult=val)
            elif typ == "add":
                _shock_mean(d, add=val)

        elif param == "fwr" and p.get("include_denials") and "denials" in p:
            d = p["denials"].get("fwr", {})
            if typ == "mult":
                _shock_mean(d, mult=val)
            elif typ == "add":
                _shock_mean(d, add=val)

        elif param == "underpay_rate" and p.get("include_underpayments") and "underpayments" in p:
            d = p["underpayments"].get("upr", {})
            if typ == "mult":
                _shock_mean(d, mult=val)
            elif typ == "add":
                _shock_mean(d, add=val)

        elif param == "ar_days" and "dar_clean_days" in p:
            d = p["dar_clean_days"]
            if isinstance(d, dict) and "mean" in d:
                m = float(d["mean"])
                if typ == "mult":
                    d["mean"] = float(np.clip(m * val, float(d.get("min", 5)), float(d.get("max", 365))))
                elif typ == "add":
                    d["mean"] = float(np.clip(m + val, float(d.get("min", 5)), float(d.get("max", 365))))

        elif param == "appeal_stage_mix":
            if p.get("include_denials") and "denials" in p and "stage_mix" in p["denials"]:
                sm = p["denials"]["stage_mix"]
                if typ == "replace" and isinstance(val_obj, dict):
                    p["denials"]["stage_mix"] = {str(k): float(v) for k, v in val_obj.items()}
                elif typ == "delta" and isinstance(val_obj, dict):
                    p["denials"]["stage_mix"] = _shock_stage_mix(
                        sm,
                        delta_L1=float(val_obj.get("L1", 0)),
                        delta_L2=float(val_obj.get("L2", 0)),
                        delta_L3=float(val_obj.get("L3", 0)),
                    )

        elif param == "underpay_recovery" and p.get("include_underpayments") and "underpayments" in p:
            d = p["underpayments"].get("recovery", {})
            if d and isinstance(d, dict):
                if typ == "mult":
                    _shock_mean(d, mult=val)
                elif typ == "add":
                    _shock_mean(d, add=val)

    return cfg


def load_scenario(path: str) -> Dict[str, Any]:
    """Load scenario from YAML or JSON."""
    with open(path) as f:
        content = f.read()
    if path.lower().endswith(".json"):
        import json
        return json.loads(content)
    return yaml.safe_load(content) or {}

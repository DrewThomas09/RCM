"""
Initiatives library: 8–12 standard RCM initiatives for the Value Creation Engine.
Each initiative defines: affected params, delta distributions, costs, ramp, confidence.
Does not change Monte Carlo math; this layer is consumed by ranking/ROI/100-day logic.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml


def _default_library_path() -> str:
    """Path to bundled initiatives_library.yaml at the project root.

    Post-refactor: this file is rcm_mc/rcm/initiatives.py — we need
    three `dirname` calls to reach the project root where configs/
    lives.
    """
    base = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ))
    return os.path.join(base, "configs", "initiatives_library.yaml")


def load_initiatives_library(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load the initiatives library from YAML.
    Returns list of initiative dicts.
    """
    p = path or _default_library_path()
    if not os.path.exists(p):
        return []
    with open(p) as f:
        data = yaml.safe_load(f) or {}
    initiatives = data.get("initiatives", [])
    return [i for i in initiatives if isinstance(i, dict)]


def get_initiative(
    initiatives: List[Dict[str, Any]],
    initiative_id: str,
) -> Optional[Dict[str, Any]]:
    """Return the initiative with the given id, or None."""
    for i in initiatives:
        if i.get("id") == initiative_id:
            return i
    return None


def get_all_initiatives(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Convenience: load and return all initiatives.
    """
    return load_initiatives_library(path)


def initiative_to_scenario(initiative: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an initiative to scenario format for apply_scenario.
    Uses delta_mean as the value; delta_sd is ignored for ranking (mean-based).
    """
    shocks = []
    for ap in initiative.get("affected_parameters", []):
        payer = ap.get("payer")
        param = ap.get("param")
        delta_type = ap.get("delta_type", "mult")
        val = ap.get("delta_mean")
        if payer and param and val is not None:
            if delta_type == "delta" and isinstance(val, dict):
                shocks.append({"payer": payer, "param": param, "type": "delta", "value": val})
            else:
                v = float(val) if isinstance(val, (int, float)) else None
                if v is not None:
                    shocks.append({"payer": payer, "param": param, "type": delta_type, "value": v})
    return {
        "name": initiative.get("name", initiative.get("id", "initiative")),
        "shocks": shocks,
    }

"""Registry that wires every CDD analytic into one app surface.

A feature counts as wired only when it resolves through this registry. The CLI
(``rcm-mc cdd ...``) and the HTTP server enumerate and run features from here,
so there are no orphan modules. Each entry maps a feature id to a builder that
returns a demo :class:`~rcm_mc.cdd.exhibit.Exhibit` (the wired, runnable
surface) plus the pure compute callable for direct use and testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from .exhibit import Exhibit


@dataclass(frozen=True)
class CddFeature:
    feature_id: str
    title: str
    audience: str
    # Zero-arg builder returning a runnable demo exhibit for the surface.
    demo: Callable[[], Exhibit]


_REGISTRY: Dict[str, CddFeature] = {}


def register(feature: CddFeature) -> CddFeature:
    if feature.feature_id in _REGISTRY:
        raise ValueError(f"duplicate CDD feature id: {feature.feature_id}")
    _REGISTRY[feature.feature_id] = feature
    return feature


def get(feature_id: str) -> CddFeature:
    if feature_id not in _REGISTRY:
        raise KeyError(f"unknown CDD feature id: {feature_id}")
    return _REGISTRY[feature_id]


def all_features() -> List[CddFeature]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def feature_ids() -> List[str]:
    return sorted(_REGISTRY)


def run(feature_id: str, internal_mode: bool = False) -> dict:
    """Run a registered feature's demo exhibit and render it for an audience."""
    return get(feature_id).demo().render(internal_mode=internal_mode)


def _autoload() -> None:
    """Import feature modules so their ``register`` calls run.

    Imports are best-effort: a feature module that fails to import (for example
    a missing optional dependency) must not take down the whole registry.
    """
    from importlib import import_module

    modules = [
        "tam_sam_som",
        "pvm_bridge",
        "payer_mix",
        "pct_medicare",
        "retention_survival",
        "ltv_cac",
        "provider_density",
        "market_saturation",
        "site_of_care",
        "concentration",
        "monte_carlo_overlay",
        "hcc_raf",
        "ffs_correction",
        "quality_benchmark",
        "positioning_map",
        "profit_pool",
        "marimekko",
        "growth_archetype",
        "unit_economics_spine",
        "rate_update_scorecard",
        "payer_economics",
        "commercial_multiplier",
        "market_concentration",
        "pricing_cm_bridge",
        "regulatory_flags",
        "forecast",
        "anomaly",
        "changepoint",
        "decisions",
        "ingestion",
        "diligence_pack",
    ]
    for name in modules:
        try:
            import_module(f"rcm_mc.cdd.{name}")
        except Exception:  # noqa: BLE001 - a broken module must not break the registry
            continue


_autoload()

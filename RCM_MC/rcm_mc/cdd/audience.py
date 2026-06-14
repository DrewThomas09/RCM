"""BOLSTER-04 Two-audience rendering layer.

Audience separation is enforced in code, not by convention. The internal
(Chartis engagement manager) view exposes assumption nodes, reconciliations,
model internals, and source plus vintage. The partner view is clean and branded
and never receives internal assumption nodes or internal-only series unless
``internal_mode`` is set.

This module wraps the exhibit render with a branded envelope and ships a
leakage check that any caller (and the golden suite) can run over a rendered
exhibit to prove no internal node escaped to a partner surface.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import registry
from .exhibit import Exhibit

PARTNER_BRAND = "SeekingChartis"

# Keys that must never appear in a partner-facing render.
INTERNAL_ONLY_KEYS = ("assumptions",)


def render_for_audience(exhibit: Exhibit, *, internal_mode: bool) -> Dict[str, Any]:
    """Render an exhibit for an audience, wrapping partner output in a brand."""
    payload = exhibit.render(internal_mode=internal_mode)
    if internal_mode:
        payload["view"] = "internal"
        return payload
    payload["view"] = "partner"
    payload["brand"] = PARTNER_BRAND
    return payload


def find_leaks(rendered: Dict[str, Any]) -> List[str]:
    """Return a list of internal-node leaks in a partner-facing render.

    A leak is any internal-only key present, or any series flagged
    internal_only that survived into the payload.
    """
    if rendered.get("internal_mode"):
        return []  # internal view is allowed to carry everything
    leaks: List[str] = []
    for key in INTERNAL_ONLY_KEYS:
        if key in rendered:
            leaks.append(f"key:{key}")
    for s in rendered.get("series", []):
        if s.get("internal_only"):
            leaks.append(f"series:{s.get('name')}")
    return leaks


def core_pack_present(rendered: Dict[str, Any]) -> bool:
    """A renderable exhibit must carry a title, a footnote, and at least one series."""
    return bool(rendered.get("title")) and rendered.get("footnote") is not None \
        and len(rendered.get("series", [])) >= 1


def audit_registry() -> Dict[str, Any]:
    """Render every registered feature in both views and report leakage.

    Returns {feature_id: {partner_leaks, partner_core, internal_core}}.
    """
    report: Dict[str, Any] = {}
    for feat in registry.all_features():
        ex = feat.demo()
        partner = render_for_audience(ex, internal_mode=False)
        internal = render_for_audience(ex, internal_mode=True)
        report[feat.feature_id] = {
            "partner_leaks": find_leaks(partner),
            "partner_core": core_pack_present(partner),
            "internal_core": core_pack_present(internal),
            "internal_has_assumptions": "assumptions" in internal,
        }
    return report

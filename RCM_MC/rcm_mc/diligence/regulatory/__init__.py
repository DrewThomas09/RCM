"""Regulatory exposure modeling subpackage (Gap 3).

Five submodules, each consumable independently or composable into
the :class:`RegulatoryRiskPacket` that attaches to a
:class:`DealAnalysisPacket` at step 5.5.

Public API::

    from rcm_mc.diligence.regulatory import (
        RegulatoryRiskPacket, RegulatoryBand,
        compute_cpom_exposure,
        compute_nsa_exposure, compute_nsa_from_ccd,
        simulate_site_neutral_impact, simulate_all_scenarios,
        compute_team_impact, is_cbsa_mandatory,
        compute_antitrust_exposure,
        compose_packet,
    )

Every submodule reads from the ``content/`` YAMLs and is pure on
its inputs. The content files carry ``last_reviewed`` timestamps;
:func:`regulatory_content_freshness_report` gives callers a
single place to check whether the curation cadence has drifted.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .antitrust_rollup_flag import compute_antitrust_exposure
from .cpom_engine import compute_cpom_exposure
from .nsa_idr_modeler import (
    compute_nsa_exposure, compute_nsa_from_ccd,
)
from .packet import (
    AntitrustExposure, CPOMExposure, CPOMReport, NSAExposure,
    RegulatoryBand, RegulatoryRiskPacket, SiteNeutralExposure,
    TEAMExposure, compose_packet, worst_band,
)
from .site_neutral_simulator import (
    simulate_all_scenarios, simulate_site_neutral_impact,
)
from .team_calculator import compute_team_impact, is_cbsa_mandatory


CONTENT_FILES = (
    "cpom_states",
    "nsa_idr_benchmarks",
    "site_neutral_rules",
    "team_cbsa_list",
    "antitrust_precedents",
)


def regulatory_content_freshness_report(
    max_age_days: int = 60,
    today: date | None = None,
) -> Dict[str, Any]:
    """Return ``{filename: {"last_reviewed": ISO, "stale": bool,
    "age_days": int}}``. ``stale`` is True when any file's
    ``last_reviewed`` is older than ``max_age_days`` or missing.

    The weekly regression test uses this so a single assertion
    locks the curation cadence across all five YAMLs.
    """
    today = today or date.today()
    content_dir = Path(__file__).parent / "content"
    out: Dict[str, Any] = {}
    for name in CONTENT_FILES:
        path = content_dir / f"{name}.yaml"
        if not path.exists():
            out[name] = {"last_reviewed": None, "stale": True,
                         "age_days": None, "error": "missing"}
            continue
        try:
            data = yaml.safe_load(path.read_text("utf-8"))
        except yaml.YAMLError as exc:
            out[name] = {"last_reviewed": None, "stale": True,
                         "age_days": None, "error": str(exc)}
            continue
        lr = (data or {}).get("last_reviewed")
        if not lr:
            out[name] = {"last_reviewed": None, "stale": True,
                         "age_days": None,
                         "error": "no last_reviewed field"}
            continue
        try:
            reviewed = date.fromisoformat(str(lr))
            age = (today - reviewed).days
            out[name] = {
                "last_reviewed": str(lr),
                "stale": age > max_age_days,
                "age_days": age,
                "error": None,
            }
        except ValueError:
            out[name] = {"last_reviewed": str(lr), "stale": True,
                         "age_days": None,
                         "error": "malformed last_reviewed"}
    return out


__all__ = [
    "AntitrustExposure",
    "CONTENT_FILES",
    "CPOMExposure",
    "CPOMReport",
    "NSAExposure",
    "RegulatoryBand",
    "RegulatoryRiskPacket",
    "SiteNeutralExposure",
    "TEAMExposure",
    "compose_packet",
    "compute_antitrust_exposure",
    "compute_cpom_exposure",
    "compute_nsa_exposure",
    "compute_nsa_from_ccd",
    "compute_team_impact",
    "is_cbsa_mandatory",
    "regulatory_content_freshness_report",
    "simulate_all_scenarios",
    "simulate_site_neutral_impact",
    "worst_band",
]

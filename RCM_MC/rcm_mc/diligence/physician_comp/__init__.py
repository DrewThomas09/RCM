"""Physician compensation FMV + productivity-drift modeling (Prompt J).

Five submodules addressing the deal-side comp analytics VMG's
FMV-MD does not cover (VMG is compliance-letter workflow; this
is forward-looking simulation).

Public API::

    from rcm_mc.diligence.physician_comp import (
        Provider, ingest_providers,
        get_benchmark, percentile_placement, comp_per_wrvu_band,
        simulate_productivity_drift, DriftResult,
        check_stark_redline, StarkFinding,
        recommend_earnout_structure, EarnoutRecommendation,
    )
"""
from __future__ import annotations

from .comp_ingester import (  # noqa: F401
    Provider, comp_per_wrvu, ingest_providers,
)
from .earnout_advisor_enhancement import (  # noqa: F401
    EarnoutRecommendation, recommend_earnout_structure,
)
from .fmv_benchmarks import (  # noqa: F401
    comp_per_wrvu_band, get_benchmark, percentile_placement,
)
from .productivity_drift_simulator import (  # noqa: F401
    DriftResult, simulate_productivity_drift,
)
from .stark_aks_red_line import (  # noqa: F401
    StarkFinding, check_stark_redline,
)

__all__ = [
    "DriftResult",
    "EarnoutRecommendation",
    "Provider",
    "StarkFinding",
    "check_stark_redline",
    "comp_per_wrvu",
    "comp_per_wrvu_band",
    "get_benchmark",
    "ingest_providers",
    "percentile_placement",
    "recommend_earnout_structure",
    "simulate_productivity_drift",
]

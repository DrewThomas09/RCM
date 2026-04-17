"""Two-source Monte Carlo layer: prediction uncertainty × execution uncertainty.

Public surface::

    from rcm_mc.mc import (
        MetricAssumption,
        RCMMonteCarloSimulator,
        MonteCarloResult,
        compare_scenarios,
        check_convergence,
    )
"""

from .convergence import ConvergenceReport, check_convergence  # noqa: F401
from .ebitda_mc import (  # noqa: F401
    DistributionSummary,
    HistogramBin,
    MetricAssumption,
    MonteCarloResult,
    RCMMonteCarloSimulator,
    TornadoBar,
    default_execution_assumption,
    from_conformal_prediction,
)
from .scenario_comparison import ScenarioComparison, compare_scenarios  # noqa: F401
from .v2_monte_carlo import (  # noqa: F401
    V2MonteCarloResult,
    V2MonteCarloSimulator,
)

__all__ = [
    "ConvergenceReport", "check_convergence",
    "MetricAssumption", "RCMMonteCarloSimulator", "MonteCarloResult",
    "DistributionSummary", "HistogramBin", "TornadoBar",
    "default_execution_assumption", "from_conformal_prediction",
    "ScenarioComparison", "compare_scenarios",
    "V2MonteCarloSimulator", "V2MonteCarloResult",
]

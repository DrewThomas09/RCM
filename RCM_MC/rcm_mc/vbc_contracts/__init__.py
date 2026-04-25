"""VBC-ContractValuator — price value-based-care contracts under
uncertainty, with Bayesian updating on prior performance.

Builds on the cohort/HCC/contract math in ``rcm_mc.vbc`` and adds:

  • Program-specific contract templates (MSSP Basic A/B/C/D,
    MSSP Enhanced E, ACO REACH Global / Professional, MA
    delegated-risk, commercial DCEs, Medicaid MCO).

  • Monte Carlo over the three dominant uncertainty sources:
      1. Patient mix (HCC distribution drift period-over-period)
      2. Attribution drift (panel turnover)
      3. HCC coding intensity (the V28 cliff scenario)

  • Bayesian updating: a target with two years of prior PMPM
    performance updates the prior distribution; the posterior is
    what the valuator simulates against.

  • Track-choice optimizer: given a panel + the program suite,
    return the optimal Track and the EV-comparison table.

CMS' 2030 goal is for all Traditional Medicare beneficiaries to
be in an accountable-care relationship; the partner's question
is which Track captures the most value at the lowest downside.

Public API::

    from rcm_mc.vbc_contracts import (
        VBCProgram, PROGRAMS,
        StochasticInputs,
        run_monte_carlo_npv,
        bayesian_update_pmpm,
        valuate_contract,
        choose_optimal_track,
        ContractValuationResult,
    )
"""
from .programs import VBCProgram, PROGRAMS, list_programs
from .stochastic import (
    StochasticInputs,
    run_monte_carlo_npv,
    sample_patient_mix,
    sample_attribution_drift,
    sample_coding_intensity,
)
from .bayesian import (
    bayesian_update_pmpm,
    PriorBelief,
)
from .valuator import (
    valuate_contract,
    choose_optimal_track,
    ContractValuationResult,
)

__all__ = [
    "VBCProgram",
    "PROGRAMS",
    "list_programs",
    "StochasticInputs",
    "run_monte_carlo_npv",
    "sample_patient_mix",
    "sample_attribution_drift",
    "sample_coding_intensity",
    "bayesian_update_pmpm",
    "PriorBelief",
    "valuate_contract",
    "choose_optimal_track",
    "ContractValuationResult",
]

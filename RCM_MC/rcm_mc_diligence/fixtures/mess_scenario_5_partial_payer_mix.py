"""mess_scenario_5 — partial payer mix.

Pathology: 40% of claims have no payer_id, 15% have an unresolvable
payer_id, 45% are clean. This breaks base-rate analyses (cohort
liquidation, denial stratification, ZBA autopsy, payer contract
yield) because every calculation requires a payer class.

Expected DQ outcome: ingestion succeeds but with CRITICAL severity
on the payer_coverage rule. The analysis_coverage section labels the
degraded analyses as non-computable with a clear reason.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .synthetic import (
    SAMPLE_HCPCS, SAMPLE_PAYERS, mrns, rng,
    sample_claim_row, write_csv, write_readme,
)


FIXTURE_NAME = "mess_scenario_5_partial_payer_mix"
N_CLAIMS = 1_000
MISSING_FRACTION = 0.40
UNRESOLVED_FRACTION = 0.15
EXPECTED_OUTCOME = {
    "overall_status": "FAIL",
    "fail_rules": ["payer_coverage"],  # CRITICAL severity
    "degraded_analyses_min": 4,
}


def generate(output_dir: Path | str, *, seed: int = 45) -> Path:
    out = Path(output_dir) / FIXTURE_NAME
    out.mkdir(parents=True, exist_ok=True)
    r = rng(seed)
    shared_mrns = mrns(400, seed=seed)

    # Generate clean rows first; overwrite a subset's payer with
    # missing / unresolvable values. Use `payer_id` as the column
    # (the medical_claims source column that rules.py inspects);
    # the connector SQL will map it to Tuva's `payer` downstream.
    rows: List[Dict[str, Any]] = []
    for _ in range(N_CLAIMS):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="primary")
        d = spec.as_dict()
        # Add payer_id column; rename 'payer' to 'payer_name'.
        d["payer_id"] = d["payer"]
        d["payer_name"] = next((n for k, n in SAMPLE_PAYERS if k == d["payer"]),
                                d["payer"])
        del d["payer"]
        rows.append(d)

    n_missing = int(N_CLAIMS * MISSING_FRACTION)
    n_unresolved = int(N_CLAIMS * UNRESOLVED_FRACTION)
    r.shuffle(rows)
    for row in rows[:n_missing]:
        row["payer_id"] = None
        row["payer_name"] = None
    unresolved_codes = ["XYZ-PAYER", "LOCAL-99", "SELF-PAY-UNCLEAR",
                        "UNKNOWN_COMMERCIAL", "PLAN-PRIVATE"]
    for row in rows[n_missing:n_missing + n_unresolved]:
        row["payer_id"] = r.choice(unresolved_codes)
        row["payer_name"] = row["payer_id"]

    r.shuffle(rows)
    write_csv(out / "medical_claims.csv", rows)

    write_readme(
        out / "README.md",
        title="mess_scenario_5 — partial payer mix",
        pathology=(
            f"{N_CLAIMS} claims. {int(MISSING_FRACTION*100)}% have no "
            f"payer_id; {int(UNRESOLVED_FRACTION*100)}% have an unresolvable "
            f"payer_id (home-grown payer codes like XYZ-PAYER). The rest "
            f"are clean. This is the pattern that breaks base-rate "
            f"analyses because you can't partition by payer class when "
            f"the payer class is missing."
        ),
        expected=(
            "Ingestion succeeds but the overall status is FAIL due to "
            "the payer_coverage rule firing with CRITICAL severity. The "
            "DQ report's analysis_coverage section labels cohort_liquidation, "
            "denial_stratification, zba_autopsy, and payer_contract_yield "
            "as non-computable with the reason 'payer coverage degraded'."
        ),
    )
    return out

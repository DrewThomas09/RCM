"""mess_scenario_4 — legacy / proprietary billing codes.

Pathology: ~5,000 claims where 12% use codes that don't match the
HCPCS/CPT 5-char alphanumeric shape (real pattern for small acquired
practices with home-grown billing systems).

Expected DQ outcome: ingestion succeeds, unmapped_procedures rule
fires with ERROR severity (≥10% unmapped), the DQ report surfaces the
top unmapped codes ranked by frequency + approximate dollar impact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .synthetic import (
    SAMPLE_HCPCS, SAMPLE_UNMAPPED_CODES,
    mrns, rng, sample_claim_row, write_csv, write_readme,
)


FIXTURE_NAME = "mess_scenario_4_unmapped_codes"
N_CLAIMS = 1_200
UNMAPPED_FRACTION = 0.12
EXPECTED_OUTCOME = {
    "overall_status": "FAIL",
    "fail_rules": ["unmapped_procedures"],  # ERROR severity at ≥10%
}


def generate(output_dir: Path | str, *, seed: int = 44) -> Path:
    out = Path(output_dir) / FIXTURE_NAME
    out.mkdir(parents=True, exist_ok=True)
    r = rng(seed)
    shared_mrns = mrns(400, seed=seed)

    rows: List[Dict[str, Any]] = []
    n_unmapped = int(N_CLAIMS * UNMAPPED_FRACTION)
    n_clean = N_CLAIMS - n_unmapped
    for _ in range(n_clean):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="primary")
        rows.append(spec.as_dict())
    for _ in range(n_unmapped):
        spec = sample_claim_row(
            r, mrn_pool=shared_mrns, data_source="primary",
            hcpcs_pool=SAMPLE_UNMAPPED_CODES,
        )
        rows.append(spec.as_dict())
    # Shuffle so the unmapped rows are interleaved, not clumped.
    r.shuffle(rows)

    write_csv(out / "medical_claims.csv", rows)

    write_readme(
        out / "README.md",
        title="mess_scenario_4 — legacy billing codes",
        pathology=(
            f"{N_CLAIMS} claims, {int(UNMAPPED_FRACTION*100)}% of which use "
            f"legacy or proprietary procedure codes that do not match the "
            f"HCPCS/CPT 5-char alphanumeric shape. Examples in this fixture "
            f"include {', '.join(SAMPLE_UNMAPPED_CODES[:3])}."
        ),
        expected=(
            f"Ingestion succeeds with FAIL overall (ERROR severity on "
            f"unmapped_procedures because the rate exceeds 10%). The DQ "
            f"report's connector_mapping section surfaces the top unmapped "
            f"codes ranked by frequency, with approximate dollar impact "
            f"computed from the associated charge_amount."
        ),
    )
    return out

"""mess_scenario_3 — duplicate adjudication records.

Pathology: ~2,000 claims, ~5% have multiple adjudication rows with
conflicting paid_amount values (rework, appeals, corrections). This
is the test that proves we let Tuva's ADR logic do the reconciliation
rather than rolling our own.

Expected DQ outcome: ingestion succeeds, duplicate_adjudication rule
fires with WARN severity, the DQ report shows reconciled vs
unresolved counts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .synthetic import (
    SAMPLE_HCPCS, claim_ids, mrns, rng,
    sample_claim_row, write_csv, write_readme,
)


FIXTURE_NAME = "mess_scenario_3_duplicate_adjudication"
N_CLAIMS = 600
DUP_FRACTION = 0.05
EXPECTED_OUTCOME = {
    "overall_status": "WARN",
    "warn_rules": ["duplicate_adjudication"],
}


def generate(output_dir: Path | str, *, seed: int = 43) -> Path:
    out = Path(output_dir) / FIXTURE_NAME
    out.mkdir(parents=True, exist_ok=True)
    r = rng(seed)
    shared_mrns = mrns(400, seed=seed)

    submitted: List[Dict[str, Any]] = []
    for _ in range(N_CLAIMS):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="primary")
        submitted.append(spec.as_dict())
    write_csv(out / "medical_claims.csv", submitted)

    # Remittance: each claim has at least one row. A DUP_FRACTION
    # subset gets a second row with a *different* paid_amount — this
    # models the "rework after appeal" pattern.
    remit: List[Dict[str, Any]] = []
    dup_targets = r.sample(submitted, k=int(N_CLAIMS * DUP_FRACTION))
    dup_set = {s["claim_id"] for s in dup_targets}
    for s in submitted:
        remit.append({
            "claim_id": s["claim_id"],
            "paid_date": s["claim_end_date"],
            "paid_amount": s["paid_amount"],
            "allowed_amount": s["allowed_amount"],
            "adjudication_event": "initial",
            "data_source": "835_primary",
        })
        if s["claim_id"] in dup_set:
            # Rework row — different paid_amount.
            remit.append({
                "claim_id": s["claim_id"],
                "paid_date": s["claim_end_date"],
                "paid_amount": round(s["paid_amount"] * r.uniform(0.70, 1.25), 2),
                "allowed_amount": s["allowed_amount"],
                "adjudication_event": "rework",
                "data_source": "835_rework",
            })
    write_csv(out / "remittance.csv", remit)

    write_readme(
        out / "README.md",
        title="mess_scenario_3 — duplicate adjudication records",
        pathology=(
            f"{N_CLAIMS} claims submitted. On the remittance side, "
            f"{int(DUP_FRACTION*100)}% of claims have two adjudication "
            f"rows with conflicting paid_amount values. This models the "
            f"rework / appeal / correction pattern where a claim is "
            f"reprocessed by the payer and an updated 835 is issued."
        ),
        expected=(
            "Ingestion succeeds with WARN overall. The "
            "duplicate_adjudication rule fires with WARN severity, "
            "surfacing the count of claims whose paid_amount varies "
            "across adjudication events. The medical_claim.sql CTE "
            "reconciles by summing paid_amount at the claim_id grain "
            "— confirming we rely on Tuva's claim-level reconciliation "
            "rather than picking a single 835 row by heuristic."
        ),
    )
    return out

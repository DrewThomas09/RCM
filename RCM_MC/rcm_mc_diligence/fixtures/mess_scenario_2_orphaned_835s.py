"""mess_scenario_2 — orphaned 835 remittances.

Pathology: 10,000 submitted 837 claims, 11,500 835 remittance rows.
The extra 1,500 remittance rows reference claim_ids that don't appear
in the submitted table — the usual cause is payer reprocessing /
secondary flows / NCPDP crossovers.

Expected DQ outcome: ingestion succeeds, orphaned_remittance rule
fires with WARN severity, the DQ report shows the orphan count and
the dollar total associated with the orphans.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .synthetic import (
    SAMPLE_HCPCS, claim_ids, mrns, rng,
    sample_claim_row, write_csv, write_readme,
)


FIXTURE_NAME = "mess_scenario_2_orphaned_835s"
N_SUBMITTED = 2_000       # keep test-fast; orphan ratio matters, not volume
N_ORPHAN = 300
EXPECTED_OUTCOME = {
    "overall_status": "WARN",
    "fail_rules": [],
    "warn_rules": ["orphaned_remittance"],
    "orphan_count": N_ORPHAN,
}


def generate(output_dir: Path | str, *, seed: int = 42) -> Path:
    out = Path(output_dir) / FIXTURE_NAME
    out.mkdir(parents=True, exist_ok=True)
    r = rng(seed)
    shared_mrns = mrns(800, seed=seed)

    # Submitted 837 claims.
    submitted: List[Dict[str, Any]] = []
    for _ in range(N_SUBMITTED):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="primary")
        submitted.append(spec.as_dict())
    write_csv(out / "medical_claims.csv", submitted)

    # 835 remittance — matches for ~90%, orphans for the rest.
    remit: List[Dict[str, Any]] = []
    sampled = r.sample(submitted, k=int(N_SUBMITTED * 0.9))
    for s in sampled:
        remit.append({
            "claim_id": s["claim_id"],
            "paid_date": s["claim_end_date"],
            "paid_amount": s["paid_amount"],
            "allowed_amount": s["allowed_amount"],
            "data_source": "835_primary",
        })
    # Orphans: claim_ids with a prefix so they can't collide with submitted.
    for _ in range(N_ORPHAN):
        fake_id = f"ORPH{r.randrange(10**9, 10**10):010d}"
        remit.append({
            "claim_id": fake_id,
            "paid_date": "2024-06-15",
            "paid_amount": round(r.uniform(40, 900), 2),
            "allowed_amount": round(r.uniform(50, 950), 2),
            "data_source": "835_orphan",
        })
    write_csv(out / "remittance.csv", remit)

    write_readme(
        out / "README.md",
        title="mess_scenario_2 — orphaned 835 remittances",
        pathology=(
            f"{N_SUBMITTED} submitted 837 claims arrive from the primary "
            f"clinic. The 835 remittance file contains {int(N_SUBMITTED*0.9) + N_ORPHAN} "
            f"rows — {N_ORPHAN} of which have claim_ids that do not match "
            f"any submitted claim. This is a real pattern when payer "
            f"reprocessing artifacts and secondary payer flows arrive on "
            f"the same 835 file."
        ),
        expected=(
            "Ingestion succeeds with WARN overall. The orphaned_remittance "
            "rule fires with WARN severity. The DQ report's "
            "raw_load_summary section includes the orphan count and the "
            "sum of paid_amount associated with orphans."
        ),
    )
    return out

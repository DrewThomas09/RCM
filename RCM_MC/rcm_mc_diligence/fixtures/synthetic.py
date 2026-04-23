"""Shared generators for the five pathological fixtures.

Deterministic given a seed — every fixture constructor takes a
``seed`` and hashes it into the RNG state so the synthetic data is
stable across runs. This is load-bearing for idempotency tests.

These are not realistic patient data; they're stochastic-but-
structured shapes that stress the ingestion pipeline's DQ detectors.
We sample CPT / ICD codes from a small curated in-memory set rather
than a real HCPCS file because the full set would bloat the package
and fail isolated-testing.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ── Small code universes ─────────────────────────────────────────────

# Real HCPCS / CPT codes, all 5-char alphanumeric. Kept small on
# purpose — the goal is realistic shape, not coverage.
SAMPLE_HCPCS = [
    "99213", "99214", "99203", "99204", "36415",
    "85025", "80053", "93000", "71046", "97110",
    "G0438", "G0439", "J0585", "J1100", "Q2038",
    "E0114", "A9150", "77057", "90471", "90658",
]

# Legacy / proprietary-looking codes that will NOT match the
# 5-char HCPCS shape. Used by mess_scenario_4 to drive the
# unmapped-procedure finding.
SAMPLE_UNMAPPED_CODES = [
    "LEGACY-07",
    "CLINIC_BLOOD_PANEL_01",
    "SELF-PAY-TELEVIS",
    "WELLNESS2024",
    "Z-SCREEN",
    "PROC.999",
    "RX-COMPLEX-IV",
    "MIC-INJ",
]

SAMPLE_PAYERS = [
    ("MCARE", "Medicare Part B"),
    ("MCAID", "Medicaid — State"),
    ("BCBS",  "Blue Cross Blue Shield PPO"),
    ("AETNA", "Aetna HMO"),
    ("UHC",   "UnitedHealthcare"),
    ("CIGNA", "Cigna HealthSpring"),
    ("HUMANA","Humana Medicare Advantage"),
    ("COMM",  "Commercial Self-Funded"),
]

SAMPLE_PLAN_NAMES = [
    "PPO Gold", "HMO Silver", "Medicare Advantage HMO", "Exchange Bronze",
    "Commercial PPO", "High Deductible HSA",
]


# ── RNG helper ───────────────────────────────────────────────────────

def rng(seed: int) -> random.Random:
    """Deterministic Random — idempotency relies on this."""
    return random.Random(seed)


# ── ID generators ────────────────────────────────────────────────────

def claim_ids(n: int, *, seed: int, prefix: str = "C") -> List[str]:
    r = rng(seed)
    return [f"{prefix}{r.randrange(10**9, 10**10):010d}" for _ in range(n)]


def mrns(n: int, *, seed: int, prefix: str = "MRN") -> List[str]:
    r = rng(seed)
    return [f"{prefix}-{r.randrange(10**6, 10**7):07d}" for _ in range(n)]


def dos_range(
    n: int, *, seed: int,
    start: date = date(2024, 1, 1), end: date = date(2024, 12, 31),
) -> List[date]:
    r = rng(seed)
    span = (end - start).days
    return [start + timedelta(days=r.randrange(0, span + 1)) for _ in range(n)]


# ── Claim row factory ────────────────────────────────────────────────

@dataclass
class ClaimRowSpec:
    """A minimal canonical claim row — fixtures munge from this."""
    claim_id: str
    claim_line_number: int
    person_id: str
    member_id: str
    payer: str
    plan: str
    claim_start_date: date
    claim_end_date: date
    hcpcs_code: str
    charge_amount: float
    paid_amount: float
    allowed_amount: float
    data_source: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_line_number": self.claim_line_number,
            "person_id": self.person_id,
            "member_id": self.member_id,
            "payer": self.payer,
            "plan": self.plan,
            "claim_start_date": self.claim_start_date.isoformat(),
            "claim_end_date": self.claim_end_date.isoformat(),
            "hcpcs_code": self.hcpcs_code,
            "charge_amount": round(self.charge_amount, 2),
            "paid_amount": round(self.paid_amount, 2),
            "allowed_amount": round(self.allowed_amount, 2),
            "data_source": self.data_source,
        }


def sample_claim_row(
    r: random.Random,
    *,
    mrn_pool: Sequence[str],
    data_source: str,
    claim_id: Optional[str] = None,
    hcpcs_pool: Optional[Sequence[str]] = None,
    payer_pool: Optional[Sequence[Tuple[str, str]]] = None,
    plan_pool: Optional[Sequence[str]] = None,
) -> ClaimRowSpec:
    hcpcs_pool = list(hcpcs_pool or SAMPLE_HCPCS)
    payer_pool = list(payer_pool or SAMPLE_PAYERS)
    plan_pool = list(plan_pool or SAMPLE_PLAN_NAMES)

    mrn = r.choice(mrn_pool)
    payer_id, _payer_name = r.choice(payer_pool)
    plan = r.choice(plan_pool)
    hcpcs = r.choice(hcpcs_pool)
    cid = claim_id or f"C{r.randrange(10**9, 10**10):010d}"
    dos = date(2024, 1, 1) + timedelta(days=r.randrange(0, 365))
    charge = round(r.uniform(80, 2200), 2)
    allowed = round(charge * r.uniform(0.35, 0.85), 2)
    paid = round(allowed * r.uniform(0.60, 1.0), 2)

    return ClaimRowSpec(
        claim_id=cid, claim_line_number=1,
        person_id=mrn, member_id=mrn + "-MEM",
        payer=payer_id, plan=plan,
        claim_start_date=dos,
        claim_end_date=dos + timedelta(days=r.randrange(0, 3)),
        hcpcs_code=hcpcs, charge_amount=charge,
        paid_amount=paid, allowed_amount=allowed,
        data_source=data_source,
    )


# ── IO helpers ───────────────────────────────────────────────────────

def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    """Write a dict-row CSV. Preserves dict key order of the *first*
    row as the header — so callers control column ordering by
    constructing row dicts deliberately.
    """
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            # DictWriter skips unknown keys silently — we pre-filter
            # to be explicit about dropped fields.
            w.writerow({k: row.get(k) for k in fieldnames})


def write_parquet(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pq.write_table(pa.table({}), path)
        return
    tbl = pa.Table.from_pylist(list(rows))
    pq.write_table(tbl, path)


def write_readme(path: Path, title: str, pathology: str, expected: str) -> None:
    """Every fixture writes a README next to its data so a human can
    open the fixture dir and know what it's testing without reading
    Python. The tests also read this file to assert the fixture's
    contract hasn't drifted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {title}\n\n"
        f"## Pathology\n\n{pathology.strip()}\n\n"
        f"## Expected DQ outcome\n\n{expected.strip()}\n",
        encoding="utf-8",
    )

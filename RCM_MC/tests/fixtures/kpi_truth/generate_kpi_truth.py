"""KPI-truth fixtures — 5 synthetic hospitals with hand-computed
ground-truth KPI values.

These fixtures are deliberately disjoint from the Phase 1 messy
fixtures under ``tests/fixtures/messy/``. Phase 1 was tested on noise;
Phase 2 is tested on correctness. Training on test is the failure
mode we're designing against (spec gauntlet §4).

Each hospital's ``expected.json`` carries the exact KPI values a
hand-computation produces on the constructed claims data. Tests match
to machine precision (≤ 1e-9 for lags, exact for counts, ≤ 0.001 for
rates). If a formula change shifts a KPI value, the test fails loud
— this is the regression lock.

Construction style: we build each fixture by writing claims with
known properties, then asserting the expected KPI values by hand in
the expected.json. We do NOT compute expected values by running the
engine; that would make the test a tautology.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List


# ── Helpers ─────────────────────────────────────────────────────────

def _write_claims(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _write_expected(path: Path, d: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# hospital_01 — "clean acute hospital"
# ═══════════════════════════════════════════════════════════════════
#
# 10 Medicare claims, all paid, no denials. Simple enough to compute
# every KPI by hand.

def build_hospital_01(root: Path) -> None:
    rows = []
    # 10 claims:
    # - charge_amount = 1000 each
    # - allowed      = 800 each
    # - paid         = 800 each
    # - service_date = 2024-01-01 + 10 days apart
    # - paid_date    = service_date + 30 days
    # - submit_date  = service_date + 5 days  → service→bill lag = 5 days
    # - bill→cash lag = 25 days
    # - payer = Medicare
    # - status = PAID, no CARCs.
    for i in range(10):
        dos = date(2024, 1, 1) + timedelta(days=i * 10)
        submit = dos + timedelta(days=5)
        paid = dos + timedelta(days=30)
        rows.append({
            "claim_id": f"H1-{i:03d}",
            "patient_id": f"P-{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": submit.isoformat(),
            "paid_date": paid.isoformat(),
            "cpt_code": "99213",
            "payer": "Medicare",
            "charge_amount": 1000.00,
            "allowed_amount": 800.00,
            "paid_amount": 800.00,
            "status": "paid",
        })
    _write_claims(root / "hospital_01_clean_acute" / "claims.csv", rows)

    # Hand-computed KPIs:
    # - Days in A/R weighted = 30 (every claim is 30, all equal weight)
    # - First-Pass Denial Rate = 0 (no denials)
    # - A/R Aging > 90: allowed − paid = 0, so no open balance → None
    # - Lag service→bill (median) = 5
    # - Lag bill→cash (median) = 25
    # - as_of for this fixture: 2025-01-01 (well after last cohort + 120d)
    expected = {
        "hospital": "hospital_01_clean_acute",
        "description": "10 Medicare claims, all paid in 30 days — bedrock KPI test.",
        "as_of_date": "2025-01-01",
        "provider_id": "H1",
        "claims_count": 10,
        "expected_kpis": {
            "days_in_ar": {"value": 30.0, "sample_size": 10},
            "first_pass_denial_rate": {"value": 0.0, "sample_size": 10},
            "ar_aging_over_90": {"value": None,
                                 "reason_contains": "no open A/R balance"},
            "cost_to_collect": {"value": None,
                                "reason_contains": "requires cost-of-collection"},
            "net_revenue_realization": {"value": None,
                                        "reason_contains": "contracted-rate"},
            "lag_service_to_bill": {"value": 5.0, "sample_size": 10},
            "lag_bill_to_cash": {"value": 25.0, "sample_size": 10},
        },
        "expected_cohort_liquidation": {
            "windows": [30, 60, 90, 120],
            # The 10 cohorts are spaced 10 days apart from 2024-01-01.
            # All paid at 30 days after service. With as_of=2025-01-01,
            # every cohort is fully mature (age ≥ 300 days).
            "mature_cohorts_all_120": True,
            # At 30 days, 100% liquidation per cohort.
            "liquidation_pct_at_30d": 1.0,
        },
    }
    _write_expected(root / "hospital_01_clean_acute" / "expected.json", expected)


# ═══════════════════════════════════════════════════════════════════
# hospital_02 — "denial-heavy outpatient practice"
# ═══════════════════════════════════════════════════════════════════
#
# 20 claims: 16 paid, 4 denied on first pass (20% FPDR).

def build_hospital_02(root: Path) -> None:
    rows = []
    for i in range(16):
        dos = date(2024, 6, 1) + timedelta(days=i * 2)
        submit = dos + timedelta(days=3)
        paid = dos + timedelta(days=20)
        rows.append({
            "claim_id": f"H2-P{i:03d}",
            "patient_id": f"P-{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": submit.isoformat(),
            "paid_date": paid.isoformat(),
            "cpt_code": "99214",
            "payer": "Aetna",
            "charge_amount": 500.00,
            "allowed_amount": 400.00,
            "paid_amount": 400.00,
            "status": "paid",
            "adjustment_reason_codes": "",
        })
    for i in range(4):
        dos = date(2024, 6, 15) + timedelta(days=i * 2)
        submit = dos + timedelta(days=3)
        rows.append({
            "claim_id": f"H2-D{i:03d}",
            "patient_id": f"P-DEN-{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": submit.isoformat(),
            "paid_date": "",
            "cpt_code": "99214",
            "payer": "Aetna",
            "charge_amount": 500.00,
            "allowed_amount": 400.00,
            "paid_amount": 0.00,
            "status": "denied",
            "adjustment_reason_codes": "50",    # medical necessity
        })
    _write_claims(root / "hospital_02_denial_heavy" / "claims.csv", rows)

    expected = {
        "hospital": "hospital_02_denial_heavy",
        "description": "20 commercial claims, 4 denied first-pass (FPDR=20%).",
        "as_of_date": "2025-01-01",
        "provider_id": "H2",
        "claims_count": 20,
        "expected_kpis": {
            "days_in_ar": {"value": 20.0, "sample_size": 16},
            "first_pass_denial_rate": {"value": 0.20, "sample_size": 20},
            # 4 denied claims × $400 open balance each = $1600 total open.
            # All denials have service dates 2024-06-15..2024-06-21, as_of
            # 2025-01-01 → ages >90 days → 100% in the >90 bucket.
            "ar_aging_over_90": {"value": 1.0, "sample_size": 4},
            "lag_service_to_bill": {"value": 3.0, "sample_size": 20},
            "lag_bill_to_cash": {"value": 17.0, "sample_size": 16},
        },
        "expected_denial_stratification": {
            "top_category": "CLINICAL",      # CARC 50 = medical necessity
            "top_category_count": 4,
            "top_category_dollars": 1600.0,
        },
    }
    _write_expected(root / "hospital_02_denial_heavy" / "expected.json", expected)


# ═══════════════════════════════════════════════════════════════════
# hospital_03 — "censoring test" — young cohorts should be refused
# ═══════════════════════════════════════════════════════════════════
#
# 5 claims in Dec 2025 (old, mature), 5 in Feb 2026 (young, as_of
# 2026-03-15 so only ~30 days after DOS).

def build_hospital_03(root: Path) -> None:
    rows = []
    # Mature cohort: December 2025
    for i in range(5):
        dos = date(2025, 12, 1) + timedelta(days=i * 3)
        paid = dos + timedelta(days=25)
        rows.append({
            "claim_id": f"H3-M{i:03d}",
            "patient_id": f"P-{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": (dos + timedelta(days=5)).isoformat(),
            "paid_date": paid.isoformat(),
            "cpt_code": "99213",
            "payer": "Medicare",
            "charge_amount": 1000.00,
            "allowed_amount": 800.00,
            "paid_amount": 800.00,
            "status": "paid",
        })
    # Young cohort: February 2026 — as_of 2026-03-15 → cohort is only
    # ~14-42 days old. 90-day and 120-day windows MUST be censored.
    for i in range(5):
        dos = date(2026, 2, 1) + timedelta(days=i * 3)
        paid = dos + timedelta(days=15)
        rows.append({
            "claim_id": f"H3-Y{i:03d}",
            "patient_id": f"P-Y{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": (dos + timedelta(days=5)).isoformat(),
            "paid_date": paid.isoformat(),
            "cpt_code": "99213",
            "payer": "Medicare",
            "charge_amount": 1000.00,
            "allowed_amount": 800.00,
            "paid_amount": 800.00,
            "status": "paid",
        })
    _write_claims(root / "hospital_03_censoring" / "claims.csv", rows)

    expected = {
        "hospital": "hospital_03_censoring",
        "description": "Dec 2025 mature cohort + Feb 2026 young cohort; as_of 2026-03-15.",
        "as_of_date": "2026-03-15",
        "provider_id": "H3",
        "claims_count": 10,
        "expected_cohort_liquidation": {
            # Mature cohort 2025-12 should have numbers at 30/60/90/120.
            "mature_cohort": "2025-12",
            "mature_cohort_status_at_120": "MATURE",
            "mature_cohort_liquidation_at_30d": 1.0,
            # Young cohort 2026-02 — age at as_of=2026-03-15 is only
            # 14-42 days → 30d MATURE only for mid/late-month DOS; 60+
            # definitely censored.
            "young_cohort": "2026-02",
            "young_cohort_status_at_90": "INSUFFICIENT_DATA",
            "young_cohort_status_at_120": "INSUFFICIENT_DATA",
        },
    }
    _write_expected(root / "hospital_03_censoring" / "expected.json", expected)


# ═══════════════════════════════════════════════════════════════════
# hospital_04 — "mixed payer mix"
# ═══════════════════════════════════════════════════════════════════
#
# Even 5/5/5/5 split across Medicare / Medicaid / Commercial / Self-Pay.
# Used by distribution-shift tests + payer-mix sanity.

def build_hospital_04(root: Path) -> None:
    payers = [
        ("Medicare", "MEDICARE"),
        ("Medicaid", "MEDICAID"),
        ("Blue Cross Blue Shield", "COMMERCIAL"),
        ("Self-Pay", "SELF_PAY"),
    ]
    rows = []
    for payer_idx, (payer_raw, _cls) in enumerate(payers):
        for i in range(5):
            dos = date(2024, 3, 1) + timedelta(days=payer_idx * 5 + i)
            paid = dos + timedelta(days=22)
            rows.append({
                "claim_id": f"H4-{payer_idx}-{i:03d}",
                "patient_id": f"P-{payer_idx}-{i:03d}",
                "date_of_service": dos.isoformat(),
                "submit_date": (dos + timedelta(days=4)).isoformat(),
                "paid_date": paid.isoformat(),
                "cpt_code": "99214",
                "payer": payer_raw,
                "charge_amount": 600.00,
                "allowed_amount": 500.00,
                "paid_amount": 500.00,
                "status": "paid",
            })
    _write_claims(root / "hospital_04_mixed_payer" / "claims.csv", rows)
    expected = {
        "hospital": "hospital_04_mixed_payer",
        "description": "Even 5/5/5/5 payer mix — for distribution-shift / payer-mix checks.",
        "as_of_date": "2025-01-01",
        "provider_id": "H4",
        "claims_count": 20,
        "expected_kpis": {
            "days_in_ar": {"value": 22.0, "sample_size": 20},
            "first_pass_denial_rate": {"value": 0.0, "sample_size": 20},
        },
        "expected_payer_class_counts": {
            "MEDICARE": 5, "MEDICAID": 5, "COMMERCIAL": 5, "SELF_PAY": 5,
        },
    }
    _write_expected(root / "hospital_04_mixed_payer" / "expected.json", expected)


# ═══════════════════════════════════════════════════════════════════
# hospital_05 — "dental DSO proxy" — all self-pay, low amounts
# ═══════════════════════════════════════════════════════════════════
#
# Used by distribution-shift test: should flag OUT_OF_DISTRIBUTION
# vs an acute-hospital-trained corpus.

def build_hospital_05(root: Path) -> None:
    rows = []
    for i in range(40):
        dos = date(2024, 1, 1) + timedelta(days=i)
        paid = dos + timedelta(days=1)    # cash at point of service
        rows.append({
            "claim_id": f"H5-{i:03d}",
            "patient_id": f"P-{i:03d}",
            "date_of_service": dos.isoformat(),
            "submit_date": dos.isoformat(),
            "paid_date": paid.isoformat(),
            "cpt_code": "D1110",        # CDT — dental cleaning
            "payer": "Self-Pay",
            "charge_amount": 125.00,
            "allowed_amount": 125.00,
            "paid_amount": 125.00,
            "status": "paid",
        })
    _write_claims(root / "hospital_05_dental_dso" / "claims.csv", rows)
    expected = {
        "hospital": "hospital_05_dental_dso",
        "description": "40 self-pay dental claims — proxy for DSO distribution shift.",
        "as_of_date": "2025-01-01",
        "provider_id": "H5",
        "claims_count": 40,
        "expected_kpis": {
            "days_in_ar": {"value": 1.0, "sample_size": 40},
            "first_pass_denial_rate": {"value": 0.0, "sample_size": 40},
        },
        "expected_distribution_shift_vs_acute_corpus":
            "OUT_OF_DISTRIBUTION",
    }
    _write_expected(root / "hospital_05_dental_dso" / "expected.json", expected)


# ── Driver ──────────────────────────────────────────────────────────

BUILDERS = {
    "hospital_01_clean_acute": build_hospital_01,
    "hospital_02_denial_heavy": build_hospital_02,
    "hospital_03_censoring": build_hospital_03,
    "hospital_04_mixed_payer": build_hospital_04,
    "hospital_05_dental_dso": build_hospital_05,
}


def regenerate_all(root: Path | None = None) -> Dict[str, Path]:
    root = root or Path(__file__).resolve().parent
    out = {}
    for name, builder in BUILDERS.items():
        d = root / name
        if d.exists():
            for f in sorted(d.rglob("*"), reverse=True):
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    f.rmdir()
        builder(root)
        out[name] = d
    return out


if __name__ == "__main__":
    for name, path in regenerate_all().items():
        print(f"  {name:40s} → {path}")

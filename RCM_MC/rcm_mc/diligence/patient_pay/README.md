# patient_pay/

**Patient payment dynamics** (Gap 9) — HDHP exposure + POS collection + state medical-debt overlay.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Surfaces `HDHPExposure` + `segment_patient_pay_exposure`. |
| `hdhp_segmentation.py` | **HDHP share × bad-debt amplifier.** HDHP members produce outsized patient balances; patient recovery is a fraction of insurer recovery → HDHP share is a material bad-debt driver. |
| `pos_collection_benchmark.py` | **Point-of-service collection-rate benchmarks** — best-in-class vs target, lift opportunity. |
| `medical_debt_overlay.py` | **State-level medical-debt credit-reporting overlay.** State laws banning medical debt on consumer credit reports compress collection tools → bad-debt reserves rise. |

## Why this matters

Patient-responsibility share has grown ~10pp over the last decade as HDHP adoption spread. For a typical target:
- Insurer-paid recovery rate: ~95%
- Patient-paid recovery rate: ~35-45%

A 10pp shift from insurer to patient responsibility can materially compress cash-to-rev. `hdhp_segmentation.py` quantifies the target's exposure; `pos_collection_benchmark.py` shows how much is recoverable with best-practice POS collections.

## The state medical-debt layer

Colorado (SB23-093, 2023), New York (FDCPA expansion, 2023), California (AB 1020), New Jersey, and others have enacted laws restricting or banning medical debt reporting to consumer credit bureaus. This removes a collection tool, pushing bad-debt reserves higher in those states.

`medical_debt_overlay.py` maps target's state footprint → enforcement tier → reserve adjustment. Refresh when new state laws pass.

## Where it plugs in

- **EBITDA bridge** — patient-pay lever in the v2 unit-economics bridge
- **Bankruptcy-Survivor Scan** — HDHP-heavy patient-pay mix is one of the 12 pattern checks
- **Working-capital DNFB reserve** — feeds the bad-debt component

## Tests

`tests/test_patient_pay*.py` — HDHP segmentation math + POS benchmark lookups + state overlay per-state coverage.

# deal_autopsy/

**"You're about to do Steward again."** Library of 12 historical PE healthcare deals (bankruptcies, distressed sales, and one or two strong exits for calibration), each reduced to a **9-dimension risk signature**. Match the target's signature → surface nearest historical outcome.

## The 9 dimensions

Each deal is reduced to a 9-vector in `[0.0, 1.0]`:
1. Payer mix concentration
2. Medicaid / Medicare-Advantage exposure
3. Lease intensity (rent-to-rev)
4. Regulatory exposure
5. Physician concentration
6. Leverage at entry
7. Capex deferral signature
8. Management tenure / quality
9. Sponsor pattern (roll-up vs platform vs take-private)

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 9-dim signature + narrative pattern. |
| `library.py` | **Curated library** of historical PE healthcare deals. Each: 9-vector entry signature + narrative of what actually happened + severity outcome. |
| `matcher.py` | **Signature extraction + similarity.** Squared Euclidean distance normalized to max theoretical distance (`sqrt(9) = 3.0`). Each dim's squared deviation surfaced so partners see which dimensions drove the match. |

## Named deals in the library

Steward (2016 MPT → 2024 bankruptcy), Cano Health (2022-2023 → bankruptcy), Envision (2018 KKR → 2023 distress), Surgery Partners, US Acute Care Solutions, Covis Pharma, Prospect Medical (2019 → 2025 distress), and others. Plus a handful of strong-exit benchmarks for calibration.

## Matcher output

```python
from rcm_mc.diligence.deal_autopsy import match_signature
result = match_signature(target_signature)
# result.top_match = "Steward Health 2016-2024"
# result.similarity = 0.74  (1.0 = identical)
# result.driving_dimensions = ["lease_intensity", "medicaid_exposure", "leverage"]
# result.narrative = "..." (full case study)
```

The **driving dimensions** are the real value — partners see which specific attributes make this target look like the named failure.

## Where it plugs in

- **Thesis Pipeline step 13** — runs after other risk modules produce signature inputs
- **Bankruptcy-Survivor Scan** — historical-failure patterns (the 6 named patterns in the 12-check scan) are backed by this library
- **Bear Case** — autopsy match is `[A1]` evidence in the PATTERN theme
- **IC Packet** — named match + narrative go into the "historical parallels" section

## Tests

`tests/test_deal_autopsy.py` — signature extraction deterministic + Euclidean distance contract + library coverage.

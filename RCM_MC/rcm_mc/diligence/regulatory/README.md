# regulatory/

**Regulatory exposure modeling** (Gap 3). Five analytics + a packet composer + TEAM calculator. Each consumable independently; composes into a `RegulatoryRiskPacket` that attaches to `DealAnalysisPacket` at step 5.5.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — five submodules + packet composition. |
| `packet.py` | **`RegulatoryRiskPacket` composer.** Attaches to `DealAnalysisPacket` at step 5.5 (after comparables, before reimbursement). Carries outputs of all five regulatory submodules. |
| `cpom_engine.py` | **Corporate Practice of Medicine exposure.** Target's legal structure × state footprint × `content/cpom_states.yaml` lattice → per-state CPOM exposure. |
| `nsa_idr_modeler.py` | **No Surprises Act IDR exposure.** For hospital-based physician groups (ER, anesthesia, radiology, pathology, neonatology, hospitalist) — OON revenue share × QPA recalc → revenue-at-risk. |
| `site_neutral_simulator.py` | **OPPS vs PFS site-neutral migration simulator.** HOPD revenue × three scenarios (current CY2026 / MedPAC all-ambulatory / full legislative expansion) × 340B overlay. |
| `antitrust_rollup_flag.py` | **FTC/DOJ antitrust rollup detector.** Target acquisition history + specialty + MSA → estimated HHI at (MSA, specialty) + HSR expansion exposure. |
| `team_calculator.py` | **CMS TEAM (Transforming Episode Accountability Model) calculator.** Mandatory bundled-payment model — 741 hospitals in 188 CBSAs starting 2026-01-01. Bundled episodes: LEJR, SHFFT, spinal fusion, CABG, major bowel. |

## Composition

Each submodule is independently consumable. `packet.py::RegulatoryRiskPacket` is the composer:

```python
from rcm_mc.diligence.regulatory import compute_regulatory_risk
packet = compute_regulatory_risk(target_profile)
# packet.cpom, packet.nsa_idr, packet.site_neutral, packet.antitrust, packet.team
# plus packet.composite_risk_tier
```

Attaches to `DealAnalysisPacket` at step 5.5 (after comparables, before reimbursement). See `analysis.packet_builder`.

## Calibration sources

- CPOM lattice: `content/cpom_states.yaml` — hand-curated per-state rules, refresh when state law changes
- NSA IDR: QPA recalculation rules from CMS Final Rule 2024
- Site-neutral: MedPAC recommendations + current CMS payment differentials
- Antitrust: HSR thresholds + FTC recent consent orders (e.g., USAP)
- TEAM: CMS Final Rule (November 2024) — 741 hospitals, 188 CBSAs

## Where it plugs in

- **Thesis Pipeline step 15** — regulatory exposure runs alongside Payer Stress + HCRIS X-Ray
- **Regulatory Calendar × Kill-Switch** (`diligence/regulatory_calendar/`) — newer cycle-shipped module that pulls from this package for individual event impact + maps to named thesis drivers
- **Bear Case** — REGULATORY theme pulls from this packet's fields

## Tests

`tests/test_regulatory*.py` — per-submodule coverage + integration through `RegulatoryRiskPacket`.

# screening/

**Pre-packet scans — the go-to-market wedge.** A 30-minute teaser scan a PE associate runs before committing hours to full diligence. If RED/CRITICAL, the deal doesn't advance.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "go-to-market wedge for 30-minute teaser scans." |
| `bankruptcy_survivor.py` | **Bankruptcy-Survivor Scan — 12 deterministic pattern checks.** |

## The 12 deterministic checks

### Historical-failure signatures (6)

1. **Steward-pattern** — REIT landlord + high rent-to-rev + Medicaid mix (see `real_estate/steward_score.py`)
2. **Cano-pattern** — MA coding-intensity exposure + V28 risk (see `ma_dynamics/v28_recalibration.py`)
3. **Envision-pattern** — NSA IDR exposure + physician-owned ER group
4. **Prospect-pattern** — undercap + REIT + distressed refi calendar
5. **USAP-pattern** — FTC consent-order-eligible physician rollup
6. **Surgery-Partners-era** — pre-V28 aggressive rollup without payer-mix protection

### Live-risk patterns (6)

7. **REIT-landlord cluster** — target + peers share the same REIT landlord
8. **V28-exposed MA rollup** — roster dx-code aggressiveness above the V28 trip wire
9. **Locum-inflated roster** — billing NPI count vs scheduled FTE >25% gap
10. **NSA-exposed ER/anesthesia/radiology** — hospital-based physician group with OON mix
11. **HDHP-heavy patient-pay mix** — HDHP share × bad-debt amplifier
12. **Deferred-capex signature** — HCRIS maint capex implausibly low vs gross PPE

## Runtime

**~30 minutes total** for a PE associate to run + review. Uses only publicly available data (HCRIS + Care Compare + FTC filings + state regulator pages). No CCD required.

If any check returns **RED/CRITICAL**, the module produces a narrative summary + recommendation: "do not advance; here's what would change our mind." The deal exits the pipeline before packet-builder spin-up, saving 4-8 hours of associate time per dead lead.

## Where it plugs in

- **Pre-packet entry** — before `analysis.packet_builder` is even called
- **Thesis Pipeline step 6** — runs when no prior screening result exists
- **IC Packet** — screening result is the first section partners read
- **Deal Profile** — screening badge displayed prominently; RED/CRITICAL badges block advance to Deal MC

## Tests

`tests/test_bankruptcy_survivor.py` — each of the 12 patterns has an isolated unit test + an integration test against known-failure fixtures.

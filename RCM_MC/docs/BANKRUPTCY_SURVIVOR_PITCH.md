# The Bankruptcy-Survivor Scan

## The wedge

Every PE sponsor who diligenced Steward in 2016, Envision in 2018,
American Physician Partners in 2016, Cano Health pre-SPAC, Prospect
in 2019, or Wellpath at any point between 2019 and 2024 missed the
same structural signals. The diligence industry — Chartis, VMG, A&M,
KPMG — sells bespoke memos on each engagement. None of them offers
a product that says:

> *We would have flagged all six of those bankruptcies at screening.*

This scan does. It runs on public data only (no CCD required), in
under 30 seconds, against twelve deterministic pattern matches. A
PE associate runs it in the first 30 minutes of looking at a
teaser. If the verdict is RED or CRITICAL, the deal doesn't
advance.

## The twelve patterns

### Six historical failure profiles

Each pattern is a rule-based match against named historical
bankruptcies. Every positive match cites the named deal's entry EV
and outcome.

1. **Steward pattern** — hospital + REIT landlord + long lease
   (>15y) + high escalator (>3%) + thin EBITDAR coverage (<1.4x)
   + rural/safety-net geography. When all five factors trip, the
   match is full CRITICAL.
   *Historical outcome: Steward Health Care, 2016 MPT
   sale-leaseback (EV $1.25B) → Ch. 11 May 2024.*

2. **Envision pattern** — hospital-based physician group + OON
   revenue share ≥35% + PE ownership.
   *Historical outcome: Envision, 2018 KKR LBO $9.9B → Ch. 11 May
   2023. NSA revenue impact directly accelerated the clock.*

3. **APP pattern** — hospital-based physician + locum dependency
   ≥30% + NSA-covered OON revenue + specialty rollup in regulated
   MSAs.
   *Historical outcome: American Physician Partners, 2016 LBO →
   July 2023 liquidation. Trustee filings cited $3.2M/mo NSA drag.*

4. **Cano pattern** — MA-risk primary care + CAC-heavy growth
   (payback >24mo) + V28 exposure.
   *Historical outcome: Cano Health, IPO'd at $4.4B (2021) →
   Ch. 11 February 2024. V28 recalibration + unit-economics failure.*

5. **Prospect pattern** — hospital + MPT landlord + aggressive
   leverage + sale-leaseback structure. Overlaps with Steward but
   triggers at a lower threshold (MPT + hospital alone).
   *Historical outcome: Prospect Medical, 2019 Leonard Green/MPT
   (EV $1.55B); MPT wrote down the master-lease in 2023; Ch. 11
   January 2025.*

6. **Wellpath pattern** — correctional healthcare + thin payer
   diversification (HHI ≥3500) + regulatory-complaint cluster.
   *Historical outcome: Wellpath → Ch. 11 November 2024. Payer
   concentration + litigation exposure.*

### Six forward-looking regulatory vectors

These fire against 2026-era regulatory changes the platform already
models in the `rcm_mc.diligence.regulatory` package.

7. **CPOM kill-zone** — legal structure voided under CA SB 351 /
   OR SB 951 / MA H.5159. RED when the target's structure appears
   in a state's `structure_bans` list.

8. **TEAM downside exposure** — IPPS hospital in a mandatory
   CBSA under the CMS TEAM final rule (741 hospitals, 188 CBSAs,
   effective 2026-01-01).

9. **NSA IDR cliff** — hospital-based physician group with OON
   revenue share ≥20%. QPA reversion compresses seller-claimed
   rates toward Medicare + regional adjustment.

10. **Site-neutral erosion** — grandfathered HOPD revenue exposed
    to CY2026 OPPS cuts + MedPAC all-ambulatory proposal ($31.2B
    10-year industry hit).

11. **Antitrust rollup trigger** — specialty concentration in a
    regulated MSA drew the FTC's attention post-USAP. Same-
    specialty same-MSA tuck-ins ≥5 OR estimated HHI ≥2500 fires
    the 30-day FTC prior-notice regime.

12. **Sale-leaseback blocker** — state-by-state feasibility:
    Massachusetts H.5159 bans new hospital REIT sale-leasebacks;
    Connecticut HB 5316 phases out by 2027-10-01; Pennsylvania
    and Rhode Island have pending legislation.

## How the verdict rolls up

    GREEN     — 0 patterns matched
    YELLOW    — 1-2 patterns, none CRITICAL
    RED       — 3+ patterns OR any 1 CRITICAL that isn't a full
                named-case replay
    CRITICAL  — full named-case pattern replay (e.g., all 5 Steward
                factors; ≥35% OON hospital-based physician)

## If we had run this scan on the historical failures

Every one of the six named bankruptcies would have returned
**RED or CRITICAL** at time of their original LBO — verified by
the `test_bankruptcy_survivor_scan.py` replay suite:

- **Steward (2016)**: CRITICAL (Steward pattern + Prospect pattern
  + sale-leaseback blocker). EV at deal $1.25B → bankruptcy 2024.
- **Envision (2018)**: CRITICAL (Envision pattern + NSA cliff
  + APP pattern). EV $9.9B → bankruptcy 2023.
- **APP (2016)**: RED (APP pattern + Envision pattern + antitrust).
  EV $860M → liquidation 2023.
- **Cano Health (pre-SPAC)**: RED (Cano pattern). EV $4.4B IPO
  → bankruptcy 2024.
- **Prospect (2019)**: CRITICAL (Prospect + Steward + sale-
  leaseback blocker). EV $1.55B → bankruptcy 2025.
- **Wellpath (2019)**: RED-to-CRITICAL (Wellpath pattern). →
  bankruptcy 2024.

## What this does NOT do

- No legal opinion. The scan matches structural patterns against
  historical failures. Every positive match tells the partner
  *which diligence questions* to drive next — not *the answer*.
- No real-time news ingestion. Pattern-matching is
  structural-signal only; event-driven surveillance is a separate
  workstream.
- No guaranteed coverage of *future* failure modes the industry
  hasn't seen yet. The scan catches the known failure playbook;
  it cannot catch the next novel structural risk until after the
  first public failure emerges.

## Integration with the rest of the platform

- **Pre-screening only** — scan runs before the full 12-step
  packet build. Intended as a gate.
- **HTML output** — one page, print-to-PDF clean, suitable for
  IC-packet attachment.
- **Route** — `GET /screening/bankruptcy-survivor` (form),
  `POST /screening/bankruptcy-survivor` (run + render).
- **No CCD required** — public data only so there's no engagement
  overhead.

## Why now

2026 is the single worst regulatory year for PE healthcare in
recent memory. TEAM mandatory enrollment (Jan 1), V28 full
effect (Jan 1), CY2026 OPPS site-neutral cuts, CA/OR CPOM bans,
MA/CT sale-leaseback restrictions all land in the same 12-month
window. A sponsor committing capital in 2026 without this
screening is underwriting on 2024 assumptions.

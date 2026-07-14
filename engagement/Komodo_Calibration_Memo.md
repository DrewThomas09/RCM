# Komodo Calibration - memo for Ray
### Engagement-side. Reads the licensed Komodo extract against the public IFT master. One page.
### Status: SKELETON - benchmarks and all ten test panels are live; awaiting the raw extract from Andrew to re-derive the observed inputs (T1). Every number below recomputes from the visual transcription and is confirmed the moment the raw file lands.

---

## What the extract is
Komodo Health ambulance claims, calendar 2025, seven codes (A0425 mileage; A0426/A0427 ALS non-emergency/emergency; A0428/A0429 BLS non-emergency/emergency; A0433 ALS2; A0434 SCT), split Commercial / Medicare / Medicaid, with Open / Closed / Combined status and four dollar columns (Total, Reported, Estimated, Combined). About **47.1M claims** and **$14.3B combined allowed** as transcribed. Three caveats travel with every number: under 1 percent of claims dropped for missing line-of-business/state; codes are not mutually exclusive to status; multiple codes can appear on one claim, so grand totals need not equal the code breakdown.

## The capture / gross-up (T2) - the number everyone needs
Komodo's Medicare base-code volume is **13.94M claims**. The reconstructed Medicare book is the FFS carrier floor (10.64M, 2024) plus the institutional wedge (0.58M) = an **11.22M FFS AFS book** - which reconciles cleanly to MedPAC's 11.3M. The residual above that floor, **2.72M**, must be Medicare Advantage that Komodo captured. Against the widest Medicare universe (FFS AFS plus an MA upper bound), Komodo captures **about 50 percent** of the Medicare book, so the candidate gross-up is **~2.0x**.
- It is a **bounded estimate, not a point**: the MA denominator is an upper bound, so the capture is a floor and the gross-up a ceiling.
- **Weakest link:** it assumes capture is **payer-uniform** - the Medicare rate is applied to Commercial and Medicaid. Komodo's commercial capture may differ. Flag this wherever the gross-up is used.

## The commercial multiples (T3) - replaces the interim anchors
Measured commercial realized price runs well above Medicare: **A0428 ~$533 per claim (~2.0x the fee schedule, ~2.0x realized); A0434 ~$2,208 (~2.5x fee schedule, ~2.4x realized); A0426 ~$626 (~1.9x)**. This is the measured, per-code replacement for the interim FAIR ~1.6x bound and the statutory balance-billing pegs. The Reported-only column (from the raw file) is the conservative version.

## The estimated-allowed disclosure (T4) - read this before quoting dollars
**About a third (34 percent) of all dollars are Komodo-modeled**, not payer-reported, filled where the payer reported no allowed amount. Any sizing built on Combined dollars must carry this share; the Reported-only figures are the floor. This is why T3 keeps both columns.

## Maturity (T5)
2025 is early: **~80 percent of claims are still open**. Volumes and dollars will rise as claims close. No projected number is printed - a completion factor from a mature prior year is the stated method, and the current bias is understatement.

## The institutional verdict (T7 - Ray's question)
**INDETERMINATE until the raw file.** Metadata (claim form type / bill type / revenue center) decides whether institutional UB-04 lines are in the extract; volume alone cannot separate the MA surplus from institutional. If EXCLUDED, add the **581,532** Medicare institutional wedge separately and cut the second extract (revenue centers 0540-0549, HCPCS A0425-A0436, billing entity, units, date, payer) - the spec is on the T7 panel, ready to forward.

## The three things the extract cannot see
1. **Unbilled transports** - the ~1-in-5 did-not-always-bill incidence.
2. **Facility-pay revenue** - 18.6 percent of organizations take it; no claims dataset contains it.
3. **Bundled transports** - Part A inpatient-bundled and SNF consolidated-billing rides that never surface as a claim.
No gross-up recovers these. They are named, not modeled.

## Firewall
The Komodo extract is licensed engagement data. It never enters `IFT_Sourced_Evidence_Master`. This calibration imports public benchmarks from the master one-way and returns nothing; a leak check confirms zero Komodo-derived values in the master or its repo. (One RVU note: A0426 = 1.20 per the master, not the order's 1.75, which is the A0432 intercept RVU - the master governs.)

## Human items
1. Andrew delivers the raw extract file (and its data dictionary if available); T1 re-derives every observed input and hashes the file.
2. If T7 returns EXCLUDED or INDETERMINATE after the raw file, the second-extract spec goes to the sizing lead before that extract is cut.

# PEdesk vertical data-depth audit + CMS enrichment roadmap

_How well the six live verticals are integrated today, where they fall short of
the hospital/HCRIS gold standard, and the prioritized plan to deepen them with
**real** CMS data (downloaded once at build time, vendored with provenance, no
runtime network, no synthetic values)._

## How integrated each vertical is today

All six are integrated to the **same plumbing depth**: a loader (`data/<v>.py`),
a screener + provider profile, per-state market intelligence, the cross-sector
benchmark framework (#619), the investable-evidence layer (#620), the CMS
Provider X-Ray (resolver + report), and curated Guide/RAG context. Where they
differ is **data richness per provider**:

| Vertical | Providers | Provider fields | Quality metrics | Financials | Patient survey | Utilization |
|---|---:|---:|---:|---|---|---|
| **Hospital / HCRIS** | 6,123 | 24 | 15 derived | **yes** (cost-report revenue/margin/expense) | — (HCAHPS available, not wired) | beds, patient-days, payer-day mix |
| SNF / Nursing Home | 14,699 | 17 | **11** | no | no | beds, avg residents/day |
| Dialysis | 7,557 | 17 | 5 | no | no | stations |
| Home Health | 12,392 | 10 | 6 | no | no | no |
| Hospice | 6,852 | 11 | 6 | no | no | no |
| IRF | 1,221 | 11 | **3** | no | no | no |
| LTCH | 317 | 12 | **3** | no | no | beds |

**Verdict.** The non-hospital verticals are *well-integrated structurally* but
*shallower in data*: the hospital vertical's "detail" is its **HCRIS
cost-report financials + 15 derived metrics + multi-year trend + peer engine**.
The thinnest are **IRF and LTCH (3 metrics each)** — and that's an
under-extraction, not a data limit: their Provider Data files carry **65 / 78
measure codes** respectively; we pivoted only 3.

## What's missing vs the hospital gold standard

1. **More quality measures** — IRF/LTCH especially; the source files already
   hold them.
2. **Patient-experience (CAHPS)** — none of the six has a patient/family survey
   dimension; CMS publishes facility-level CAHPS for HH, Hospice, and Dialysis.
3. **Enforcement / ownership depth** — SNF has fines/penalties counts but not
   the dated deficiency, ownership, or PBJ-staffing detail CMS publishes.
4. **Financials / cost reports** — only hospitals (HCRIS). SNF cost reports
   (CMS 2540) and HHA/Hospice cost reports exist but are a heavier lift.
5. **Multi-year trend** — every vertical is a single dated snapshot (the
   prediction-readiness audit's panel-data gap).

## Enrichment roadmap (real CMS datasets, prioritized by ROI)

Confirmed available in the CMS Provider Data Catalog metastore. Each becomes
its own PR: download once → normalize a compact CSV with `source`/`source_date`
provenance → extend the loader → surface in screener + X-Ray + Guide → tests.

**Tier 1 — deepen the thinnest from data we already have / one file.**
- **IRF**: pivot more of the 65 Provider Data measure codes (within-stay PPR,
  pressure ulcer, falls-with-injury, function change, flu vaccination, …).
  Requires the **CMS IRF QRP measure dictionary** for honest names (codes are
  not self-describing — we will source names, not guess). 3 → ~8–10 metrics.
- **LTCH**: same, from its 78 codes. 3 → ~8 metrics.
- **Dialysis**: add ESRD-QIP measures (dialysis adequacy, NHSN infection) and
  more DFC measures already in `DFC_FACILITY`.

**Tier 2 — add the patient-experience dimension (named, readable files).**
- **Home Health → HHCAHPS** (`Home Health Care - Patient Survey (HHCAHPS)`).
- **Hospice → CAHPS Hospice Survey** (`Hospice care - Provider CAHPS …`).
- **Dialysis → ICH CAHPS** (`Patient survey (ICH CAHPS) - Facility`).
  CAHPS files carry human-readable measure columns → honest labels without a
  dictionary.

**Tier 3 — SNF enforcement/ownership depth.**
- **Ownership**, **Penalties**, **Health Deficiencies**, **Fire-Safety
  Deficiencies**, **PBJ staffing**, **SNF QRP**, **SNF VBP** datasets — adds
  dated enforcement events + ownership chains (also unlocks a real *enforcement
  event* label for the prediction roadmap).

**Tier 4 — financials (heaviest).**
- SNF cost reports (CMS 2540) and HHA/Hospice cost reports → revenue/margin
  proxies, bringing non-hospital verticals toward HCRIS-level financial depth.

## Guardrails (unchanged)

Real CMS public data only; download at build time, vendor compact CSVs with
provenance; **no runtime CMS/network calls, no synthetic data, no fabricated
measure names or values**. CMS public quality ≠ commercial revenue (except
HCRIS); percentile = peer deviation; concentration = composition not market
share. No auth/Caddy/systemd/deploy/env/secret/Ollama/Tailscale/RAG-runtime
changes; #579/#580 stay parked.

## Recommended execution order

1. IRF + LTCH measure deepening (Tier 1) — biggest depth jump, source files in
   hand, needs the QRP measure dictionary for honest names.
2. HH / Hospice / Dialysis CAHPS (Tier 2) — new dimension, self-labelling files.
3. SNF enforcement/ownership (Tier 3).
4. Cost-report financials (Tier 4).

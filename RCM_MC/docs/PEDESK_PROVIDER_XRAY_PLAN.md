# PEdesk CMS Provider X-Ray — plan

_The universal diligence scanner: enter any CCN / provider id / name, PEdesk
detects the vertical, pulls every relevant CMS fact, benchmarks it against
peers, and turns it into investable evidence with a Guide-aware page._

**Strategy:** the vertical pages are the *library*; the benchmark/evidence
framework is the *math layer*; the Guide/RAG corpus is the *explanation
layer*; **X-Ray is the analyst workflow** that composes them. We do **not**
rebuild benchmarks, evidence scoring, loaders, or Guide coverage — we reuse:

- six vertical loaders (`data/{home_health,hospice,snf,dialysis,irf,ltch}.py`)
- cross-sector benchmark framework (`data/cross_sector.py`, #619)
- investable-evidence scoring (`data/investable_evidence.py`, #620)
- prediction/data-readiness conclusions (#621 — descriptive only, no forecast)
- Guide/RAG page-context patterns (#617–#623)
- existing provider-profile + HCRIS X-Ray conventions

## Verticals & identifiers

| Vertical | id | Identifier | Loader | Profile route |
|---|---|---|---|---|
| Hospital | `hospital` | CCN | `hcris._get_latest_per_ccn()` | `/hospital/<ccn>` |
| SNF / Nursing Home | `nursing-homes` | CCN | `snf.load_snf_providers()` | `/nursing-homes/<ccn>` |
| Home Health | `home-health` | CCN | `home_health.load_home_health_providers()` | `/home-health/<ccn>` |
| Hospice | `hospice` | CCN | `hospice.load_hospice_providers()` | `/hospice/<ccn>` |
| Dialysis | `dialysis` | CCN | `dialysis.load_dialysis_providers()` | `/dialysis/<ccn>` |
| IRF | `inpatient-rehab` | CCN | `irf.load_irf_providers()` | `/inpatient-rehab/<ccn>` |
| LTCH | `long-term-care-hospital` | CCN | `ltch.load_ltch_providers()` | `/long-term-care-hospital/<ccn>` |

All seven key on **CCN** (string; leading zeroes preserved). No vertical uses
an alternate provider id today.

### Cross-vertical CCN sharing (important, real)

Hospital-based **IRF and LTCH units share their CCN** with the HCRIS hospital
record. So an IRF/LTCH CCN resolves to **multiple** matches. The resolver
returns *all* of them (`Ambiguous`) and the UI shows a resolver table — it
never guesses. SNF / Home Health / Hospice / Dialysis CCN ranges do not
collide with HCRIS, so they resolve singly.

## Locality & fields by vertical

- **Home Health** carries `city` only (no county) — locality benchmarks use
  city. All other verticals carry `county`.
- Every vertical exposes `state`, `city`, `ownership`, `source`,
  `source_date`, plus its quality metrics (see `cross_sector` headline keys
  and `investable_evidence._QUALITY_METRICS`).
- Hospital/HCRIS adds `beds`, `net_patient_revenue`, `operating_expenses`,
  `net_income`, `medicare/medicaid_day_pct` — the one vertical with real
  cost-report financials (so HCRIS X-Ray can speak to margin/revenue; the
  others cannot and must not).

## Benchmarkable metrics (higher-is-better headline per vertical)

Reused from `cross_sector`/`investable_evidence`:

- Home Health → quality star rating, timely initiation, DTC, ambulation
- Hospice → Care Index, composite process, pain screening, treatment prefs
- SNF → overall / health-inspection / staffing / QM star ratings (+ SFF,
  abuse icon, penalties, ownership-change risk flags)
- Dialysis → 5-star
- IRF / LTCH → discharge-to-community (lower-is-better readmission & MSPB are
  shown raw but excluded from the higher=better index)
- Hospital → HCRIS cost-report metrics (beds, revenue, margin) where present

## Caveats by vertical (carried into the report + Guide)

- CMS public data only — **not** commercial revenue (except HCRIS hospital
  cost-report fields), payer mix, or private-pay volume.
- Concentration (HHI) is provider-**count** composition, **not** market share.
- Percentile is peer deviation; never a recommendation or causal claim.
- IRF (~1,200) and LTCH (~320) are small universes → small per-state samples;
  percentile/z-score suppressed below n=5.

## Resolver module (PR A — this PR)

`data/provider_xray.py`:

- `search_provider_xray(query, state=None) -> list[ProviderMatch]` — exact
  CCN/id across all verticals first, else case-insensitive name-contains.
- `resolve_provider_xray(identifier, state=None) -> ProviderMatch | Ambiguous | None`.
- `provider_match_by_ccn(ccn, vertical) -> ProviderMatch | None` — deterministic
  lookup once the vertical is known (e.g. from `?vertical=`).
- `ProviderMatch`: vertical, vertical_label, provider_id, ccn, name, state,
  city, county, source_dataset, profile_url, xray_url.

Resolver order: Hospital → SNF → Home Health → Hospice → Dialysis → IRF → LTCH.

## Proposed route map

- `/diligence/xray` — search / resolver landing.
- `/diligence/xray?ccn=<ccn>&vertical=<id>` — the benchmarked report.
- Linked from the **Diligence** nav, from each vertical provider profile
  ("Open in X-Ray"), and from the command palette ("Run CMS X-Ray").

## Proposed UI sections (PR C)

Search/resolver · provider identity header · diligence signal strip ·
benchmark table · peer-set panel · market context · evidence & limitations ·
8–12 suggested diligence questions · Guide context for the active provider.

## PR sequence

- **PR A (this):** plan doc + `provider_xray.py` resolver + tests. No UI.
- **PR B:** benchmark report object composing `cross_sector` +
  `investable_evidence` for a resolved provider; tests.
- **PR C:** `/diligence/xray` page + Diligence nav entry + Guide context
  (visible UI — approval-gated).
- **PR D:** RAG source cards (`docs/rag_sources/provider_xray.md`, …) + Guide
  questions + validators.

## Honesty / scope rules

No synthetic data, no fabricated revenue/market-share, no causal/prediction
claims, no new data vendoring, no runtime external calls. No changes to
auth/login, Caddy, systemd, deploy, secrets, Ollama/Tailscale, or RAG
runtime. #579/#580 stay parked. Visible-UI PRs (PR C) require approval.

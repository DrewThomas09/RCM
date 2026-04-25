# Multi-Asset Class Expansion: Beyond Hospitals

The platform today is a hospital-diligence engine — every data source,
predictor, and UI section assumes a HCRIS-shaped target. The PE
healthcare universe is ~5,000 hospitals + ~50,000 physician groups +
~5,800 ASCs + ~10,000 behavioral-health sites + ~30,000 post-acute
facilities. Expanding lets the platform underwrite ~10× more of the
addressable deal flow.

This document maps the path for four asset classes ranked by
near-term PE deal volume:

  1. **Physician groups** (PCP, specialty, MSO)
  2. **ASCs** (Ambulatory Surgery Centers)
  3. **Behavioral health** (SUD, mental health, autism, IDD)
  4. **Post-acute** (SNF, home health, hospice)

For each: what carries over, what needs new data + models + UI, and
the build sequence.

## What carries over from the hospital build

Every asset class reuses the **platform spine**:

- `colors.py`, `ui_kit.py`, `power_table`, `power_chart`,
  `compare`, `empty_states`, `loading`, `nav`, `theme`,
  `responsive`, `metric_glossary`, `provenance_badge` — the UI
  scaffolding is asset-agnostic.
- `trained_rcm_predictor.py` Ridge + k-fold CV scaffold — works on
  any target metric with any feature set.
- `ensemble_methods.py`, `regime_detection.py`, `volume_trend_
  forecaster.py`, `geographic_clustering.py` — analytical primitives
  that operate on time-series / cross-sectional data, asset-
  agnostic.
- `payer_mix_cascade.py` — the payer-mix → downstream-metrics
  cascade structure works for every fee-for-service asset; only the
  per-payer reimbursement indices change.
- `improvement_potential.py` — peer-benchmark gap → EBITDA $$
  scaffold with realism factors. Realism factors are asset-specific
  but the scaffold is shared.
- `comparable_finder.py` — peer-similarity scoring; only the
  weight set + features change per asset class.
- Auth, sessions, audit, exports — all asset-agnostic.

The platform is well-architected for multi-asset: the `data/`,
`ml/`, and `ui/` separation already isolates the hospital-specific
pieces. Expansion is mostly **add modules** rather than refactor.

What does NOT carry over is the hospital-specific data ingestion
(HCRIS, Hospital MRF, AHRQ HCUP, Hospital Compare) and the predictor
calibrations trained on hospital features.

---

## #1 — Physician Groups (highest PE deal volume)

### The asset

Single-specialty (cardiology, dermatology, ortho, dental) and
multi-specialty groups. Includes MSO + Friendly-PC structures, the
dominant PE healthcare model since ~2018. ~50,000 candidates in the
US; hundreds of deals/year.

### Data sources to add

| Source | What it provides | Complexity |
|---|---|---|
| **CMS Provider Utilization & Payment** (already partially ingested as Part B) | Procedure mix + volumes per NPI | Low — extend |
| **HRSA Area Health Resources File** | Demographics + supply-demand by county | Medium |
| **CMS Open Payments** (already ingested) | Industry payments per physician | Done |
| **Truven / IQVIA** (commercial) | Patient-encounter market-share | High — paid feed |
| **NPPES Type 1** (already ingested) | Per-physician registry | Done |
| **State medical board public data** | Licensure + disciplinary actions | Medium — 50 sources |
| **Medicare Provider of Services** | Practice locations + setting type | Low |

The big lift is moving from **facility-centric** to **physician-
centric** data — every existing pipeline that joined on `ccn` needs
a parallel `npi` join.

### Models to add or retune

| Model | Hospital version | Physician version |
|---|---|---|
| Volume forecaster | Service-line volumes per CCN | Procedure-mix CAGR per NPI |
| Comparable finder | 6-dimension hospital weights | Specialty + geography + procedure mix + payer mix |
| Improvement potential | 7 RCM levers | 4 levers (denial / DSO / collection / coding accuracy); RCM rev cycle is simpler in physician practices |
| Regime detection | Margin trend on financial panel | Volume trend + prior-auth-burden trend |
| Forward distress | 24mo margin forecast | Volume-decline-12mo forecast (revenue not the primary risk) |
| **NEW** — Physician-departure risk | n/a | Prior-auth + retirement-age + opioid-flag concentration → key-person-risk score |
| **NEW** — Roll-up synergy | n/a | Per-add-on physician group → expected EBITDA contribution under the platform |

### UI changes

- New asset-type field on `Deal`: `asset_class ∈ {hospital, physician_group, asc, behavioral, post_acute}`. Routes branch on it.
- `/deal/<id>/profile` becomes section-aware: physician-group profile shows procedure mix + key physician concentration + payer concentration; hospital profile shows beds + payer mix + occupancy.
- New `/screening/physician-groups` route reusing the same screening dashboard with a different metric set.
- Comp set finder filters by specialty + geography by default.

### Build sequence

1. **Phase 1 (4 wks)**: Schema extensions + Type-1 NPI predictor pipeline + procedure-mix volume forecaster.
2. **Phase 2 (4 wks)**: Physician-departure risk model + roll-up synergy model.
3. **Phase 3 (3 wks)**: UI branching on asset_class + new screening dashboard.
4. **Phase 4 (3 wks)**: Per-specialty calibration runs (cardiology, dermatology, ophthalmology, ortho, GI, dental — the top 6 PE specialties).

Total: ~14 weeks to physician-group-ready platform.

---

## #2 — ASCs (Ambulatory Surgery Centers)

### The asset

~5,800 Medicare-certified ASCs. Hot PE category — single-specialty (ophthalmology, orthopedics) often >25% EBITDA margin; multi-specialty ~15-20%. Typical deal $20-200M EV.

### Data sources to add

| Source | What it provides | Complexity |
|---|---|---|
| **CMS ASC Quality Reporting (ASCQR)** | Quality measures per ASC | Medium |
| **CMS ASC Payment Limit Files** | Medicare reimbursement by HCPCS for ASCs (vs HOPD) | Low |
| **ASC accreditation databases** (AAAHC, JCAHO, AAAASF) | Accreditation status + cycle | Medium |
| **State ASC licensing** | Per-state license + survey | High — 50 sources |
| **CMS POS file** (already ingested for hospitals) | Already covers ASCs (POS code 24) | Done |
| **HCRIS — ASC-specific (CMS-216-94)** | ASC cost reports — sparse but available | Medium |

### Models to add

| Model | Notes |
|---|---|
| Site-of-service shift extension | Already exists for hospitals; extend the model to predict OPPS→ASC migration explicitly |
| ASC EBITDA bridge | Different lever set: case-mix-shift (commercial vs Medicare), block-time utilization, surgeon-recruitment. RCM levers smaller (denials are lower in ASCs) |
| Surgeon-concentration risk | Top-3-surgeon share of cases drives key-person risk |
| Add-on-density model | ASCs cluster — buying #5 in a metro is different from #1. Geographic-saturation-aware add-on potential |
| Block-time utilization predictor | New target metric: predicted block utilization given case mix + surgeon roster |

### UI changes

- ASC profile renders: cases/year, top procedures, surgeon roster (top 5 by case volume), block utilization, accreditation status, vs nearest hospital HOPD pricing.
- Specialty filter chips (cardiology / GI / ophthalmology / ortho / pain / general surgery).
- "ASC vs HOPD pricing" comparison view using the existing `compare` module.

### Build sequence

1. **Phase 1 (3 wks)**: ASC POS filter + ASC-specific HCRIS-216 ingest + ASC payment limit files.
2. **Phase 2 (4 wks)**: Surgeon-concentration risk + block-time utilization predictor.
3. **Phase 3 (3 wks)**: UI extensions (ASC profile + specialty screening).
4. **Phase 4 (2 wks)**: Site-of-service shift model retrained on combined hospital+ASC volume data.

Total: ~12 weeks.

---

## #3 — Behavioral Health (SUD / mental health / autism / IDD)

### The asset

~10,000+ sites including IOPs, residential treatment, autism (ABA) clinics, methadone clinics, mental-health hospitals. PE volume surged post-pandemic. Heterogeneous: some are FFS, some are managed-care heavy, some are 1115 waiver / state-funded. Deal sizes $30-300M.

### Data sources to add

| Source | What it provides | Complexity |
|---|---|---|
| **SAMHSA N-SSATS / N-MHSS surveys** | Per-site service mix + capacity + payer mix | Medium |
| **SAMHSA Behavioral Health Treatment Locator** | Geographic registry | Low |
| **CMS OASAS / DEA** | SUD treatment authority + buprenorphine waiver counts | Medium |
| **State 1115 waiver expenditure data** | State-by-state Medicaid SUD payment streams | High |
| **Medicaid managed care contracts** (state + HHSC RFP databases) | Capitation rates | High |
| **Joint Commission BHC accreditation** | Accreditation status | Low |

The behavioral health data layer is **fragmented across federal SAMHSA + 50 state Medicaid offices** — meaningful ingestion lift.

### Models to add

| Model | Notes |
|---|---|
| Reimbursement-stream classifier | Predict % FFS / Medicaid managed care / state grant given site type + state |
| Capacity utilization | Beds × occupancy for residential; encounters × capacity for outpatient |
| Average-length-of-stay (ALOS) predictor | Critical financial driver for residential / inpatient psych |
| State-policy risk | Map per-state pending legislation that affects rate (1115 waiver renewals, prior-auth changes) |
| Workforce-shortage index | Behavioral-health workforce shortage acute; shortage in hiring radius is a deal-stopper |

### UI changes

- New profile renders: site type, license types, payer mix (FFS / Medicaid MCO / state contract / private), accreditation, ALOS, workforce-supply ratio.
- Reimbursement-stream pie chart (ASC / hospital / behavioral all use this in different ways).
- State-policy-risk panel with the recent `regime_detection` regulatory monitor extended to behavioral-health-specific rule changes.

### Build sequence

1. **Phase 1 (4 wks)**: SAMHSA N-SSATS / N-MHSS ingest + Behavioral Health Treatment Locator.
2. **Phase 2 (5 wks)**: Reimbursement-stream classifier + ALOS predictor + state-policy-risk overlay.
3. **Phase 3 (3 wks)**: UI extensions + workforce-shortage index integration.
4. **Phase 4 (4 wks)**: State-by-state Medicaid managed care ingestion (highest-volume 10 states first).

Total: ~16 weeks.

---

## #4 — Post-Acute (SNF / home health / hospice)

### The asset

- ~15,000 SNFs (most regulated; CMS Five-Star Rating is the bible)
- ~12,000 home health agencies
- ~5,000 hospice agencies

PE has been heavy in post-acute since 2010s; recent deal flow has slowed on regulatory pressure (PDPM transition, hospice fraud cases, RCS-1 unwinding).

### Data sources to add

| Source | What it provides | Complexity |
|---|---|---|
| **CMS Care Compare — SNF / HHA / Hospice** | Quality + 5-Star + survey deficiencies | Low — extend |
| **CMS LTC PEPPER reports** | Per-SNF utilization patterns vs peers | Medium |
| **CMS hospice CAHPS** | Family experience scores | Low |
| **MDS 3.0 (Minimum Data Set)** | Per-resident assessment data — sparse public; rich research-restricted | High |
| **OSCAR / CASPER** | Survey deficiency data per facility | Medium |
| **CMS SNF / HHA / hospice provider files** | Cost reports — already in HCRIS pipeline | Low |
| **DHHS OIG enforcement actions** | Fraud / qui tam / settlements | Medium |

### Models to add

| Model | Notes |
|---|---|
| 5-Star trajectory | Predict where the facility's star rating moves over 12mo from current quality measures |
| Deficiency-citation risk | Probability of next-survey deficiency cluster given current operational profile |
| OIG / RAC audit risk | Hospice especially — flagged by CMS for fraud-prone discharge patterns. Predict per-agency audit probability |
| PDPM rate optimizer | SNFs only — predict the rate uplift available from coding + assessment-timing optimization |
| Discharge-disposition shift | Track patients leaving hospital → SNF vs home, by region. Affects downstream demand |

### UI changes

- Post-acute profile renders: bed count or census, 5-Star trajectory, deficiency history, payer mix (heavy Medicare A in SNF, Medicare-only in hospice), CMS audit-risk overlay.
- Star-rating sparkline as a dashboard hero metric.
- Deficiency-history table with severity color-coded (using `colors.severity_color`).

### Build sequence

1. **Phase 1 (3 wks)**: Care Compare SNF/HHA/hospice ingest extensions + provider cost reports through existing HCRIS pipeline.
2. **Phase 2 (4 wks)**: 5-Star trajectory + deficiency-citation risk models.
3. **Phase 3 (4 wks)**: OIG/RAC audit-risk model + PDPM rate optimizer (SNF-specific).
4. **Phase 4 (3 wks)**: UI extensions for post-acute profile + dashboard.

Total: ~14 weeks.

---

## Cross-asset infrastructure (build once, all assets benefit)

These are the spine extensions that pay off across every asset class:

### Asset-class abstraction

`rcm_mc/asset/` — new package:

```python
class AssetClass(str, Enum):
    HOSPITAL = "hospital"
    PHYSICIAN_GROUP = "physician_group"
    ASC = "asc"
    BEHAVIORAL = "behavioral"
    POST_ACUTE = "post_acute"


class AssetProfile(Protocol):
    """Shared shape every asset-class profile satisfies."""
    asset_id: str           # CCN, NPI, or asset-specific
    asset_class: AssetClass
    name: str
    state: str
    cbsa: Optional[str]
    annual_revenue_mm: Optional[float]
    annual_ebitda_mm: Optional[float]
    payer_mix: Dict[str, float]
```

Each asset class subclasses with its own type-specific fields (beds for hospitals, surgeons for ASCs, license types for behavioral, etc.).

### Per-asset peer-benchmark library

`rcm_mc/benchmarks/` — keyed `(asset_class, metric, percentile)`. Peer percentile lookups today are hospital-specific; abstracting lets every comparison reuse the recent UI components.

### Asset-aware routing

Existing `/deal/<id>/profile` switches its rendered sections based on `packet.asset_class`. The 9-section narrative becomes:

- Hospital: Entity / Market / Comps / Metrics / Predictions / Bridge / Scenarios / Risks / Actions
- Physician group: Entity / Specialty Mix / Procedure Volume / Comps / Predictions / Bridge / Scenarios / Risks / Actions
- ASC: Entity / Surgeon Roster / Case Mix / Comps / Predictions / Bridge / Scenarios / Risks / Actions
- Behavioral: Entity / Service Mix / Reimbursement / Comps / Predictions / Bridge / Scenarios / Risks / Actions
- Post-acute: Entity / Quality / Deficiencies / Comps / Predictions / Bridge / Scenarios / Risks / Actions

### Asset-class screening dashboard

`/screening/<asset_class>` — same `screening/dashboard.py` scaffold with asset-specific column set + filter chips.

---

## Build sequence — full multi-asset roadmap

If we ran the four expansions sequentially:

| Quarter | Work | Cumulative coverage |
|---|---|---|
| Q1 | Physician groups Phase 1-2 | +50K assets |
| Q2 | Physician groups Phase 3-4 + ASC Phase 1-2 | +50K + ~5.8K assets |
| Q3 | ASC Phase 3-4 + Behavioral Phase 1 | All ASCs + start behavioral |
| Q4 | Behavioral Phase 2-4 | + ~10K behavioral |
| Q5 | Post-acute Phase 1-3 | + ~30K post-acute |
| Q6 | Post-acute Phase 4 + cross-asset infra | All four classes shipped |

Six quarters to underwrite ~95% of the addressable PE healthcare deal universe.

If we parallelize across two engineers:

| Quarter | Engineer A | Engineer B |
|---|---|---|
| Q1 | Physician groups P1-2 | Asset-class abstraction + benchmarks |
| Q2 | Physician groups P3-4 | ASC P1-3 |
| Q3 | Behavioral P1-2 | ASC P4 + Post-acute P1 |
| Q4 | Behavioral P3-4 | Post-acute P2-4 |

Four quarters with two engineers.

---

## Risk + mitigation

- **Data licensing**: Truven / IQVIA / commercial claims feeds are
  expensive and gated. v1 of physician-group expansion sticks to
  free CMS public data (Part B, Open Payments, NPPES). Paid feeds
  are upgrade path, not blocker.
- **State-by-state behavioral-health data**: Most fragmented surface
  on the map. Plan A is to ingest the top-10 PE-active states first
  (CA, TX, FL, NY, IL, PA, OH, MI, GA, NC) and gracefully fall back
  to 'no state-specific data' for the rest.
- **Per-specialty calibration**: Physician-group predictors trained
  on aggregated all-specialty data underperform. The Phase 4 per-
  specialty calibration runs are non-optional for partner trust.
- **5-Star moving target**: CMS regularly redefines the SNF 5-Star
  methodology; predictor needs annual recalibration.

---

## What success looks like

After the full multi-asset rollout, the platform supports:

- **Underwriting any healthcare PE deal** — a partner uploads a CIM
  for any of the four asset classes and gets a screening score
  within minutes.
- **Cross-asset portfolio view** — when a single sponsor owns
  multiple asset classes (common — Mednax, US Anesthesia Partners),
  the platform shows the unified portfolio at one URL.
- **Comparable transactions across asset classes** — ASC-of-MSO
  rollups, hospital-system + physician-group integrated networks,
  multi-modal behavioral health platforms.

The recent UI sprint already supports this — the dashboard, deal
profile, comparison module, search, and visualization layer are
asset-agnostic. The expansion is a data + model lift; the UI scales
without rewrite.

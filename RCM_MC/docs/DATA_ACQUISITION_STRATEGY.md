# Data Acquisition Strategy (next 12 months)

The platform already ingests 18 public CMS / Census / CDC sources
covering hospitals, payers, demographics, and Medicare Advantage.
Each new dataset adds either (a) coverage of an unaddressed asset
class, (b) predictive lift on an existing model, or (c) a new
analytical surface. The acquisition strategy ranks candidates by
**predictive power per dollar of effort**, not by superficial
data-volume.

## Scoring framework

Every candidate dataset gets four scores:

  • **Predictive lift** (0-10): expected improvement on at least
    one platform model, measured as R² delta or analyst-hours-saved.
  • **Engineering effort** (0-10): integration weeks. 0 = trivial
    refresh of an existing pipeline, 10 = new ETL + schema +
    parser + normalization layer.
  • **Dollar cost**: free public / low (≤$10K/yr) / medium
    ($10K-100K/yr) / high (≥$100K/yr).
  • **Strategic value** (0-10): unlocks a new asset class, makes
    a competitive moat, anchors an enterprise pricing tier.

**Net rank = (predictive_lift + strategic_value) / effort**, with
dollar cost as a tiebreaker. The right answer is rarely 'the most
complete' — it's 'the lift you can ship in 4 weeks for $0'.

---

## Top-tier candidates (highest predictive lift per effort)

### 1. ASCQR — ASC Quality Reporting (CMS public)

  - **Predictive lift**: 8/10 — unlocks ASC asset class which has no
    quality data today; quality is the headline negotiation lever
    in ASC PE deals.
  - **Engineering effort**: 3/10 — same shape as existing
    `cms_quality_metrics.py`; one parser + one schema migration.
  - **Dollar cost**: free.
  - **Strategic value**: 9/10 — unlocks the ~5,800-asset ASC
    universe (per the multi-asset expansion plan).
  - **Models improved**: ASC profile metrics, comp finder for
    ASCs, quality-adjusted EBITDA bridge.

**Net rank: highest.** Cheap, fast, opens an entire asset class.

### 2. SAMHSA N-SSATS / N-MHSS — Behavioral health treatment surveys

  - **Predictive lift**: 7/10 — only public source for behavioral-
    health site-level service mix + capacity + payer mix.
  - **Engineering effort**: 4/10 — published as XLSX + metadata
    PDFs; need a custom parser for the survey format.
  - **Dollar cost**: free.
  - **Strategic value**: 9/10 — unlocks behavioral health (~10K+
    assets, hot PE category).
  - **Models improved**: ALOS predictor, reimbursement-stream
    classifier, behavioral-health peer-similarity.

### 3. CMS SNF / HHA / Hospice cost reports (already in HCRIS pipeline; format extensions only)

  - **Predictive lift**: 7/10 — extends existing HCRIS predictors
    to post-acute. Models retrain on additional ~30K assets.
  - **Engineering effort**: 2/10 — same HCRIS pipeline; just a
    schema map for the post-acute Worksheet structure.
  - **Dollar cost**: free.
  - **Strategic value**: 8/10 — unlocks post-acute (~30K
    facilities).
  - **Models improved**: every existing financial predictor
    (margin, cash, denial-style metrics) re-trained on
    post-acute panel.

### 4. CMS Hospital VBP + HAC reduction program data

  - **Predictive lift**: 6/10 — direct CMS quality payments
    affecting hospital margin. Improves the existing forward
    distress predictor and EBITDA bridge by capturing the
    ~$2-4M VBP swing per typical hospital.
  - **Engineering effort**: 2/10 — same pattern as
    `cms_quality_metrics.py`.
  - **Dollar cost**: free.
  - **Strategic value**: 7/10 — depth on existing hospital asset
    class.

### 5. BLS QCEW wage data (Quarterly Census of Employment & Wages)

  - **Predictive lift**: 6/10 — meaningfully improves the labor
    efficiency model. Currently labor cost is a hospital-level
    average; QCEW gives metro-level wage rates so peer
    comparisons normalize for labor-market variation.
  - **Engineering effort**: 4/10 — large CSV files quarterly;
    metro-FIPS join required.
  - **Dollar cost**: free.
  - **Strategic value**: 6/10 — improves an existing model rather
    than opening a new surface.

---

## Mid-tier candidates (substantial lift, more effort)

### 6. State Medicaid managed care RFP awards + capitation rates

  - **Predictive lift**: 7/10 — direct revenue input for any
    Medicaid-heavy asset (safety-net hospitals, behavioral health,
    SNF, DSNPs). Captures the rate trajectory under managed-care
    procurement cycles.
  - **Engineering effort**: 8/10 — fragmented across 50 state
    Medicaid agencies; varying formats; mostly PDF awards.
  - **Dollar cost**: free (public records) but high
    extraction cost.
  - **Strategic value**: 8/10 — Medicaid-rate-trajectory is the
    most cited risk factor in safety-net + behavioral-health
    deals.
  - **Sequencing**: top-10 PE-active states first (CA / TX / FL /
    NY / IL / PA / OH / MI / GA / NC).
  - **Recommended**: build manual ingestion for top-10 first;
    extend later via the existing regulatory-discovery LDA.

### 7. State Certificate of Need (CON) data

  - **Predictive lift**: 6/10 — supply-constraint moat for CON
    states (35 states have some CON laws). Predicts entry
    barriers for ASCs, hospitals, and behavioral-health
    facilities.
  - **Engineering effort**: 7/10 — fragmented per-state, varying
    application + decision portals.
  - **Dollar cost**: free public.
  - **Strategic value**: 7/10 — meaningful for ASC + hospital
    underwriting in CON states.

### 8. State medical board data + disciplinary actions

  - **Predictive lift**: 5/10 — physician-departure risk +
    key-person concentration scoring; surfaces fraud/discipline
    signals.
  - **Engineering effort**: 8/10 — 50 state boards with no
    standard format; some require API keys.
  - **Dollar cost**: free public records.
  - **Strategic value**: 7/10 — physician group asset class needs
    this to credibly model key-person risk.

### 9. OIG enforcement + qui tam settlements

  - **Predictive lift**: 5/10 — feeds compliance / fraud risk
    scoring. Especially valuable for hospice + DME + behavioral
    health where OIG attention is high.
  - **Engineering effort**: 4/10 — single OIG.gov source with
    structured publication; scraper-friendly.
  - **Dollar cost**: free.
  - **Strategic value**: 6/10 — niche but high signal where
    relevant.

### 10. ASC accreditation databases (AAAHC + JCAHO + AAAASF)

  - **Predictive lift**: 4/10 — accreditation status is a binary
    quality signal that affects negotiation leverage.
  - **Engineering effort**: 5/10 — three different sources, each
    with their own format.
  - **Dollar cost**: free public lists.
  - **Strategic value**: 6/10 — required for ASC asset-class
    completeness.

---

## Premium-tier candidates (high cost, paid feeds)

These would not be platform-bundled but rather customer-license
pass-through under the Enterprise tier. They unlock major
predictive lift but at $100K+/year cost.

### 11. Truven / IQVIA / Komodo commercial claims

  - **Predictive lift**: 9/10 — the single biggest analytical
    upgrade. Ground-truth commercial claims data lets every
    predictor train on real outcomes instead of inferred-from-
    HCRIS.
  - **Engineering effort**: 5/10 — formats are documented; the
    licensing is the gating factor.
  - **Dollar cost**: $250K-1M/yr depending on license scope.
  - **Strategic value**: 9/10 — Enterprise-tier-only feature.
  - **Recommendation**: **don't bundle**; offer Enterprise
    pass-through where customer brings their own license.

### 12. Definitive Healthcare / Trilliant Health affiliations

  - **Predictive lift**: 6/10 — physician-hospital affiliation
    networks for downstream demand modeling. Not in any free
    public source.
  - **Engineering effort**: 3/10 — clean APIs, well-documented.
  - **Dollar cost**: $25-100K/yr.
  - **Strategic value**: 7/10 — physician group asset class
    affiliation modeling.
  - **Recommendation**: license ourselves at Pro tier (cost
    amortizable across paying customers).

### 13. PitchBook / S&P CapIQ deal comps

  - **Predictive lift**: 7/10 — actual transaction multiples for
    backtest validation. Ground truth on what deals actually
    closed at.
  - **Engineering effort**: 4/10 — APIs exist.
  - **Dollar cost**: $25-50K/yr per seat.
  - **Strategic value**: 8/10 — validates platform predictions
    against reality; required for IC defensibility.
  - **Recommendation**: license for internal use first; Enterprise
    pass-through later.

---

## Defer / decline

These look attractive but aren't worth the effort:

  - **Real-time hospital admission feeds**: massive operational
    lift, marginal predictive value beyond what HCUP already
    provides quarterly.
  - **Provider Tax / Disproportionate Share Hospital (DSH) detail**:
    relevant only for safety-net subset; covered by HCRIS at
    sufficient depth.
  - **Drug-level price transparency (CMS Part D Public Use File
    Detail)**: sub-feature of Part D already ingested; marginal
    extra lift.
  - **CDC SVI** (Social Vulnerability Index): substantially overlaps
    with CDC PLACES + Census ACS already ingested; marginal lift.
  - **Joint Commission accreditation data** (unrelated to
    ASC accreditation): expensive license; covered at sufficient
    depth by Hospital Compare for hospital underwriting.

---

## Sequencing — quarter-by-quarter plan

If we run as a single workstream:

| Quarter | Datasets added | Asset classes unlocked |
|---|---|---|
| **Q1** | ASCQR + SNF/HHA/Hospice cost reports + CMS VBP/HAC | ASC + post-acute (initial) |
| **Q2** | SAMHSA N-SSATS + state Medicaid managed care top-10 + ASC accreditation | Behavioral health + post-acute (full) |
| **Q3** | BLS QCEW + state CON top-15 + OIG enforcement | Cross-asset (labor + supply + compliance) |
| **Q4** | State medical board top-10 + Definitive Healthcare license | Physician group affiliation + key-person risk |

If we parallelize across two engineers:

| Quarter | Engineer A (asset-class expansion) | Engineer B (cross-asset depth) |
|---|---|---|
| Q1 | ASCQR + SNF/HHA/Hospice | CMS VBP/HAC + BLS QCEW |
| Q2 | SAMHSA N-SSATS + ASC accreditation | State Medicaid top-10 + OIG |
| Q3 | State CON top-15 | State medical board top-10 |
| Q4 | Definitive Healthcare license | Truven/IQVIA pass-through scaffold |

---

## Predictive lift compounding

Each new dataset doesn't just add coverage — it improves *every
existing model* that touches the affected asset class. After one
year:

  - **Forward distress predictor** retrained on hospital + post-
    acute data: expected R² lift from 0.42 → 0.55.
  - **Comparable finder** with state-specific Medicaid context:
    expected similarity-score precision lift (top-5 comp set hit
    rate) from 73% → 85%.
  - **EBITDA bridge** with VBP/HAC inputs: ~$2-4M/yr per hospital
    of previously-unmodeled revenue swing.
  - **Labor efficiency model** with metro-level QCEW wages:
    over/under-staffing flags become actionable rather than
    directional.

The compounding effect is the case for prioritizing breadth over
depth in year one — every additional asset class + cross-asset
depth dataset improves models trained on the rest.

---

## What we don't bundle (and why)

The platform's pricing model (per the business model plan)
deliberately does NOT bundle premium paid feeds. Instead:

  - Free + Pro tiers ship every public dataset above.
  - Enterprise tier offers **license pass-through** for paid
    feeds — customer brings their own Truven / IQVIA / PitchBook
    license; the platform plumbs it in.

Why: paid-feed economics don't scale across small + mid-market
customers. A $500K/yr Truven license amortized across 10 customers
is $50K/yr each — but each Pro-tier customer is paying $30K/yr
total. The math only works for Enterprise (where seat counts +
revenue per account justify it) or for the customer-licenses-
direct model.

This keeps the Pro tier price-competitive vs CapIQ + PitchBook
while still offering Enterprise-grade depth.

---

## Strategic implication

Year one of data acquisition focuses on **breadth over depth**:
unlock four asset classes (ASC, behavioral health, post-acute,
physician groups) before deepening any single one. The reason: a
healthcare PE shop's deal flow is heterogeneous — partners need
the platform to underwrite *whatever crosses their desk*. A
narrow-but-deep platform that only handles hospitals loses the
shop to a generalist tool the moment they screen an ASC.

Year two pivots to depth — once breadth is established, customers
demand richer per-asset-class models (specialty-specific
physician-group calibrations, payer-specific behavioral health
contracting). That's when paid feeds + custom predictors earn
their cost.

The recommended sequence collapses 4 quarters of breadth into 4
quarters of depth, leaving year three for Enterprise-tier
differentiation (premium-data pass-through, custom retraining,
on-premise deployment).

# Tuva + Myelin Integration Spec — Analytics Core & Pricing Engine

**Status**: design spec + first two native modules shipped
**Owner**: diligence analytics
**Companion code**: [`rcm_mc/diligence/risk_adjustment/`](../rcm_mc/diligence/risk_adjustment/README.md) · [`rcm_mc/diligence/policy_shock/`](../rcm_mc/diligence/policy_shock/README.md)

---

## 1. The decision in one paragraph

The [Tuva Project](https://github.com/tuva-health/tuva) (an open-source claims/clinical data model with HCC risk adjustment, chronic-condition groupers, quality measures, readmissions, PMPM, and episode grouping) and [Myelin / LibrePPS](https://github.com/Bedrock-Billing/LibrePPS) (a Python bridge to the **official CMS Java groupers/pricers** — MS-DRG, MCE, IOCE, IPPS/OPPS/etc.) together encode most of the healthcare-specific logic this workbench would otherwise hand-build. **We adopt their *architecture and algorithms*, not their *runtime*.** Tuva is a dbt package that assumes a warehouse and a beneficiary-level claims extract; Myelin needs a JVM and CMS jar files. Both violate this repo's load-bearing invariant — *stdlib + numpy + pandas + matplotlib only, no external services, nothing leaves the laptop* (see [`CLAUDE.md`](../CLAUDE.md)) — and neither can run in the public-data, zero-network posture the product ships in. So we **reimplement the slices we need natively**, in the existing `diligence/` module pattern, and define a **clean optional adapter** so a team that *does* have dbt + Java + a target's claims extract (confirmatory diligence) can swap the certified engines in behind the same interface, with no caller changes.

This is the same call the codebase already made for denial modeling (Naive Bayes instead of scikit-learn) and Monte Carlo (stdlib inverse-normal instead of scipy): wrap the *idea*, not the *dependency*.

---

## 2. Why not adopt wholesale

| Concern | Tuva (dbt) | Myelin (JPype + CMS jars) |
|---|---|---|
| Runtime dependency | dbt-core + a warehouse adapter (DuckDB/Snowflake/BigQuery/Redshift) | JVM + JPype + CMS-distributed Java jars |
| Repo invariant | breaks "numpy + pandas only" | breaks "no external services / Python-only" |
| Sandbox / no-network posture | can't materialize marts without a warehouse + claims | can't start a JVM or fetch jars |
| Data it needs | beneficiary-level claims (LDS/CCLF) | claim-level service detail |
| When that data exists | confirmatory diligence only | confirmatory diligence only |
| Auditability | dbt SQL is readable, but adds a second toolchain | grouper internals are a black box (certified, but opaque) |

The product's primary mode is **public aggregate data** (HCRIS, Care Compare, Part D, 10-K, 990). On that data the **terminology sets, the HCC/chronic-condition groupers, and the quality-measure logic are directly reusable**; the full claim-level marts only pay off once a target's extract lands. So the native modules are built to run *now* on aggregate inputs and to *upgrade in place* when the extract arrives.

---

## 3. Patterns adopted (the durable value)

1. **Layered data model: input → core → marts.** Tuva separates raw ingestion from normalized core from analytic marts so new sources don't touch analytics and marts stay testable. The workbench already has this spine: `diligence/ingest/` (raw → Canonical Claims Dataset) → `analysis/packet.py` (the `DealAnalysisPacket` core) → the per-module diligence marts. The two new modules are **marts** that read the core, never raw inputs. *Action: keep every new analytic a mart; never let it reach past the CCD/packet.*

2. **Data-quality tests as first-class artifacts.** Tuva ships DQ tests with the data. The workbench already has `diligence/integrity/` (leakage checks, distribution scoring, temporal validity). *Action: for diligence, "here are the integrity checks the target's data passed/failed" is itself a partner deliverable — every new mart should declare the DQ preconditions it assumes (e.g., the risk model surfaces `unmapped_conditions` so crosswalk coverage is visible rather than silently dropped).*

3. **Wrap official tools; never hand-code a certified grouper.** Myelin's whole thesis. *Action: the native RAF scorer and (future) pricing estimator are explicitly documented as approximations with a swap path to the certified engine — see §5. We never claim payment-grade precision from the native path.*

---

## 4. The two native modules shipped in this cycle

Both map directly onto Tuva marts and follow the established `diligence/<module>/{__init__,…,README.md}` + `tests/test_<module>.py` pattern, with frozen dataclass outputs, `source_module`/`citation_key` trust hooks, seeded computation, and named verdict thresholds.

### 4.1 `risk_adjustment` — CMS-HCC (maps to Tuva `cms_hcc` mart)

The risk-adjusted benchmarking the brief flags as *"the healthcare-specific analytic you're missing and it's central."* Normalizes a target's cost/outcomes for case mix so peer comparison is apples-to-apples instead of getting fooled by a sicker panel.

- `compute_raf(Demographics, conditions)` → decomposed RAF (demographic + disease-HCC-after-hierarchy + interactions).
- `score_panel(...)` → mean/median/p90 RAF + per-HCC prevalence.
- `risk_adjust_metric(...)` → observed-to-expected (O/E) ratio vs a peer cohort, with a verdict that separates the **case-mix story** from the **operator story**.

Curated to the **CMS-HCC V28 community/non-dual/aged** segment (the diligence default), ~24 of ~115 payment HCCs — representative magnitudes, not payment-grade. Full README: [`risk_adjustment/README.md`](../rcm_mc/diligence/risk_adjustment/README.md).

### 4.2 `policy_shock` — Difference-in-Differences (Tuva has no equivalent; this is net-new IC rigor)

The brief's *"causal/quasi-experimental for policy shocks."* Turns "what does OBBBA Medicaid / the MA rate cut do to this asset" into an estimated, bounded number instead of a flat haircut.

- `estimate_did(PanelData)` → two-way fixed-effects DiD, cluster-robust SEs, with `event_study` parallel-trends + `placebo_test` baked into the verdict.
- `synthetic_control(...)` → single-treated-unit fallback (simplex-constrained donor weights).
- `policy_ebitda_overlay(...)` → ATT → EBITDA-at-risk dollars feeding the Deal MC `reg_headwind` driver.
- `POLICY_SHOCKS` → curated catalog (OBBBA Medicaid, CY2027 MA rate/V28, PFS, site-neutral).

Full README: [`policy_shock/README.md`](../rcm_mc/diligence/policy_shock/README.md).

---

## 5. Optional-integration adapter spec (for teams with the full stack)

When a team *does* run dbt + Java and has a target's claims extract, they should be able to swap the certified engines in **without touching any caller**. The contract is a Protocol the native engine already satisfies; the certified path lives behind a packaging *extra* with **guarded imports** so the default install stays zero-dependency.

### 5.1 Risk model interface

```python
# rcm_mc/diligence/risk_adjustment/protocol.py  (spec)
from typing import Protocol, Sequence
from .risk_scorer import Demographics, RiskScore

class RiskModel(Protocol):
    def compute_raf(
        self, demographics: Demographics, conditions: Sequence[str],
    ) -> RiskScore: ...

# Native (default) — the shipped scorer already conforms.
# Certified — a thin adapter over the Tuva cms_hcc mart output:
#   class TuvaHCCAdapter:  reads the mart's per-bene RAF + HCC list,
#   returns the SAME RiskScore dataclass. No benchmarking-caller change.
```

`risk_adjust_metric` depends only on RAF *numbers*, so it is engine-agnostic by construction — point it at native RAFs today, mart RAFs tomorrow.

### 5.2 Pricing engine interface (Myelin)

```python
# rcm_mc/diligence/reimbursement/protocol.py  (spec — future module)
from typing import Protocol
from dataclasses import dataclass

@dataclass
class PricedClaim:
    drg: str | None
    allowed_amount_usd: float
    pricer: str            # "IPPS" | "OPPS" | ... | "native-estimate"
    fee_schedule_year: int

class PricingEngine(Protocol):
    def price(self, claim: dict, fee_schedule_year: int) -> PricedClaim: ...

# Native default: a fee-schedule-table estimator (public CMS rate files),
#   labeled pricer="native-estimate" — honest about approximation.
# Certified: MyelinPricingClient wraps the CMS Java pricers via JPype,
#   guarded import; raises a clear "install rcm-mc[myelin]" if unavailable.
```

### 5.3 Packaging

```toml
# pyproject.toml (spec)
[project.optional-dependencies]
tuva   = ["dbt-core", "dbt-duckdb"]     # materialize marts from a claims extract
myelin = ["jpype1"]                      # bridge to CMS Java pricers (+ jars, configured separately)
```

Default install pulls **none** of these. Every certified adapter does a guarded import and degrades to the native estimator (with a logged warning) when the extra isn't present — so a partner on a laptop never hits an `ImportError`, and a team in a data room gets payment-grade numbers by installing one extra.

---

## 6. Roadmap — further native marts (each tied to a diligence question)

All native, same pattern. ✅ = shipped in this work stream.

| Mart (Tuva analog) | Diligence question | Status / notes |
|---|---|---|
| **Risk adjustment (CMS-HCC)** | case-mix-normalized benchmarking | ✅ `diligence/risk_adjustment/` |
| **Policy-shock evaluator (DiD)** | causal effect of OBBBA/MA/PFS | ✅ `diligence/policy_shock/` |
| **Readmissions / retention (survival)** | time-to-readmission, churn/LTV | ✅ `diligence/survival/` — KM + log-rank + Cox |
| **Hierarchical/multilevel benchmarking** | small-n facility shrinkage | ✅ `diligence/hierarchical_bench/` — empirical-Bayes partial pooling; consumes `risk_adjustment` O/E |
| **PMPM / financial** | per-member cost trend, normalized by RAF | reuse `risk_adjustment` for the denominator |
| **Episode grouping + service-line P&L** | cost-per-episode, line margin | the unit PE underwrites on |
| **Quality measures (HEDIS/CQM)** | gap-closure, star drivers | benchmark via `risk_adjust_metric(lower_is_better=False)` |
| **Spatial competition (Huff + isochrones)** | TAM / white-space beyond radius circles | optional geo extra |
| **Referral-network analysis** | captive-volume moat | shared-patient graph centrality |
| **Benford's-law screen** | fast billing-integrity check | cheap addition to `diligence/integrity/` |

Anomaly detection is already covered by the existing isolation-forest work — ahead of the public fraud repos, which mostly use logistic regression / random forests.

The four shipped marts compose: `risk_adjustment` produces per-unit O/E → `hierarchical_bench` shrinks them so small-n sites rank honestly → `policy_shock` sizes the regulatory headwind on the survivors → `survival` measures whether the retained volume actually sticks. That chain is the case-mix-aware, causally-grounded, small-area-correct benchmarking stack the brief asked for, built without leaving the numpy/pandas envelope.

---

## 7. References

- Tuva Project — https://github.com/tuva-health/tuva
- Myelin / LibrePPS — https://github.com/Bedrock-Billing/LibrePPS
- CMS-HCC risk-adjustment model + Rate Announcements (factor tables) — cms.gov
- `medicaid-utils` (uc-cms), `hcris-app` (klocey) — reference patterns for the roadmap marts
- This repo: [`CLAUDE.md`](../CLAUDE.md) (invariants), [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) (layering), [`docs/ANALYSIS_PACKET.md`](ANALYSIS_PACKET.md) (the core the marts read)

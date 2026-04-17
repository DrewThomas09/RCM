# Boss-Ready Benchmark Pack — Industry Sources (Citable)

This document ties each benchmark to **published industry sources** and maps them into Monte Carlo inputs. Configs (`actual.yaml`, `benchmark.yaml`) are calibrated to these ranges.

---

## 1) Benchmark Set (Industry Sources)

### A. Denials: Initial Denial Rate (IDR)

**Definition (HFMA MAP Keys / Claim Integrity Task Force):** Initial denials = denied claims ÷ total claims submitted (claim volume or dollars).

**Benchmarks (hospital/provider reported, recent):**

| Payer | Value | Source |
|-------|-------|--------|
| Commercial initial denials | **13.9%** | [AHA market scan][2] |
| Medicare Advantage | **15.7%** | [AHA][2] |
| Private payer (survey avg) | **~15%** (range higher) | [Premier][3] |
| Overall (all payers, 2024) | **11.81%** | [TechTarget/RevCycle][4] |
| Medicare FFS | **8–9%** (lower) | [Fierce Healthcare][10] |
| Medicaid | **15–17%** | [Fierce Healthcare][10] |

**Takeaway:** Commercial and MA denials often sit mid-teens; overall averages lower due to Medicare FFS mix.

---

### B. Denials: Final Write-Offs (FWR) / AR-6

**Definition (HFMA MAP Key AR-6):** Denial write-offs as % of net patient service revenue (NPSR).

**Benchmarks (Kodiak/HealthLeaders):**

| Level | Value |
|-------|-------|
| Average (all orgs) | **2.8% of NPSR** |
| Top-10 performance | **2.2% of NPSR** |

**Interpretation:** 2.2% = strong, 2.8% = typical, >3% = diligence red flag unless explained.

---

### C. A/R Speed: True A/R Days

**Benchmarks (Kodiak/HealthLeaders):**

| Level | Value |
|-------|-------|
| Average | **56.9 days** |
| Top-10 | **43.6 days** |

**PE use:** Cash trapped ≈ (NPSR / 365) × Δ(A/R days)

---

### D. A/R >90 Days

| Reference | Value |
|-----------|-------|
| Best practice | **<15%** of A/R >90 days |
| Observed (benchmark sample) | **35.9%** |

**Takeaway:** Best practice <15%; many systems above that today — investable value in backlog.

---

### E. Cost to Collect (CTC)

**Definition (HFMA):** Total RCM cost ÷ total patient service cash collected.

**Benchmarks (AKASA/HFMA survey):**

| Category | Value |
|----------|-------|
| Average overall | **3.68%** |
| Automation users | **3.51%** |
| Non-automation | **3.74%** |

---

## 2) Semi-Okay Target Hospital Profile

**Target:** $500M NPSR general acute hospital ("Midwest Community Hospital") — mid-pack.

### Payer Mix

- Medicare (FFS + MA): **42%**
- Medicaid: **18%**
- Commercial: **35%**
- Self-pay / other: **5%**

### Core RCM KPIs

| Metric | Target (Semi-Okay) | Industry Avg | Top-Decile |
|--------|--------------------|--------------|------------|
| IDR (MA) | 16% | 15.7% | ~12–14% |
| IDR (Commercial) | 14% | 13.9% | ~11–12% |
| IDR (Medicaid) | 15–17% | 15–17% | ~14–15% |
| IDR (Medicare FFS) | 8–9% | 8–9% | ~7–8% |
| FWR (AR-6) | 3.1% NPSR | 2.8% | 2.2% |
| True A/R days | 60 | 56.9 | 43.6 |
| Cost to collect | 3.9% | 3.68% | ~3.5% |
| A/R >90 | 22% | 35.9% | <15% |

---

## 3) Map to Monte Carlo Inputs

For each payer:

1. **Revenue share** (s_i)
2. **IDR** (claim volume or dollars; consistent with HFMA)
3. **FWR** (calibrate to AR-6 2.2%–2.8%–3%+ ranges)
4. **True A/R days** (anchor to 56.9 avg / 43.6 top-10)
5. **CTC** (anchor to ~3.68% avg)

Recommended: denial mix (auth/admin vs coding vs clinical vs eligibility), appeal stage mix (L1/L2/L3), A/R >90 as aging check.

---

## 4) Talk Track for Your Boss

- "HFMA provides standardized denial metric definitions; we use those."
- "AHA and Premier show initial denials mid-teens for commercial and MA."
- "Kodiak benchmarking: FWR avg ~2.8% NPSR, top performers ~2.2%."
- "Kodiak: true A/R days avg ~56.9, top performers ~43.6."
- "HFMA/AKASA survey: CTC avg ~3.68%."
- "A/R >90 best practice <15%; many systems above that — investable value."

---

## References (URLs)

1. [HFMA — Standardizing denial metrics](https://www.hfma.org/guidance/standardizing-denial-metrics-revenue-cycle-benchmarking-process-improvement/)
2. [AHA — Payer Denial Tactics $20B problem](https://www.aha.org/aha-center-health-innovation-market-scan/2024-04-02-payer-denial-tactics-how-confront-20-billion-problem)
3. [Premier — Claims adjudication $25.7B](https://premierinc.com/newsroom/policy/claims-adjudication-costs-providers-257-billion-18-billion-is-potentially-unnecessary-expense)
4. [TechTarget — Initial claim denial rates 2024](https://www.techtarget.com/revcyclemanagement/news/366625109/Initial-claim-denial-rates-put-revenue-cycle-in-tough-spot)
5. [HealthLeaders — 8 KPIs (Kodiak)](https://www.healthleadersmedia.com/revenue-cycle/quick-tips-improve-rev-cycle-performance-against-8-kpis)
6. [PMC — Revenue Cycle Management (A/R >90)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11219169/)
7. [Kodiak — LinkedIn A/R days](https://www.linkedin.com/posts/kodiak-solutions_the-average-true-accounts-receivable-days-activity-7333900973041487872-trQm)
8. [HFMA — Cost to Collect guide](https://www.hfma.org/wp-content/uploads/2025/09/Cost-to-Collect-Better-Practices.pdf)
9. [AKASA — CTC survey](https://akasa.com/press/survey-cost-to-collect-lower-with-automation)
10. [Fierce Healthcare — Providers $10.6B overturning denials](https://www.fiercehealthcare.com/providers/providers-wasted-106b-2022-overturning-claims-denials-survey-finds)

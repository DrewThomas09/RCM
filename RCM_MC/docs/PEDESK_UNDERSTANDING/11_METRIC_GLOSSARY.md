# 11 · Metric glossary — definitions & sources

> The canonical meaning of every metric name used across PE Desk, with **definition · how it's computed · data source · scale**. When a page shows a metric, this tells you what it is and where it came from. (The in-app version is `/metric-glossary`, which pages deep-link via `#<metric_key>`.)

**Scale conventions** (important — see §`PEDESK_DATA`): financial figures → 2 decimals (`$450.25M`); percentages → 1 decimal (`15.3%`); multiples → 2 decimals + `x` (`2.50x`). Rate metrics inside the packet are on a **0–100 scale** (a 12% denial rate is stored `12.0`, not `0.12`); `weighted_irr` in the rollup is a **fraction** (`0.219`).

---

## Returns / PE-math
| Metric | Definition · computation · source |
|---|---|
| **MOIC** | Multiple on Invested Capital = `total_distributions / entry_equity`. Per-deal from `deal_snapshots.moic`; corpus realized from `public_deals.realized_moic`. Scale `x`. |
| **IRR** | Internal Rate of Return — the discount rate where NPV(cashflows)=0, solved by **bisection over [−0.99, 10.0]** (mixed-sign PE flows). Source: `pe_math.irr` / corpus `realized_irr`. Stored as a fraction in the rollup. |
| **Weighted MOIC / IRR** | Entry-EV-weighted mean across the portfolio's sized deals (deals with moic+irr+entry_ev), summed in `Decimal`. Source: `portfolio_rollup`. Powers the `/app` return hero. |
| **DPI / TVPI** | Distributions-to-paid-in / total-value-to-paid-in. **Not computed in PE Desk today** — anywhere they appear they render `—` (no NAV/distribution data). |
| **EV** | Enterprise Value. `deal_snapshots.entry_ev` / corpus `ev_mm`. |
| **Entry / exit multiple** | EV / EBITDA at entry/exit. |
| **Value-creation bridge** | `exit_ebitda = entry + organic(compounded) + rcm_uplift`; organic & RCM valued at entry multiple, multiple-expansion on total exit EBITDA; reconciles exactly to exit EV. Source: `pe_math.value_creation_bridge`. |
| **Covenant headroom / cushion** | Headroom in turns = `covenant_max − actual_leverage`; EBITDA cushion % = `(EBITDA − trip_EBITDA)/EBITDA`. Source: `pe_math.covenant_check`. |

## RCM operational KPIs (the levers)
| Metric | Definition · computation · source · scale |
|---|---|
| **Initial denial rate (IDR) / first-pass denial rate** | Share of claims denied on first submission. CCD: denied-on-initial / total. Benchmark cite HFMA/AAPC. 0–100 in packet. |
| **Final write-off rate (FWR)** | Share of claims ultimately written off. Simulator models it in logit space with backlog penalties. |
| **Clean claim rate** | Share of claims accepted without rework. Bridge lever 4. |
| **Days in A/R (DAR)** | Paid-$-weighted average days from service to payment. CCD: avg `(paid_date − service_date)`. HFMA MAP Key. |
| **A/R aging >90 days** | $ share of open balance (`allowed − paid`) aged ≥90 days. |
| **Net collection rate (NCR)** | `actual_collected / contractually_allowed`. Bridge lever 3 (`×0.60` coefficient). |
| **Cost to collect** | `RCM cost / cash collected`. Requires analyst input (else `—`). |
| **First-pass resolution rate** | Share resolved without rework. Bridge lever 6. |
| **Case mix index (CMI)** | Acuity index; bridge lever 7 affects **Medicare revenue only** (`Δcmi/0.01 × Medicare_rev × 0.75%`). |
| **Underpayment rate (UPR)** | Share of claims paid below contract. Simulated via Poisson on claims. |

## Hospital fundamentals (HCRIS)
| Metric | Definition · source |
|---|---|
| **Beds** | Licensed beds. HCRIS. |
| **Net patient revenue (NPR/NPSR)** | Net patient service revenue. HCRIS. Note: treated as **derived** (= gross − contractual allowances) by the leakage audit even though raw in HCRIS — an accounting identity, so its components count as leakage. |
| **Operating margin** | `(NPR − operating_expenses) / NPR`, clamped to credible range. HCRIS-derived. |
| **Revenue per bed** | `NPR / beds`. COMPUTED. |
| **Payer-day mix** | medicare_day_pct / medicaid_day_pct / commercial (= 1 − the two). HCRIS. |
| **Case-mix index, occupancy, DSH/IME, bad debt, charity care** | HCRIS cost-report fields. |

## Risk & concentration
| Metric | Definition · scale |
|---|---|
| **HHI (Herfindahl)** | Market concentration. **⚠ TWO SCALES coexist:** the deal-risk scorer & deal-page market-structure use **0–10,000** (`Σ(share×100)²`, DOJ thresholds 1500/2500); the corpus `market_concentration` module uses **0–1 fractional** (`Σ(share²)`). Same index, different scaling — don't read "5000" next to "0.30" as an error. |
| **CR3 / CR5** | Sum of top-3 / top-5 market shares. |
| **Composite risk score (0–100)** | 5-factor: entry-multiple 0.30, payer-concentration 0.20, hold 0.20, vintage 0.15, size 0.15. Tier <25 Low / <50 Med / <70 High / else Critical. `deal_risk_scorer`. |
| **Concerning signals** | Count of concerning flags on a deal snapshot; ≥1 feeds the health-score deduction and `/app` signal scan. |

## Scores & grades
| Metric | Definition · scale |
|---|---|
| **Health score (0–100)** | Deduction model from 100 (covenant −40/−15, signals, EBITDA variance, alerts). Band green ≥80 / amber 50–79 / red <50. `health_score.compute_health`. |
| **Investability (0–100)** | `0.30·opportunity + 0.40·value + 0.30·stability`. Grade A ≥85 / B ≥72 / C ≥58 / D ≥42 / F. `investability_scorer`. |
| **Exit readiness (0–100)** | Weighted mean of 12 dimensions. Verdict ready ≥85 / soft_launch ≥65 / not_ready. `exit_readiness`. |
| **Stress robustness grade (A–F)** | A: ≥90% downside pass & 0 breaches; B ≥80% & ≤1; C ≥60%; D ≥40%; F below. `stress_test`. |
| **Consistency score (0–100)** | Sponsor: `0.40·moic_score + loss_penalty + irr_score + cred_score`. `sponsor_track_record`. |
| **Data Confidence Score (0–100)** | Snapshot tab only: starts 100, deducts for completeness gaps + 837↔835 match shortfall. `data_confidence`. |
| **Completeness grade (A–D)** | Fraction of required metrics present. `analysis/completeness` & `data/sources.confidence_grade`. |
| **Reliability grade (A–D)** | Per predicted metric, from cohort size + LOO R². `ridge_predictor`. |

## Reasonableness & verdicts
| Term | Meaning |
|---|---|
| **Band verdict** | IN_BAND / STRETCH / OUT_OF_BAND / IMPLAUSIBLE — a metric vs its acceptable band (size×payer-regime-keyed for IRR). `reasonableness.py`. |
| **IC recommendation** | PASS / PROCEED_WITH_CAVEATS / PROCEED / STRONG_PROCEED — from worst band + highest heuristic severity (logic in §03). `narrative._compose_recommendation`. |
| **Heuristic severity** | INFO / LOW / MEDIUM / HIGH / CRITICAL — from the 19 partner-reflex rules. `heuristics.py`. |
| **QoR band** | IMMATERIAL <2% / WATCH 2–5% / CRITICAL ≥5% — management-vs-claims accrual divergence. `cash_waterfall`. |

## Provenance tags (what trust a number carries)
HCRIS (CMS filing, high) · SELLER (data room, high) · CALIBRATED (Bayesian blend, high) · COMPUTED (derived, high) · ML_PREDICTION (modeled, medium) · BENCHMARK (peer P50, low) · DEFAULT (assumption, low). Priority: calibrated > seller > hcris > ml > default.

---
*This glossary is the connective tissue: any metric on any page resolves to a row here, and any row resolves to a source in `PEDESK_DATA` and a formula in `PEDESK_ALGORITHMS`.*

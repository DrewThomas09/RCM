# Glossary

Every healthcare, PE, and internal term that shows up in the
codebase. Written for someone with zero background in either field.
If a term appears in comments, method names, or variable names and
you don't recognize it, check here first.

## Healthcare revenue-cycle terms

**RCM — Revenue Cycle Management.** The end-to-end business process
that turns a patient visit into collected cash. Starts at patient
registration, ends when the hospital gets paid. Most of what this
platform analyzes.

**Claim.** A bill submitted to a payer (insurance company, Medicare,
etc.) for a specific patient encounter. Payers either pay it (clean
claim), deny it, or pay a reduced amount.

**Denial.** A payer refusing to pay a claim (in whole or in part).
Reasons are categorized: eligibility (patient wasn't covered),
authorization (prior auth missing), coding (wrong code or missing
modifier), medical necessity (payer questions whether the service was
needed), timely filing (submitted past the payer's window).

**Initial denial rate.** Share of claims denied on first submission.
A leading indicator of front-end process quality. Typical benchmark
P50 ≈ 5.2%; P90 ≈ 14.5%.

**Final denial rate.** Share of claims that stay denied after appeals
are exhausted. These dollars never come back — pure revenue loss.
Typical P50 ≈ 1.3%.

**Clean claim rate.** Share of claims submitted without edit failures.
Inversely correlated with denials. Industry target is 95%+.

**First-pass resolution rate (FPR).** Share of claims that pay on
first submission — combines clean-claim rate with first-pass denial
rate. High FPR means minimal rework and tight cash cycle.

**Days in A/R (AR days, DSO).** Average age of outstanding
receivables. A hospital with 50 days in A/R is waiting ~50 days
between bill-out and cash. Lower is better; P50 ≈ 45 days.

**A/R > 90 days %.** Share of receivables aged past 90 days.
Heavy-90+ = collection-process breakdown or payer-dispute backlog.

**DNFB — Discharged Not Final Billed.** Days between patient
discharge and claim submission. Caused by coding backlog or
documentation queries. Compresses the cash cycle.

**Net collection rate (NCR).** Cash collected as a share of expected
(post-contract) revenue. Ceiling on revenue realization — every
percentage point recovered is nearly pure EBITDA.

**Cost to collect.** RCM operations spend as a share of net patient
service revenue. Drops with automation, self-service payments, lower
denial volume. Typical 2.8%.

**Case Mix Index (CMI).** Weighted average DRG relative weight.
Reflects patient acuity and documentation completeness. Each 0.01
CMI point lifts Medicare DRG revenue ~0.5-1%. Main CDI lever.

**CDI — Clinical Documentation Improvement.** Program that trains
physicians and coders to document patient severity more completely,
which raises CMI and therefore Medicare reimbursement.

**DRG — Diagnosis-Related Group.** Medicare's way of paying for
inpatient stays: each DRG has a fixed relative weight × Medicare
base rate. Prospective payment — hospital gets the DRG rate whether
the actual stay costs more or less.

**APC — Ambulatory Payment Classification.** Outpatient equivalent
of DRG; Medicare's OPPS (Outpatient Prospective Payment System)
uses APCs for outpatient services.

**IPPS / OPPS.** Inpatient / Outpatient Prospective Payment Systems
— the two Medicare rule sets that govern payment rates.

**HCRIS — Healthcare Cost Report Information System.** Annual CMS
cost report every Medicare-participating hospital files. Public
data; we use it for peer comparables + financial benchmarking.

**NPSR / NPR — Net Patient Service Revenue.** Revenue after
contractual adjustments and bad debt. The "net revenue" partners
model.

**Gross patient revenue.** Charge-based revenue before contractual
adjustments. Not a KPI to optimize; scale variable only.

**Contractual adjustments.** Difference between charged (gross) and
contracted rate (net). Typically 55-65% of gross.

**Bad debt.** Uncollectible receivables written off. Driven by aged
A/R, self-pay concentration, Medicaid exposure.

**MA — Medicare Advantage.** Private insurance alternative to
Medicare FFS. MA plans use AI-powered pre-auth reviews aggressively
and deny more often than traditional Medicare.

**FFS — Fee-for-Service.** Paid per claim / per service rendered.
Commercial FFS, Medicare FFS.

**Capitation.** Prepaid PMPM (per-member-per-month) payment —
hospital gets a flat fee regardless of services used.

**HFMA MAP Keys.** Healthcare Financial Management Association's
canonical set of 29 RCM performance metrics. We ship a registry
with these + PE-specific financials.

**CARC/RARC.** Claim adjustment / remittance advice reason codes —
the payer's reason for denying or adjusting a claim.

**OBBBA.** Legislation projected by CBO to cause ~11.8M Medicaid
coverage losses, with Medicaid work-requirement provisions
effective Dec 31, 2026. High-Medicaid hospitals face material
bad-debt pressure under this law.

**Sequestration.** Mandatory Medicare payment reduction (~4% 2026-2034
under OBBBA). Affects Medicare-heavy hospitals disproportionately.

**VBP — Value-Based Purchasing.** Quality / total-cost-of-care
performance-linked payment.

**RAC — Recovery Audit Contractor.** CMS contractor that audits paid
claims retrospectively and clawbacks overpayments. DRG country.

**Per diem.** Reimbursement method paying a flat daily rate ×
length-of-stay (LOS).

**Bundled payment / case rate.** Single flat payment for an entire
episode of care (e.g., a joint replacement including pre-op, surgery,
post-op, rehab).

**Cost-based reimbursement.** Allowable-cost × CMS cost-report
settlement. Used for Critical Access Hospitals (<25 beds).

## PE / deal terms

**EBITDA.** Earnings Before Interest, Taxes, Depreciation, and
Amortization. The single number PE underwrites.

**EBITDA margin.** EBITDA ÷ net revenue. <5% = execution-risk-heavy;
>10% = well-run.

**Exit multiple (EV/EBITDA).** Enterprise-value to EBITDA ratio at
exit. Typical healthcare services 10-15×.

**MOIC — Multiple on Invested Capital.** Exit proceeds ÷ entry
equity. Partner's headline return metric.

**IRR — Internal Rate of Return.** Annualized return that discounts
cashflows to zero NPV.

**Covenant.** Debt term constraining the borrower's financial ratios
(e.g., max leverage of 6.0×). Covenant breach triggers default.

**Hold period.** Years between acquisition and exit. 3-7 years typical.

**Diligence (due diligence).** Pre-acquisition investigation of a
target. RCM diligence is where this platform lives.

**IC — Investment Committee.** The partner-level group that approves
deal pricing and execution.

**LP — Limited Partner.** The investors in a PE fund; receive LP
updates on portfolio performance.

**Rollup / Platform.** PE strategy of acquiring a platform company
then bolting on smaller acquisitions to scale.

**Working capital.** Short-term operational cash — A/R + inventory −
A/P. Improving AR days releases working capital.

**One-time vs. recurring.** Critical distinction — partners multiply
recurring EBITDA by the exit multiple to get EV impact; one-time cash
release never scales.

## Internal RCM-MC terms

**DealAnalysisPacket.** The canonical per-deal analysis object.
Every UI page, API endpoint, and export renders from it. Built by
`packet_builder.build_analysis_packet()`. See
[ANALYSIS_PACKET.md](ANALYSIS_PACKET.md).

**ReimbursementProfile.** Per-hospital reimbursement exposure across
method archetypes (FFS / DRG / APC / per-diem / capitation / bundled
/ value-based / cost-based). Built by Prompt 2's engine. Lives in
`rcm_mc.finance.reimbursement_engine`. Distinct from
`MetricReimbursementSensitivity` (per-metric, in `rcm_mc.domain`).

**MetricReimbursementSensitivity.** Per-metric sensitivity across
5 reimbursement regimes (FFS / DRG / capitation / bundled /
value-based). Each `MetricDefinition.reimbursement_sensitivity` is
one of these. Previously named `ReimbursementProfile` — renamed to
resolve the name collision. Old name remains as a back-compat alias.

**Ontology.** The `rcm_mc/domain/econ_ontology.py` registry — maps
every metric to a domain, pathway, directionality, and causal
relationships.

**Ridge + conformal predictor.** ML layer that fills missing metrics
from comparable hospitals. Ridge regression + split conformal
prediction for 90% coverage intervals. See
[README_LAYER_ML.md](README_LAYER_ML.md).

**Two-source Monte Carlo.** Composes prediction uncertainty
(conformal CIs on predicted metrics) with execution uncertainty
(beta distribution per lever family) over the EBITDA bridge.

**Value bridge v1.** `rcm_mc/pe/rcm_ebitda_bridge.py` — research-band
coefficients calibrated to a $400M NPR reference hospital. Uniform
across hospitals.

**Value bridge v2.** `rcm_mc/pe/value_bridge_v2.py` — unit-economics
bridge that reads reimbursement-profile + realization-path and routes
impacts through four separate flavors (recurring revenue / cost /
one-time WC / financing). Different profile → different value.

**Provenance graph.** Directed acyclic graph connecting every metric
value back to its source (observed input, prediction, calculation).
Rich graph in `rcm_mc/provenance/graph.py`; flat snapshot in
`packet.provenance`.

**Completeness grade (A/B/C/D).** Output of `assess_completeness()`.
A = ≥90% coverage AND no critical flags; D = <50%.

**Reliability grade (A/B/C/D).** Output of `ridge_predictor._grade()`.
A = ridge with 30+ peers and R² ≥ 0.60; D = benchmark fallback.

**Hospital benchmarks.** SQLite table populated by CMS data loaders.
Used as the comparable-hospital pool.

**Rich vs. flat provenance.** Rich = `rcm_mc.provenance.graph.ProvenanceGraph`
with typed edges + cycle detection. Flat =
`rcm_mc.analysis.packet.ProvenanceSnapshot` — a simplified wire-format
that JSON round-trips. Packet-side previously named `ProvenanceGraph`;
renamed to `ProvenanceSnapshot` to resolve the name collision with the
rich class. Old name remains as a back-compat alias.

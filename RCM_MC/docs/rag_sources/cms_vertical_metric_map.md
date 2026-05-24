# RAG source — CMS vertical metric map (what's comparable, and why not across verticals)

Each vertical's higher-is-better **headline** metric (what the X-Ray
percentile/index is built on) and the key caveat. Metrics are **not**
comparable *across* verticals — a SNF star rating and an IRF
discharge-to-community rate measure different things on different scales.

| Vertical | Headline (higher = better) | Also shown | Caveat |
|---|---|---|---|
| Home Health | Quality star rating | timely care, DTC, ambulation | locality = **city** (no county) |
| Hospice | Hospice Care Index | composite process, pain screening, treatment prefs | compliance-sensitive sector |
| SNF / Nursing Home | Overall star rating | health-inspection / staffing / QM stars | + risk flags: SFF, abuse icon, ownership change, penalties |
| Dialysis | Overall 5-star | (mortality/hospitalization/readmission are lower-better → not in index) | two-chain concentrated market |
| IRF | Discharge to community (risk-std) | readmission & MSPB are lower-better | small universe (~1,200) |
| LTCH | Discharge to community (risk-std) | readmission, MSPB, beds | very small universe (~320) |
| Hospital | HCRIS cost-report metrics (beds, revenue, margin) | — | the only source with real financials; not peer-benchmarked in the post-acute X-Ray view |

**Why metrics don't cross verticals.** Different measures, scales,
risk-adjustment, and reporting cadence. X-Ray benchmarks a provider **only
against its own vertical's peers**; it never ranks a SNF against a hospice.

**Every metric carries:** its source dataset, its directionality
(higher/lower/neutral), its missingness behavior, and whether the peer set is
large enough to benchmark (n ≥ 5).

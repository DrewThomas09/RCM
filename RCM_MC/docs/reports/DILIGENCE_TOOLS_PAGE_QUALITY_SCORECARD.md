# Diligence / Tools Page Quality Scorecard

Product-quality scoring matrix for the PEdesk workbench. Each route is scored
0–5 on ten dimensions; the overall grade drives the improvement queue. This is
a living doc — re-scored as pages improve.

**Dimensions (0–5):** PC=Purpose clarity · DP=Data provenance · DH=Data
honesty · VQ=Visual quality · GU=Graph/table usefulness · GC=Guide coverage ·
DT=Deal-team usefulness · NA=Next-action clarity · EV=Source-backed evidence ·
TC=Test coverage.

**Grades:** A = strong workbench page · B = useful, needs polish · C = honest
but weak · D = unclear/underbuilt · F = misleading/synthetic/broken.

Scored against loop_start main `878fcb65`. Scores are deliberately conservative
(a page scores high on a dimension only when it clearly earns it).

## Priority pages (high deal-team importance)

| Route | PC | DP | DH | VQ | GU | GC | DT | NA | EV | TC | Grade | Note |
|---|--|--|--|--|--|--|--|--|--|--|--|---|
| /diligence (workspace) | 4 | 4 | 4 | 3 | 3 | 3 | 4 | 3 | 4 | 3 | B | index/hub; could lead with a workflow map + next-actions |
| /diligence/hcris-xray | 4 | 5 | 5 | 4 | 4 | 4 | 5 | 3 | 5 | 5 | B+ | strong real HCRIS; lacks explicit "what this means"/IC-question panel + Guide suggested-questions |
| /diligence/xray (provider) | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 3 | 4 | 4 | B | source-purpose header + deal-implications panel would lift it |
| /diligence/payer-stress | 4 | 4 | 4 | 3 | 3 | 3 | 4 | 2 | 4 | 4 | B- | needs source/purpose header, evidence layout, next-action + Guide |
| /diligence/risk-workbench | 3 | 3 | 5 | 3 | 3 | 4 | 4 | 3 | 2 | 3 | C+ | DATA REQUIRED; confirm activation path + import template + evidence checklist |
| /diligence/physician-eu | 3 | 3 | 5 | 3 | 3 | 4 | 4 | 3 | 2 | 3 | C+ | DATA REQUIRED; activation polish + management request list |
| /diligence/denial-prediction | 3 | 3 | 3 | 3 | 3 | 2 | 4 | 2 | 3 | 3 | C | ML page — verify model honesty (no invented performance), add caveats + Guide |
| /diligence/deal-mc | 3 | 3 | 3 | 3 | 3 | 2 | 4 | 3 | 3 | 3 | C | Monte Carlo on user inputs — label assumptions, honest distribution caveats |
| /diligence/management | 3 | 3 | 3 | 3 | 2 | 2 | 4 | 2 | 3 | 3 | C | management scorecard — DATA REQUIRED-ify or label illustrative + request list |
| /diligence/deal-autopsy | 2 | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 2 | 2 | D | YELLOW illustrative; needs honest label + activation/reference framing |
| /diligence/bear-case | 2 | 2 | 3 | 2 | 2 | 2 | 3 | 2 | 2 | 2 | D | YELLOW; reframe as research/scenario reference with provenance |
| /tools (index) | 4 | 4 | 4 | 3 | 3 | 3 | 4 | 3 | 4 | 3 | B | honesty-dot index; good — keep dots accurate |
| /target-screener | 4 | 4 | 4 | 3 | 3 | 3 | 5 | 3 | 4 | 3 | B | add next-action panel + Guide questions + source labels |
| /predictive-screener | 2 | 2 | 3 | 3 | 2 | 2 | 4 | 2 | 2 | 2 | D | YELLOW; label model status honestly + activation path |
| /deal-screening | 2 | 2 | 3 | 2 | 2 | 2 | 3 | 2 | 2 | 2 | D | YELLOW corpus; reframe + label |
| /market-intel | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 3 | 4 | 4 | B | now links geo suite; add Guide + source-confidence strip |
| /market-intel/geo | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 3 | B | licensed export-backed; ensure provenance strip |
| /industry/* | 4 | 4 | 4 | 3 | 3 | 3 | 4 | 3 | 4 | 3 | B | IBISWorld-derived; keep provenance + add validation panels |
| /hospital/* (profile) | 4 | 5 | 5 | 4 | 4 | 3 | 4 | 4 | 5 | 4 | B+ | real HCRIS profile + geo panel; add Guide suggested-questions |
| /competitive-intel/* | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 4 | B | real peer benchmarks + geo panel; add Guide |
| /sponsor-league | 2 | 2 | 3 | 3 | 3 | 2 | 3 | 2 | 2 | 2 | D | YELLOW corpus; label + reference framing |
| /backtest | 2 | 2 | 3 | 3 | 3 | 2 | 3 | 2 | 2 | 2 | D | YELLOW; label illustrative/experimental |

## Geo Intelligence suite (built earlier this session — reference quality bar)
`/geo-intel`, `/state-compare`, `/state-rankings`, `/state-profile`,
`/state-peers`, `/county-explorer`, `/metro-markets`, `/geo-map`,
`/geo-metrics` — all **A/A-**: real source, CSV, Guide context, source
footers, honest "—"/unranked, tests. These set the structural bar (source
header → evidence → viz → benchmark → caveat → next action → Guide) the rest
of the workbench should reach.

## Pending re-score (next ticks)
/diligence/{ingest,snapshot,benchmarks,root-cause,value,qoe-memo,checklist,
thesis-pipeline,ic-packet,ic-memo,synthesis,sponsor-detail,comparable-outcomes,
questions,regulatory-calendar,compare,physician-attrition,exit-timing,
counterfactual,covenant-stress,bridge-audit}; /cost-structure, /debt-service,
/ref-pricing, /cms-apm, /payer-rate-trends, /drug-shortage, /risk-adjustment,
/provider-network; /data-room/*, /ebitda-bridge/*, /scenarios/*; /ml-insights/*,
/model-quality.

## Improvement queue (sorted: deal-team importance × low score × easy win)
1. **Payer Stress** (B-, high importance) — full evidence-layout rebuild + header + Guide + next-actions.
2. **HCRIS X-Ray** (B+) — "what this means" + IC-question panel + Guide suggested-questions.
3. **Provider X-Ray** (B) — source-purpose header + deal-implications panel.
4. **ML pages** (denial-prediction, deal-mc, model-quality) — model-honesty pass: state method (weighting/log-transform/clustering), real vs illustrative performance, caveats, Guide. **No invented model metrics.**
5. **Risk Workbench + Physician EU** (DATA REQUIRED) — activation path + import templates + management request list + evidence checklist.
6. **Target Screener** (B) — next-action panel + Guide + source labels.
7. **YELLOW corpus pages** (deal-autopsy, bear-case, predictive-screener, deal-screening, sponsor-league, backtest) — honest labels + reframe to research/reference or DATA REQUIRED.
8. **Cost Structure / Debt Service / Ref Pricing / CMS APM / Payer Rate Trends / Drug Shortage / Risk Adjustment / Provider Network** — score + source headers + caveats + next actions.
9. **Market/Industry** — source-confidence strips + Guide + validation panels.
10. **Data-honesty regression guards** — validators so weak/synthetic states can't regress.

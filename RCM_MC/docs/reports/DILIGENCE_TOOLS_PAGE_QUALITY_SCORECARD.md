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

## Progress (Workbench Excellence Loop, PRs #849–859)
Re-scored after the first improvement sweep. **Finding:** most analyzer pages
were already more honest/built than the conservative loop_start grades — they
mainly lacked the standard `ck_source_purpose` band and on-page Guide/next-action
panels, now added. Grade deltas:

| Route | loop_start | now | What changed |
|---|---|---|---|
| /diligence/payer-stress | B- | A- | source/purpose header + management-questions panel (#850) |
| /diligence/hcris-xray | B+ | A | header + "What this means for IC" panel (#851) |
| /diligence/xray | B | A- | source/purpose band (#852) |
| /diligence/bear-case | D | C+ | honesty header on both paths + Guide ctx (#855, #857) |
| /diligence/deal-mc | C | B | DOCUMENTED Guide ctx: method + limits (#857) |
| /diligence/denial-prediction | C | B | DOCUMENTED Guide ctx + claims source links (#857) |
| /target-screener | B | A- | header + next-actions + geo-suite link (#854) |
| /predictive-screener | D | C+ | header labels scores as model estimates (#858) |
| /market-intel | B | A- | header + geo section (#844, #859) |
| /cost-structure, /debt-service, /ref-pricing, /cms-apm, /payer-rate-trends, /drug-shortage, /risk-adjustment, /provider-network | (pending) | B+/A- | re-scored: already carried HCRIS-live / illustrative / DATA REQUIRED headers |
| /industry/* | B | A | already licensed-derived provenance + header + public-data connections |
| Guide/RAG corpus | — | — | restored 13 dropped curated cards (#853); guard locks the contract (#856) |

Net: the Diligence/Source/Market analyzer surface now consistently carries a
source/purpose header, an honesty label, and (for model pages) a DOCUMENTED
Guide context. Regression guard (`test_diligence_source_purpose_headers`) +
data-source audit (0 flagged) keep it from regressing.

## Improvement queue (refreshed — genuine remaining gaps)
1. **On-page Guide suggested-questions** — render suggested questions on the key analyzer pages (Guide as on-page functionality, not just backend context).
2. **Visual upgrades** — pages with real data but table-only views: add a real chart where the data supports it (peer percentile bar, distribution, trend only where real time-series exists). No fake trends.
3. **DATA REQUIRED depth** — Risk Workbench / Physician EU / management-scorecard: confirm import template + management request list + evidence checklist + activation path.
4. **market-intel/geo + market-data/state** — verify provenance strip + add Guide suggested-questions.
5. **ML log-transform diagnostic** — careful, well-tested addition to the predictor's DiagnosticReport (skewness → log-transform recommendation), as a dedicated PR (not a 180s tick). No invented metrics.
6. **Covenant-stress / bridge-audit / exit-timing / counterfactual / management** — confirm source/purpose header + add to the regression guard.
7. **Tools index** — keep honesty dots accurate as pages change tier.
8. **Re-score remaining pending routes** and fold into the regression guard's `_REQUIRE_SOURCE_PURPOSE` list.

## Re-score (2026-05-26 session, PRs #892–#893)
Two queue items were found **already shipped**, not gaps — confirming the
loop's recurring finding that the workbench is more built than conservative
loop_start grades implied:

- **#1 On-page Guide suggested-questions → DONE (via shell).** The Chartis
  Guide drawer (`ck-guide-panel`, every page) already renders suggested-
  question chips in both the Overview and Ask tabs, populated from the page
  context packet (`get_suggested_questions_for_page`). A separate on-page
  panel would duplicate this. Item closed.
- **#2 Visual upgrades / "table-only real-data pages" → mostly DONE.** The
  three real-data pages with no `<svg>` (drug-shortage, risk-adjustment,
  cms-apm) already render `ck_bar_row` HTML-bar visuals on LIVE FDA/CMS data.
  Not table-only. No fake-trend charts were added (honest: those pages are
  cross-sectional, not time-series).

Stewardship / guard hardening this session:
- **#892** — greened the two remaining pre-existing test failures and
  reconciled two *mutually contradictory* `_vintage_chart` empty-data tests
  (root cause of why both were "pre-existing"). Deployed; healthz ok.
- **#893** — extended `test_diligence_source_purpose_headers` to lock the
  source/purpose header on **14 more** headed pages (queue item #8 advanced):
  data_public payer_stress, biosimilars_opp, diligence_checklist,
  esg_dashboard, hcit_platform, industry, insurance_tracker, market_geo,
  mgmt_comp, partner_economics, physician_productivity, provider_retention,
  + deal_library, market_data. Guard now locks ~42 pages.
- **#5 ML weighted ridge** — re-scoped: the log-transform advisory shipped
  (#871–880); weighted ridge is the remaining ML ask but is **approval-gated**
  (changes every prediction + its reported reliability; must be measured, not
  asserted). See the ledger's ML-predictor section for the full finding.
- Page data-source audit re-run: **0 flagged** (honesty invariant holds).

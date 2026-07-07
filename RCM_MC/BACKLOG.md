# BACKLOG — scored items (rubric: Chartis×3 + PE-cred×3 + data-realism×2 + UX×2 + effort⁻¹×1)

Each item lists: score / rationale / verification plan. Re-groomed every refill.

| # | Item | Score | Verification plan |
|---|---|---|---|
| 1 | ✅ DONE — Azure→DO purge | — | LOG #1 |
| 2d | ✅ DONE — P2 CIM Cross-Check | — | LOG #2; live ckpt-1 |
| 3d | ✅ DONE — P7 Roll-Up Builder | — | LOG #3; live ckpt-1 |
| 4d | ✅ DONE — P4 percentile chip | — | LOG #4 |
| 5d | ✅ DONE — P11 DQ dashboard | — | LOG #5 |
| 6d | ✅ DONE — P8b reg exposure | — | LOG #6 |
| 7d | ✅ DONE — P1 active-deal context | — | LOG #7 |
| 2 | **P2 CIM Cross-Check vertical slice** — claim entry (market size $, provider count, margin %, payer mix %, volume) → independent HCRIS/universe estimates → variance table w/ green≤10/yellow≤25/red flags + drill-to-source + memo export. Hospital subsector, one state. | 43 | Fabricate claims from real TX data ±7/18/40% → exactly green/yellow/red fire; every estimate row links source; memo exports; pytest unit tests on variance math; screenshot |
| 3 | **P7 Roll-Up Scenario Builder slice** — pick 2–3 real HCRIS CCNs in one state → combined volumes, NPR, payer blend, state share + HHI before/after, antitrust note >Δ200 | 40 | Hand-check aggregate math vs the 3 single-facility rows; HHI delta recomputed by hand; screenshot; tests on the combine math |
| 4 | **P4 percentile chip** — reusable ck_peer_percentile(value, dist) "p78 vs TX hospitals (n=412)" + sparkline; wire into deal quick-view + CIM estimates | 36 | Hand-check 3 facilities' percentile placement vs raw distribution; tests on percentile math incl. ties/NaN |
| 5 | **P11 Data Quality dashboard** — one screen: registry sources × vintage, rows, null-rate on key fields, gap census (reuse gap_fill_registry), pages-consuming | 34 | Numbers match `rcm-mc data gaps` + 2 independent spot-checks; screenshot |
| 6 | **P8b facility→rule exposure** — join provider type → applicable rules from regulatory_calendar; exposure panel on X-Ray with rule dates + source links | 33 | One hospital + one SNF-ish CCN map to correct rule sets; every headline cites its rule URL; tests on the join |
| 7 | **P13 insight-bullet primitive** — template+significance-guard engine (suppress <0.5pp deltas); apply to /portfolio + state market page; copy-to-clipboard | 31 | 10 bullets read against panels: zero unsupported claims; guard test (tiny delta → no bullet) |
| 8 | **P1 deal switcher** — active-deal context in nav (cookie/session), screener/X-Ray/market pre-scope to deal geography; deal home links back | 31 | Create real-CCN deal, confirm 3 modules open pre-scoped; tests on context carry |
| 9 | **B in-UI model card** — holdout coverage + calibration summary for ridge+conformal on /methodology + predictive screener footer ("90% conformal band covered 89.3% on 2024 holdout") | 30 | Numbers reproduced by a checked-in script; never claims AI/LLM; test asserts wording |
| 10 | ✅ DONE — H demo-deal realism (sth rebuilt as White Plains Hospital, CCN 330304: HCRIS values as sourced observed_metrics; ENTERED→ACTUAL relabel where sourced; CCN named on deal surfaces) | — | LOG W4-006 |
| 11 | ✅ DONE — P12 entity jump (Cmd-K 6-digit CCN → HCRIS X-Ray); name search deferred (needs backend index) | — | LOG #17 |
| 12 | ✅ DONE — P5 ExhibitFactory v1 (+ corpus-seed batching perf fix found in pre-commit suite) | — | LOG #11 |
| 13 | ✅ DONE — P9 vintage-diff snapshots on saved screens (+ fixed session-username bug that hid the whole owner panel) | — | LOG #18 |
| 14 | ✅ DONE — Est. AR Days column + "?" explainer + 25–75 bound on predictive screener | — | LOG #14 |
| 15 | **A empty-state sweep** — top-10 pages with ?state=ZZ / empty db: consistent ck_empty_state, no dead controls | 20 | Walker variant with empty db; screenshots |

| 16 | ✅ DONE — deal-context slice 2 (cookie prefills CIM state/ccn + rollup basket) | — | LOG #12 |
| 17 | ✅ DONE — roll-up scenarios saved to deals as sourced notes (recomputed server-side, basis stated) | — | LOG #19 |
| 18 | ✅ DONE — DQ staleness chips (CURRENT/AGING/STALE by cadence; SNF amber) | — | LOG #15 |
| 19 | ✅ DONE — route_walker --discover + nan/None-leak gate, wired into weekly sweep | — | LOG #16 |
| 20 | ✅ DONE — screener hospital row → CIM action (state+ccn scoped) | — | LOG #13 |


## Refill 2 (scored 12:25Z) — ready queue
| # | Item | Score | Verification plan |
|---|---|---|---|
| 21 | ✅ DONE — P12b palette name-search (shipped earlier; pinned by test_palette_entity_jump) | — | verified 2026-06-12 |
| 22 | ✅ DONE — P9 slice-2 diff detail (?diff=<id> row-level view in target_screener_page) | — | verified 2026-06-12 |
| 23 | ✅ DONE — P4b: CIM claim chip upgraded to ck_peer_percentile visual (track + scope label, engine rank) | — | W2-182 |
| 26 | ✅ DONE — exhibit chrome on X-Ray peer roster + screener compare | — | W2-185 |
| 24 | ✅ DONE — roll-up note: anchor (earlier) + ROLL-UP chip (W2-183) | — | W2-183 |
| 30 | ✅ DONE — empty-state sweep is a permanent test gate (ZZ + empty db, walker markers) | — | W2-186 |
| 25 | ✅ DONE — DQ snapshot dates (all WIRED sources carry real vendored dates) | — | verified 2026-06-12 |
| 29 | ✅ DONE — model-card link on screener footer (/methodology) | — | verified 2026-06-12 |
| 27 | ✅ DONE — walker --deal-cookie + weekly-sweep second pass | — | W2-184 |
| 28 | ✅ DONE — screener state prefill (shipped earlier; main-view only, params win) | — | verified 2026-06-12 |

## Groomed-out / blocked
- Medicaid S-3 re-ingest + POS bed backfill: NETWORK-GATED (sources named in
  gap_fill_registry; loaders runnable when egress opens).
- ONC CHPL HCIT wiring: NETWORK-GATED (api named in FEATURE_MATRIX E).

## Refill 3 (groomed 2026-06-12, window 3) — ready queue
| # | Item | Score | Verification plan |
|---|---|---|---|
| 31 | ✅ DONE — state-detail pin map (no-fake-points, shipped earlier) + catchment-radius nub: Off/15 mi/30 mi ring control on the state-detail pin map, rings ONLY around real-coordinate pins, geometry derived from the projection's actual px/deg scale (labeled straight-line equirectangular approx., not drive time), ?radius=-synced, off by default | — | LOG W4-010 |
| 32 | ✅ DONE — P10 provenance-coverage metric (static AST scan of ck_kpi_block call sites; per-page + overall % published live on /methodology) | — | LOG W4-007 |
| 33 | ✅ DONE — all-hospital peer sets link → /pipeline/rollup?ccns= | — | W2-211 |
| 34 | ✅ DONE — P13 long-tail: guarded bullets on /metro-markets (2 templates, landed earlier) + /county-explorer (3 templates); figures recomputed from the same rows/footer the panels render; tiny-delta + empty-data guards test-pinned on both pages | — | LOG W4-008 |
| 35 | ✅ DONE — glossary long-tail: predictive-screener headers (part 1, W2-218) + HCRIS X-Ray benchmark-grid metric labels via metric_label_link attr→key alias table (10 of 15 linked; 5 no-card attrs guard-fall-through to plain text — no dead anchors) | — | LOG W4-009 |
| 36 | ✅ DONE — memo + package routes record registry rows | — | W2-210 |

## Groomed-out / blocked (window 3 additions)
- P9 per-CCN CHOW diff alerts: NETWORK-GATED (vendored snf_chow is
  state×year aggregate; per-CCN CHOW feed named in gap registry).

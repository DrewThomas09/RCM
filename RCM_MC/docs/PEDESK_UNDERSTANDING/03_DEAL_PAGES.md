# 03 · Per-deal pages — every score & band sourced

> The `/deal/<id>/...` surfaces. Unlike `/app`, these read a **`DealAnalysisPacket`** plus a **`PartnerReview`** (the "PE Brain" output that consumes the packet without mutating it). This file gives the exact formula/threshold behind every headline number, so you can answer "how is the investability score computed?" or "what makes a deal grade F on the stress grid?" precisely.

## Shared substrate — how every PE-intelligence page is built

All of `partner-review`, `red-flags`, `archetype`, `investability`, `market-structure`, `white-space`, `stress`, `ic-packet` go through one helper, `_build_partner_review_context(deal_id)` (`server.py:10358`):
1. `get_or_build_packet(store, deal_id, skip_simulation=True)` — load/build + cache the packet (`analysis_store.py`).
2. `pe_intelligence.partner_review.partner_review(packet)` → a `PartnerReview` object, **without mutating the packet**.
3. `_enrich_secondary_analytics` then attaches `review.regime`, `.market_structure`, `.operating_posture`, `.stress_scenarios`, `.white_space`, `.investability` — each in its own try/except, so a failed sub-analysis becomes `{"error": …}` rather than a crash.

**Universal empty state:** if the packet can't build or `partner_review` raises, every page shows an "insufficient data — run a simulation first" banner linking to `/analysis/<id>`. Sub-analyses degrade to a printed note, never a 500.

---

## 1. `/deal/<id>` — main deal dashboard
Not a packet page — reads `PortfolioStore` directly. The headline is the **health score**.

**Health score (0–100)** — `deals/health_score.py::compute_health`. **Starts at 100 and subtracts** severity-weighted deductions (it is a deduction model, not additive):
| Deduction | Trigger → penalty |
|---|---|
| Covenant | `TRIPPED → −40`, `TIGHT → −15` (largest single factor) |
| Concerning signals | `≥5 → −15`, `≥3 → −8`, `≥1 → −3` |
| EBITDA variance (latest quarter) | `≤ −15% → −25`, `≤ −10% → −15`, `≤ −5% → −5` |
| Residual alerts | amber `−5`, else `−10` (only deadline/cluster/regress kinds, to avoid double-counting) |

Clamped to `[0,100]`. **Band:** green ≥80 · amber 50–79 · red <50. **Trend:** `delta = score − prior_score` (most recent history row before today) → ↑/↓/→. **Sparkline:** `history_series(days=90)`, fixed 0–100 axis, dashed reference lines at 80 and 50 — **returns nothing if <2 history points** (a one-sighting deal has no chart). Tooltip lists the deductions; "No deductions — healthy." when clean. Empty: no snapshot → `score=None`, band "unknown", dashboard shows `—`. Scores are persisted idempotently to `deal_health_history`.

The rest of this page (snapshot trail, variance, initiatives, notes, tags, owner, deadlines) renders from the `deals/` and `portfolio/` store modules, not the packet.

## 2. `/deal/<id>/profile`
Reads packet attributes directly. Sections: entity (`packet.profile`), market (`packet.market_context` — CBSA/population/growth/attractiveness), comps (`packet.comparables.members`), observed metrics (`packet.observed_metrics`), predictions (`packet.predicted_metrics`, 90% conformal interval), and the **EBITDA bridge** (`packet.ebitda_bridge`).

**EBITDA bridge section:** `current_ebitda`, `target_ebitda`, `total_ebitda_impact`, and `per_metric_impacts`. The lever-contribution chart sorts levers by `|ebitda_impact|`, bar width = `|eb|/max·100` (green if uplift, red if drag), and **needs ≥2 non-zero levers or it hides**. Empty states are explicit: "No bridge built yet — needs RCM metrics + research-band coefficients" / "Bridge has no lever impacts."

## 3. `/deal/<id>/partner-review` — the IC verdict
**IC recommendation** = `narrative.recommendation`, computed by `narrative._compose_recommendation(bands, hits)`. **Exact logic:**
```
worst_band == IMPLAUSIBLE   OR  n_critical >= 1            → PASS
worst_band == OUT_OF_BAND   OR  n_high_plus >= 2           → PROCEED_WITH_CAVEATS
worst_band == STRETCH       OR  worst_severity == HIGH     → PROCEED_WITH_CAVEATS
worst_band == IN_BAND       AND worst_severity in {INFO,LOW}→ STRONG_PROCEED
worst_severity == MEDIUM                                   → PROCEED
else                                                       → PROCEED
```
(`n_high_plus` = count of HIGH+CRITICAL hits; `n_critical` = count of CRITICAL.) **Fundable** = recommendation ∈ {PROCEED, STRONG_PROCEED}.

**Reasonableness bands** (`pe_intelligence/reasonableness.py`): each metric is classified IN_BAND / STRETCH / OUT_OF_BAND / IMPLAUSIBLE by `Band.classify(value)` — inside `[low,high]` → IN_BAND, above high but ≤ stretch_high → STRETCH, above implausible_high → IMPLAUSIBLE, else OUT_OF_BAND. **IRR bands are keyed by `(size_bucket, payer_regime)`**:
- size buckets (by EBITDA): small <$10M, lower_mid <$25M, mid <$75M, upper_mid <$200M, large ≥$200M
- payer regimes: govt_heavy (medicare+medicaid ≥0.70), medicaid_heavy (≥0.30 medicaid), medicare_heavy (≥0.55 medicare), commercial_heavy (≥0.45 commercial), else balanced

Margin bands are keyed by hospital type; exit-multiple ceilings and lever-realizability timeframes have their own tables. Missing input → verdict UNKNOWN (not an error). The page also shows a band-position bullet per row (shaded acceptable band + observed marker, green in-band/red out).

**Heuristic hits** (`pe_intelligence/heuristics.py`): 19 rules, each emitting a `HeuristicHit` at INFO/LOW/MEDIUM/HIGH/CRITICAL, sorted most-severe-first. Examples: `aggressive_denial_improvement` (MEDIUM ≤350 bps/yr, HIGH ≤600, CRITICAL >600), `leverage_too_high_govt_mix` (govt ≥0.60 & leverage >5.5× → HIGH, >6.5× → CRITICAL), `covenant_headroom_tight` (<20% MEDIUM, <10% HIGH). A rule that raises degrades to a LOW "evaluation failed" hit.

**Investability KPI** on this page reads `review.investability["composite_score"]` (full computation in §6). Tiles: Bands Out = `OUT_OF_BAND + IMPLAUSIBLE` count; Critical Flags = CRITICAL count.

## 4. `/deal/<id>/red-flags` — 30-second triage
A focused subset of the partner review: only hits + band violations.
- **Verdict banner:** `crit→HARD STOP`; `high or implausible→SERIOUS CONCERNS`; `medium or out-of-band or stretch→WATCHLIST`; else `CLEAN SCAN`.
- KPI tiles: Critical / High / Medium+Low (from `severity_counts()`), **Band Violations = OUT_OF_BAND + IMPLAUSIBLE**, Total Hits.
- Band-violations table: reasonableness checks with verdict OUT_OF_BAND/IMPLAUSIBLE. Empty: "No band violations — the numbers sit inside the reasonableness envelope."

## 5. `/deal/<id>/archetype` — sponsor structure + regime
**Sponsor-structure archetype** (`deal_archetype.classify_archetypes`, min_confidence 0.25): each archetype scorer accumulates additive points (e.g. platform_rollup: +0.40 rollup thesis, +0.30 platform flag, +0.30 add-ons, +0.10 fragmented; confidence = min(score,1)). Only hits ≥0.25 shown, sorted desc; primary archetype uses ≥0.30. Confidence bands: HIGH ≥0.75, MEDIUM ≥0.50, else LOW. Empty: nothing above 0.25 → "missing structural metadata."

**Regime** (`regime_classifier.classify_regime`): five scorers (durable / emerging / steady / stagnant / declining), each scoring additive signals on revenue CAGR, growth stddev, positive-growth years (e.g. durable_growth: CAGR >0.06, σ ≤0.04, 5/5 positive years). Picks max confidence; ties resolve declining > stagnant > steady > durable > emerging. **All-zero → STEADY, confidence 0.0, "Insufficient signals."** Each regime carries a fixed playbook + key risk.

## 6. `/deal/<id>/investability` — composite 0–100 + exit readiness
**Investability composite** (`investability_scorer.score_investability`):
```
composite = 0.30·opportunity + 0.40·value + 0.30·stability
score     = round(composite · 100)
```
Each sub-score is the mean of its present components (default 0.50 if none):
- **Opportunity (30%):** consolidation-play score (raw 0–1), fragmentation verdict {fragmented 0.75, consolidating 0.55, consolidated 0.25}, white-space top score.
- **Value (40%):** IRR/exit band verdict {IN_BAND 0.75, STRETCH 0.55, OUT_OF_BAND 0.30, IMPLAUSIBLE 0.05}; raw IRR (≥22%→0.85 … else 0.30); MOIC (≥2.5×→0.80 … else 0.25).
- **Stability (30%):** stress grade map {A 0.95, B 0.80, C 0.60, D 0.35, F 0.10}; downside pass rate; regime map; operating-posture map; **any CRITICAL hit drags it to ~0.05**; covenant breaches → 0.30.

**Grade:** A ≥85 · B ≥72 · C ≥58 · D ≥42 · F <42.

**Exit readiness (12 weighted dimensions)** (`exit_readiness.score_exit_readiness`): `score = round(Σ(finding·weight)/Σweight)`. Weights: audited_financials 0.15, quality_of_earnings 0.12, ebitda_trend 0.12, kpi_reporting 0.10, data_room 0.10, margin_trend 0.08, buyer_universe 0.08, management_retention 0.08, legal_clean 0.05, ebitda_vs_plan 0.05, ebitda_adjustments 0.04, revenue_vs_plan 0.03. Yes/No/unknown → 100/0/50. **Verdict:** ready ≥85 · soft_launch ≥65 · not_ready <65. (Note: the page text lists extra verdict labels that the engine doesn't emit — cosmetic aliases.)

## 7. `/deal/<id>/market-structure` — concentration
From `market_structure.analyze_market_structure(shares)`:
- **HHI = Σ(share·100)²** on the 0–10,000 scale (DOJ convention here — distinct from the 0–1 fractional HHI used by the corpus market-concentration module).
- **CR3 / CR5** = sum of top-3 / top-5 normalized shares.
- **Fragmentation verdict:** fragmented <1500 · consolidating 1500–2499 · consolidated ≥2500 (DOJ/FTC thresholds).
- **Consolidation-play score (0–1)** = `0.35·hhi_score + 0.25·cr5_score + 0.20·n_score + 0.20·dom_score` (each a clamped transform favoring fragmented, low-CR5, many-player, no-dominant-incumbent markets).
- Thesis hint: fragmented & score ≥0.60 → platform rollup; consolidating → buy-and-build; top share ≥0.35 → challenger/niche; else scale/capability. Empty: no shares → guided state showing the `profile.market_shares` schema.

## 8. `/deal/<id>/white-space` — growth adjacencies
From `white_space.detect_white_space`: per-opportunity score (0–1) by dimension — geographic (adjacent 0.6 / else 0.4), segment (registry-adjacency 0.70 / else 0.45), channel (registry 0.65 / else 0.40). Sorted desc; top_dimension = highest aggregate. Score color: ≥0.75 positive, ≥0.50 warning, ≥0.25 dim. Empty: no opportunities → guided scan state.

## 9. `/deal/<id>/stress` — robustness grade
From `stress_test.run_stress_grid` over 10 downside scenarios (rate −100/200/300 bps, volume −5/10%, multiple compression, lever slip 60/40%, labor shock 10/20%):
- **Robustness grade** (`_robustness_grade`): `n_downsides==0 → "?"`; **A: pass ≥90% AND 0 breaches**; **B: pass ≥80% AND ≤1 breach**; **C: pass ≥60%**; **D: pass ≥40%**; **F: below 40%**.
- **Downside pass rate** = passing downside scenarios / evaluable downsides. Upside capture = passing upsides / evaluable upsides. Worst/best case = min/max EBITDA Δ%.
- **Covenant breaches** = sum of `covenant_breach` flags across scenarios; rendered per-row BREACH/OK.
- Empty: "Stress grid could not be computed."
> This is exactly why a deal reads **grade F**: <40% of downside scenarios pass (it fails under most downsides) — "do not bring to IC as modeled."

## 10. `/deal/<id>/ic-packet` — the master bundle
`master_bundle.build_master_bundle(packet)` assembles up to 10 sections: IC memo (HTML), analyst cheat-sheet, bear patterns, regulatory items, 100-day plan, partner discussion, scenario narrative, board memo, LP pitch, audit trail. KPIs: Sections N/10 (populated count), Bear Patterns count, Regulatory Items, Healthcare Checks (`review.healthcare_checks["total_hits"]`), and the IC verdict banner (`narrative.recommendation`). Each missing section renders a placeholder note; the sticky TOC links only populated sections.

---

## How the explainer numbers connect (the chain)
A deal's investability/stress/bands all ultimately trace back to the **packet's `rcm_profile`** (observed-or-predicted metrics) and `profile` (size, payer mix, structure). So: public CMS data or seller data → observed/predicted metrics → packet → `partner_review` reasonableness bands + heuristics → recommendation; and packet → bridge + stress grid → investability stability sub-score. If a partner asks "why PROCEED_WITH_CAVEATS?", the answer is on the partner-review page: the worst band verdict and the highest-severity heuristic hit drove it, per the recommendation logic above.

---
*Next: `04_DILIGENCE_RCM.md` — the RCM commercial-diligence pipeline and workbenches.*

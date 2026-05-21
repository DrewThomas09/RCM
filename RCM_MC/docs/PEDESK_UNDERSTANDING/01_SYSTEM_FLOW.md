# 01 · System Flow — how a number gets to the screen

> The single most important thing to understand about PE Desk: **almost every per-deal number you see is read from one frozen object, the `DealAnalysisPacket`.** Pages don't compute numbers themselves — they render a packet. This file traces the whole path: HTTP request → auth → route → packet build → render, and explains the packet's anatomy so the per-page files can reference it.

---

## 1. The request lifecycle (`rcm_mc/server.py`)

PE Desk is one stdlib HTTP server (`ThreadingHTTPServer`), one handler class `RCMHandler`. Every request runs the same pipeline before a page is produced:

1. **Request ID + timing** — a UUID is stamped on the request; `X-Request-Id` and `X-Response-Time` headers come back. Response times feed `/api/metrics` (p50/p95/p99).
2. **Auth / session** — a session cookie is looked up (`auth.user_for_session`, 7-day sliding TTL with idle timeout). Unauthenticated navigations redirect to `/login`; `/` then redirects an authenticated user to `/app`. (If no users exist and no auth is configured, PE Desk runs in single-user "open mode" — laptop use.)
3. **CSRF** — state-changing POSTs need a `csrf_token` field or `X-CSRF-Token` header (a small JS shim auto-adds it). A short exempt list covers login/logout/health.
4. **Rate-limit / size cap** — login, data-refresh, and deletes are throttled; requests over 10 MB are rejected.
5. **Workspace mode** — the `ck_workspace_mode` cookie sets a per-request mode (PE Partner default, or Chartis Consulting) used only to swap vocabulary.
6. **Route dispatch** — `do_GET`/`do_POST` match the path and call a `_route_*` handler, which calls a renderer in `rcm_mc/ui/…`.
7. **Render + shell** — the renderer returns an HTML body; `chartis_shell(...)` wraps it in the editorial chrome (topbar, nav, fonts). Charts are inline SVG.
8. **gzip + ETag + audit** — the response is compressed (>1 KB), packet/JSON GETs send an ETag (304 on `If-None-Match`), and the event is appended to the audit log with the request ID.

**Key takeaway:** the server is plumbing. The *intelligence* is in the packet build (per-deal pages) or in a corpus query (library/portfolio pages). Where a page's numbers come from depends on which of those two it is — see §4.

---

## 2. The DealAnalysisPacket — the spine

`rcm_mc/analysis/packet.py` defines `DealAnalysisPacket`. Its own docstring states the invariant: *"UI routes, API endpoints, and exports render from this object — nothing renders independently. If a number shows up on a page, it came from here."*

Why it exists:
- **No number drift** — if `/deal/<id>/profile` and `/deal/<id>/partner-review` both show "EBITDA $38M", they read the same packet field. A disagreement is a rendering bug, not a data discrepancy.
- **A frozen snapshot** — the packet records "what we knew at time T" (`as_of`, `generated_at`, `model_version`), so an IC memo is reproducible.
- **Round-trippable** — every nested section serializes to JSON and back, so the packet can be cached and exported byte-for-byte.

It is built by `analysis/packet_builder.py`, cached in the `analysis_runs` SQLite table (keyed on `(deal_id, hash_inputs)`), loaded by `analysis/analysis_store.get_or_build_packet(store, deal_id)`, and exported by `exports/packet_renderer.py`.

### Packet sections (what each per-page file will reference)
| Packet field | What it holds | Built by |
|---|---|---|
| `profile` | The hospital/deal profile: name, geography, beds, payer mix, financials. | step 1 |
| `observed_metrics` | Metrics that are **measured** (seller-entered / HCRIS / 990 / Care Compare), each tagged with its source. | step 2 |
| `completeness` | A registry + grade of how much of the needed data is present. | step 3 |
| `comparables` | The peer cohort matched from the corpus (with similarity scores). | step 4 |
| `predicted_metrics` | Metrics **filled by the ridge+conformal predictor** where not observed, each with a 90% interval + reliability grade. | step 5 |
| `rcm_profile` | The merged "best value per metric" (observed wins over predicted), the input to the bridges. | step 6 |
| `ebitda_bridge` | The **7-lever v1 EBITDA bridge** result (current → target EBITDA, per-lever impacts). | step 7 |
| `value_bridge_result` (+ leverage/EV summaries) | The **payer/method-mix v2 bridge**. | step 7b |
| `simulation` | The **two-source Monte Carlo** distribution (P5…P95, P(breach), P(MOIC≥x)). | step 8 |
| `v2_simulation` | The v2 Monte Carlo, when the v2 bridge produced levers. | step 8b |
| `metric_forecasts` | Per-metric temporal forecasts (only when historical values were supplied). | step 8c |
| `risk_flags` | Structured risk flags from metrics, completeness, comparables, bridge, regulatory context. | step 9 |
| `provenance` | The data-lineage graph (every metric → its source nodes). | step 10 |
| `diligence_questions` | Auto-generated questions from the risk flags + gaps. | step 11 |

---

## 3. The packet build — 12 steps (`build_analysis_packet`)

Each step is best-effort: a failure marks **that section** `INCOMPLETE`/`FAILED`/`SKIPPED` rather than killing the packet. No IO happens outside the passed `store` handle.

1. **Profile** — assemble the deal/hospital profile (with analyst overrides applied per namespace, loaded once in step 1b; a data-integrity preflight runs in 1c).
2. **Observed metrics** — collect measured metrics, each tagged with its source (`USER_INPUT`/`HCRIS`/`IRS990`/`CARE_COMPARE`/`UTILIZATION`).
3. **Completeness** — score how much of the required metric set is present (drives the confidence grade).
4. **Comparables** — match a peer cohort from the corpus; 4b runs anomaly detection against that cohort.
5. **Predicted metrics** — for each missing metric, run the **ridge + split-conformal** predictor against the comparables (ladder: ridge ≥15 peers → weighted median ≥5 → benchmark fallback). Dollar metrics are never predicted (partner-supplied).
6. **Merge RCM profile** — combine observed + predicted into one "best value" per metric (observed always wins). 6b builds the reimbursement / revenue-realization views (payer-class and method mix).
7. **EBITDA bridge (v1)** — run the 7-lever bridge from current → target metrics. 7b runs the payer/method-mix **v2 value bridge** using the *same* targets, so the two can be compared.
8. **Monte Carlo** — when the bridge is OK, run the **two-source MC** (prediction uncertainty from the conformal CIs × execution uncertainty from per-lever Beta distributions); else fall back to the legacy YAML simulate path. 8b runs the v2 MC; 8c runs temporal forecasts if historical values exist.
9. **Risk flags** — derive structured flags from metrics, completeness, comparables, bridge, and regulatory context (9a is a static state-regulatory lookup).
10. **Provenance graph** — assemble the lineage graph linking every metric to its source nodes.
11. **Diligence questions** — generate questions from the risk flags and data gaps.
12. **Assemble + cache** — pack everything into the `DealAnalysisPacket`, stamp version/run-id/timestamps, and (on the server path) cache it in `analysis_runs`.

---

## 4. Two kinds of page → two kinds of number

Every page in PE Desk gets its numbers from one of two places. Knowing which tells you immediately where a number comes from:

**(A) Per-deal pages** — `/deal/<id>/*`, `/app` (when a deal is focused), the diligence workbenches. These **load a packet** (`get_or_build_packet`) and render its sections. A number on these pages traces to a packet field → the build step that produced it → its data source. *Example:* the EBITDA bridge waterfall on `/deal/<id>/profile` is `packet.ebitda_bridge.per_metric_impacts`, produced by step 7 from `rcm_profile` (observed-or-predicted metrics) via the 7-lever formulas in `pe/rcm_ebitda_bridge.py`.

**(B) Corpus / portfolio pages** — the library, comparables, sponsor league, payer intelligence, deal-risk scores, market rates, the ~150 `data_public` modules. These **query the realized-deal corpus** (`public_deals`) and/or **CMS public data** (`hospital_benchmarks`), then compute an analytic in a `data_public/<topic>.py` engine. A number here traces to the corpus/CMS table → the engine function → its formula. *Example:* a sponsor's P50 MOIC on `/sponsor-league` is the median of `realized_moic` over that sponsor's corpus deals (`data_public/sponsor_track_record.py`).

The portfolio-operations pages (`/app` KPI strip, `/portfolio/monitor`) are a third, lighter case: they read **portfolio state** from SQLite directly (`deals`, `deal_snapshots`, `alerts`, `initiative_actuals`) via `portfolio_rollup()` / `latest_per_deal()` — not a packet, not the corpus. *Example:* the `/app` Weighted MOIC hero is `portfolio_rollup(store)["weighted_moic"]`, an entry-EV-weighted mean over the deal snapshots.

---

## 5. Provenance — every number knows what it is

So a partner never mistakes a measurement for a model output, three systems tag each number (full detail in `../PEDESK_DATA.md` §4):

- **UI source badges** (`ui/provenance.py`): a small badge on a value — `HCRIS` (real cost-report filing, high trust), `SELLER` (data-room, high), `CALIBRATED` (Bayesian blend of ML + seller, high), `COMPUTED` (derived, high), `ML_PREDICTION` (modeled, medium), `BENCHMARK` (peer P50, low), `DEFAULT` (assumption, low). Priority when several exist: **calibrated > seller > hcris > ml > default**.
- **Provenance graph** (`provenance/graph.py`): the "why is this 8.2%?" explorer — typed nodes (SOURCE/OBSERVED/PREDICTED/CALCULATED/AGGREGATED/BENCHMARK) and edges, traversable upstream.
- **Confidence grade** (`data/sources.py`): an A–D grade from the fraction of inputs that are observed vs assumed.

**The defensibility rule throughout:** PE Desk shows honest empty / `INCOMPLETE` states rather than fabricated numbers. The bridge returns `INCOMPLETE` with a reason when it has no revenue baseline; the predictor returns benchmark fallbacks graded `D`; synthetic backtests are labeled; the synthetic slice of the corpus is gated from partner view. If a number is modeled, its badge says so.

---

## 6. Where the deal's input metrics come from (the front of the funnel)

A per-deal packet is only as real as its inputs. Those arrive three ways:
1. **Public CMS data** — for a screened hospital (by CCN), HCRIS cost-report metrics (revenue, margin, beds, payer-day mix), Care Compare quality, IRS 990 financials are pulled from `hospital_benchmarks`. This is what makes a deal analyzable *before* the seller shares anything.
2. **Seller data room** — during diligence, the analyst enters seller-provided metrics (`data_room_entries`); these are tagged `SELLER` and **override** public/predicted values.
3. **Bayesian calibration** — when both a model prediction and thin seller data exist, they're blended into a posterior (`data_room_calibrations`, tagged `CALIBRATED`) — shrinking to the peer prior when seller-n is small, converging to the seller value when it's rich.

Whatever isn't supplied is **predicted** (with a 90% interval) or falls back to a **benchmark** (graded `D`) — never silently zero-filled.

---
*Next: `02_COMMAND_CENTER.md` traces every number on the `/app` landing page through this machinery.*

# HCRIS X-Ray — Component & Token Map (design-handoff migration)

**Status:** Phase-0 migration map for the `~/Desktop/design_handoff_xray`
rebuild. **Docs only — no production code changes in this PR.** Per
`docs/PEDESK_DESIGN_HANDOFF_CONTRACT.md`, this map must be reviewed before any
code lands. It is the contract that PRs 1–N implement.

Handoff files inspected: `README.md`, `xray-input.html`, `xray-results.html`,
`reference/styles.css`, `reference/input-variants.jsx`,
`reference/results-variants.jsx`, `reference/results-a-v2.jsx`.

---

## 1. Selected variants

| Page | Selected variant | Rejected variants |
|---|---|---|
| **Input** | **B · Workstation** — two-up: intake form (left) + live SAMPLE output preview (right) | A (single-column form), C (wizard) |
| **Results** | **A v2 · Headline** — inverted pyramid: top finding → 3-yr trend → EBITDA gap → payer-mix driver → deviation cards → full 15-metric table → peer roster + comps → cross-refs | A v1 (variance-rail), B (tabbed), C (dense grid) |

The input page already ships a "B · Workstation" first cut
(`_xray_workstation`); this rebuild brings it to handoff fidelity. The results
page is currently a benchmark-grid report and needs the A-v2 inversion.

---

## 2. Production route map (current state)

| Concern | Current |
|---|---|
| Input route | `/diligence/hcris-xray` (no query) → landing/workstation |
| Results route | `/diligence/hcris-xray?q=<name/ccn>&state=&fiscal_year=&peer_k=&bed_band_pct=` (same route renders the report) |
| Renderer file | `rcm_mc/ui/hcris_xray_page.py` (`render_hcris_xray_page`) |
| UI kit | `rcm_mc/ui/xray_kit.py` (`XRAY_CSS`, `xr_eyebrow`, `xr_crumb`, `xr_ribbon`, `xr_chip`, `xr_caveat`, `xr_source`, `xr_peer_band`, `xr_benchmark_table`) |
| Data engine | `rcm_mc/diligence/hcris_xray/` — `xray()`, `search_hospitals()`, `get_target_history()`, `dataset_summary()`, `catalog_by_category()`; dataclasses `HospitalMetrics`, `MetricBenchmark`, `PeerMatch`, `XRayReport` |
| Server route | `server.py::_route_hcris_xray_page` (single route; results keyed off `q`) |
| Guide context | `manual_page_contexts.py` → `/diligence/hcris-xray` ("HCRIS X-Ray") |

**Decision (routes):** keep the single `/diligence/hcris-xray` route. No-query =
input workstation; with `q` = results. Matches the handoff's
`/x-ray?ccn=…` intent without adding a route or breaking bookmarks. No
redirects needed.

---

## 3. Section inventory

### Input page (B · Workstation)
1. Breadcrumb `HOME / DILIGENCE / HCRIS X-RAY`
2. Eyebrow (green dash) + H1 `HCRIS X-Ray` (italic-green "X-Ray") + lede
3. **① Identify the hospital** card — name/CCN/city input · state filter · FY segmented control
4. **② Peer engine** card — peer pool · bed band ± · match-on
5. Action row — `▸ Run X-Ray` · `↓ Sample output` · live `~Xs · N peers expected` readout
6. **Right: live SAMPLE preview** — TARGET identity · 4-cell mini KPI grid · sample peer band · plain-English read
7. Dataset/source coverage line (`SOURCE: CMS HCRIS · N filings · N states · N FYs`)

### Results page (A v2 · Headline)
1. Breadcrumb + identity row (H1, classification subtitle, trend chip, Export/Print/→Deal MC)
2. **① Top finding** card (headline + 2 mini driver cards w/ box-plots)
3. **② 3-year margin trend** chart (target vs peer median)
4. **③ EBITDA gap · sized** waterfall
5. **④ Payer-mix** stacked bars (target vs peer median)
6. **⑤ Four deviation cards** (metric + box-plot + mini-trend)
7. **⑥ Full benchmark table** — 15 metrics × (target/P25/median/P75/band/3y/Δ%), section ribbon
8. **⑦ Peer roster** (top 6 of N)
9. **⑧ Public-comp context** table
10. Footer cross-references (pre-seeded links to Deal MC / Payer Stress / etc.)
11. Caveats / provenance + Guide suggested questions

---

## 4. Data-binding map — **the honesty contract**

Status legend: **REAL** (engine value) · **DERIVED** (computed from engine
values, server-side) · **ASSUMPTION** (needs a stated input, label it) ·
**SAMPLE-ONLY** (static demo, must be labeled, never in a real report) ·
**UNAVAILABLE** (no data source — show an honest "insufficient data" state,
never fabricate).

### Input page
| Value | Status | Source / note |
|---|---|---|
| Breadcrumb, title, lede, form labels | STATIC | UI copy |
| Hospital search / FY / peer-engine inputs | REAL (form state) | submitted to `xray()` |
| `~Xs · N peers expected` readout | DERIVED | optional debounced count; OK to show static "~Ns" until wired |
| Dataset coverage (`N filings · N states · N FYs`) | REAL | `dataset_summary()` |
| **Right preview card (Stroger · CCN 140124 · all values)** | **SAMPLE-ONLY** | static demo of output format — **must carry a visible "SAMPLE" tag; never rendered as a real target.** Already labeled in current code; keep. |

### Results page
| Section / value | Status | Source / note |
|---|---|---|
| Identity (name, CCN, county, state, beds, NPR, classification, FY) | REAL | `XRayReport.target` (`HospitalMetrics`) |
| Trend chip (improving/deteriorating) | REAL | `XRayReport.trend_signal` |
| Top finding headline + above/below counts | REAL | `XRayReport.headline`, `above/below/inside_peer_count` |
| Hero mini drivers (e.g. Medicaid day %, opex/pt-day) + Δ vs peer median | REAL/DERIVED | `MetricBenchmark` target vs median; Δ% derived server-side |
| 3-year margin trend (target line) | REAL | `get_target_history()` per-metric series |
| 3-year trend (peer-median line) | DERIVED | median of peer history if available; else show target-only + note |
| Payer-mix bars — **target** (Medicare/Medicaid/other-day %) | REAL | `medicare_day_pct`, `medicaid_day_pct`, `other_day_pct` |
| Payer-mix bars — **peer median** | DERIVED | median of peer day-mix; REAL inputs |
| Deviation cards (4 flagged metrics + box-plots + mini-trends) | REAL | `MetricBenchmark` + history |
| Full benchmark table (15 metrics × P25/median/P75/Δ%/band) | REAL | `XRayReport.metrics` (`xr_benchmark_table`) |
| 3Y sparkline column | REAL | `get_target_history()` per metric |
| Peer roster (CCN, name, beds, Medicaid %, op margin, distance) | REAL | `XRayReport.peers` (`PeerMatch`) + peer `HospitalMetrics` |
| **EBITDA gap — close-to-peer-median (pp + $)** | **DERIVED** | `(peer_median_op_margin − target_op_margin) × NPR` — all REAL inputs |
| **EBITDA EV (`~$595M EV @ 9.0× cap`)** | **ASSUMPTION** | cap multiple is an *input*, not engine data → render with an explicit, user-visible assumption (e.g. "@ 9.0× — assumption") or omit the EV line until wired to a deal assumption |
| **EBITDA "close gap to public comps" step (+$211M)** | **UNAVAILABLE** | needs public-comp margins (not in engine) → **omit this waterfall step** in v1 |
| **⑧ Public-comp context (HCA/THC/UHS/ARDT, EV/EBITDA)** | **REFERENCE (real) — CORRECTION** | Verified in code: public comps come from the vendored `market_intel.public_comps` module (real curated public-company op-margins + EV/EBITDA), NOT the handoff mock. The results page already renders them from this real source via `_public_comp_context`. Label RESEARCH REFERENCE; this supersedes the earlier "UNAVAILABLE" assumption. |
| Footer cross-ref pre-seeded EV/EBITDA/equity/debt | DERIVED/ASSUMPTION | links are real routes; seeded $ values depend on the cap-multiple assumption — label or omit |

**Net rule:** the report ships **identity, trend, payer mix, deviation cards,
full benchmark table, peer roster, and the peer-median EBITDA gap** as real /
derived. The **public-comp step + table** and the **cap-multiple EV** are
*not* real data — they degrade to honest "insufficient data / assumption"
states. No Stroger sample value ever appears in a real report.

---

## 5. Token map (handoff → PEdesk)

The handoff tokens already match `xray_kit.XRAY_CSS` (`--xr-*`) almost 1:1 —
this rebuild reuses the kit, it does not introduce a new token set.

| Handoff token | Hex | PEdesk / xray_kit token |
|---|---|---|
| `--page-bg` `#ede7d4` | page background | `--sc-parchment` (global canvas) |
| `--paper` `#faf6ec` | card surface | `--xr-paper` |
| `--paper-2` `#f3eddb` | subdued surface | `--xr-paper2` |
| `--paper-3` `#ebe3c8` | input bg | `--xr-paper3` |
| `--navy` `#0d2336` | ribbon header | `--xr-navy` |
| `--ink` `#15202b` | primary text | `--xr-ink` |
| `--ink-2` `#2a3a4a` | body text | `--xr-ink2` |
| `--muted` `#6a7480` | labels | `--xr-muted` |
| `--rule` `#c9c1ac` | borders | `--xr-rule` |
| `--green` / `--green-deep` | accent / CTA | `--xr-green` / `--xr-green-deep` |
| `--amber` `#b8842e` | warning | `--xr-amber` |
| `--red` `#b14a3a` | negative | `--xr-red` |
| Source Serif 4 / Public Sans / JetBrains Mono | type roles | `--xr-serif` / `--sc-sans` / `--xr-mono` |
| border-radius `0` | sharp corners | already enforced (XRAY_CSS has no radius) |

**No new fonts, no CDN.** The three families are already loaded by the shell.

---

## 6. Component map

`Status`: ✅ exists · 🔧 extend existing · ➕ new helper · 🟡 honest-degrade.

| Prototype section/component | Production helper/component | Data source | Status | Notes |
|---|---|---|---|---|
| Breadcrumb | `xr_crumb` | static | ✅ | |
| Eyebrow + H1 + lede | `xr_eyebrow` + `ck_page_title` | static | ✅ | |
| Ribbon section header | `xr_ribbon` | static | ✅ | |
| Identify / Peer-engine cards | `_xray_workstation` (rebuild to fidelity) | form state | 🔧 | already exists; refine markup/spacing |
| FY segmented control | existing `.xr-seg` | form state | ✅ | |
| Live `N peers expected` readout | small mono span (+ optional count endpoint) | DERIVED | 🔧 | static OK until wired |
| Right SAMPLE preview | `_xray_workstation` right card | SAMPLE-ONLY | ✅ | keep visible "SAMPLE" tag (`xr_chip`/`xr_caveat`) |
| `<BoxRow>` / `<FullBox>` box-plot | `xr_peer_band` | REAL | ✅ | reuse |
| `<TrendChart>` (2-line SVG) | `xr_trend_chart` | REAL/DERIVED | ➕ | new: target solid + peer-median dashed |
| `<RowSpark>` (table sparkline) | `xr_row_spark` | REAL | ➕ | new: per-metric 3y |
| `<PayerStack>` (stacked bars) | `xr_payer_stack` | REAL/DERIVED | ➕ | new: target vs peer median day-mix |
| `<EbitdaBridge>` (waterfall) | `xr_ebitda_bridge` | DERIVED (+ASSUMPTION) | ➕ + 🟡 | peer-median step real; drop public-comp step; EV line labeled assumption |
| `<DevCard>` (deviation tile) | `xr_dev_card` | REAL | ➕ | metric + box-plot + mini-trend |
| Full benchmark table | `xr_benchmark_table` (+ spark column) | REAL | 🔧 | extend with sparkline + section rows |
| Peer roster | `xr_peer_table` (or inline table) | REAL | ➕/🔧 | from `PeerMatch` |
| Public-comp context | honest empty state | UNAVAILABLE | 🟡 | "public comps not wired" — no fabricated tickers |
| Top-finding card | compose (`xr_*` + serif) | REAL | 🔧 | inverted-pyramid lead |
| Cross-reference footer | links list | real routes | 🔧 | seeded $ labeled/omitted |
| Guide suggested questions | `manual_page_contexts` | n/a | 🔧 | update context |

---

## 7. Implementation plan (PRs)

- **PR 1 — xray_kit additions + HCRIS input workstation to fidelity.** New
  helpers `xr_trend_chart`, `xr_row_spark`, `xr_payer_stack`, `xr_dev_card`,
  `xr_ebitda_bridge` (pure server-rendered SVG/HTML, scoped `.xr`, no CDN);
  rebuild `_xray_workstation` to handoff spec; keep the SAMPLE tag. Kit unit
  tests (render + escaping + missing-value handling).
- **PR 2 — HCRIS results A-v2 headline report.** Reorder/compose the results
  page into the inverted pyramid using the kit; wire identity, trend, payer
  mix, deviation cards, full benchmark table, peer roster from the engine;
  EBITDA gap (peer-median, real/derived); public comps + cap-multiple EV
  degrade honestly.
- **PR 3 — Guide/RAG interpretation + suggested questions.** Update the
  `/diligence/hcris-xray` context with the A-v2 sections, the
  real-vs-assumption framing, and questions ("what's the recoverable EBITDA
  and how is it derived?", "why are public comps unavailable?").
- **PR 4 (later) — CMS Provider X-Ray reuse.** Point the non-hospital X-Ray at
  the same kit + A-v2 grammar, with conditional sections for verticals lacking
  revenue / payer mix / EBITDA inputs.

Each PR: tests (presence **and** absence — no raw CSS in body, no SAMPLE value
in real reports), Guide context, approval before merge (visible UI).

---

## 8. Guardrails (carried from the contract)
- No fake/synthetic values · **no SAMPLE-only value (Stroger) in a real report**
  · public comps + cap-multiple EV degrade to honest "insufficient data /
  assumption", never fabricated.
- **No raw CSS in the page body** (the prior HCRIS bug) — CSS via `extra_css`
  / `<style>` only.
- No external React/Babel/CDN runtime scripts; reuse the loaded fonts.
- No auth/login, Caddy, systemd, deploy, env, secrets, Ollama/Tailscale, or RAG
  runtime changes. `#579/#580` parked.

---

## 9. Tests to add (per PR)
- HCRIS **input** route renders with **no raw CSS in the body** (strip
  `<style>`, assert no selectors leak) and the SAMPLE preview is labeled.
- HCRIS **results** route renders with no raw CSS; a known provider shows
  identity + 15-metric benchmark table + peer roster.
- **No SAMPLE-only value** (e.g. the Stroger preview numbers) appears in a real
  report for a different provider.
- Unavailable sections (public comps) render an honest "insufficient data"
  state — not fabricated tickers.
- Kit helpers: render expected classes, escape strings, handle missing values,
  no CDN refs.
- Guide context exists for `/diligence/hcris-xray`; `/login` + auth unaffected.

---

## 10. Open questions for review
1. **EV / cap-multiple:** show "+$X recoverable EBITDA @ N× (assumption)" with
   a visible assumption tag, or omit the EV line until wired to a deal's cap
   assumption? (Map assumes: show the $ gap as real/derived; label or omit EV.)
2. **Public comps:** honest empty state in v1 (recommended), or defer the whole
   ⑧ section until a public-comp data source exists?
3. **Peer-median trend line:** compute from peer history if present, else
   target-only with a note — acceptable?

Pending review of this map, PR 1 (kit + input) proceeds first.

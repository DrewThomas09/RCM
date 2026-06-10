# ARCHITECTURE — running design notes (session 2026-06-10)

## Data registry & provenance spine (as found)
- HCRIS: rcm_mc/data/hcris.py → `_get_latest_per_ccn()` (6,123 hospitals,
  latest authoritative filing per CCN; coordinate map verified vs 7 systems).
- Source→URL provenance: `rcm_mc/ui/_chartis_kit.SOURCE_URLS` + ck_source_link.
- Plausibility bands: `rcm_mc/core/margins.py` (margin −40…+30%, occupancy ≤105%).
- Gap registry: `rcm_mc/data/gap_fill_registry.py` (+ `rcm-mc data gaps`).
- Prediction bounds: `rcm_mc/ml/prediction_bounds.py`.
- Basis badges: ACTUAL / PREDICTED / ENTERED via `ck_basis_badge`.

## P2 — CIM Cross-Check / Variance Engine (this session)
**Spec.** A consultant enters management's CIM claims for a hospital target /
market; the engine computes independent public-data estimates for each claim
from the HCRIS universe scoped to (state [, bed band] [, target CCN]) and
renders a variance table: claim | independent estimate (value, n, source,
method, drill link) | variance % | flag (green ≤10%, yellow ≤25%, red >25%,
grey UNVERIFIABLE when the public side is a gap). One-click variance memo
(text) + CSV export listing claim / estimate / variance / source / suggested
expert-call question. Claims are ENTERED; estimates are ACTUAL with
source links. Claim types in slice 1 (hospital subsector):
- market_size_dollars  → Σ net_patient_revenue in scope (state patient-revenue base)
- provider_count       → count of HCRIS hospitals in scope
- median_operating_margin_pct → median margin in scope (plausible band only)
- medicare_share_pct / medicaid_share_pct → median day-share in scope (NaN-aware)
- inpatient_days       → Σ total_patient_days in scope
- target_net_revenue_dollars → the target CCN's own filed NPR (CIM top line vs filing)
**Module layout.** Pure logic in `rcm_mc/diligence/cim_crosscheck.py`
(estimators + variance + memo text, fully unit-testable, no UI imports);
page in `rcm_mc/ui/cim_crosscheck_page.py` (GET form → table → exports);
route `/diligence/cim-crosscheck` + palette + Diligence sub-nav.
**Honesty rules.** Estimates name n and vintage; margin medians use the core
plausible band; unverifiable ≠ zero; the engine never fabricates an estimate
when scope is empty. Variance against a Σ-claim uses the same scope the
consultant chose — scope is printed on the table header.

## Deploy/verify loop (canonical)
main merge → deploy.yml (test gate → SSH droplet → restart pedesk.service →
public pedesk.app/healthz + guide-health) → sandbox verification = deploy-run
conclusion + local playwright screenshots + route_walker markers on the same
SHA (sandbox egress cannot reach pedesk.app — DECISIONS.md #1).

## P7 — Roll-Up Scenario Builder (this session)
**Spec.** PE thesis-testing motion: pick N real HCRIS hospitals (CCNs) →
pro-forma combined view: aggregate beds / inpatient days / NPR (filed,
labeled), blended payer-day mix (day-weighted, NaN-aware), state market share
before/after on NPR, state HHI before/after with Δ (note when post-HHI>2500
or Δ>200 — the DOJ/FTC screening zone), per-facility table, overlap note when
facilities share a state (county granularity backlogged — HCRIS lacks
reliable county for all rows). Synergy toggles (G&A % of combined opex)
clearly labeled USER ASSUMPTION, default off. Exports: scenario CSV.
**Module layout.** Pure logic `rcm_mc/pe/rollup_scenario.py` (combine math +
HHI before/after, unit-testable); page `rcm_mc/ui/rollup_builder_page.py` at
/pipeline/rollup; route + Pipeline sub-nav + palette. Entry points: CCNs via
comma list (?ccns=) — the screener's compare basket already produces such
lists, so a "Roll-up these" link from the screener compare view comes free.
**Honesty.** All facility figures are filed HCRIS values (ACTUAL); the
combined column is arithmetic on filings (DERIVED, labeled); synergies are
ENTERED assumptions; HHI uses NPR shares within the chosen state market and
says so (a state is a coarse antitrust market — labeled as screening proxy,
not a relevant-market analysis).

## P4 — Peer-percentile chip (this session, slice 1)
**Spec.** One reusable primitive `ck_peer_percentile(value, dist, *, peer_label,
higher_is_better=None, unit_fmt=None)` → "p78 vs TX hospitals (n=412)" with a
60px position track. Percentile = share of peers strictly below + half of
ties (standard percentile rank), NaN peers excluded. Honesty: n<8 renders
"peer set too small (n=K)" instead of a percentile; value None/NaN renders
nothing. Color tones by higher_is_better when given, neutral otherwise.
Consumers slice 1: deal quick-view profile KPIs vs the portfolio's other
deals (user 3's daily question: where does this deal sit vs the book).
X-Ray already has its own band component (left as-is).

## P11 — Data Quality dashboard (this session, slice 1)
**Spec.** /data-quality — the 60-second internal certification screen:
(1) live-computed table per wired source: rows, key-field null rates,
vintage + honest staleness vs the source's OWN cadence (HCRIS cost reports
run ~18mo behind FY end — green within that, not "stale" by naive age);
(2) gap census reusing data/gap_fill_registry.gap_report (counts + fill-kind
chips, RE-INGEST/EXTERNAL/ARTIFACT); (3) consumer map per source (which
pages read it — maintained next to the loaders' registry entries);
(4) registered-but-not-wired sources from data/vendor/source_registry.csv
with their vintages. All numbers computed at render from the same loaders
the product uses — the dashboard can't drift from reality.

## P1 — Deal Workspace slice 1: active-deal context (this session)
**Design.** The deal becomes ambient context without threading a parameter
through 100+ chartis_shell call sites: activation endpoint
`/deal-context?set=<deal_id>&return=<path>` resolves the deal's profile
(name + state + ccn when present), writes two cookies —
`pedesk_active_deal` (id) and `pedesk_active_deal_meta` (URL-encoded JSON
{id,name,state,ccn}) — and 303s back. A small shell JS shim (house-approved
vanilla pattern) reads the cookies on every page and renders a slim
active-deal bar under the topbar: deal name → deal home, plus PRE-SCOPED
module links built from the meta (screener ?state=, HCRIS X-Ray ?ccn=,
CIM cross-check ?state=&ccn=, roll-up). `?set=` with empty value clears.
Cookie-only UI state (no server data mutation) → GET+303 is acceptable
(same class as the existing ?limit= prefs); logged in DECISIONS.md.
Deal quick-view + workbench get "Set active deal" affordances.
Slice 2 (later): modules read the cookie server-side to default their forms.

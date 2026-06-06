# UI Improvement Plan — grounded review (2026-06)

How this was assessed: rendered the live surfaces logged-in against a
seeded demo portfolio (`demo.seed` + the real server on a free port,
driven with headless Chromium) and read the page renderers. Findings
are tied to what the pages actually show, not theory. Severity is
P0 (most visible / highest payoff) → P2 (nice-to-have). Effort is S/M/L.

---

## 0. What is already strong — leave it alone

- The **editorial Chartis system** (parchment, Source Serif display,
  Inter labels, JetBrains mono numerics, hairline rules, one teal
  accent) is coherent and calm across every in-app page.
- **Real, cited data** everywhere (HCRIS, CMS, the deal store). No
  fabricated-metric grids in the app.
- The **marketing landing** was rewritten this branch (fake "proof" →
  real capability catalog, flat styling, honest sample labels).
- The **em-dash / title-separator cleanup** already landed app-wide.

The opportunities below are about **density, empty states, hierarchy,
and first-run feel** — not slop removal, which is done.

---

## 1. Cross-cutting themes (fix once, helps many pages)

### T1 — Empty-state quality on a data-light portfolio  ·  **P0 · M**
The single biggest "unfinished" feeling. On a freshly-seeded portfolio
the **Command Center** (`/app`) stacks 6+ half-empty panels:
"No initiatives tracked yet", "No initiative actuals recorded…",
"No deliverables generated yet", covenant heatmap "Select a deal…",
EBITDA-drag "Select a deal above…". Each empty panel still reserves
full height, so the most important page in the product reads sparse and
top-heavy with grey boxes.

Fixes:
- Give `ck_empty_state` a **compact variant** (one line + one action),
  and use it in dashboard panels so an empty panel is ~80px, not ~240px.
- For panels that need a **row selection** (covenant heatmap, EBITDA
  drag), default to the **first/worst deal** instead of an instructional
  blank, so the panel is populated on load and the click just re-targets.
- Where a panel is empty because a feature hasn't been used yet
  (initiatives, deliverables), make the empty state **show the value +
  a real CTA** ("Track an initiative →") rather than a dead sentence.

### T2 — "—" placeholder tiles before data loads  ·  **P1 · S**
Deal Profile (`/diligence/deal/<slug>`) opens with the market-context
tiles all showing "—" (target multiple, peer median, delta, closest
peers) until the JS hydrates / data exists. On a deal with no market
pull, the whole top band is dashes.

Fix: render these tiles in a **skeleton/"not yet computed" state** with
a one-click "Run market read" affordance, not bare em-dash glyphs that
look like missing data.

### T3 — KPI strip evenness  ·  **P1 · S**
The top KPI row on `/app` mixes a big serif number card (Weighted MOIC
2.50x), a percent card (IRR 20.0%), a small count ("2 of 5"), and a card
with an inline date-range dropdown. The cards are visually uneven —
different value sizes and one has a control in it.

Fix: standardise the KPI card to value + label + sub (+ optional trend);
move the date-range control out of the card into the section header.

### T4 — Page length / "scroll tax" on landing surfaces  ·  **P1 · M**
`/app` and the Deal Profile are very tall (every panel always rendered,
full height). A partner scrolls a lot to reach alerts/variance.

Fixes:
- Two-column the dashboard mid-section panels that are currently full
  width and short (covenant heatmap + EBITDA drag are already 2-col;
  extend to initiative-variance + deliverables).
- Add a thin **in-page jump rail** (Brief · Working deals · Alerts ·
  Variance · Deliverables) so the page is navigable without scrolling.

### T5 — Dense-table ergonomics  ·  **P2 · M**
Target Screener / HCRIS tables render the full result set (hundreds of
rows) in one scroll with no sticky header. Useful but heavy.

Fixes: sticky `<thead>`, a result count + "showing N of M", and
client-side top-N truncation with "show all". (Filters already exist
at top — keep them.)

---

## 2. Page-by-page

### 2.1 Command Center `/app`  ·  **P0**
*Strong bones (morning brief, pipeline funnel, alerts, quick access),
let down by empty panels on a fresh portfolio.*
- Apply T1 (compact empties + default-deal selection) and T4 (2-col +
  jump rail). **This is the highest-leverage page** — it's what a
  partner opens every morning and what a demo opens first.
- "Quick access" tiles are good; the single dark "All surfaces" tile is
  a nice accent — keep.
- Headline "Command center." + lede is concrete — keep.

### 2.2 Deal Profile `/diligence/deal/<slug>`  ·  **P1**
*The analytic catalog (tools grouped by lifecycle phase) is the strong
part and reads well.*
- Apply T2 (market tiles skeleton).
- The page leads with a slug form + market tiles before the catalog;
  consider leading with the **catalog** (the reason you're here) and
  demoting the slug form to a compact header control.
- Long page — a phase jump-rail (Pre-NDA · Diligence · Financial ·
  Exports) would help.

### 2.3 Target Screener `/target-screener`  ·  **P2**
*Map + dense provider table on real HCRIS data — substantive.*
- Apply T5 (sticky header, result count, top-N).
- The choropleth + table pairing is good; add a one-line read of what
  the map encodes above it (currently the legend does the work).

### 2.4 Research hub `/research`  ·  **P2**
- Section blurbs were tightened this branch; the hub is concrete.
- Low priority — mostly a launcher.

### 2.5 Marketing `/` — **DONE this branch.** Listed for completeness.

---

## 3. Micro-polish backlog (each S, batchable)
- Dashboard panel headers: the mono "code" chips (FNL/ALR/HLT/…) read as
  developer noise to a partner — consider dropping or making them a
  muted hover-only affordance.
- Several explainer paragraphs are **dry layout enumerations** ("Seven-
  panel partner landing: pipeline funnel, active alerts, …") — rewrite
  to say what the partner *gets*, not what panels exist.
- Confirm KPI/number formatting matches the house rules (2dp money,
  1dp percent, 2dp×) on the dashboard strip.
- Login page: heavy card drop-shadow + radial body wash are slightly off
  the flat editorial system — soften to a hairline card (low priority;
  test-pinned, so do carefully).

---

## 4. Suggested execution order
1. **T1 empty states + T3 KPI strip on `/app`** (P0, one focused PR).
2. **T4 two-column + jump rail on `/app`** (P0/P1).
3. **T2 market-tile skeletons + catalog-first on Deal Profile** (P1).
4. **T5 table ergonomics** (P2) + the micro-polish backlog (P2).

Each is independently shippable and testable; none requires new runtime
deps or schema changes. The dashboard items (1–2) are the ones a partner
and a demo viewer feel immediately.

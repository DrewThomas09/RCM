# Target Screener — the 6-screen Source workbench

How the `/target-screener` page works as the unified Source workflow, so the
Guide can answer "where do I start hunting for deals", "how do I filter by
state", "what's the difference between the six screens", and "how do I share
a screen state".

## What it is

The Target Screener is the front-end of the **Source workflow**:

```
Source  →  Target Screener  →  evaluate  →  compare  →  just-missed scan
        →  save screen  →  open profile / X-Ray  →  promote to Pipeline
```

It's a 6-screen workbench — every screen operates over the same public
CMS / provider universes (this is **market data**, not your deals). The
historical realized-deal corpus is never an active target universe; only a
labelled benchmark/research reference.

## The 6 screens (URL: `?view=...`)

| # | Key | Label | Purpose |
|---|-----|-------|---------|
| 01 | `main` | Main | Universe selector + map + ranked-provider table |
| 02 | `inspector` | Inspector | One CCN drawer: peer set + market + history |
| 03 | `columns` | Columns | Column picker / metric dictionary |
| 04 | `compare` | Compare | Side-by-side metric-by-metric of staged providers |
| 05 | `missed` | Just missed | Providers narrowly outside the current filter |
| 06 | `saved` | Saved screens | Persisted query state (shareable URLs) |

Screens 1-3 are **workbench states** of the same data (toggle without
losing state). Screens 4-6 are **linked screens** that take a richer
follow-up action.

## The 9 universes (URL: `?vertical=...`)

Every universe is a real CMS / provider dataset:

- `hospitals` (HCRIS), `home_health` (CMS HHA), `hospice` (CMS Hospice),
- `snf` (CMS SNF), `dialysis` (CMS Dialysis), `irf` (CMS IRF),
  `ltch` (CMS LTCH),
- `provider_supply` (NPPES / supply), `market` (geographic).

Each chip on the universe selector now carries a real provider-count
badge so partners can compare scale across universes at a glance.

## The Main screen anatomy

```
┌─ Title + source-purpose strip ─┐
├─ Workbench tabs (01-06, sticky)
├─ Choose a universe & entry point  ← one merged panel with 4 sub-blocks:
│    UNIVERSE          (9 chips with real counts)
│    ACTIVE SCREEN     (KPIs + active-filter chip strip)
│    ENTRY POINTS      (3 mode cards: Thesis Sourcing / Hospital Screener
│                       / Predictive Screener)
│    MAP LAYER         (Provider count / Age 65+ / Income / Uninsured % …)
├─ Provider density · click a state to filter (map panel)
├─ Ranked providers · X-Ray / Inspect / +Cmp (table panel)
└─ Screen the market, then the target · next steps (A/B/C action list)
```

## URL is the state

Every refinement encodes into the query string so the **URL IS the
bookmark**. Sharing a target-screener view means copying the URL — the
share-link button at the top of the Active-screen sub-block does this in
one click. Parameters:

- `view=` (which workbench screen)
- `vertical=` (which universe)
- `state=` (state-code filter — set by clicking the map)
- `layer=` (which map shading layer)
- `sort=` + `direction=` (table sort)
- `limit=` (Top-N row cap: 10 / 25 / 50 / 100 / 150)
- `min_quality=`, `min_size=`, `ownership=` (refine filters)
- `hide=` (column visibility list)
- `compare=` (CCN-list bucket for the Compare screen)

Stale or hostile `?limit=9999` silently falls back to 150 so a partner
never accidentally renders the full universe.

## Active filter chip strip

Every non-default param renders as a removable chip in the Active-screen
sub-block. Each chip is a one-click "remove this filter" link; "Reset to
defaults" appears whenever any chip is active. Sort chip shows the
direction arrow (↑/↓) and the readable column name ("Provider name ↑").

## Table features

The ranked-providers table has:
- Top-N row toggle (10 / 25 / 50 / 100 / 150) above the table
- Client-side instant search input on the toolbar — type any name / CCN
  / city / state; rows hide in real time. Use `/` to focus from anywhere
  on the page, ESC to clear.
- Column-header click to sort (asc/desc); active column reads navy + teal-
  deep + ↓/↑ glyph; the "Showing X of Y" status line names the sort
  ("sorted by Provider name (ascending)") and offers a `reset sort` link.
- Collapsible Refine filters in a `<details>` that auto-opens when any
  filter is active.
- Per-row action chips: **X-Ray** (jump to /diligence/xray), **Inspect**
  (jump to /target-screener?view=inspector), **+Cmp** (add to compare
  basket).
- Compare-basket banner above the table when the basket is non-empty:
  shows the count of staged providers, "View comparison →", "Clear
  basket".

## Map features

Sticky map shows provider density by state, color-encoded by the active
layer. Click any state to filter the screen to it; the state-filter
banner below the map shows full state name (e.g. "TX · Texas"), the
in-state provider count, and a chip-styled clear link.

## What it is NOT

- Not a deal screening surface — operates on the public universe only.
- Not a comparable-transactions search (that's `/find-comps`).
- Not a deal valuation engine (that's `/diligence/deal` and downstream).

## Related surfaces

- `/source` — Thesis Sourcing entry point (mode card 1).
- `/screen` — Hospital Screener entry point (mode card 2).
- `/predictive-screener` — Predictive Screener entry point (mode card 3).
- `/diligence/hcris-xray` — what the X-Ray row action opens.
- `/find-comps` — for realized-deal comparable searches (different
  universe).
- `/pipeline` — where promoted candidates land.

# PEdesk interactive maps

PEdesk renders geographic data **locally** — inline SVG, no external map
tiles, no Mapbox/Google Maps, no CDN, no runtime network. This keeps the
Mac-hosted, offline-capable, single-tenant setup private and dependency-free.

## Current: Phase 1 — US state tile-grid cartogram

`rcm_mc/ui/us_map.py :: render_us_state_map(...)` is the reusable renderer.

It draws a **state tile-grid** — every state + DC is an equal-size cell in
its approximate geographic position, shaded by a per-state metric, with:
- hover tooltip (state name + metric; never color-only)
- click selection (emits a `us-map-select` event; fills any
  `[data-us-map-selected]` element)
- a metric legend + accent outlines (e.g. CON states) + a "no data" swatch
- an honest empty state (the map still draws; absent states show "no data",
  never invented values)

**Why a tile grid, not boundary outlines:** it needs no geometry asset
(fully local + tiny), is equal-area so large states don't dominate a metric
read, and never fabricates coastlines. It is a *metric map*, not a
coastline map.

First integration: **`/portfolio/map`** — states shaded by portfolio deal
count, CON jurisdictions outlined in amber.

## Future phases (hooks — not yet built)

These need data and/or assets that don't exist in-repo yet. Build in order:

### Phase 2 — real boundary choropleth (optional upgrade)
Vendor a **simplified** `us-states` GeoJSON/TopoJSON (~60–100 KB) into a
static asset path (e.g. `rcm_mc/ui/assets/`), public-domain source (US
Census cartographic boundary files / Natural Earth). Add a
`render_us_state_choropleth(...)` alongside the tile grid; pages opt in.
Still local — the asset ships in the repo, no runtime fetch.

### Phase 3 — state → county drilldown
Requires county geometry (Census county boundaries) **and** county-level
data keyed by 5-digit county FIPS. Selecting a state loads its counties.

### Phase 4 — hospital / facility point overlay
Requires per-facility latitude/longitude (or a CCN→lat/lon lookup). HCRIS
has provider CCNs; a CCN→coordinate table would let us plot hospital points.
`rcm_mc/data/geo_lookup.py` currently has only **state-capital centroids**,
not facility coordinates — do **not** claim hospital locations until real
coordinates exist.

### Phase 5 — market-intelligence + table↔map brushing
MSA/CBSA overlays; clicking a state/county filters the page's tables and
side panels (and vice-versa).

## Pages that should eventually use the map

`/portfolio/map` (done) · `/market-intel` · `/market-data/state/<state>` ·
`/payer-intelligence` · `/diligence/hcris-xray` · `/screen` ·
`/rcm-benchmarks` · `/comparables` · `/portfolio/risk-scan`.

Wire them one at a time, each with state-level data it actually has — never
default a page to the map if it has no geographic data to show.

## Guardrails

- No external map APIs / tiles / CDNs. Local SVG only.
- No invented geography — states/counties/facilities render only from real
  data; absent data shows an honest "no data" / empty state.
- Accessibility: SVG + cells carry `role="img"` + `aria-label`/`<title>`;
  hover info is text, not color-only; legends explain shading.

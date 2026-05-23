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

### Integrations (Phase 1 + 1B)

| Route | Status | Metric shaded |
|-------|--------|---------------|
| `/portfolio/map` | ✅ wired | portfolio deal count per state (CON states accented) |
| `/market-data/map` | ✅ wired | selected HCRIS metric per state (margin / HHI / hospitals / NPR / Medicare %), above the existing heatmap table |
| `/market-intel` | ⛔ not wired | no state-level data on the page (don't fabricate geography) |
| `/payer-intelligence` | ⛔ not wired | no state-level payer data on the page |
| `/rcm-benchmarks` | ⛔ not wired | benchmarks are by facility type / segment, not by state |
| `/market-data/state/<ST>` | future | single-state detail; a map would just highlight one state — low value until county/facility overlays exist |

Rule: wire the map only where a page already has state-keyed data. Pages
without it keep their tables unchanged — no forced/empty map.

`/market-data/map` cells now **drill down**: clicking a state navigates to
`/market-data/state/<ST>` (its hospital detail), which links back to the
national view. Enabled by the renderer's `state_link_template` option.

## Geography data audit

What geographic keys each candidate route actually has, and the honest map
type it can support today.

| Route | Geography present | Best map type | Status |
|-------|-------------------|---------------|--------|
| `/portfolio/map` | deal `state` | state_tile_grid | ✅ wired |
| `/market-data/map` | HCRIS per-`state` aggregates | state_tile_grid (+ drilldown) | ✅ wired |
| `/market-data/state/<ST>` | single state + hospital list (CCN/name/city/county/zip) | single_state_summary | ✅ already has hospital list + national back-link |
| `/diligence/hcris-xray` | one target hospital + peers (`state`, "same-state" flag) | not_applicable | single-target, no multi-state aggregate |
| `/market-intel` | none | not_applicable | no state key |
| `/payer-intelligence` | none | not_applicable | payer data not keyed by state |
| `/rcm-benchmarks` | facility-type/segment bands | not_applicable | no state dimension |
| `/screen` · `/deal-screening` | hospital rows incl. `state` | state_tile_grid_future | possible later (counts by state) |
| `/portfolio/risk-scan` · `/portfolio/monitor` | no per-item `state` today | not_applicable | needs state on portfolio items |
| county view (any) | HCRIS `county` **name** only | county_drilldown_future | **blocked**: no county FIPS + no county geometry asset |
| hospital points (any) | HCRIS CCN/name/city/state/zip/county | hospital_points_future | **blocked**: no lat/lon (and no ZIP/CCN→lat-lon lookup) |

### Concrete data gaps (what unlocks the next phases)

- **Boundary choropleth (Phase 2):** vendor a local `us-states`
  GeoJSON/TopoJSON asset (see below). Nothing else missing.
- **County map:** HCRIS carries a `county` *name* + `state`, but **no county
  FIPS** and there is **no county geometry asset**. Need both: a
  county-name/state → FIPS mapping *and* a simplified county boundary asset.
- **Hospital points:** HCRIS has CCN, name, city, state, zip, county — but
  **no latitude/longitude**. Need either per-facility lat/lon, or a
  ZIP-centroid / CCN→lat-lon lookup table (with provenance). Until then a
  hospital-location map would be fabricated and must not be built.
- **MSA/CBSA region map:** no MSA/CBSA identifiers on these pages today.

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

# PEdesk interactive maps

PEdesk renders geographic data **locally** — inline SVG, no external map
tiles, no Mapbox/Google Maps, no CDN, no runtime network. This keeps the
Mac-hosted, offline-capable, single-tenant setup private and dependency-free.

## Current: Phase 2 — real US geographic map (Albers boundary choropleth)

`rcm_mc/ui/us_geo_map.py :: render_us_geo_map(...)` is the reusable renderer,
shading **real US state boundaries** (Albers Equal-Area Conic projection of US
Census cartographic boundaries, vendored offline in `rcm_mc/ui/_us_geo_paths.py`
— public domain, no runtime network). Alaska & Hawaii are scaled bottom-left
insets. It is a drop-in replacement for the old tile grid (same
`us-map-select` event, same `state_link_template` drilldown), with:
- hover tooltip (state name + metric; never color-only)
- click-through navigation when a `state_link_template` is set; otherwise
  click selection (emits `us-map-select`; fills any `[data-us-map-selected]`)
- a metric legend + an honest "no data" swatch
- an honest empty state (the map still draws; absent states show "no data",
  never invented values) + an honest projection caveat line

**Superseded:** the Phase-1 **state tile-grid cartogram**
(`rcm_mc/ui/us_map.py :: render_us_state_map(...)`) — equal-size cells in
approximate geographic position. It still exists as a fallback renderer but no
page calls it; every choropleth surface was migrated to the real geographic map
(#1019). The point-overlay helper `render_state_hospital_points(...)` in the
same module is unrelated and still in use (real lat/lon scatter — see below).

### Integrations (live)

| Route | Status | Metric shaded |
|-------|--------|---------------|
| `/portfolio/map` | ✅ wired | portfolio deal count per state (CON states accented) |
| `/market-data/map` | ✅ wired | selected HCRIS metric per state (margin / HHI / hospitals / NPR / Medicare %), above the existing heatmap table |
| `/geo-map` | ✅ wired | any shared-registry metric across all 50 states + DC, drilldown to State Profile |
| `/sector-screener` · `/target-screener` | ✅ wired | universe/sector geographic distribution |
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
| `/portfolio/map` | deal `state` | state_geo_map (real Albers) | ✅ wired |
| `/market-data/map` | HCRIS per-`state` aggregates | state_geo_map (+ drilldown) | ✅ wired |
| `/market-data/state/<ST>` | single state + hospital list (CCN/name/city/county/zip) | single_state_summary | ✅ already has hospital list + national back-link |
| `/diligence/hcris-xray` | one target hospital + peers (`state`, "same-state" flag) | not_applicable | single-target, no multi-state aggregate |
| `/market-intel` | none | not_applicable | no state key |
| `/payer-intelligence` | none | not_applicable | payer data not keyed by state |
| `/rcm-benchmarks` | facility-type/segment bands | not_applicable | no state dimension |
| `/screen` · `/deal-screening` | hospital rows incl. `state` | state_geo_map_future | possible later (counts by state) |
| `/portfolio/risk-scan` · `/portfolio/monitor` | no per-item `state` today | not_applicable | needs state on portfolio items |
| county view (any) | HCRIS `county` **name** only | county_drilldown_future | **blocked**: no county FIPS + no county geometry asset |
| hospital points (any) | HCRIS CCN/name/city/state/zip/county | hospital_points_future | **blocked**: no lat/lon (and no ZIP/CCN→lat-lon lookup) |

### Concrete data gaps (what unlocks the next phases)

- **Boundary choropleth (Phase 2):** ✅ **SHIPPED** (#1019). The simplified
  Albers-projected `us-states` paths are vendored in
  `rcm_mc/ui/_us_geo_paths.py` and rendered by `render_us_geo_map`; every
  choropleth page now uses the real geographic map.
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

### Phase 2 — real boundary choropleth ✅ SHIPPED (#1019)
Done. A simplified, Albers-projected `us-states` path set is vendored in
`rcm_mc/ui/_us_geo_paths.py` (public-domain US Census cartographic boundaries,
generated offline by `tools/build_us_geo_paths.py`). `render_us_geo_map(...)`
renders it as a drop-in replacement for the tile grid, and every choropleth
page was migrated to it. Still 100% local — the paths ship in the repo, no
runtime fetch.

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

## Hospital geography status

**UPDATE 2026-05-23 — hospital point maps are now BUILT.** A local
CCN→lat/lon crosswalk was created by a **one-time, offline** batch geocode
of public CMS *Hospital General Information* addresses through the free US
Census Geocoder (`Public_AR_Current`). The app reads only the vendored file
`rcm_mc/data/hospital_coords.csv` (loader `rcm_mc/data/hospital_coords.py`)
— **no runtime geocoding, no external calls, never private/deal data.**

- Coverage: **4,630 of 5,432 CMS hospitals geocoded (85.2%)** — 3,681
  exact + 949 approximate street matches. The 802 that didn't geocode are
  **absent from the file** and get **no point** (never a fabricated or
  state-centroid location).
- Columns: `ccn, facility_name, address, city, state, zip, county, lat, lon,
  match_quality, source, source_date` — provenance on every row.
- Rendered by `render_state_hospital_points(...)` in `ui/us_map.py`
  (local lat/lon→SVG projection), wired into **`/market-data/state/<ST>`**:
  the state's HCRIS hospitals are joined to the crosswalk by CCN; geocoded
  ones are plotted with an honest "N geocoded of M" note + source line;
  the rest stay in the table, unplotted. Approximate (`Non_Exact`) matches
  are visually distinguished and labeled.
- **Rule still in force:** no live geocoding at render time, no
  browser-to-geocoder calls, no ZIP/state/county-centroid substitution
  presented as a real location.

### Original discovery (why this needed sourcing)

Verified against the actual source files, the raw data had **no
coordinates** — which is why the offline crosswalk above was necessary:

| Source | file | CCN | name | address/city | state | ZIP | county | lat/lon |
|--------|------|-----|------|--------------|-------|-----|--------|---------|
| HCRIS (6,123 hospitals) | `data/hcris.py` | ✅ | ✅ | city ✅ | ✅ | ✅ | ✅ (name) | ❌ |
| CMS Hospital General Info | `data/general_sample.csv` (25-row sample; loader `data/cms_hospital_general.py`, override `RCM_MC_GENERAL_CSV`) | ✅ (`Facility ID`) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| CMS Provider of Services | `data/cms_pos.py` | ✅ | ✅ | city ✅ | ✅ | ✅ | ❌ | ❌ |
| `data/geo_lookup.py` | — | — | — | — | ✅ | — | — | **state-capital centroids only (50)** |

The bundled CMS General Info sample columns are: `Facility ID, Facility
Name, State, Hospital Type, Hospital Ownership, Emergency Services` + 5
rating columns — **no coordinate column**, and the loader's candidate-column
lists don't even anticipate one (it would be dropped if present).

**Why state-capital centroids are NOT acceptable for hospital points:**
`geo_lookup.STATE_CENTROIDS` is 50 state capitals; `city_state_to_latlon()`
returns the *state* centroid for any city ("±50 miles error acceptable").
`system_network.py` already plots hospitals at these — so every hospital in
a state lands on one point. That's fine for coarse system-proximity math,
but as a *map* it would stack all of a state's hospitals on the capital —
misleading. Do not present it as hospital locations.

**What unlocks real hospital maps:** a vendored coordinate source keyed to
CCN, ideally `CCN | facility_name | address | city | state | zip | county |
lat | lon | source | source_date`. Either (a) a fuller CMS export that
actually carries geocoded lat/lon (the bundled sample does not; a real
`RCM_MC_GENERAL_CSV` would need verification), or (b) a CCN→lat/lon
crosswalk file committed to the repo. Then a small loader upgrade + a
`render_hospital_points(...)` renderer.

**What unlocks *approximate* hospital maps:** HCRIS + POS already carry ZIP.
A vendored ZIP→lat/lon centroid table (~42k rows, public domain) gives
ZIP-centroid points — acceptable **only if labeled "approximate (ZIP
centroid), not actual facility location."**

**Rule:** do not render hospital points unless the coordinate source is
explicit and labeled. No live geocoding, no silent ZIP/county/state-centroid
substitution presented as real locations.

## Guardrails

- No external map APIs / tiles / CDNs. Local SVG only.
- No invented geography — states/counties/facilities render only from real
  data; absent data shows an honest "no data" / empty state.
- Accessibility: SVG + cells carry `role="img"` + `aria-label`/`<title>`;
  hover info is text, not color-only; legends explain shading.

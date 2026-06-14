# Spatial Competition (Huff Gravity + Moran's I)

**In one sentence**: estimates patient-capture probability by attractiveness and distance — the rigorous service area, not a radius circle — and tests whether utilization actually clusters in space.

---

## What problem does this solve?

A radius circle around a facility is a lie: it ignores that patients flow to bigger, closer, more attractive competitors, and that a competitor across the street guts your capture. TAM and white-space maps drawn as circles overstate reach and miss competitive overlap.

Partners ask:
- *"What's this facility's realistic catchment given who else is nearby?"*
- *"How much volume does a new competitor down the road actually take?"*
- *"Is utilization genuinely clustered (a real catchment) or just noise?"*

---

## How it works

1. **Huff gravity model** (`huff_capture`) — for each demand point (population centroid), P(choose facility j) ∝ `attractiveness_j / distance_ij^β`, normalized across all competitors. Expected capture for j is the demand-weighted sum. `β` tunes distance decay (higher = patients stick closer). Distances via **haversine** — no geo dependency.
2. **Moran's I** (`morans_i`) — global spatial autocorrelation of a variable (utilization, cost) over locations, with inverse-distance row-standardized weights, a normal-approximation z/p, and a **CLUSTERED / DISPERSED / RANDOM** verdict.

## The demo moment

```python
from rcm_mc.diligence.spatial import DemandPoint, Facility, huff_capture, morans_i

res = huff_capture(
    demand_points=[DemandPoint("z1", 40.0, -75.0, 5000)],
    facilities=[Facility("target", 40.05, -75.0, 200),
                Facility("competitor", 41.0, -75.0, 50)],
    beta=2.0, target_facility_id="target",
)
print(res.headline)   # target's share, leader, total demand

m = morans_i(lats, lons, utilization)
print(m.headline)     # "Moran's I = 0.42 ... utilization is spatially clustered."
```

---

## Where it plugs in

- **Market sizing / white-space** — replaces radius-circle TAM with capture-probability surfaces.
- **Competitive overlap** — re-run `huff_capture` with/without a competitor to size volume at risk.
- **Provenance graph** — outputs carry `source_module="diligence.spatial"` and `citation_key="SP1"`.

## Files

```
spatial/
├── __init__.py
└── competition.py    # haversine_km / huff_capture / morans_i
```

## Honesty about the method

- **Straight-line distance**, not drive time — drive-time isochrones need a routing engine (an optional geo extra); raise `β` to proxy travel friction.
- **Attractiveness is your proxy** (beds, providers, service breadth) — an explicit input, so the model is only as good as it.

## Tests

```bash
python -m pytest tests/test_spatial.py -q
# Expected: 12 passed
```

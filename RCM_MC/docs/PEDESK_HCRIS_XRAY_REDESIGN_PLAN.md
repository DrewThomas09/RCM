# PEdesk HCRIS X-Ray redesign — plan

_Handoff: `~/Desktop/design_handoff_xray` (reference-only, not vendored).
Selected directions: **Input = B · Workstation**, **Results = A v2 · Headline**._

## Strategy

Restyle the existing HCRIS X-Ray onto the handoff's editorial system using the
shared **`rcm_mc/ui/xray_kit.py`** primitives (Part 2A) — **without replacing
the data engine**. The same kit then carries into the universal CMS Provider
X-Ray (Part 3) so both products share one visual grammar.

## Current implementation (mapped)

| Piece | Where |
|---|---|
| Route | `GET /diligence/hcris-xray` → `RCMHandler._route_hcris_xray_page` (`server.py`) |
| Page renderer | `rcm_mc/ui/hcris_xray_page.py` → `render_hcris_xray_page(qs=...)` |
| Data engine | HCRIS cost-report rollups + peer matching + 15 derived RCM/cost/margin metrics + P25–P75 band (existing — **preserve**) |
| Nav / palette | Diligence sub-nav + Cmd+K palette entry (`/diligence/hcris-xray`) |

**Rule:** the HCRIS benchmark engine, peer matching, and metric math are
preserved. The redesign is presentation only; real HCRIS values replace any
prototype values, and any section without real data renders an honest
"insufficient data" state (no fabricated EBITDA bridge, trends, public comps,
or peer distances).

## Part 2A — shared primitives (this PR)

`rcm_mc/ui/xray_kit.py` (scoped `.xr-*`): eyebrow (green dash), breadcrumb,
card, **navy ribbon**, buttons (primary/ghost/ink), chips/pills (green/red/
amber/neutral), the signature **peer-band box-plot** (`xr_peer_band` — P25–P75
IQR box, median tick, target diamond colored by state; honest empty band when
unplaceable), the **benchmark table** (`xr_benchmark_table` with section
rows), caveat panel, and source line. Sharp 90° corners, 1px rules, the
paper/navy/green palette and Source-Serif/Public-Sans/JetBrains-Mono roles
from the handoff. No external scripts/CDNs.

## Part 2B — input page (B · Workstation) — follow-on PR

Two-column workstation over the existing lookup: left = "① Identify the
hospital" + "② Peer engine" + action row (`▸ Run X-Ray`, `↓ Sample output`,
micro-readout); right = a clearly-**labelled SAMPLE** preview (the handoff
Stroger values are allowed only under a "sample" label; real runs use the
engine). Preserve existing route params; submit on Enter / Run X-Ray.

## Part 2C — results page (A v2 · Headline) — follow-on PR

Story-first inverted pyramid: identity row → top-finding hero (worst real
deviation + peer band + drivers) → 3-yr margin trend (if real) → EBITDA-bridge
/ payer-mix (only if real inputs) → four deviation cards → full benchmark
table (section rows SIZE/PAYER/RCM/COST/MARGIN with peer-band + Δ%) → peer
roster → public-comp context (only if present, else empty) → cross-links.
Every derived figure carries a source/caveat; unavailable sections degrade
honestly.

## Part 3 — CMS Provider X-Ray adopts the kit

The `/diligence/xray` page (already shipped) is restyled onto `xray_kit` so it
matches HCRIS X-Ray, rendering only the sections each vertical's real data
supports (HH has city not county; small sectors flag sample size; non-HCRIS
verticals never fake revenue/payer/financial sections).

## Part 4 — Guide / RAG

`docs/rag_sources/hcris_xray_design_and_interpretation.md`,
`xray_benchmark_visuals.md`, `provider_xray_design_pattern.md` + Guide context
so the Guide explains peer selection, the peer band, P25/P50/P75, the target
diamond, the biggest signal, observed-vs-derived, what not to infer, and how
HCRIS X-Ray differs from CMS Provider X-Ray.

## Guardrails

No synthetic/fake values, no fabricated bridge/comps/trends/distances, no
causality claims, no external prototype scripts/CDNs, reference folders stay
reference-only. No auth/Caddy/systemd/deploy/env/secret/Ollama/Tailscale/
RAG-runtime changes. Visible-UI PRs auto-merge only under the user's standing
approval for this effort.

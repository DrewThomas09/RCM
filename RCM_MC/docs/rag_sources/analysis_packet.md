# The Deal Analysis Packet

PEdesk's load-bearing data structure: every per-deal page, API, and export
renders from ONE DealAnalysisPacket, so the same numbers appear everywhere and
are auditable. Explains the backend so the Guide can answer "what is the
analysis packet / why does a page say 'build a packet first'".

## What it is
A single object holding a deal's computed analysis — simulation summary,
EBITDA bridge, predicted KPIs, risk flags, diligence questions, completeness
grade, and provenance. Nothing per-deal renders independently; this is the
invariant that keeps the UI and audit consistent.
- Modules: `rcm_mc/analysis/packet.py` (the dataclass + JSON round-trip),
  `rcm_mc/analysis/packet_builder.py` (a ~12-step orchestrator that builds it).
- Cached in the `analysis_runs` table; exported via
  `rcm_mc/exports/packet_renderer.py`.

## How to read it
- Per-deal model surfaces (the /models/* family, /analysis, /ebitda-bridge)
  read sections of this packet — their figures are model output over the
  deal's inputs, not realized results.
- A page that prompts "build a packet" simply means the deal has no cached
  packet yet (run `rcm-mc analysis <deal_id>` or the in-app build).

## Caveats
- The packet is only as good as the deal's input data and the builder's
  assumptions; it carries a completeness grade so gaps are visible (see the
  provenance & data-quality card).

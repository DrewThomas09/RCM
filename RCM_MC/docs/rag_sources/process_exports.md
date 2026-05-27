# Backend Process: Exports & Reports

How PEdesk produces analyst-/LP-facing outputs, so the Guide can explain the
/exports surface and export actions.

## What it produces
- CSV exports everywhere — defanged against Excel formula injection (leading
  =, +, -, @ are neutralized) so a malicious cell can't execute on open.
- LP digest / update — partner-ready HTML (and downloadable) portfolio update.
- IC packet — one-click investment-committee packet from a deal's analysis
  packet.
- Report sections, exit memo, PPTX export.
- Modules: `rcm_mc/exports/packet_renderer.py`, `rcm_mc/reports/`.

## How to read it
- Exports render from the same analysis packet the pages use, so the numbers
  match what's on screen — they are model output / stored figures, not audited
  statements.
- Generated exports are tracked (the generated_exports table) and remain
  browsable even after a deal is deleted (its FK nulls out).

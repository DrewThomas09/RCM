# Exports

Document generation and export rendering. Every export path (HTML memo, PPTX deck, Excel workbook, JSON blob, diligence package, exit package) renders from a `DealAnalysisPacket` so numbers cannot drift between formats.

| File | Purpose |
|------|---------|
| `packet_renderer.py` | Central export renderer: takes a packet and produces HTML memos, PPTX decks, JSON blobs, CSVs, and LP updates |
| `xlsx_renderer.py` | Multi-sheet Excel export with six tabs (RCM Profile, EBITDA Bridge, Monte Carlo, Risk Flags, Raw Data, Audit) and conditional formatting |
| `diligence_package.py` | One-click diligence package: generates a zip with 9 documents and a manifest for IC preparation |
| `exit_package.py` | Exit-package generator: zip archive with exit memo, value creation summary, and buyer data room checklist |
| `lp_quarterly_report.py` | Fund-level quarterly LP report aggregating deployed capital, MOIC, EBITDA growth, and per-deal cards |
| `export_store.py` | Append-only audit log of generated exports tracking what was handed out, when, to whom, and from which analysis run |

## Key Concepts

- **Packet as single source**: Every export renders from the same `DealAnalysisPacket`, eliminating number drift between formats.
- **Audit footers**: Every export prints the packet hash and run_id so stale numbers can be traced to their exact analysis run.
- **Graceful fallback**: When `python-pptx` is not installed, the PPTX path emits a structured `.txt` with the same outline.

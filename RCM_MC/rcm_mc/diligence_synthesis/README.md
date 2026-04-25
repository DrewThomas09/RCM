# diligence_synthesis/

The "tie it all together" layer. After every individual diligence module has run, this synthesizes the cross-module narrative — what's the through-line, where do findings agree, where do they conflict?

| File | Purpose |
|------|---------|
| `runner.py` | Orchestrates the run across all completed module outputs and assembles a unified story |
| `dossier.py` | The output dataclass — top findings ranked by severity × cross-module agreement, plus a recommendation |

## Why a separate synthesis layer

Each module returns its own headline number. Without synthesis, the IC packet reads as 17 disconnected verdicts. The synthesis layer re-reads every output, identifies repeated themes (e.g., "three different modules flag payer concentration"), surfaces cross-module conflicts, and renders one paragraph that a partner can read in 30 seconds.

Used by `bear_case/` (de-duplicated evidence), `ic_memo/` (executive summary), and the dashboard headline.

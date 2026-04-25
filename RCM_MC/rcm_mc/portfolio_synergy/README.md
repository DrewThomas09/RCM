# portfolio_synergy/

Cross-portfolio synergy estimation. Quantifies the lift one portco gets from another — shared best practices, vendor consolidation, cross-referrals, talent.

| File | Purpose |
|------|---------|
| `alpha.py` | "Portfolio alpha" — expected lift per active portco from membership in this fund's playbook |
| `diffusion.py` | Best-practice diffusion model: how fast does an initiative that worked at deal A propagate to deal B? |
| `sdid.py` | Synthetic-DiD specialization for portfolio-level treatment-effect studies |

## Why this is hard

You can't run a randomized trial across portcos — every deal is unique. `sdid.py` (delegating to `causal/sdid.py`) is the rigorous estimator; `alpha.py` is the heuristic shortcut for partner-driven scenarios.

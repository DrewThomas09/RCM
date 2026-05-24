# RAG source card — Investable evidence & statistics

Applies to: all analytic pages — `/portfolio-analytics`, `/concentration-risk`,
`/competitive-intel`, `/market-data`, `/home-health`, `/hospice`,
`/nursing-homes`, and any provider profile.

Sources: derived statistics over vendored CMS public datasets (no external
runtime calls). Concepts defined in
`PEDESK_INVESTABLE_EVIDENCE_FRAMEWORK.md`.

Primary keys: provider CCN; peer set = same-state / same-county providers.

Metrics & formulas:
- Peer percentile: `percentile_i = 100 * rank_i / |P|` (rank ascending for
  higher-is-better; invert for lower-is-better — state directionality).
- Z-score: `z_i = (x_i - mean(x_P)) / sd(x_P)`; require n ≥ 5; if sd = 0,
  "insufficient variation."
- Concentration (HHI): `HHI = sum_k s_k^2` over composition shares —
  **portfolio/ownership composition, not market share.**
- Quality composite: `score_i = sum_j w_j * z_{ij}` — show components +
  weights + missingness.

How to use: read percentile/z-score as *peer deviation* to locate outliers
and value-creation headroom; read HHI/CR3 as composition concentration for
single-point risk. Pair every color/flag with text.

Limitations: CMS Medicare-certified provider data — not commercial revenue,
not market share, not causal. Small samples (n<5) and zero-variance peer
sets yield no z-score. A signal is "investable evidence" only when it clears
the 8-point threshold in the framework doc (adequate n, interpretable
direction, peer-stable, slice-robust, not outlier-driven, caveated, maps to
a diligence action, out-of-sample-validated if predictive).

Suggested questions:
- "Is this percentile/z-score an investable signal or just variance?"
- "What's the peer sample size — is it big enough for a z-score?"
- "Is this concentration figure composition or true market share?"
- "What would make this signal robust across states/time?"
- "What should I verify with target documents before relying on this?"

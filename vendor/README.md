# vendor/

External / vendored projects kept alongside the codebase for reference. **Not part of the RCM-MC product.** Nothing in `RCM_MC/` imports from these directories.

| Directory | What it is |
|-----------|------------|
| [`ChartisDrewIntel/`](ChartisDrewIntel/) | Vendored copy of the Chartis dbt project (healthcare data models, claims-data marts, dbt tests). Useful as reference when wiring an RCM-MC integration that consumes Chartis-style claims tables. See its own [`README.md`](ChartisDrewIntel/README.md). |
| [`cms_medicare/`](cms_medicare/) | Earlier exploration of the CMS public-use APIs — advisory analytics, beneficiary risk plots, gender / age / state breakdowns. Predates the structured `rcm_mc/data/` loaders; preserved for the visualization patterns. See its own [`README.md`](cms_medicare/README.md). |

## Why these are vendored, not submodules

These were dropped in as snapshots for reference, not pulled as live submodules. Pinning a snapshot keeps reads reproducible and avoids carrying remote-update churn. If you need a fresh upstream pull, replace the directory in place.

## Safe to delete?

- **`ChartisDrewIntel/`** — yes, if you're not planning a Chartis-style claims integration in the next 6 months.
- **`cms_medicare/`** — yes, the canonical CMS data path is now `RCM_MC/rcm_mc/data/cms_*.py`. Nothing here is referenced by RCM-MC.

Both are kept until explicitly pruned to avoid losing reference material that took time to assemble.

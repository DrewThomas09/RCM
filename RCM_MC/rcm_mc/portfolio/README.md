# Portfolio

Portfolio-level data store, monitoring, dashboards, and cross-deal analytics. Manages the SQLite-backed deal snapshot store and provides digest, synergy, and monitoring capabilities across the full portfolio.

| File | Purpose |
|------|---------|
| `store.py` | Core `PortfolioStore`: SQLite-backed storage for deal data, snapshots, and portfolio-wide queries |
| `portfolio_snapshots.py` | Append-only deal snapshots at key milestones (IOI, LOI, SPA, close, quarterly re-mark) with `latest_per_deal()` aggregation |
| `portfolio_dashboard.py` | Self-contained HTML dashboard: weighted MOIC/IRR, stage pipeline, covenant heatmap, and full deal table (no external JS deps) |
| `portfolio_digest.py` | Early-warning digest: surfaces only material changes (new deals, stage moves, covenant crossings) since the last review |
| `portfolio_monitor.py` | Per-deal delta detection: compares latest vs prior packet and flags new risks and threshold crossings |
| `portfolio_synergy.py` | Cross-platform RCM synergy math: shared denials teams, technology, and payer leverage across 3+ portfolio companies |
| `portfolio_cli.py` | CLI entry point for portfolio store operations (snapshot, query, export) |

## Key Concepts

- **Append-only snapshots**: The audit trail from IOI through exit is preserved; `latest_per_deal()` aggregates to current state.
- **Digest over dashboard**: The digest surfaces the *diff* since last review; the dashboard is the point-in-time snapshot. Together they eliminate Monday-morning re-reading.
- **No external JS**: Dashboard renders with inline styles + SVG so it works offline, in email, and pastes into Notion.

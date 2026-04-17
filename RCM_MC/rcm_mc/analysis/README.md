# Analysis

Deal-level analysis engine: packet construction, screening, risk assessment, diligence automation, and cross-deal search. The `DealAnalysisPacket` is the spine of the product -- every UI route, API endpoint, and export renders from this single canonical object.

| File | Purpose |
|------|---------|
| `packet.py` | `DealAnalysisPacket` dataclass -- the canonical, JSON-serializable container for one deal's full analysis |
| `packet_builder.py` | Master orchestrator that walks twelve sequential steps to build a packet; partial failures mark sections as INCOMPLETE rather than killing the build |
| `analysis_store.py` | SQLite-backed append-only cache for packet runs, keyed by `(deal_id, scenario_id, as_of, hash_inputs)` |
| `anomaly_detection.py` | Automated anomaly detection on calibration inputs; flags unusual values that may indicate data quality issues |
| `challenge.py` | Reverse challenge solver -- bisection search to find what assumptions would produce a target EBITDA drag |
| `cohorts.py` | Cohort analytics: group-by-tag portfolio rollup with weighted averages across deal tags |
| `compare_runs.py` | Run comparison tool and year-over-year trend analysis between two output directories or summary CSVs |
| `completeness.py` | Data-quality layer assessing coverage, missing metrics ranked by EBITDA sensitivity, and trust flags |
| `cross_deal_search.py` | Full-text search across deal notes, overrides, risk flags, diligence questions, and packets with RCM jargon expansion |
| `deal_overrides.py` | Per-deal analyst overrides persisted in SQLite across five validated namespaces with audit trail |
| `deal_query.py` | Rule-based natural-language query parser and executor for filtering deals by field/operator/value triples |
| `deal_screener.py` | Fast deal screening from public data only -- scores quality and benchmark position without ML or MC |
| `deal_sourcer.py` | Predictive deal sourcing: scores every HCRIS hospital against a fund's investment thesis criteria |
| `diligence_questions.py` | Auto-generates prioritized diligence questionnaires from risk flags and completeness gaps |
| `playbook.py` | Operational playbook builder: finds historical deals sharing the same archetype and surfaces success rates per lever |
| `pressure_test.py` | Management plan pressure-test: achievability classification, sensitivity-to-miss MC runs, and timeline cross-checks |
| `refresh_scheduler.py` | Stale-analysis detector that identifies packets built before their data sources refreshed and optionally auto-rebuilds |
| `risk_flags.py` | Automated risk-flag assessment across six categories (operational, regulatory, payer, coding, data quality, financial) |
| `stress.py` | Stress testing utilities for Monte Carlo simulations with beta-distributed parameter shocks |
| `surrogate.py` | Placeholder for a fast ML surrogate model trained on MC runs; not used by the main CLI or report |

## Key Concepts

- **Single source of truth**: The `DealAnalysisPacket` is the only object renderers consume. If a number shows up on a page, it came from here.
- **Graceful degradation**: Each of the twelve builder steps can fail independently without killing the packet.
- **Append-only caching**: Analysis runs are never overwritten so partners can diff "what we thought on Feb 3" vs today.

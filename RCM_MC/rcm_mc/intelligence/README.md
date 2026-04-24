# intelligence/

**The Seeking Alpha-shaped composite layer.** 5 files — composite score, research-article generator, market-pulse indicators, 17,000-hospital screener. Turns the raw analytical outputs into the "stock ticker" partner experience.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker. |
| `caduceus_score.py` | **SeekingChartis Composite Score 0-100** — single rating per hospital. Weighted: market position (35%) + financial health (25%) + operational (20%) + RCM opportunity (15%) + cyber/regulatory (5%). |
| `insights_generator.py` | **Platform-generated Seeking Alpha-style research articles.** Scans the portfolio for patterns → generates named insights like "Three hospitals in your watchlist hit PASS on covenant stress but FAIL on regulatory calendar." |
| `market_pulse.py` | **Daily healthcare-PE market-pulse indicators** — composite signals from public data + portfolio state. Drives the `home_v2.py` market-pulse panel. |
| `screener_engine.py` | **Hospital screener over 17,000+ hospitals.** Seeking Alpha stock-screener equivalent. Analysts build custom filters on any metric combination (denial rate × occupancy × margin × payer mix × etc.). |

## Where it plugs in

- **Home page** (`ui/home_v2.py`) — market pulse panel + composite-score leaderboard
- **Insights feed** — browser-rendered research articles with dates + citations
- **Screener page** (`ui/predictive_screener.py`) — powers the killer "filter 17K hospitals by predicted RCM performance" feature

## Design philosophy

The intelligence layer is **aggregation + narrative**, not new math. Underlying signals come from `ml/`, `analysis/`, and `data_public/`. This layer composes them into user-facing shapes (a single score, a timely article, a live indicator, a powerful filter).

## Related

- `ml/investability_scorer.py` — HCRIS-fitted composite. `caduceus_score.py` is the partner-UI-shaped wrapper.
- `pe_intelligence/investability_scorer.py` — the PE-judgment version composed from `PartnerReview`. Three parallel scorers for three audiences.

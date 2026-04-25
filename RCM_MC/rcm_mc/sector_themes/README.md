# sector_themes/

Sector-thematic intelligence. Identifies which corners of healthcare are gathering investor attention, momentum, and consensus.

| File | Purpose |
|------|---------|
| `corpus.py` | Source corpus loader — earnings transcripts, sell-side notes, conference agendas, news |
| `themes.py` | Theme catalog — site-neutral, MA shift, behavioral consolidation, ASC migration, CPOM enforcement, etc. |
| `lda.py` | Latent Dirichlet Allocation (pure-numpy collapsed Gibbs sampler) for theme discovery from the corpus |
| `tfidf.py` (referenced from `regulatory/`) | Shared TF-IDF backbone |
| `momentum.py` | Theme-momentum scoring — which themes are accelerating in mention frequency |
| `heatmap.py` | Sector × geography heatmap visualization |
| `target_universe.py` | Per-theme target-universe builder — given a hot theme, which deals fit it? |

## Output

A `SectorBriefing` per theme that's surfaced in the dashboard's "What's hot" panel and in the deal-sourcing screener as a "deals matching X theme" filter.

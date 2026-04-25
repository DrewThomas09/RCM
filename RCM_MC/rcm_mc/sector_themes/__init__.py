"""SectorThemeDetector — LDA topic modeling on healthcare PE corpus.

Surfaces the emerging themes a partner needs to bias their
target universe toward — GLP-1 specialty pharmacy, hybrid-care
platforms, AI-enabled RCM, MA Star-rating arbitrage — without
hand-curating a fixed taxonomy.

Two operating modes:

  • **Discovery mode**: collapsed-Gibbs LDA fits K topics on a
    corpus of deal descriptions / press releases / industry
    coverage. Output: per-topic top-words + per-document topic
    mix. Useful when the partner doesn't know what they're
    looking for.

  • **Theme-anchored mode**: hand-curated theme anchors (a few
    keywords per theme) match deals against the four named
    themes plus any custom additions. Output: per-deal theme
    match scores + an emerging-theme heatmap (theme × time).

The LDA is pure numpy + stdlib — no scikit-learn / gensim. The
collapsed-Gibbs sampler is the textbook Griffiths & Steyvers
(2004) implementation; for diligence-grade modeling at K ≤ 20
topics × N ≤ 5K documents it converges in a few seconds.

Public API::

    from rcm_mc.sector_themes import (
        Document, Corpus, build_vocabulary,
        LDAModel, fit_lda_collapsed_gibbs,
        THEME_ANCHORS, score_deal_against_themes,
        emerging_theme_heatmap, build_target_universe,
    )
"""
from .corpus import Document, Corpus, build_vocabulary
from .lda import LDAModel, fit_lda_collapsed_gibbs
from .themes import (
    THEME_ANCHORS,
    score_deal_against_themes,
    ThemeMatch,
)
from .heatmap import emerging_theme_heatmap
from .target_universe import build_target_universe

__all__ = [
    "Document", "Corpus", "build_vocabulary",
    "LDAModel", "fit_lda_collapsed_gibbs",
    "THEME_ANCHORS", "ThemeMatch", "score_deal_against_themes",
    "emerging_theme_heatmap",
    "build_target_universe",
]

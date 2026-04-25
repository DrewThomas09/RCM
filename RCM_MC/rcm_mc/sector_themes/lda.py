"""LDA — Latent Dirichlet Allocation via collapsed Gibbs sampling.

Implementation follows Griffiths & Steyvers (2004). The sampler
draws topic assignments z_dn for each token n in document d, with
the conditional probability

    p(z_dn = k | z_-dn, w) ∝ (n_dk + α) × (n_kw + β) / (n_k + V β)

where n_dk = topic k count in doc d (excluding the current token),
n_kw = word w count in topic k (excluding current), n_k = total
tokens in topic k. After T iterations we read out the φ (topic ×
word) and θ (doc × topic) distributions.

Pure numpy — no scikit-learn. For diligence-grade corpora
(hundreds of documents, K ≤ 20 topics) it converges in a few
seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .corpus import Corpus


@dataclass
class LDAModel:
    """Trained LDA: topic-word + doc-topic probabilities."""
    K: int                          # number of topics
    vocab: List[str] = field(default_factory=list)
    phi: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 0)))
    theta: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 0)))
    n_iterations: int = 0

    def top_words(
        self, topic: int, n_top: int = 10,
    ) -> List[Tuple[str, float]]:
        """Top-N words for a topic ranked by P(w | topic)."""
        if topic < 0 or topic >= self.K:
            return []
        probs = self.phi[topic]
        order = np.argsort(probs)[::-1][:n_top]
        return [(self.vocab[i], float(probs[i])) for i in order]


def fit_lda_collapsed_gibbs(
    corpus: Corpus,
    *,
    K: int = 8,
    alpha: float = 0.1,
    beta: float = 0.01,
    n_iter: int = 100,
    seed: int = 0,
    burn_in: int = 20,
) -> LDAModel:
    """Fit LDA with collapsed-Gibbs sampling.

    Args:
      corpus — built via ``build_vocabulary``.
      K — number of topics.
      alpha, beta — Dirichlet hyperparameters (smaller = more
        peaked; defaults match the standard "thin priors" choice
        for LDA on bag-of-words text).
      n_iter — total Gibbs iterations.
      burn_in — discarded initial iterations before reading out
        φ / θ.

    Returns a fitted LDAModel.
    """
    if not corpus.vocab or not corpus.doc_token_ids:
        return LDAModel(K=K, vocab=corpus.vocab)
    rng = np.random.default_rng(seed)
    V = len(corpus.vocab)
    D = len(corpus.doc_token_ids)

    # Topic assignments z_dn — flattened so we can iterate fast.
    # Per-doc lists of token-id arrays.
    z: List[np.ndarray] = []
    for tokens in corpus.doc_token_ids:
        z.append(rng.integers(0, K, size=len(tokens)))

    # Counts
    n_dk = np.zeros((D, K), dtype=np.int32)   # doc × topic
    n_kw = np.zeros((K, V), dtype=np.int32)   # topic × word
    n_k = np.zeros(K, dtype=np.int32)         # tokens per topic
    for d, tokens in enumerate(corpus.doc_token_ids):
        for n, w in enumerate(tokens):
            k = int(z[d][n])
            n_dk[d, k] += 1
            n_kw[k, w] += 1
            n_k[k] += 1

    Vbeta = V * beta

    for it in range(n_iter):
        for d, tokens in enumerate(corpus.doc_token_ids):
            for n in range(len(tokens)):
                w = tokens[n]
                k_old = int(z[d][n])
                # Decrement counts
                n_dk[d, k_old] -= 1
                n_kw[k_old, w] -= 1
                n_k[k_old] -= 1
                # Sampling distribution
                p = ((n_dk[d] + alpha)
                     * (n_kw[:, w] + beta)
                     / (n_k + Vbeta))
                p = p / p.sum()
                k_new = int(rng.choice(K, p=p))
                z[d][n] = k_new
                # Increment
                n_dk[d, k_new] += 1
                n_kw[k_new, w] += 1
                n_k[k_new] += 1

    # Read out φ (topic × word) and θ (doc × topic)
    phi = (n_kw + beta) / (n_k[:, None] + Vbeta)
    theta = (n_dk + alpha) / (
        n_dk.sum(axis=1, keepdims=True) + K * alpha)

    return LDAModel(
        K=K, vocab=corpus.vocab,
        phi=phi, theta=theta,
        n_iterations=n_iter,
    )

"""Sobol low-discrepancy sequences in pure numpy.

Sobol sequences fill the unit hypercube more uniformly than
pseudo-random samples, dramatically improving convergence on
smooth integrands. For the diligence use-case (typically ≤ 8
risk factors) we ship pre-computed direction numbers for
dimensions 1 through 8 — the Joe & Kuo (2008) scheme.

This is a minimal scrambled-free Sobol generator. For
publication-grade work, scrambling is recommended; for
diligence-grade modeling at N ≤ 1024, the un-scrambled version is
sufficient and inspectable.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np


# Joe & Kuo (2008) direction numbers — primitive polynomial coeffs
# (a_k) and initial m-values for dimensions 1-8. Directions for
# d=1 are trivial; for d ≥ 2 we use the published values.
#
# Format per dimension: (degree_s, polynomial_a, initial_m_values)
_DIRECTIONS = [
    # d=1 — trivial: m_k = 1 for all k → directions = 2^(-k)
    (1, 0, [1]),
    # d=2 — polynomial x + 1
    (1, 0, [1]),
    # d=3 — polynomial x² + x + 1
    (2, 1, [1, 3]),
    # d=4 — polynomial x³ + x + 1
    (3, 1, [1, 3, 1]),
    # d=5 — polynomial x³ + x² + 1
    (3, 2, [1, 1, 1]),
    # d=6 — polynomial x⁴ + x + 1
    (4, 1, [1, 1, 3, 3]),
    # d=7 — polynomial x⁴ + x³ + 1
    (4, 4, [1, 3, 5, 13]),
    # d=8 — polynomial x⁴ + x³ + x² + x + 1
    (4, 7, [1, 1, 5, 5]),
]


def _build_direction_matrix(dim: int, n_bits: int) -> np.ndarray:
    """Build the V matrix of direction integers for one dimension.

    V[k] is the k-th direction integer (left-shifted into
    the n_bits MSB region). Sobol point at index i is the
    XOR of V[k] for every set bit k in the Gray-code of i."""
    s, a, m_init = _DIRECTIONS[dim]
    V = np.zeros(n_bits, dtype=np.uint64)
    if dim == 0:
        # Trivial first dimension: V[k] = 2^(n_bits - 1 - k)
        for k in range(n_bits):
            V[k] = np.uint64(1) << np.uint64(n_bits - 1 - k)
        return V

    for k in range(min(s, n_bits)):
        V[k] = np.uint64(m_init[k]) << np.uint64(n_bits - 1 - k)
    for k in range(s, n_bits):
        # Recurrence: V[k] = a_1 V[k-1] XOR a_2 V[k-2] XOR ...
        #            XOR V[k-s] XOR (V[k-s] >> s)
        v = V[k - s] ^ (V[k - s] >> np.uint64(s))
        for j in range(1, s):
            if (a >> (s - 1 - j)) & 1:
                v ^= V[k - j]
        V[k] = v
    return V


def sobol_sequence(
    n_samples: int,
    dim: int,
    *,
    skip: int = 1,
) -> np.ndarray:
    """Generate the first ``n_samples`` Sobol points in [0, 1)^d.

    ``skip``=1 drops the leading zero which is technically
    valid but rarely useful in practice.

    Supports dim in [1, 8]. Raises ValueError otherwise.
    """
    if dim < 1 or dim > 8:
        raise ValueError(
            f"sobol_sequence supports dim in [1, 8]; got {dim}")
    if n_samples <= 0:
        return np.zeros((0, dim), dtype=float)

    n_bits = 32
    V_per_dim = [_build_direction_matrix(d, n_bits)
                 for d in range(dim)]

    out = np.zeros((n_samples, dim), dtype=float)
    X = np.zeros(dim, dtype=np.uint64)
    factor = 1.0 / (1 << n_bits)

    for i in range(skip + n_samples):
        if i > 0:
            # Index of lowest 0 bit in (i - 1) gives the Gray-code
            # bit that flipped between i-1 and i.
            c = 0
            v = i - 1
            while v & 1:
                v >>= 1
                c += 1
            for d in range(dim):
                X[d] ^= V_per_dim[d][c]
        if i >= skip:
            for d in range(dim):
                out[i - skip, d] = float(X[d]) * factor
    return out

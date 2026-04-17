"""
Centralized RNG management using SeedSequence.

Produces independent, reproducible streams for each simulation component,
eliminating the fragile seed+1 pattern. Each named stream produces the
same sequence regardless of call order.
"""
from __future__ import annotations

import hashlib
from typing import Dict

import numpy as np


class RNGManager:
    """Manages reproducible, independent RNG streams."""

    def __init__(self, seed: int):
        self._base_seed = int(seed)
        self._seq = np.random.SeedSequence(self._base_seed)
        self._cache: Dict[str, np.random.Generator] = {}

    def spawn(self, name: str) -> np.random.Generator:
        """Create a named child RNG stream. Same name always gives same stream."""
        if name in self._cache:
            return self._cache[name]
        name_hash = int(hashlib.sha256(name.encode()).hexdigest()[:16], 16)
        child_seq = np.random.SeedSequence(self._base_seed ^ name_hash)
        rng = np.random.default_rng(child_seq)
        self._cache[name] = rng
        return rng

    def spawn_pair(self) -> tuple:
        """Create two independent streams (for actual/benchmark)."""
        rng_a = self.spawn("__pair_actual__")
        rng_b = self.spawn("__pair_benchmark__")
        return rng_a, rng_b

    @property
    def seed(self) -> int:
        return self._base_seed

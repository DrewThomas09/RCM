"""Provider-disjoint train / calibration / test splits.

Conformal CIs are valid iff the calibration set is exchangeable with
the test point. Split conformal in ``ml/conformal.py`` currently
shuffles by row, which lets the same provider's rows end up in both
train and calibration — and if a CCD row leaks into calibration, the
90% coverage claim is simply false.

This module produces three buckets where every ``provider_id`` appears
in *exactly one*. The split is:

- TRAIN       — fit the ridge model
- CALIBRATION — fit the conformal margin
- TEST        — held-out final evaluation (and includes the target
                deal's own provider_id so no predictor ever trains on
                the target)

The target provider_id is *always* in TEST. Other provider IDs are
partitioned by a deterministic hash so two runs with the same pool
produce the same split (no silent drift between a partner's two reads
of the same packet).

A :class:`SplitViolation` is raised on construction if the pool is too
small to produce three non-empty buckets — partners should know that
their comparable pool is insufficient rather than get a degraded CI
silently.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass
class ProviderSplit:
    """Three disjoint provider-ID sets + the target provider.

    Invariants (enforced at construction):

    - ``target_provider_id`` is a member of ``test`` and *not* of
      ``train`` or ``calibration``.
    - ``train``, ``calibration``, ``test`` are pairwise disjoint.
    - Sum of sizes equals the input pool size (plus the target).
    """
    train: Set[str]
    calibration: Set[str]
    test: Set[str]
    target_provider_id: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "target_provider_id": self.target_provider_id,
            "train": sorted(self.train),
            "calibration": sorted(self.calibration),
            "test": sorted(self.test),
            "sizes": {
                "train": len(self.train),
                "calibration": len(self.calibration),
                "test": len(self.test),
            },
        }


class SplitViolation(Exception):
    """Raised when the pool cannot be split three ways without
    violating disjointness or producing an empty bucket."""


# ── Construction ────────────────────────────────────────────────────

def make_three_way_split(
    *,
    target_provider_id: str,
    provider_pool: Iterable[str],
    train_fraction: float = 0.5,
    calibration_fraction: float = 0.3,
    random_seed: int = 0,
) -> ProviderSplit:
    """Produce a provider-disjoint three-way split.

    The remaining fraction (``1 - train - calibration``) lands in the
    test bucket along with the target provider. Shuffling is
    deterministic via ``random_seed`` so two calls with the same pool
    yield the same split; we don't use :mod:`random` because that
    makes the result sensitive to any other ``random`` consumer in the
    process. Instead, each provider's bucket is decided by a
    seed-keyed sha256 of the provider ID — stable across runs and
    across Python versions.
    """
    if not target_provider_id:
        raise SplitViolation("target_provider_id is required")
    if not (0.0 < train_fraction < 1.0):
        raise SplitViolation(f"train_fraction must be in (0, 1), got {train_fraction}")
    if not (0.0 < calibration_fraction < 1.0):
        raise SplitViolation(
            f"calibration_fraction must be in (0, 1), got {calibration_fraction}"
        )
    if train_fraction + calibration_fraction >= 1.0:
        raise SplitViolation(
            "train_fraction + calibration_fraction must leave a non-empty test "
            f"bucket; got {train_fraction + calibration_fraction}"
        )

    # Deduplicate + remove the target (it lands in test unconditionally).
    pool = sorted({str(p) for p in provider_pool if p} - {str(target_provider_id)})
    if len(pool) < 3:
        raise SplitViolation(
            f"pool too small for three-way split: {len(pool)} providers "
            f"(need ≥3 after excluding target)"
        )

    train: Set[str] = set()
    calibration: Set[str] = set()
    test: Set[str] = {str(target_provider_id)}

    # Deterministic assignment via hash(seed || provider_id) modulo a
    # large prime. This is O(n) and reproducible without touching
    # global RNG state.
    for pid in pool:
        q = _seeded_quantile(pid, random_seed)
        if q < train_fraction:
            train.add(pid)
        elif q < train_fraction + calibration_fraction:
            calibration.add(pid)
        else:
            test.add(pid)

    # Every bucket must have at least one provider — if the hash
    # distribution collapsed (tiny pool + extreme fractions), bump.
    split = ProviderSplit(
        train=train, calibration=calibration, test=test,
        target_provider_id=str(target_provider_id),
    )
    _rebalance_if_degenerate(split, pool)
    assert_provider_disjoint(split)
    return split


def _seeded_quantile(pid: str, seed: int) -> float:
    """Deterministic pseudo-uniform in [0, 1) keyed by (seed, pid)."""
    h = hashlib.sha256(f"{seed}|{pid}".encode("utf-8")).digest()
    # Use 8 bytes of the hash → 64-bit unsigned int → /2**64 → [0, 1).
    n = int.from_bytes(h[:8], "big", signed=False)
    return n / float(1 << 64)


def _rebalance_if_degenerate(split: ProviderSplit, pool: Sequence[str]) -> None:
    """Nudge a tiny empty bucket by pulling one provider from the
    fullest bucket. Only triggers on pools of size 3–5 where the hash
    occasionally concentrates everything in one bucket."""
    if not split.train or not split.calibration:
        fullest_name = "test" if len(split.test) >= len(split.train) else "train"
        fullest: Set[str] = getattr(split, fullest_name)
        target_bucket_name = "train" if not split.train else "calibration"
        target_bucket: Set[str] = getattr(split, target_bucket_name)
        # Move the lexicographically first provider (other than the
        # target) from fullest → empty bucket.
        for pid in sorted(fullest):
            if pid == split.target_provider_id:
                continue
            fullest.remove(pid)
            target_bucket.add(pid)
            break


# ── Invariant check ────────────────────────────────────────────────

def assert_provider_disjoint(split: ProviderSplit) -> None:
    """Raise :class:`SplitViolation` if the invariants are broken.

    Called at construction and exposed for tests that want to check a
    hand-built split. Cheap: O(|pool|) set intersections.
    """
    if not split.target_provider_id:
        raise SplitViolation("target_provider_id is empty")
    if split.target_provider_id not in split.test:
        raise SplitViolation(
            "target provider must be in test bucket, "
            f"but test={sorted(split.test)} missing {split.target_provider_id!r}"
        )
    if split.target_provider_id in split.train:
        raise SplitViolation(
            f"target {split.target_provider_id!r} leaked into TRAIN"
        )
    if split.target_provider_id in split.calibration:
        raise SplitViolation(
            f"target {split.target_provider_id!r} leaked into CALIBRATION"
        )
    pairs = (
        ("train", "calibration", split.train & split.calibration),
        ("train", "test",        split.train & split.test),
        ("calibration", "test",  split.calibration & split.test),
    )
    for a, b, overlap in pairs:
        if overlap:
            raise SplitViolation(
                f"{a} ∩ {b} non-empty: {sorted(overlap)}"
            )
    if not split.train:
        raise SplitViolation("train bucket is empty")
    if not split.calibration:
        raise SplitViolation("calibration bucket is empty")
    if not split.test:
        raise SplitViolation("test bucket is empty")


# ── Row-level filtering ─────────────────────────────────────────────

def rows_in_bucket(
    rows: Iterable[Dict[str, object]],
    *,
    bucket: Set[str],
    provider_id_key: str = "provider_id",
) -> List[Dict[str, object]]:
    """Filter a list of row-dicts to those whose ``provider_id`` is in
    ``bucket``. Used by the ridge / conformal caller to assemble the
    train and calibration matrices *after* the split has been decided
    at the provider level."""
    bucket_ids = {str(b) for b in bucket}
    return [r for r in rows if str(r.get(provider_id_key)) in bucket_ids]

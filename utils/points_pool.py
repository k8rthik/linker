"""Points-pool model for weighted random link selection.

Every profile maintains a fixed-size pool of TOTAL_POOL (100) points
distributed across its links. Each link's selection probability is its
share of the pool. Opening a link applies an exponential point loss
(more aggressive as the link's remaining points fall below baseline)
and redistributes that loss equally to the other links, so that the
sum is conserved. Adding a link funds it by subtracting equally from
existing links; deleting one redistributes its points equally to those
remaining.

All public functions in this module are pure: they accept a List[float]
pool and return a new list, never mutating the input.
"""

from __future__ import annotations

import math
from typing import List

TOTAL_POOL: float = 100.0

# Loss curve parameters. At p = baseline a link sheds α·baseline points
# per open. As p drops below baseline the loss grows as exp(β·(b−p)/b),
# i.e. doubling roughly every (ln 2)/β · b decrease.
LOSS_BASE_FRACTION: float = 0.1
LOSS_EXPONENT: float = 1.0

# Tolerance for the sum-conservation invariant.
INVARIANT_TOL: float = 1e-6


def baseline(n: int) -> float:
    """Per-link baseline for a pool of n links."""
    if n <= 0:
        return 0.0
    return TOTAL_POOL / n


def compute_loss(points: float, base: float) -> float:
    """Exponential loss for an opened link, floored at its current points.

    loss = base · α · exp(β · (base − points) / base)
    """
    if points <= 0.0 or base <= 0.0:
        return 0.0
    raw = base * LOSS_BASE_FRACTION * math.exp(
        LOSS_EXPONENT * (base - points) / base
    )
    return min(raw, points)


def initialize(n: int) -> List[float]:
    """Fresh pool with n links each holding the baseline share."""
    if n <= 0:
        return []
    b = baseline(n)
    return [b] * n


def invariant_holds(pool: List[float], tol: float = INVARIANT_TOL) -> bool:
    """True iff every point is non-negative and the sum matches TOTAL_POOL.

    An empty pool is considered valid (a degenerate but legal state for a
    profile with no links).
    """
    if not pool:
        return True
    if any(p < -tol for p in pool):
        return False
    return math.isclose(sum(pool), TOTAL_POOL, abs_tol=tol)


def renormalize(pool: List[float]) -> List[float]:
    """Floor negatives at zero and rescale so the pool sums to TOTAL_POOL.

    If every entry is zero (degenerate), reset to a uniform baseline so
    the invariant is restored.
    """
    if not pool:
        return []
    floored = [max(0.0, p) for p in pool]
    total = sum(floored)
    if total <= 0.0:
        return initialize(len(pool))
    scale = TOTAL_POOL / total
    return [p * scale for p in floored]


def apply_open(pool: List[float], index: int) -> List[float]:
    """Apply one open to `pool[index]`: subtract the loss, redistribute
    equally to the other links. Single-link pools are unchanged (nowhere
    to redistribute). Empty pools are unchanged."""
    if not pool:
        return []
    if index < 0 or index >= len(pool):
        raise IndexError(f"index {index} out of range for pool of size {len(pool)}")
    n = len(pool)
    if n == 1:
        return list(pool)

    b = baseline(n)
    loss = compute_loss(pool[index], b)
    share = loss / (n - 1)
    result = [p + share for p in pool]
    result[index] = pool[index] - loss
    return renormalize(result)


def apply_add(pool: List[float]) -> List[float]:
    """Grow the pool by one link. The new link receives the new baseline;
    each existing link contributes new_baseline / n. Renormalized to absorb
    rounding and any depleted-link shortfall."""
    n = len(pool)
    if n == 0:
        return [TOTAL_POOL]
    new_baseline = baseline(n + 1)
    contribution = new_baseline / n
    reduced = [p - contribution for p in pool]
    reduced.append(new_baseline)
    return renormalize(reduced)


def apply_delete(pool: List[float], index: int) -> List[float]:
    """Shrink the pool by one link. The removed link's points are split
    equally among the remaining links. Removing the last link yields an
    empty pool."""
    if not pool:
        return []
    if index < 0 or index >= len(pool):
        raise IndexError(f"index {index} out of range for pool of size {len(pool)}")
    n = len(pool)
    if n == 1:
        return []
    removed_points = pool[index]
    share = removed_points / (n - 1)
    result = [p + share for i, p in enumerate(pool) if i != index]
    return renormalize(result)

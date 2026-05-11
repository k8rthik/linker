"""Weighted random selection utilities for random-link openers."""

import random
from typing import List

from models.link import Link


def weighted_choice(
    indices: List[int],
    links: List[Link],
    exponent: float = 1.0,
) -> int:
    """Pick a random index from `indices`, biased against frequently-opened links.

    Opened links use an inverse-power curve on open_count: more opens → lower
    weight, scaled by `exponent`.

    Unopened links (open_count == 0) are *decoupled* from this curve and pinned
    at the mean weight of opened links. Without this, the formula spikes at
    zero and a brand-new favorite dominates every draw — especially under high
    exponents (a freshly favorited link with exponent=3 was 8× more likely than
    one opened a single time). Anchoring unopened at the baseline keeps "I just
    added this" links at probability ≈ 1/n while still skewing among opened
    links.

    When every passed-in link is unopened, falls back to uniform random.
    """
    if not indices:
        raise ValueError("indices must not be empty")
    if exponent < 0:
        raise ValueError("exponent must be non-negative")

    opened_indices = [i for i in indices if links[i].open_count > 0]
    if not opened_indices:
        return random.choice(indices)

    def opened_weight(i: int) -> float:
        return 1.0 / (links[i].open_count + 1) ** exponent

    baseline = sum(opened_weight(i) for i in opened_indices) / len(opened_indices)

    weights = [
        baseline if links[i].open_count == 0 else opened_weight(i)
        for i in indices
    ]
    return random.choices(indices, weights=weights, k=1)[0]


def weighted_sample(
    indices: List[int],
    links: List[Link],
    k: int,
    exponent: float = 1.0,
) -> List[int]:
    """Pick up to `k` unique indices via repeated weighted draws without replacement.

    Uses the same biasing rules as `weighted_choice`. Returns fewer than `k`
    items when the pool is smaller. Returns an empty list when `k <= 0` or
    `indices` is empty.
    """
    if k <= 0 or not indices:
        return []

    pool = list(indices)
    chosen: List[int] = []
    while pool and len(chosen) < k:
        pick = weighted_choice(pool, links, exponent=exponent)
        chosen.append(pick)
        pool.remove(pick)
    return chosen

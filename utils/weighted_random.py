"""Weighted random selection over a pool of links.

Selection weight is `link.points`, which is maintained by the points-pool
model (see `utils/points_pool`). Each link's probability of being drawn
equals its share of the live pool. If every candidate has zero points
(a degenerate state), selection falls back to a uniform draw so no link
becomes permanently unreachable.
"""

from __future__ import annotations

import random
from typing import List

from models.link import Link


def weighted_choice(indices: List[int], links: List[Link]) -> int:
    """Pick one index from `indices`, biased by link.points.

    Falls back to a uniform draw when every candidate has zero weight.
    """
    if not indices:
        raise ValueError("indices must not be empty")

    weights = [max(0.0, links[i].points) for i in indices]
    if sum(weights) <= 0.0:
        return random.choice(indices)
    return random.choices(indices, weights=weights, k=1)[0]


def weighted_sample(indices: List[int], links: List[Link], k: int) -> List[int]:
    """Pick up to `k` unique indices via repeated weighted draws without
    replacement. Returns fewer than `k` items when the pool is smaller, an
    empty list when `k <= 0` or `indices` is empty.
    """
    if k <= 0 or not indices:
        return []

    pool = list(indices)
    chosen: List[int] = []
    while pool and len(chosen) < k:
        pick = weighted_choice(pool, links)
        chosen.append(pick)
        pool.remove(pick)
    return chosen

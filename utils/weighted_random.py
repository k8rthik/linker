"""Weighted random selection utilities for random-link openers."""

import random
from typing import List

from models.link import Link


def weighted_choice(
    indices: List[int],
    links: List[Link],
    exponent: float = 1.0,
) -> int:
    """Pick a random index from `indices`, weighted by inverse of open_count."""
    if not indices:
        raise ValueError("indices must not be empty")
    if exponent < 0:
        raise ValueError("exponent must be non-negative")

    weights = [1.0 / (links[i].open_count + 1) ** exponent for i in indices]
    return random.choices(indices, weights=weights, k=1)[0]

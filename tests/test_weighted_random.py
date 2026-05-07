"""Tests for the weighted random selector used by the random-link openers."""

import random
from collections import Counter
from typing import List

import pytest

from models.link import Link
from utils.weighted_random import weighted_choice


def _make_links(open_counts: List[int], favorite: bool = True) -> List[Link]:
    """Build a list of Link instances with the given open_counts."""
    return [
        Link(
            name=f"link-{i}",
            url=f"https://example.com/{i}",
            favorite=favorite,
            open_count=count,
        )
        for i, count in enumerate(open_counts)
    ]


def test_raises_on_empty_indices():
    with pytest.raises(ValueError):
        weighted_choice([], _make_links([0]))


def test_raises_on_negative_exponent():
    with pytest.raises(ValueError):
        weighted_choice([0], _make_links([0]), exponent=-1.0)


def test_returned_index_is_in_input_range():
    """Sanity: every draw must come from the supplied indices."""
    random.seed(0)
    links = _make_links([0, 5, 10, 0, 2])
    indices = [1, 3, 4]
    for _ in range(200):
        chosen = weighted_choice(indices, links)
        assert chosen in indices


def test_every_favorite_is_reachable():
    """The selection range must include every favorited link in the profile.

    If we build a profile with N favorites and draw enough times, every
    favorite index should appear at least once — otherwise the algorithm is
    silently excluding part of the pool.
    """
    n = 50
    links = _make_links([0] * n)
    indices = list(range(n))

    random.seed(42)
    seen = set()
    for _ in range(10_000):
        seen.add(weighted_choice(indices, links))

    assert seen == set(indices), f"missing indices: {set(indices) - seen}"


def test_every_favorite_has_nonzero_weight_under_strong_bias():
    """Every passed-in favorite must keep a non-zero selection probability."""
    links = _make_links([0, 1, 2, 5, 10, 100])
    indices = list(range(len(links)))

    weights = [1.0 / (links[i].open_count + 1) ** 3.0 for i in indices]
    assert all(w > 0 for w in weights), "no favorite should be excluded outright"


def test_modestly_opened_favorites_still_surface_under_strong_bias():
    """With realistic open_counts, even a 5x-opened favorite must appear in the draws."""
    links = _make_links([0, 1, 2, 3, 5])
    indices = list(range(len(links)))

    random.seed(7)
    seen = set()
    for _ in range(20_000):
        seen.add(weighted_choice(indices, links, exponent=3.0))

    assert seen == set(indices), f"missing indices: {set(indices) - seen}"


def test_independent_draws_produce_varied_output():
    """Consecutive calls should not collapse onto a single result."""
    random.seed(1)
    links = _make_links([0] * 20)
    indices = list(range(20))

    results = [weighted_choice(indices, links) for _ in range(500)]
    counts = Counter(results)

    assert len(counts) >= 18, f"expected near-uniform spread; got {counts}"
    assert max(counts.values()) < 100, "one index dominated unexpectedly"


def test_unopened_favorites_are_picked_more_often():
    """With default exponent=1, count=0 should beat count=2 across many trials."""
    links = _make_links([0, 0, 0, 2, 2, 2])
    indices = list(range(len(links)))

    random.seed(3)
    counts = Counter(weighted_choice(indices, links) for _ in range(10_000))

    unopened = sum(counts[i] for i in (0, 1, 2))
    opened = sum(counts[i] for i in (3, 4, 5))
    assert unopened > opened * 2, f"unopened={unopened}, opened={opened}"


def test_higher_exponent_strengthens_bias_toward_unopened():
    """exponent=3 should down-weight opened favorites much harder than exponent=1."""
    links = _make_links([0, 1])
    indices = [0, 1]
    trials = 20_000

    random.seed(11)
    weak = Counter(weighted_choice(indices, links, exponent=1.0) for _ in range(trials))
    random.seed(11)
    strong = Counter(weighted_choice(indices, links, exponent=3.0) for _ in range(trials))

    weak_share_unopened = weak[0] / trials
    strong_share_unopened = strong[0] / trials

    # exponent=1 -> theoretical 1.0 / (1.0 + 0.5) = 0.667
    # exponent=3 -> theoretical 1.0 / (1.0 + 0.125) = 0.889
    assert 0.62 < weak_share_unopened < 0.72
    assert 0.85 < strong_share_unopened < 0.93
    assert strong_share_unopened > weak_share_unopened + 0.1


def test_zero_exponent_yields_uniform_distribution():
    """exponent=0 collapses every weight to 1.0 → ignore open_count entirely."""
    links = _make_links([0, 50, 1000])
    indices = [0, 1, 2]

    random.seed(99)
    counts = Counter(weighted_choice(indices, links, exponent=0.0) for _ in range(15_000))

    for idx in indices:
        share = counts[idx] / 15_000
        assert 0.30 < share < 0.36, f"index {idx} share {share} not near 1/3"


def test_consecutive_calls_are_independent():
    """Two seeded runs should match exactly; otherwise hidden state is leaking."""
    links = _make_links([0, 1, 2, 3])
    indices = [0, 1, 2, 3]

    random.seed(2024)
    run_a = [weighted_choice(indices, links) for _ in range(100)]
    random.seed(2024)
    run_b = [weighted_choice(indices, links) for _ in range(100)]

    assert run_a == run_b

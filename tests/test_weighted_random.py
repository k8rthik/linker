"""Tests for the weighted random selector used by the random-link openers."""

import random
from collections import Counter
from typing import List

import pytest

from models.link import Link
from utils.weighted_random import weighted_choice, weighted_sample


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


def test_unopened_link_sits_at_baseline_one_over_n():
    """An unopened link in a mixed pool should land at probability ≈ 1/n.

    With links [0, 1, 5] (one unopened, two opened), the unopened index must
    end up near 1/3 — not dominate as it did before the decoupling fix.
    """
    links = _make_links([0, 1, 5])
    indices = [0, 1, 2]
    trials = 30_000

    random.seed(5)
    counts = Counter(
        weighted_choice(indices, links, exponent=3.0) for _ in range(trials)
    )

    unopened_share = counts[0] / trials
    assert 0.30 < unopened_share < 0.37, (
        f"unopened share {unopened_share} should be near baseline 1/3"
    )


def test_less_opened_links_outrank_more_opened_among_opened_pool():
    """Among opened-only pools the inverse curve still applies — a 1-opened
    link must beat a 5-opened link by a wide margin."""
    links = _make_links([1, 5])
    indices = [0, 1]
    trials = 20_000

    random.seed(7)
    counts = Counter(
        weighted_choice(indices, links, exponent=1.0) for _ in range(trials)
    )

    # weights: [1/2, 1/6] -> shares [0.75, 0.25]
    light_share = counts[0] / trials
    assert 0.70 < light_share < 0.80


def test_higher_exponent_widens_spread_among_opened():
    """Higher exponent should sharpen the down-weighting of more-opened links
    *within the opened pool* (decoupling did not weaken this skew)."""
    links = _make_links([1, 5])
    indices = [0, 1]
    trials = 20_000

    random.seed(11)
    weak = Counter(
        weighted_choice(indices, links, exponent=1.0) for _ in range(trials)
    )
    random.seed(11)
    strong = Counter(
        weighted_choice(indices, links, exponent=3.0) for _ in range(trials)
    )

    # exp=1: weights [1/2, 1/6]   -> light share ≈ 0.75
    # exp=3: weights [1/8, 1/216] -> light share ≈ 0.964
    weak_light = weak[0] / trials
    strong_light = strong[0] / trials

    assert 0.70 < weak_light < 0.80
    assert strong_light > 0.93
    assert strong_light > weak_light + 0.1


def test_new_favorite_not_overprefered_against_singly_opened():
    """Regression: at exponent=3 a brand-new favorite used to win 89% of draws
    against a once-opened favorite. Decoupling pins the new one at the mean
    weight of opened links — with one opened peer, that's a 50/50 split."""
    links = _make_links([0, 1])
    indices = [0, 1]
    trials = 20_000

    random.seed(17)
    counts = Counter(
        weighted_choice(indices, links, exponent=3.0) for _ in range(trials)
    )

    new_share = counts[0] / trials
    assert 0.46 < new_share < 0.54, (
        f"new favorite share {new_share} should be ≈ 0.5, not the old ~0.89"
    )


def test_zero_exponent_yields_uniform_distribution():
    """exponent=0 collapses every weight to 1.0 → ignore open_count entirely."""
    links = _make_links([0, 50, 1000])
    indices = [0, 1, 2]

    random.seed(99)
    counts = Counter(weighted_choice(indices, links, exponent=0.0) for _ in range(15_000))

    for idx in indices:
        share = counts[idx] / 15_000
        assert 0.30 < share < 0.36, f"index {idx} share {share} not near 1/3"


def test_weighted_sample_returns_unique_indices():
    """Sampling must never repeat an index, no matter the bias."""
    random.seed(0)
    links = _make_links([0, 1, 2, 3, 5])
    indices = list(range(len(links)))

    chosen = weighted_sample(indices, links, k=len(indices), exponent=3.0)
    assert sorted(chosen) == sorted(indices)
    assert len(set(chosen)) == len(chosen)


def test_weighted_sample_caps_at_pool_size():
    """Asking for more than the pool returns the whole pool, no repeats."""
    random.seed(0)
    links = _make_links([0, 1])
    chosen = weighted_sample([0, 1], links, k=10)
    assert sorted(chosen) == [0, 1]


def test_weighted_sample_zero_or_empty_returns_empty_list():
    links = _make_links([0, 1, 2])
    assert weighted_sample([0, 1, 2], links, k=0) == []
    assert weighted_sample([], links, k=5) == []


def test_weighted_sample_partial_draw_size_matches_k():
    random.seed(123)
    links = _make_links([0, 1, 2, 3, 5, 8])
    chosen = weighted_sample(list(range(6)), links, k=3, exponent=2.0)
    assert len(chosen) == 3
    assert len(set(chosen)) == 3
    assert all(0 <= i < 6 for i in chosen)


def test_consecutive_calls_are_independent():
    """Two seeded runs should match exactly; otherwise hidden state is leaking."""
    links = _make_links([0, 1, 2, 3])
    indices = [0, 1, 2, 3]

    random.seed(2024)
    run_a = [weighted_choice(indices, links) for _ in range(100)]
    random.seed(2024)
    run_b = [weighted_choice(indices, links) for _ in range(100)]

    assert run_a == run_b

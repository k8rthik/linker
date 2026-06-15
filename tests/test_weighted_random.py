"""Tests for the weighted random selector used by the random-link openers.

Selection weight is `link.points`. The points themselves are maintained
by the points-pool model and tested separately in test_points_pool.py.
"""

import random
from collections import Counter
from typing import List

import pytest

from models.link import Link
from utils.weighted_random import weighted_choice, weighted_sample


def _make_links(points: List[float]) -> List[Link]:
    """Build a list of Link instances with the given point values."""
    return [
        Link(
            name=f"link-{i}",
            url=f"https://example.com/{i}",
            points=p,
        )
        for i, p in enumerate(points)
    ]


def test_raises_on_empty_indices():
    with pytest.raises(ValueError):
        weighted_choice([], _make_links([1.0]))


def test_returned_index_is_in_input_range():
    """Every draw must come from the supplied indices, not the full pool."""
    random.seed(0)
    links = _make_links([1.0, 1.0, 1.0, 1.0, 1.0])
    indices = [1, 3, 4]
    for _ in range(200):
        chosen = weighted_choice(indices, links)
        assert chosen in indices


def test_every_link_is_reachable_under_equal_weights():
    n = 50
    links = _make_links([2.0] * n)
    indices = list(range(n))

    random.seed(42)
    seen = set()
    for _ in range(10_000):
        seen.add(weighted_choice(indices, links))

    assert seen == set(indices), f"missing indices: {set(indices) - seen}"


def test_higher_points_link_is_drawn_more_often():
    """A link with 3× the points of its peer should be drawn ~3× as often."""
    links = _make_links([3.0, 1.0])
    indices = [0, 1]
    trials = 20_000

    random.seed(7)
    counts = Counter(weighted_choice(indices, links) for _ in range(trials))

    heavy_share = counts[0] / trials
    assert 0.72 < heavy_share < 0.78, (
        f"heavy-weight share {heavy_share} should be near 3/4"
    )


def test_zero_point_link_never_chosen_when_others_have_weight():
    """A link at zero points must not be picked if any other candidate has weight."""
    links = _make_links([0.0, 5.0, 5.0])
    indices = [0, 1, 2]

    random.seed(11)
    counts = Counter(weighted_choice(indices, links) for _ in range(5_000))
    assert counts[0] == 0


def test_all_zero_pool_falls_back_to_uniform():
    """If every candidate has zero points, selection must still spread the draws."""
    links = _make_links([0.0, 0.0, 0.0])
    indices = [0, 1, 2]

    random.seed(13)
    counts = Counter(weighted_choice(indices, links) for _ in range(15_000))

    for idx in indices:
        share = counts[idx] / 15_000
        assert 0.30 < share < 0.37, f"index {idx} share {share} not near 1/3"


def test_negative_points_treated_as_zero():
    """Defensive: a (theoretically impossible) negative weight must not blow up
    random.choices. It is clamped to zero, leaving other links to share the draw."""
    links = _make_links([-5.0, 1.0, 1.0])
    indices = [0, 1, 2]

    random.seed(17)
    counts = Counter(weighted_choice(indices, links) for _ in range(5_000))
    assert counts[0] == 0
    assert counts[1] > 0 and counts[2] > 0


def test_consecutive_calls_are_independent():
    """Two seeded runs should match exactly; otherwise hidden state is leaking."""
    links = _make_links([1.0, 2.0, 3.0, 4.0])
    indices = [0, 1, 2, 3]

    random.seed(2024)
    run_a = [weighted_choice(indices, links) for _ in range(100)]
    random.seed(2024)
    run_b = [weighted_choice(indices, links) for _ in range(100)]

    assert run_a == run_b


# --- weighted_sample ----------------------------------------------------


def test_weighted_sample_returns_unique_indices():
    random.seed(0)
    links = _make_links([1.0, 2.0, 3.0, 4.0, 5.0])
    indices = list(range(len(links)))

    chosen = weighted_sample(indices, links, k=len(indices))
    assert sorted(chosen) == sorted(indices)
    assert len(set(chosen)) == len(chosen)


def test_weighted_sample_caps_at_pool_size():
    random.seed(0)
    links = _make_links([1.0, 1.0])
    chosen = weighted_sample([0, 1], links, k=10)
    assert sorted(chosen) == [0, 1]


def test_weighted_sample_zero_or_empty_returns_empty_list():
    links = _make_links([1.0, 1.0, 1.0])
    assert weighted_sample([0, 1, 2], links, k=0) == []
    assert weighted_sample([], links, k=5) == []


def test_weighted_sample_partial_draw_size_matches_k():
    random.seed(123)
    links = _make_links([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    chosen = weighted_sample(list(range(6)), links, k=3)
    assert len(chosen) == 3
    assert len(set(chosen)) == 3
    assert all(0 <= i < 6 for i in chosen)


def test_weighted_sample_excludes_zero_point_link_when_others_available():
    """With one zero-weight link and 3 picks among 4 candidates, the
    zero-weight one should consistently be the one left out."""
    links = _make_links([0.0, 5.0, 5.0, 5.0])
    indices = [0, 1, 2, 3]

    random.seed(31)
    runs = 200
    excluded = Counter()
    for _ in range(runs):
        chosen = weighted_sample(indices, links, k=3)
        leftover = set(indices) - set(chosen)
        for i in leftover:
            excluded[i] += 1

    # Index 0 should be excluded every time — only the all-zero fallback
    # path could let it sneak in, and that only fires when the remaining
    # pool is itself all-zero.
    assert excluded[0] == runs

"""Tests for the points-pool model behind weighted random link selection.

The pool maintains the invariant that all link points sum to TOTAL_POOL (100).
- New profiles initialize every link at baseline (100/N).
- Opening a link applies an exponential loss to it and redistributes the
  loss equally to the remaining links.
- Adding a link gives it baseline points by subtracting equally from
  existing links.
- Deleting a link redistributes its points equally to remaining links.
"""

from __future__ import annotations

import math
from typing import List

import pytest

from utils.points_pool import (
    LOSS_BASE_FRACTION,
    LOSS_EXPONENT,
    TOTAL_POOL,
    apply_add,
    apply_delete,
    apply_open,
    baseline,
    compute_loss,
    initialize,
    invariant_holds,
    renormalize,
)

TOL = 1e-6


def _approx_sum(pool: List[float], expected: float = TOTAL_POOL, tol: float = TOL) -> bool:
    return math.isclose(sum(pool), expected, abs_tol=tol)


# --- baseline -----------------------------------------------------------


def test_baseline_zero_pool():
    assert baseline(0) == 0.0


def test_baseline_single_link_gets_full_pool():
    assert baseline(1) == TOTAL_POOL


def test_baseline_divides_pool_evenly():
    assert math.isclose(baseline(10), TOTAL_POOL / 10)
    assert math.isclose(baseline(100), TOTAL_POOL / 100)


# --- compute_loss -------------------------------------------------------


def test_loss_at_baseline_equals_base_fraction_of_baseline():
    b = baseline(10)
    expected = b * LOSS_BASE_FRACTION
    assert math.isclose(compute_loss(b, b), expected)


def test_loss_grows_as_points_drop_below_baseline():
    b = baseline(10)
    loss_at_baseline = compute_loss(b, b)
    loss_half = compute_loss(b / 2, b)
    loss_quarter = compute_loss(b / 4, b)
    assert loss_half > loss_at_baseline
    assert loss_quarter > loss_half


def test_loss_shrinks_above_baseline():
    b = baseline(10)
    loss_at_baseline = compute_loss(b, b)
    loss_above = compute_loss(b * 2, b)
    assert loss_above < loss_at_baseline


def test_loss_floored_at_current_points():
    """A link cannot lose more than it has."""
    b = baseline(10)
    # 0.001 points left — even an exponential loss must not push below zero.
    loss = compute_loss(0.001, b)
    assert loss <= 0.001 + TOL


def test_loss_is_zero_when_points_already_zero():
    assert compute_loss(0.0, baseline(10)) == 0.0


def test_loss_exponential_shape_matches_formula():
    """compute_loss must match b * α * exp(β · (b − points) / b), floored at points."""
    b = 1.0
    for p in (0.1, 0.5, 1.0, 1.5, 3.0):
        expected = b * LOSS_BASE_FRACTION * math.exp(LOSS_EXPONENT * (b - p) / b)
        expected = min(expected, p)
        assert math.isclose(compute_loss(p, b), expected, abs_tol=TOL)


# --- initialize ---------------------------------------------------------


def test_initialize_empty():
    assert initialize(0) == []


def test_initialize_single():
    assert initialize(1) == [TOTAL_POOL]


def test_initialize_uniform_and_sums_to_pool():
    pool = initialize(7)
    assert len(pool) == 7
    assert all(math.isclose(p, TOTAL_POOL / 7) for p in pool)
    assert _approx_sum(pool)


# --- invariant_holds ----------------------------------------------------


def test_invariant_holds_on_initialized_pool():
    assert invariant_holds(initialize(5))


def test_invariant_holds_on_empty_pool():
    # Empty profile is a degenerate but valid state.
    assert invariant_holds([])


def test_invariant_fails_on_wrong_sum():
    assert not invariant_holds([50.0, 49.0])


def test_invariant_fails_on_negative_points():
    assert not invariant_holds([110.0, -10.0])


def test_invariant_tolerates_small_floating_drift():
    assert invariant_holds([50.0, 50.0 + 1e-9])


# --- renormalize --------------------------------------------------------


def test_renormalize_noop_on_already_normalized():
    pool = [25.0, 25.0, 50.0]
    assert renormalize(pool) == pool


def test_renormalize_corrects_drift():
    pool = [25.0, 25.0, 50.5]  # total 100.5
    result = renormalize(pool)
    assert _approx_sum(result)


def test_renormalize_floors_negatives_then_scales():
    pool = [-5.0, 60.0, 60.0]  # would scale wrong if negative left in
    result = renormalize(pool)
    assert all(p >= 0 for p in result)
    assert _approx_sum(result)


def test_renormalize_zero_sum_falls_back_to_uniform():
    """If every link has zero points (degenerate), reset to baseline."""
    result = renormalize([0.0, 0.0, 0.0])
    assert _approx_sum(result)
    assert all(math.isclose(p, TOTAL_POOL / 3) for p in result)


def test_renormalize_empty():
    assert renormalize([]) == []


# --- apply_open ---------------------------------------------------------


def test_open_preserves_pool_size():
    pool = initialize(5)
    result = apply_open(pool, 0)
    assert len(result) == 5


def test_open_preserves_total():
    pool = initialize(5)
    result = apply_open(pool, 2)
    assert _approx_sum(result)


def test_open_does_not_mutate_input():
    pool = initialize(5)
    snapshot = list(pool)
    apply_open(pool, 1)
    assert pool == snapshot


def test_open_decreases_opened_links_points():
    pool = initialize(5)
    result = apply_open(pool, 0)
    assert result[0] < pool[0]


def test_open_increases_other_links_points_equally():
    pool = initialize(5)
    result = apply_open(pool, 0)
    others = result[1:]
    assert all(p > pool[1] for p in others)
    # All "other" links gained the same amount.
    gains = [p - pool[i + 1] for i, p in enumerate(others)]
    assert max(gains) - min(gains) < TOL


def test_open_loss_matches_compute_loss():
    pool = initialize(5)
    expected_loss = compute_loss(pool[0], baseline(5))
    result = apply_open(pool, 0)
    actual_loss = pool[0] - result[0]
    assert math.isclose(actual_loss, expected_loss, abs_tol=TOL)


def test_open_with_single_link_is_noop():
    """N=1: nowhere to redistribute, so no points move."""
    pool = [TOTAL_POOL]
    assert apply_open(pool, 0) == pool


def test_open_empty_pool_returns_empty():
    assert apply_open([], 0) == []


def test_open_raises_on_out_of_range_index():
    with pytest.raises(IndexError):
        apply_open(initialize(3), 5)


def test_open_repeated_increases_loss_exponentially():
    """As the opened link's points drop, each successive open removes more."""
    pool = initialize(10)
    losses: List[float] = []
    for _ in range(5):
        next_pool = apply_open(pool, 0)
        losses.append(pool[0] - next_pool[0])
        pool = next_pool
    # Each successive loss is greater than the previous one (until floor).
    assert all(losses[i + 1] > losses[i] for i in range(len(losses) - 1))


def test_open_many_times_never_violates_invariant():
    pool = initialize(8)
    for _ in range(50):
        pool = apply_open(pool, 0)
        assert invariant_holds(pool, tol=1e-6)


def test_open_two_links_split_loss_equally():
    """With N=2, the single 'other' link absorbs the full loss."""
    pool = [50.0, 50.0]
    result = apply_open(pool, 0)
    loss = pool[0] - result[0]
    gain = result[1] - pool[1]
    assert math.isclose(loss, gain, abs_tol=TOL)


# --- apply_add ----------------------------------------------------------


def test_add_to_empty_pool_yields_singleton_at_full_pool():
    result = apply_add([])
    assert result == [TOTAL_POOL]


def test_add_grows_pool_size_by_one():
    pool = initialize(4)
    result = apply_add(pool)
    assert len(result) == len(pool) + 1


def test_add_preserves_total():
    pool = initialize(4)
    result = apply_add(pool)
    assert _approx_sum(result)


def test_add_does_not_mutate_input():
    pool = initialize(4)
    snapshot = list(pool)
    apply_add(pool)
    assert pool == snapshot


def test_add_new_link_at_baseline_when_pool_uniform():
    pool = initialize(4)
    result = apply_add(pool)
    new_baseline = baseline(5)
    assert math.isclose(result[-1], new_baseline, abs_tol=TOL)
    for p in result[:-1]:
        assert math.isclose(p, new_baseline, abs_tol=TOL)


def test_add_subtracts_equally_from_existing_links():
    """Equal subtraction preserves relative differences between existing links."""
    pool = [60.0, 30.0, 10.0]  # sum = 100
    result = apply_add(pool)
    # Differences between existing links must be preserved exactly.
    assert math.isclose(result[0] - result[1], pool[0] - pool[1], abs_tol=TOL)
    assert math.isclose(result[1] - result[2], pool[1] - pool[2], abs_tol=TOL)


def test_add_to_depleted_pool_floors_at_zero_and_holds_invariant():
    """When an existing link doesn't have enough to cover its share, the result
    is still non-negative and the pool still sums to TOTAL_POOL."""
    pool = [99.0, 1.0]  # link 1 is almost dead
    # Going 2 → 3: new baseline = 33.33; each existing owes 33.33/2 = 16.67.
    # Link 1 (1.0 points) cannot pay 16.67 → floor at zero, renormalize.
    result = apply_add(pool)
    assert len(result) == 3
    assert all(p >= 0 for p in result)
    assert _approx_sum(result)


def test_add_then_open_then_add_keeps_invariant():
    pool = initialize(3)
    pool = apply_add(pool)
    pool = apply_open(pool, 1)
    pool = apply_add(pool)
    assert invariant_holds(pool)


# --- apply_delete -------------------------------------------------------


def test_delete_shrinks_pool_size_by_one():
    pool = initialize(4)
    result = apply_delete(pool, 0)
    assert len(result) == 3


def test_delete_preserves_total():
    pool = initialize(4)
    result = apply_delete(pool, 0)
    assert _approx_sum(result)


def test_delete_does_not_mutate_input():
    pool = initialize(4)
    snapshot = list(pool)
    apply_delete(pool, 1)
    assert pool == snapshot


def test_delete_redistributes_equally_to_remaining_links():
    pool = [25.0, 25.0, 25.0, 25.0]
    result = apply_delete(pool, 0)  # remove a 25-point link
    # Each remaining link gains 25/3 ≈ 8.33.
    expected = 25.0 + 25.0 / 3
    for p in result:
        assert math.isclose(p, expected, abs_tol=TOL)


def test_delete_preserves_relative_differences_among_remaining():
    pool = [10.0, 20.0, 30.0, 40.0]  # sum = 100
    result = apply_delete(pool, 0)  # remove the 10-point link
    # Remaining differences (between original [20, 30, 40]) must be preserved.
    assert math.isclose(result[1] - result[0], 10.0, abs_tol=TOL)
    assert math.isclose(result[2] - result[1], 10.0, abs_tol=TOL)


def test_delete_single_link_returns_empty_pool():
    """Deleting the last link is allowed mathematically — yields []."""
    assert apply_delete([TOTAL_POOL], 0) == []


def test_delete_empty_pool_returns_empty():
    assert apply_delete([], 0) == []


def test_delete_raises_on_out_of_range_index():
    with pytest.raises(IndexError):
        apply_delete(initialize(3), 5)


def test_delete_removes_zero_point_link_safely():
    """Removing a depleted (zero-point) link must leave the remaining links unchanged."""
    pool = [0.0, 50.0, 50.0]
    result = apply_delete(pool, 0)
    assert math.isclose(result[0], 50.0, abs_tol=TOL)
    assert math.isclose(result[1], 50.0, abs_tol=TOL)


# --- combined / scenario tests ------------------------------------------


def test_full_lifecycle_preserves_invariant():
    """Initialize, open repeatedly, add, delete — invariant must always hold."""
    pool = initialize(5)
    assert invariant_holds(pool)

    for _ in range(20):
        pool = apply_open(pool, 0)
        assert invariant_holds(pool)

    pool = apply_add(pool)
    assert invariant_holds(pool)

    pool = apply_delete(pool, 2)
    assert invariant_holds(pool)

    for i in range(len(pool)):
        pool = apply_open(pool, i)
        assert invariant_holds(pool)

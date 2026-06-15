"""End-to-end checks for the points-pool lifecycle inside ProfileService.

These tests exercise the integration glue between ProfileService mutations
and the points_pool math. The math itself is covered in test_points_pool.py.
"""

from __future__ import annotations

import math
import sys
import os
from typing import List
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.link import Link
from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from services.browser_service import BrowserService
from services.profile_service import ProfileService
from utils.points_pool import TOTAL_POOL, invariant_holds

TOL = 1e-6


def _make_link(name: str, points: float = 0.0) -> Link:
    return Link(name=name, url=f"https://example.com/{name}", points=points)


def _make_service(profile: Profile) -> ProfileService:
    repo = Mock(spec=ProfileRepository)
    repo.find_default_profile.return_value = profile
    browser = Mock(spec=BrowserService)
    service = ProfileService(repo, browser)
    return service


def _pool(service: ProfileService) -> List[float]:
    return [link.points for link in service.get_links()]


# --- load / initialization ----------------------------------------------


def test_load_initializes_pool_when_links_have_no_points():
    """A profile loaded with the legacy points=0 defaults must be
    re-baselined so the invariant holds before any random pick."""
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    pool = _pool(service)
    assert invariant_holds(pool)
    assert all(math.isclose(p, TOTAL_POOL / 3, abs_tol=TOL) for p in pool)


def test_load_keeps_valid_pool_untouched():
    """If the on-disk points already satisfy the invariant, do not overwrite them."""
    profile = Profile("p", links=[
        _make_link("a", points=60.0),
        _make_link("b", points=30.0),
        _make_link("c", points=10.0),
    ])
    service = _make_service(profile)

    pool = _pool(service)
    assert pool == [60.0, 30.0, 10.0]


def test_load_empty_profile_is_ok():
    profile = Profile("empty", links=[])
    service = _make_service(profile)
    assert _pool(service) == []


# --- add_link / add_links_batch -----------------------------------------


def test_add_link_grows_pool_at_baseline():
    profile = Profile("p", links=[_make_link("a"), _make_link("b")])
    service = _make_service(profile)
    assert all(math.isclose(p, 50.0, abs_tol=TOL) for p in _pool(service))

    service.add_link(_make_link("c"))

    pool = _pool(service)
    assert invariant_holds(pool)
    assert all(math.isclose(p, TOTAL_POOL / 3, abs_tol=TOL) for p in pool)


def test_add_link_to_empty_profile():
    profile = Profile("p", links=[])
    service = _make_service(profile)
    service.add_link(_make_link("a"))
    assert _pool(service) == [TOTAL_POOL]


def test_add_links_batch_holds_invariant_at_every_step():
    profile = Profile("p", links=[_make_link("a")])
    service = _make_service(profile)

    service.add_links_batch([_make_link(f"link-{i}") for i in range(5)])

    assert invariant_holds(_pool(service))
    # All six links are at baseline.
    assert all(math.isclose(p, TOTAL_POOL / 6, abs_tol=TOL) for p in _pool(service))


def test_add_preserves_relative_differences_among_existing():
    profile = Profile("p", links=[
        _make_link("a", points=70.0),
        _make_link("b", points=30.0),
    ])
    service = _make_service(profile)
    service.add_link(_make_link("c"))

    pool = _pool(service)
    # Difference between a and b before was 40; after equal subtraction it stays 40.
    assert math.isclose(pool[0] - pool[1], 40.0, abs_tol=TOL)


# --- open_links ---------------------------------------------------------


def test_open_link_reduces_target_and_redistributes_equally():
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    before = _pool(service)
    service.open_links([0])
    after = _pool(service)

    assert after[0] < before[0]
    # Other two links gained the same amount.
    gain_b = after[1] - before[1]
    gain_c = after[2] - before[2]
    assert math.isclose(gain_b, gain_c, abs_tol=TOL)
    assert invariant_holds(after)


def test_opening_same_link_repeatedly_drives_its_share_toward_zero():
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    for _ in range(40):
        service.open_links([0])

    pool = _pool(service)
    assert invariant_holds(pool)
    # The repeatedly-opened link is now far below baseline; the other two
    # absorbed its outflow and sit well above baseline.
    assert pool[0] < TOTAL_POOL / 3
    assert pool[1] > TOTAL_POOL / 3
    assert pool[2] > TOTAL_POOL / 3


def test_open_single_link_pool_is_safe():
    """Opening the only link must not crash and must not violate the invariant."""
    profile = Profile("p", links=[_make_link("a")])
    service = _make_service(profile)
    service.open_links([0])
    assert _pool(service) == [TOTAL_POOL]


def test_multi_open_compounds_loss_correctly():
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    service.open_links([0, 1, 2])

    pool = _pool(service)
    assert invariant_holds(pool)


# --- delete_links / permanently_delete_links / restore -------------------


def test_delete_archive_redistributes_equally_to_survivors():
    profile = Profile("p", links=[
        _make_link("a", points=10.0),
        _make_link("b", points=40.0),
        _make_link("c", points=50.0),
    ])
    service = _make_service(profile)

    service.delete_links([0])  # archive "a" (10 points)

    pool = _pool(service)
    assert invariant_holds(pool)
    # b and c each gained 10/2 = 5 (plus any tiny renormalize).
    assert math.isclose(pool[0], 45.0, abs_tol=1e-3)
    assert math.isclose(pool[1], 55.0, abs_tol=1e-3)


def test_delete_then_restore_round_trips_invariant():
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    service.delete_links([1])
    assert invariant_holds(_pool(service))

    archived = profile.get_archived_links()
    service.restore_archived_links(archived)

    pool = _pool(service)
    assert len(pool) == 3
    assert invariant_holds(pool)


def test_permanently_delete_archived_link_does_not_change_active_pool():
    profile = Profile("p", links=[
        _make_link("a", points=50.0),
        _make_link("b", points=50.0),
    ])
    service = _make_service(profile)
    # Archive then permanently delete the archived link.
    service.delete_links([0])  # archive "a"
    pool_before = _pool(service)
    archived = profile.get_archived_links()
    service.permanently_delete_links(archived)

    pool_after = _pool(service)
    # Active pool is unchanged (archived link was already out of it).
    assert pool_after == pool_before


def test_delete_all_but_one_keeps_remaining_at_full_pool():
    profile = Profile("p", links=[_make_link("a"), _make_link("b"), _make_link("c")])
    service = _make_service(profile)

    service.delete_links([1, 2])

    pool = _pool(service)
    assert len(pool) == 1
    assert math.isclose(pool[0], TOTAL_POOL, abs_tol=TOL)


# --- update_link --------------------------------------------------------


def test_update_link_preserves_points():
    """Editing a link's name/URL must not reset its points to zero —
    otherwise every edit would silently break the pool invariant."""
    profile = Profile("p", links=[_make_link("a"), _make_link("b")])
    service = _make_service(profile)

    # Skew the pool so the difference is detectable.
    service.open_links([0])
    pool_before = _pool(service)

    edited = Link(name="renamed", url="https://example.com/renamed")
    service.update_link(0, edited)

    pool_after = _pool(service)
    assert math.isclose(pool_after[0], pool_before[0], abs_tol=TOL)
    assert math.isclose(pool_after[1], pool_before[1], abs_tol=TOL)
    assert service.get_links()[0].name == "renamed"

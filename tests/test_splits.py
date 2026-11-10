import random
import pytest
from app.services.splits import split_equal, split_exact, split_percent
from app.errors import ApiError


def test_split_equal_basic():
    assert split_equal(10000, [1, 2, 3]) == {1: 3334, 2: 3333, 3: 3333}
    # Unordered input gives the same result
    assert split_equal(10000, [3, 1, 2]) == {1: 3334, 2: 3333, 3: 3333}
    assert split_equal(10000, [2, 3, 1]) == {1: 3334, 2: 3333, 3: 3333}


def test_split_equal_small_amount():
    assert split_equal(1, [1, 2, 3]) == {1: 1, 2: 0, 3: 0}


def test_split_percent_basic():
    assert split_percent(100, {1: 3333, 2: 3333, 3: 3334}) == {1: 33, 2: 33, 3: 34}


def test_validation_raises():
    with pytest.raises(ApiError):
        split_percent(100, {1: 5000, 2: 4000})  # sum != 10000
    with pytest.raises(ApiError):
        split_exact(10000, {1: 4000, 2: 5000})  # sum != 10000


def test_property_loop_sum_invariants():
    rng = random.Random(42)
    for _ in range(500):
        n = rng.randint(1, 20)
        user_ids = list(range(1, n + 1))
        amount = rng.randint(1, 10_000_000)

        # Equal split property
        eq_shares = split_equal(amount, user_ids)
        assert sum(eq_shares.values()) == amount

        # Percent split property: generate random partition of 10000
        cuts = sorted([rng.randint(0, 10000) for _ in range(n - 1)])
        pts = [0] + cuts + [10000]
        bps = {uid: pts[i + 1] - pts[i] for i, uid in enumerate(user_ids)}
        assert sum(bps.values()) == 10000

        pct_shares = split_percent(amount, bps)
        assert sum(pct_shares.values()) == amount

import random
import pytest
from app.services.balances import compute_net_balances, simplify_debts


def test_balances_basic_and_sign():
    # A=1, B=2, C=3
    # A pays 90000 for A, B, C equally (30000 each)
    expense = {
        "paid_by": 1,
        "amount_cents": 90000,
        "splits": [
            {"user_id": 1, "share_cents": 30000},
            {"user_id": 2, "share_cents": 30000},
            {"user_id": 3, "share_cents": 30000},
        ],
    }
    net = compute_net_balances([1, 2, 3], [expense], [])
    assert net == {1: 60000, 2: -30000, 3: -30000}

    # Sign test: B pays A 30000 (from_user=2, to_user=1, amount=30000)
    settlement = {
        "from_user": 2,
        "to_user": 1,
        "amount_cents": 30000,
    }
    net_after = compute_net_balances([1, 2, 3], [expense], [settlement])
    assert net_after == {1: 30000, 2: 0, 3: -30000}


def test_empty_and_zero_balances():
    assert simplify_debts({}) == []
    assert simplify_debts({1: 0, 2: 0, 3: 0}) == []


def test_simplify_debts_basic():
    net = {1: 60000, 2: -30000, 3: -30000}
    payments = simplify_debts(net)
    assert len(payments) <= 2
    # Verify applying payments zeros out net
    simulated_net = dict(net)
    for p in payments:
        simulated_net[p["from_user_id"]] += p["amount_cents"]
        simulated_net[p["to_user_id"]] -= p["amount_cents"]
    assert all(val == 0 for val in simulated_net.values())


def test_property_loop_balances_and_simplify():
    rng = random.Random(12345)
    for _ in range(300):
        n = rng.randint(2, 10)
        member_ids = list(range(1, n + 1))

        # Generate random expenses
        num_expenses = rng.randint(0, 10)
        expenses = []
        for _ in range(num_expenses):
            payer = rng.choice(member_ids)
            amount = rng.randint(10, 50000)
            # Pick random subset of participants
            parts = rng.sample(member_ids, rng.randint(1, n))
            # Partition amount among parts
            cuts = sorted([rng.randint(0, amount) for _ in range(len(parts) - 1)])
            pts = [0] + cuts + [amount]
            splits = [{"user_id": uid, "share_cents": pts[i + 1] - pts[i]} for i, uid in enumerate(parts)]
            expenses.append({"paid_by": payer, "amount_cents": amount, "splits": splits})

        # Generate random settlements
        num_settlements = rng.randint(0, 5)
        settlements = []
        for _ in range(num_settlements):
            u1, u2 = rng.sample(member_ids, 2)
            s_amount = rng.randint(10, 20000)
            settlements.append({"from_user": u1, "to_user": u2, "amount_cents": s_amount})

        net = compute_net_balances(member_ids, expenses, settlements)

        # Invariant: sum of nets is always 0
        assert sum(net.values()) == 0

        # Invariant: simplify_debts has at most n - 1 payments
        payments = simplify_debts(net)
        assert len(payments) <= n - 1

        # Invariant: applying payments brings every net to exactly 0
        test_net = dict(net)
        for p in payments:
            test_net[p["from_user_id"]] += p["amount_cents"]
            test_net[p["to_user_id"]] -= p["amount_cents"]
        assert all(val == 0 for val in test_net.values())

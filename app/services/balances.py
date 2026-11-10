from typing import Dict, List, Any


def _get(obj: Any, key: str) -> Any:
    """Helper to access dict key or object attribute."""
    if isinstance(obj, dict):
        return obj[key]
    return getattr(obj, key)


def compute_net_balances(
    member_ids: List[int],
    expenses: List[Any],
    settlements: List[Any],
) -> Dict[int, int]:
    """
    Compute net balance in cents for each member.
    Positive net = the group owes this person.
    Negative net = this person owes the group.
    """
    net: Dict[int, int] = {m: 0 for m in member_ids}
    for e in expenses:
        net[_get(e, "paid_by")] += _get(e, "amount_cents")
        for s in _get(e, "splits"):
            net[_get(s, "user_id")] -= _get(s, "share_cents")
    for st in settlements:
        net[_get(st, "from_user")] += _get(st, "amount_cents")  # payer's debt shrinks
        net[_get(st, "to_user")] -= _get(st, "amount_cents")    # receiver is owed less
    return net


def simplify_debts(net: Dict[int, int]) -> List[Dict[str, int]]:
    """
    Simplify net balances to at most n - 1 transactions.
    Returns [{"from_user_id": ..., "to_user_id": ..., "amount_cents": ...}].
    """
    creditors = sorted(
        [[amt, uid] for uid, amt in net.items() if amt > 0],
        key=lambda x: (-x[0], x[1]),
    )
    debtors = sorted(
        [[-amt, uid] for uid, amt in net.items() if amt < 0],
        key=lambda x: (-x[0], x[1]),
    )

    result: List[Dict[str, int]] = []
    i = 0  # creditor pointer
    j = 0  # debtor pointer

    while i < len(creditors) and j < len(debtors):
        pay = min(creditors[i][0], debtors[j][0])
        if pay > 0:
            result.append({
                "from_user_id": debtors[j][1],
                "to_user_id": creditors[i][1],
                "amount_cents": pay,
            })
        creditors[i][0] -= pay
        debtors[j][0] -= pay
        if creditors[i][0] == 0:
            i += 1
        if debtors[j][0] == 0:
            j += 1

    return result

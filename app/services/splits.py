from typing import Dict, List
from app.errors import ApiError


def format_currency(cents: int) -> str:
    """Format paise to Indian rupee representation without floating point."""
    is_neg = cents < 0
    cents = abs(cents)
    rupees = cents // 100
    paise = cents % 100

    s = str(rupees)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        groups.append(last3)
        formatted = ",".join(groups)
    else:
        formatted = s

    sign = "-" if is_neg else ""
    if paise == 0:
        return f"{sign}₹{formatted}"
    else:
        return f"{sign}₹{formatted}.{paise:02d}"


def split_equal(amount_cents: int, user_ids: List[int]) -> Dict[int, int]:
    """
    Split amount_cents equally among user_ids.
    Sort user_ids ascending. base, rem = divmod(amount_cents, n).
    The first rem users in sorted order get base + 1; the rest get base.
    """
    if not user_ids:
        raise ApiError(422, "validation_error", "At least one participant is required.")
    sorted_ids = sorted(user_ids)
    n = len(sorted_ids)
    base, rem = divmod(amount_cents, n)
    result: Dict[int, int] = {}
    for i, uid in enumerate(sorted_ids):
        result[uid] = base + (1 if i < rem else 0)
    return result


def split_exact(amount_cents: int, values: Dict[int, int]) -> Dict[int, int]:
    """
    Split amount_cents with exact values per participant.
    Each value must be >= 0. The sum must equal amount_cents.
    """
    if not values:
        raise ApiError(422, "validation_error", "At least one participant is required.")
    for val in values.values():
        if val < 0:
            raise ApiError(422, "validation_error", "Values must be non-negative.")
    total = sum(values.values())
    if total != amount_cents:
        x_str = format_currency(total)
        y_str = format_currency(amount_cents)
        raise ApiError(422, "validation_error", f"The amounts add up to {x_str} but the total is {y_str}.")
    return dict(values)


def split_percent(amount_cents: int, basis_points: Dict[int, int]) -> Dict[int, int]:
    """
    Split amount_cents using basis points (33.33% is 3333, 100% is 10000).
    Uses largest-remainder method with integer math only:
    1. For each user: product = amount_cents * bp, floor = product // 10000, frac = product % 10000.
    2. leftover = amount_cents - sum(floors) (always 0 <= leftover < n).
    3. Give +1 to the leftover users with largest frac; ties broken by smaller user_id.
    """
    if not basis_points:
        raise ApiError(422, "validation_error", "At least one participant is required.")
    for bp in basis_points.values():
        if bp < 0 or bp > 10000:
            raise ApiError(422, "validation_error", "Percentage basis points must be between 0 and 10000.")
    total_bp = sum(basis_points.values())
    if total_bp != 10000:
        raise ApiError(422, "validation_error", "The percentages must add up to 100%.")

    floors: Dict[int, int] = {}
    fracs: Dict[int, int] = {}
    for uid, bp in basis_points.items():
        product = amount_cents * bp
        floors[uid] = product // 10000
        fracs[uid] = product % 10000

    leftover = amount_cents - sum(floors.values())
    # Sort candidate user IDs by (-frac, user_id)
    sorted_uids = sorted(basis_points.keys(), key=lambda uid: (-fracs[uid], uid))

    result = dict(floors)
    for i in range(leftover):
        result[sorted_uids[i]] += 1
    return result

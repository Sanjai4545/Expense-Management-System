import pytest
from tests.conftest import signup, make_group


def test_settlements_and_balances(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    signup(client, "Ravi", "ravi@example.com")

    g = make_group(client, h_sanjai, name="Goa Trip", members=["priya@example.com", "ravi@example.com"])
    gid = g["id"]
    uids = {m["name"]: m["id"] for m in g["members"]}
    s_id, p_id, r_id = uids["Sanjai"], uids["Priya"], uids["Ravi"]

    # Sanjai pays 90000 for Sanjai, Priya, Ravi equally (30000 each)
    client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Villa",
            "amount_cents": 90000,
            "paid_by": s_id,
            "split_type": "equal",
            "participants": [{"user_id": s_id}, {"user_id": p_id}, {"user_id": r_id}],
        },
        headers=h_sanjai,
    )

    # Initial balances: Sanjai +60000, Priya -30000, Ravi -30000
    b_resp = client.get(f"/api/groups/{gid}/balances", headers=h_sanjai)
    assert b_resp.status_code == 200
    b_data = b_resp.json()
    bal_map = {b["user_id"]: b["net_cents"] for b in b_data["balances"]}
    assert bal_map[s_id] == 60000
    assert bal_map[p_id] == -30000
    assert bal_map[r_id] == -30000
    assert len(b_data["simplified"]) == 2

    # Priya records payment to Sanjai of 30000
    s_resp = client.post(
        f"/api/groups/{gid}/settlements",
        json={"from_user": p_id, "to_user": s_id, "amount_cents": 30000, "note": "UPI"},
        headers=h_sanjai,
    )
    assert s_resp.status_code == 201
    sid = s_resp.json()["id"]

    # Updated balances: Sanjai +30000, Priya 0, Ravi -30000
    b_after = client.get(f"/api/groups/{gid}/balances", headers=h_sanjai).json()
    bal_after = {b["user_id"]: b["net_cents"] for b in b_after["balances"]}
    assert bal_after[s_id] == 30000
    assert bal_after[p_id] == 0
    assert bal_after[r_id] == -30000
    assert len(b_after["simplified"]) == 1
    assert b_after["simplified"][0]["from_user_id"] == r_id
    assert b_after["simplified"][0]["to_user_id"] == s_id

    # Undo (DELETE) restores balances
    del_resp = client.delete(f"/api/groups/{gid}/settlements/{sid}", headers=h_sanjai)
    assert del_resp.status_code == 204

    b_restored = client.get(f"/api/groups/{gid}/balances", headers=h_sanjai).json()
    bal_res = {b["user_id"]: b["net_cents"] for b in b_restored["balances"]}
    assert bal_res[s_id] == 60000
    assert bal_res[p_id] == -30000


def test_paying_yourself_and_non_member(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    h_out = signup(client, "Outsider", "outsider@example.com")
    out_id = client.get("/api/auth/me", headers=h_out).json()["id"]

    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]

    # Paying yourself gives 422
    r_self = client.post(
        f"/api/groups/{gid}/settlements",
        json={"from_user": s_id, "to_user": s_id, "amount_cents": 1000},
        headers=h_sanjai,
    )
    assert r_self.status_code == 422
    assert r_self.json()["error"]["message"] == "You can't pay yourself."

    # Non-member gives 422
    r_out = client.post(
        f"/api/groups/{gid}/settlements",
        json={"from_user": s_id, "to_user": out_id, "amount_cents": 1000},
        headers=h_sanjai,
    )
    assert r_out.status_code == 422
    assert r_out.json()["error"]["message"] == "Everyone in the split must be a member of this group."


def test_overpayment_reverses_debt_direction(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]

    # Sanjai pays 1000 for Priya only (Priya owes Sanjai 1000)
    client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Coffee",
            "amount_cents": 1000,
            "paid_by": s_id,
            "split_type": "equal",
            "participants": [{"user_id": p_id}],
        },
        headers=h_sanjai,
    )

    # Priya overpays 1500 to Sanjai
    client.post(
        f"/api/groups/{gid}/settlements",
        json={"from_user": p_id, "to_user": s_id, "amount_cents": 1500},
        headers=h_sanjai,
    )

    # Now Priya is owed 500, Sanjai owes 500
    b = client.get(f"/api/groups/{gid}/balances", headers=h_sanjai).json()
    bal = {item["user_id"]: item["net_cents"] for item in b["balances"]}
    assert bal[p_id] == 500
    assert bal[s_id] == -500
    assert b["simplified"][0]["from_user_id"] == s_id
    assert b["simplified"][0]["to_user_id"] == p_id
    assert b["simplified"][0]["amount_cents"] == 500


def test_activity_feed_order_and_types(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]

    # 1. Expense
    client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Item 1", "amount_cents": 1000, "paid_by": s_id, "split_type": "equal", "participants": [{"user_id": p_id}]},
        headers=h_sanjai,
    )
    # 2. Settlement
    client.post(
        f"/api/groups/{gid}/settlements",
        json={"from_user": p_id, "to_user": s_id, "amount_cents": 500},
        headers=h_sanjai,
    )
    # 3. Another Expense
    client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Item 2", "amount_cents": 2000, "paid_by": p_id, "split_type": "equal", "participants": [{"user_id": s_id}]},
        headers=h_sanjai,
    )

    # Get activity
    act_resp = client.get(f"/api/groups/{gid}/activity", headers=h_sanjai)
    assert act_resp.status_code == 200
    feed = act_resp.json()
    assert len(feed) == 3
    # Check types and ordering
    assert feed[0]["type"] == "expense"
    assert feed[0]["expense"]["description"] == "Item 2"
    assert feed[1]["type"] == "settlement"
    assert feed[1]["settlement"]["amount_cents"] == 500
    assert feed[2]["type"] == "expense"
    assert feed[2]["expense"]["description"] == "Item 1"

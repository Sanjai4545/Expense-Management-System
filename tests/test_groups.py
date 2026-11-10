import pytest
from tests.conftest import signup, make_group


def test_create_list_detail_group(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    h_priya = signup(client, "Priya", "priya@example.com")

    # Sanjai creates "Goa Trip"
    g1 = make_group(client, h_sanjai, name="Goa Trip")
    gid1 = g1["id"]

    # Priya creates "Flat 4B"
    g2 = make_group(client, h_priya, name="Flat 4B")
    gid2 = g2["id"]

    # Sanjai lists groups -> only sees Goa Trip
    resp_s = client.get("/api/groups", headers=h_sanjai)
    assert resp_s.status_code == 200
    groups_s = resp_s.json()
    assert len(groups_s) == 1
    assert groups_s[0]["id"] == gid1
    assert groups_s[0]["name"] == "Goa Trip"
    assert groups_s[0]["member_count"] == 1
    assert groups_s[0]["my_balance_cents"] == 0

    # Priya lists groups -> only sees Flat 4B
    resp_p = client.get("/api/groups", headers=h_priya)
    assert resp_p.status_code == 200
    groups_p = resp_p.json()
    assert len(groups_p) == 1
    assert groups_p[0]["id"] == gid2

    # Group detail
    detail = client.get(f"/api/groups/{gid1}", headers=h_sanjai)
    assert detail.status_code == 200
    data = detail.json()
    assert data["name"] == "Goa Trip"
    assert len(data["members"]) == 1
    assert data["members"][0]["name"] == "Sanjai"


def test_non_member_forbidden(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    h_outsider = signup(client, "Outsider", "outsider@example.com")

    g = make_group(client, h_sanjai, name="Secret Group")
    gid = g["id"]
    s_id = g["members"][0]["id"]

    # Outsider gets 403 on group detail, balances, activity, expenses, and settlements
    for url, method, body in [
        (f"/api/groups/{gid}", "get", None),
        (f"/api/groups/{gid}/balances", "get", None),
        (f"/api/groups/{gid}/activity", "get", None),
        (f"/api/groups/{gid}/expenses", "post", {"description": "X", "amount_cents": 100, "paid_by": s_id, "split_type": "equal", "participants": [{"user_id": s_id}]}),
        (f"/api/groups/{gid}/settlements", "post", {"from_user": s_id, "to_user": s_id, "amount_cents": 100}),
    ]:
        if method == "get":
            resp = client.get(url, headers=h_outsider)
        else:
            resp = client.post(url, json=body, headers=h_outsider)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "forbidden"
        assert resp.json()["error"]["message"] == "You're not a member of this group."


def test_my_balance_cents_in_group_list_after_expense(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    g = make_group(client, h_sanjai, name="Goa Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]

    # Sanjai pays 10000 for Sanjai and Priya equally (5000 each)
    client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Lunch",
            "amount_cents": 10000,
            "paid_by": s_id,
            "split_type": "equal",
            "participants": [{"user_id": s_id}, {"user_id": p_id}],
        },
        headers=h_sanjai,
    )

    # Sanjai is owed 5000
    groups_s = client.get("/api/groups", headers=h_sanjai).json()
    assert groups_s[0]["my_balance_cents"] == 5000


def test_add_member_scenarios(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")

    g = make_group(client, h_sanjai, name="Goa Trip")
    gid = g["id"]

    # 1. 404 when email not found
    resp404 = client.post(
        f"/api/groups/{gid}/members",
        json={"email": "nobody@example.com"},
        headers=h_sanjai,
    )
    assert resp404.status_code == 404
    assert resp404.json()["error"]["message"] == "No account found for that email. Ask them to sign up first."

    # 2. Add member case-insensitively
    resp_add = client.post(
        f"/api/groups/{gid}/members",
        json={"email": "PRIYA@EXAMPLE.COM"},
        headers=h_sanjai,
    )
    assert resp_add.status_code == 201
    member = resp_add.json()
    assert member["name"] == "Priya"
    assert member["email"] == "priya@example.com"

    # 3. 409 duplicate member
    resp409 = client.post(
        f"/api/groups/{gid}/members",
        json={"email": "priya@example.com"},
        headers=h_sanjai,
    )
    assert resp409.status_code == 409
    assert resp409.json()["error"]["message"] == "Priya is already in this group."

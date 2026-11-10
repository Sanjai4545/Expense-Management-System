import pytest
from app.models import ExpenseSplit, Expense
from tests.conftest import signup, make_group


def test_create_expenses_equal_exact_percent(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    signup(client, "Ravi", "ravi@example.com")

    # Group with Sanjai (owner), Priya, Ravi
    g = make_group(client, h_sanjai, name="Goa Trip", members=["priya@example.com", "ravi@example.com"])
    gid = g["id"]
    uids = [m["id"] for m in g["members"]]
    s_id, p_id, r_id = uids[0], uids[1], uids[2]

    # 1. Equal split
    r_eq = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "amount_cents": 90000,
            "paid_by": s_id,
            "split_type": "equal",
            "participants": [{"user_id": s_id}, {"user_id": p_id}, {"user_id": r_id}],
        },
        headers=h_sanjai,
    )
    assert r_eq.status_code == 201
    eq_data = r_eq.json()
    assert sum(s["share_cents"] for s in eq_data["splits"]) == 90000

    # 2. Exact split
    r_ex = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Taxi",
            "amount_cents": 15000,
            "paid_by": p_id,
            "split_type": "exact",
            "participants": [
                {"user_id": s_id, "value": 5000},
                {"user_id": p_id, "value": 10000},
            ],
        },
        headers=h_sanjai,
    )
    assert r_ex.status_code == 201
    ex_data = r_ex.json()
    assert sum(s["share_cents"] for s in ex_data["splits"]) == 15000

    # 3. Percent split
    r_pct = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Groceries",
            "amount_cents": 10000,
            "paid_by": r_id,
            "split_type": "percent",
            "participants": [
                {"user_id": s_id, "value": 3333},
                {"user_id": p_id, "value": 3333},
                {"user_id": r_id, "value": 3334},
            ],
        },
        headers=h_sanjai,
    )
    assert r_pct.status_code == 201
    pct_data = r_pct.json()
    assert sum(s["share_cents"] for s in pct_data["splits"]) == 10000


def test_amount_validation_strictint(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    g = make_group(client, h_sanjai, name="Trip")
    gid = g["id"]
    uid = g["members"][0]["id"]

    # Float amount (10.5)
    r_flt = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 10.5, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert r_flt.status_code == 422

    # String amount ("100")
    r_str = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": "100", "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert r_str.status_code == 422

    # Zero amount
    r_zero = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 0, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert r_zero.status_code == 422

    # Negative amount
    r_neg = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": -500, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert r_neg.status_code == 422

    # Over limit (> 1,000,000,000)
    r_over = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 1_000_000_001, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert r_over.status_code == 422


def test_participants_and_membership_validation(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    h_outsider = signup(client, "Outsider", "outsider@example.com")

    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]
    out_id = client.get("/api/auth/me", headers=h_outsider).json()["id"]

    # Participant not in group
    r_part = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 1000, "paid_by": s_id, "split_type": "equal", "participants": [{"user_id": s_id}, {"user_id": out_id}]},
        headers=h_sanjai,
    )
    assert r_part.status_code == 422
    assert r_part.json()["error"]["message"] == "Everyone in the split must be a member of this group."

    # Payer not in group
    r_payer = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 1000, "paid_by": out_id, "split_type": "equal", "participants": [{"user_id": s_id}]},
        headers=h_sanjai,
    )
    assert r_payer.status_code == 422
    assert r_payer.json()["error"]["message"] == "Everyone in the split must be a member of this group."

    # Duplicate participants
    r_dup = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Test", "amount_cents": 1000, "paid_by": s_id, "split_type": "equal", "participants": [{"user_id": s_id}, {"user_id": s_id}]},
        headers=h_sanjai,
    )
    assert r_dup.status_code == 422
    assert r_dup.json()["error"]["code"] == "validation_error"


def test_mismatch_exact_and_percent_messages(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com"])
    gid = g["id"]
    s_id, p_id = g["members"][0]["id"], g["members"][1]["id"]

    # Exact total mismatch
    r_ex = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Taxi",
            "amount_cents": 10000,
            "paid_by": s_id,
            "split_type": "exact",
            "participants": [{"user_id": s_id, "value": 3000}, {"user_id": p_id, "value": 3000}],
        },
        headers=h_sanjai,
    )
    assert r_ex.status_code == 422
    assert "The amounts add up to" in r_ex.json()["error"]["message"]

    # Percent total not 10000
    r_pct = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Lunch",
            "amount_cents": 10000,
            "paid_by": s_id,
            "split_type": "percent",
            "participants": [{"user_id": s_id, "value": 5000}, {"user_id": p_id, "value": 4000}],
        },
        headers=h_sanjai,
    )
    assert r_pct.status_code == 422
    assert r_pct.json()["error"]["message"] == "The percentages must add up to 100%."


def test_update_replaces_splits_and_delete_cascades(client, db):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    signup(client, "Priya", "priya@example.com")
    signup(client, "Ravi", "ravi@example.com")
    g = make_group(client, h_sanjai, name="Trip", members=["priya@example.com", "ravi@example.com"])
    gid = g["id"]
    s_id, p_id, r_id = g["members"][0]["id"], g["members"][1]["id"], g["members"][2]["id"]

    # Create expense with 3 splits
    resp = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Initial",
            "amount_cents": 9000,
            "paid_by": s_id,
            "split_type": "equal",
            "participants": [{"user_id": s_id}, {"user_id": p_id}, {"user_id": r_id}],
        },
        headers=h_sanjai,
    )
    eid = resp.json()["id"]
    assert db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == eid).count() == 3

    # Update to 2 splits
    up_resp = client.put(
        f"/api/groups/{gid}/expenses/{eid}",
        json={
            "description": "Updated",
            "amount_cents": 6000,
            "paid_by": p_id,
            "split_type": "equal",
            "participants": [{"user_id": s_id}, {"user_id": p_id}],
        },
        headers=h_sanjai,
    )
    assert up_resp.status_code == 200
    assert db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == eid).count() == 2

    # Delete cascades splits
    del_resp = client.delete(f"/api/groups/{gid}/expenses/{eid}", headers=h_sanjai)
    assert del_resp.status_code == 204
    assert db.query(Expense).filter(Expense.id == eid).count() == 0
    assert db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == eid).count() == 0


def test_permissions_edit_delete(client):
    h_owner = signup(client, "Owner", "owner@example.com")
    h_creator = signup(client, "Creator", "creator@example.com")
    h_member = signup(client, "Member", "member@example.com")

    g = make_group(client, h_owner, name="Perm Group", members=["creator@example.com", "member@example.com"])
    gid = g["id"]
    uids = {m["email"]: m["id"] for m in g["members"]}

    # Creator creates expense
    r = client.post(
        f"/api/groups/{gid}/expenses",
        json={"description": "Pizza", "amount_cents": 3000, "paid_by": uids["creator@example.com"], "split_type": "equal", "participants": [{"user_id": uids["creator@example.com"]}]},
        headers=h_creator,
    )
    eid = r.json()["id"]

    # Member (neither creator nor owner) tries to edit -> 403
    r_edit_denied = client.put(
        f"/api/groups/{gid}/expenses/{eid}",
        json={"description": "Hacked", "amount_cents": 3000, "paid_by": uids["creator@example.com"], "split_type": "equal", "participants": [{"user_id": uids["creator@example.com"]}]},
        headers=h_member,
    )
    assert r_edit_denied.status_code == 403
    assert r_edit_denied.json()["error"]["message"] == "Only the person who added this expense or the group owner can change it."

    # Member tries to delete -> 403
    r_del_denied = client.delete(f"/api/groups/{gid}/expenses/{eid}", headers=h_member)
    assert r_del_denied.status_code == 403

    # Creator can edit
    r_creator_edit = client.put(
        f"/api/groups/{gid}/expenses/{eid}",
        json={"description": "Pizza Party", "amount_cents": 3000, "paid_by": uids["creator@example.com"], "split_type": "equal", "participants": [{"user_id": uids["creator@example.com"]}]},
        headers=h_creator,
    )
    assert r_creator_edit.status_code == 200

    # Owner can delete
    r_owner_del = client.delete(f"/api/groups/{gid}/expenses/{eid}", headers=h_owner)
    assert r_owner_del.status_code == 204


def test_expense_from_another_group_returns_404(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    g1 = make_group(client, h_sanjai, name="Group 1")
    g2 = make_group(client, h_sanjai, name="Group 2")
    uid = g1["members"][0]["id"]

    r = client.post(
        f"/api/groups/{g1['id']}/expenses",
        json={"description": "Exp", "amount_cents": 1000, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    eid = r.json()["id"]

    # Attempt to edit in group 2
    resp = client.put(
        f"/api/groups/{g2['id']}/expenses/{eid}",
        json={"description": "Exp", "amount_cents": 1000, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    assert resp.status_code == 404


def test_atomicity_failing_update_leaves_original_unchanged(client):
    h_sanjai = signup(client, "Sanjai", "sanjai@example.com")
    g = make_group(client, h_sanjai, name="Group 1")
    uid = g["members"][0]["id"]

    r = client.post(
        f"/api/groups/{g['id']}/expenses",
        json={"description": "Original", "amount_cents": 1000, "paid_by": uid, "split_type": "equal", "participants": [{"user_id": uid}]},
        headers=h_sanjai,
    )
    eid = r.json()["id"]

    # Try invalid update (exact mismatch)
    bad_up = client.put(
        f"/api/groups/{g['id']}/expenses/{eid}",
        json={"description": "Corrupted", "amount_cents": 1000, "paid_by": uid, "split_type": "exact", "participants": [{"user_id": uid, "value": 500}]},
        headers=h_sanjai,
    )
    assert bad_up.status_code == 422

    # Verify original is still intact by checking group expenses or retrieving it
    # We can fetch through group list or verify description
    summary = client.get("/api/groups", headers=h_sanjai).json()
    assert summary[0]["my_balance_cents"] == 0  # paid 1000, share 1000

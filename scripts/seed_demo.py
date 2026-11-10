"""
Seed demo data for Halfway application.
Run with: python -m scripts.seed_demo
"""

import sys
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement
from app.security import hash_password
from app.services.splits import split_equal, split_exact, split_percent


def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        demo_password = "Demo@1234"
        users_data = [
            {"name": "Sanjai", "email": "sanjai@example.com"},
            {"name": "Priya", "email": "priya@example.com"},
            {"name": "Ravi", "email": "ravi@example.com"},
            {"name": "Asha", "email": "asha@example.com"},
        ]

        users = {}
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                existing = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=hash_password(demo_password),
                )
                db.add(existing)
                db.flush()
            users[u["email"]] = existing

        # Check or create group "Goa Trip"
        sanjai = users["sanjai@example.com"]
        priya = users["priya@example.com"]
        ravi = users["ravi@example.com"]
        asha = users["asha@example.com"]

        group = db.query(Group).filter(Group.name == "Goa Trip", Group.owner_id == sanjai.id).first()
        if not group:
            group = Group(name="Goa Trip", owner_id=sanjai.id)
            db.add(group)
            db.flush()

            # Add all four members
            for u in [sanjai, priya, ravi, asha]:
                db.add(GroupMember(group_id=group.id, user_id=u.id))
            db.flush()

            today = datetime.now(timezone.utc).date()

            # 5 mixed expenses
            # 1. Equal split: Villa rental (₹12,000)
            exp1_amount = 1_200_000
            exp1_uids = [sanjai.id, priya.id, ravi.id, asha.id]
            exp1_shares = split_equal(exp1_amount, exp1_uids)
            exp1 = Expense(
                group_id=group.id,
                paid_by=sanjai.id,
                created_by=sanjai.id,
                description="Beach Villa Rental",
                amount_cents=exp1_amount,
                split_type="equal",
                expense_date=today - timedelta(days=3),
            )
            db.add(exp1)
            db.flush()
            for uid, share in exp1_shares.items():
                db.add(ExpenseSplit(expense_id=exp1.id, user_id=uid, share_cents=share))

            # 2. Equal split: Dinner (₹3,600)
            exp2_amount = 360_000
            exp2_uids = [sanjai.id, priya.id, ravi.id, asha.id]
            exp2_shares = split_equal(exp2_amount, exp2_uids)
            exp2 = Expense(
                group_id=group.id,
                paid_by=priya.id,
                created_by=priya.id,
                description="Dinner at Fisherman's Wharf",
                amount_cents=exp2_amount,
                split_type="equal",
                expense_date=today - timedelta(days=2),
            )
            db.add(exp2)
            db.flush()
            for uid, share in exp2_shares.items():
                db.add(ExpenseSplit(expense_id=exp2.id, user_id=uid, share_cents=share))

            # 3. Exact split: Water sports (₹8,000)
            exp3_amount = 800_000
            exp3_values = {sanjai.id: 250_000, priya.id: 250_000, ravi.id: 300_000}
            exp3_shares = split_exact(exp3_amount, exp3_values)
            exp3 = Expense(
                group_id=group.id,
                paid_by=ravi.id,
                created_by=ravi.id,
                description="Scuba Diving & Water Sports",
                amount_cents=exp3_amount,
                split_type="exact",
                expense_date=today - timedelta(days=1),
            )
            db.add(exp3)
            db.flush()
            for uid, share in exp3_shares.items():
                db.add(ExpenseSplit(expense_id=exp3.id, user_id=uid, share_cents=share))

            # 4. Percent split: Airport Taxi (₹2,400)
            exp4_amount = 240_000
            exp4_bps = {sanjai.id: 2500, priya.id: 2500, ravi.id: 2500, asha.id: 2500}
            exp4_shares = split_percent(exp4_amount, exp4_bps)
            exp4 = Expense(
                group_id=group.id,
                paid_by=asha.id,
                created_by=asha.id,
                description="Airport Taxi & Highway Tolls",
                amount_cents=exp4_amount,
                split_type="percent",
                expense_date=today - timedelta(days=1),
            )
            db.add(exp4)
            db.flush()
            for uid, share in exp4_shares.items():
                db.add(ExpenseSplit(expense_id=exp4.id, user_id=uid, share_cents=share))

            # 5. Equal split: Breakfast at Cafe (₹1,000)
            exp5_amount = 100_000
            exp5_uids = [sanjai.id, priya.id]
            exp5_shares = split_equal(exp5_amount, exp5_uids)
            exp5 = Expense(
                group_id=group.id,
                paid_by=sanjai.id,
                created_by=sanjai.id,
                description="Breakfast at Cafe",
                amount_cents=exp5_amount,
                split_type="equal",
                expense_date=today,
            )
            db.add(exp5)
            db.flush()
            for uid, share in exp5_shares.items():
                db.add(ExpenseSplit(expense_id=exp5.id, user_id=uid, share_cents=share))

            # 1 settlement: Priya pays Sanjai ₹1,000 via UPI
            settlement = Settlement(
                group_id=group.id,
                from_user=priya.id,
                to_user=sanjai.id,
                amount_cents=100_000,
                note="UPI",
                created_by=priya.id,
            )
            db.add(settlement)

        db.commit()

        print("\n==========================================")
        print("  Demo data seeded successfully!")
        print("==========================================")
        print("Group: 'Goa Trip' with 4 members, 5 expenses, and 1 settlement.\n")
        print("Logins (Password: Demo@1234):")
        for u in users_data:
            print(f"  • {u['name']}: {u['email']}")
        print("==========================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

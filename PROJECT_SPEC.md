# Halfway: Bill Splitting App Specification

## 1. Product summary
Halfway lets a group of friends share costs and always know who owes whom.
- A person signs up and logs in.
- They create a group (for example "Goa Trip") and add friends who already have accounts.
- Anyone in the group adds an expense: who paid, how much, and how it is split.
- The app shows each person's balance and the fewest payments needed to settle everyone.
- People record payments when they settle up.
- Every group has an activity feed of expenses and payments.
Currency is fixed to Indian Rupees (₹). Multi-currency is out of scope.

## 2. Quality bar (non-negotiable)
1. No runtime errors. Server logs show no tracebacks during normal use. Browser console shows no errors or warnings.
2. Money is always an integer number of paise (1 ₹ = 100 paise). No float or Decimal for money anywhere in backend or frontend logic. Floats are allowed only in the single display-formatting helper.
3. Server is the source of truth. The client never sends computed shares for equal or percent splits. The server computes them.
4. Every group route checks membership.
5. Every user-visible string from the database is rendered with textContent (or the el() helper), never innerHTML.
6. All tests pass (pytest -q exits 0), including the invariant tests.
7. The UI works from 360px wide to 1440px wide, with visible keyboard focus and no horizontal scrolling.

## 3. Tech stack
- Python 3.11+
- FastAPI, Pydantic v2
- SQLite via SQLAlchemy 2.0 (sync, Session, typed Mapped[...] models)
- Auth: JWT with PyJWT (HS256), passwords hashed with bcrypt package directly
- Config: python-dotenv, values from .env
- Frontend: Plain HTML, CSS, JavaScript ES modules. No framework, no build step.
- Tests: pytest, FastAPI TestClient (needs httpx)

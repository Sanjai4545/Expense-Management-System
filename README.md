# Halfway — Bill Splitting App

Halfway lets a group of friends share costs and always know who owes whom. Built with FastAPI, SQLite, and vanilla ES modules (no framework, no build step).

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Virtual environment tool (e.g. `venv`)

### 2. Setup Virtual Environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure `SECRET_KEY` is set:
```env
SECRET_KEY=halfway-super-secret-key-for-development-2026
DATABASE_URL=sqlite:///./halfway.db
```

### 5. Run the Server
```bash
uvicorn app.main:app --reload
```
Open your browser at `http://127.0.0.1:8000/`.

### 6. Run the Test Suite
All backend tests, algorithm invariant tests, and property loops can be executed with:
```bash
pytest -q
```

### 7. Seed Demo Data
To populate the database with sample users (`sanjai@example.com`, `priya@example.com`, `ravi@example.com`, `asha@example.com`) and the "Goa Trip" group with mixed expenses and a settlement:
```bash
python -m scripts.seed_demo
```
All seeded accounts use the password: `Demo@1234`.

---

## Architectural Decisions

1. **Integer Paise for All Financial Calculations**:
   - Currency is fixed to Indian Rupees (₹).
   - All backend database tables, Pydantic request models, and internal algorithms operate strictly on integer paise (1 ₹ = 100 paise).
   - In accordance with the non-negotiable quality bar, no `float` or `Decimal` is used anywhere in backend or frontend logic.
   - The only place floating-point division is allowed is in the single display-formatting helper (`formatPaise` in `frontend/js/money.js`).

2. **Core Pure Services**:
   - `app/services/splits.py`: Implements `split_equal` (with divmod and deterministic remainder distribution), `split_exact`, and `split_percent` (largest-remainder integer method using basis points where 100% = 10,000).
   - `app/services/balances.py`: Pure net balance calculation (`compute_net_balances`) and debt simplification (`simplify_debts`) via two-pointer credit-debt matching.

3. **Strict Validation & Uniform Error Schema**:
   - All money and user identifier fields enforce `StrictInt` to prevent lax coercion of floats or strings.
   - All API errors (validation, 401, 403, 404, 409, 500) follow the uniform format:
     ```json
     {
       "error": {
         "code": "<error_code>",
         "message": "<human_readable_message>",
         "fields": { "<field_name>": "<field_message>" }
       }
     }
     ```

4. **Zero-Framework Vanilla Frontend**:
   - Pure HTML, CSS (design tokens in `css/tokens.css`, resets and typography in `css/base.css`, components in `css/components.css`), and JavaScript ES modules.
   - Single origin: FastAPI serves static files at `/` with hash routing (`#/login`, `#/signup`, `#/groups`, `#/groups/:id`).
   - Every dynamic string from the API and users is safely created using `document.createTextNode` via the `el()` helper. Neither `innerHTML`, `outerHTML`, nor `insertAdjacentHTML` are ever used for data rendering.
   - Native `<dialog>` element handles focus trap, Escape key closing, and modal state.

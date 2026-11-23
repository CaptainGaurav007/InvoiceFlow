# InvoiceFlow

A beginner-friendly invoice and payment reconciliation REST API. Built for learning **SQL, relational database design, atomic transactions, duplicate-payment prevention and integration testing**. No real money is processed.

## Stack
Python, FastAPI, SQLAlchemy 2, PostgreSQL (SQLite default for quick start), Pytest.

## Quick start

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** and use the interactive Swagger interface.

By default, the app creates `invoiceflow.db` using SQLite so you can try it immediately. **For the PostgreSQL version you should show on your CV**, install PostgreSQL, create a database named `invoiceflow`, and set `DATABASE_URL` as shown in `.env.example` (the `.env` file is an example only; export the environment variable yourself):

PowerShell:
```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/invoiceflow"
uvicorn app.main:app --reload
```

## Example workflow

1. `POST /customers` with `{"name":"Asha","email":"asha@example.com"}`
2. `POST /invoices` with `{"customer_id":1,"amount_cents":1000}`
3. `POST /payments` with `{"invoice_id":1,"amount_cents":400,"external_reference":"bank-txn-001"}`
4. `GET /invoices/1/balance` → 600 cents outstanding, `PARTIALLY_PAID`
5. `POST /payments` with `{"invoice_id":1,"amount_cents":600,"external_reference":"bank-txn-002"}`
6. `GET /invoices/1/balance` → 0 cents outstanding, `PAID`
7. `GET /reconciliation` → invoice balances and unmatched imported payments.

## Database model

- `customers(id, name, email UNIQUE)`
- `invoices(id, customer_id FK, amount_cents, status)`
- `payments(id, invoice_id NULLABLE FK, amount_cents, external_reference UNIQUE)`

All amounts use **integer cents**, never floating-point currency amounts.

## Why transactions matter

`POST /payments` adds a payment and changes the invoice status in **one database commit**. If an insert fails, the transaction rolls back, preventing a saved payment with an unsaved status change. `external_reference` has a unique database constraint to reject duplicates.

## Run tests

```bash
pytest -q
```

Tests exercise the HTTP API and real SQLAlchemy persistence using an isolated SQLite database. **For PostgreSQL-specific integration confidence, run an additional test suite against a disposable PostgreSQL database**; these SQLite tests alone do not validate PostgreSQL behavior.

## Known limitations / next steps

- This is an educational MVP, not a production billing service.
- No authentication, authorization, refunds, currency conversion or actual payment gateway.
- **Concurrent payments to the same invoice are not protected from races.** A production design needs database row locking/conditional updates and PostgreSQL concurrency tests.
- `POST /payments/import` stores unknown invoice references as unmatched, but does not preserve the originally requested invoice ID; a real import flow would retain the raw source reference for later reconciliation.
- Duplicate references return HTTP 409 (deduplication), not full replay-safe idempotent responses.
- Tables are created automatically for learning; use Alembic migrations for a deployed app.
- No forced crash-in-the-middle rollback test yet; the current tests cover validation failures and state preservation.

## Interview talking points

Explain foreign keys, uniqueness, why money uses integer cents, what `flush()` vs `commit()` means, how outstanding balance is calculated with `SUM()`, and what is **not** concurrency-safe in the MVP.

Do not claim production-grade concurrency, PostgreSQL-specific integration tests, or performance numbers until you've implemented and verified them.

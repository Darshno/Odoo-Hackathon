
# Brightloop Subscription Management System

Brightloop is a full-stack subscription operations system. Phase 1 provides authentication, role-based access, user management, profiles, and dashboards. Phase 2 adds product catalog management, product variants, and validated recurring subscription plans.

## Stack

The frontend uses React, Vite, JavaScript/JSX, React Router, Axios, Lucide React, and custom CSS. The backend uses Python, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic, PostgreSQL-compatible database URLs, JWT bearer authentication, and Argon2 password hashing. Backend tests use pytest; frontend tests use Vitest and React Testing Library.

## Structure

`frontend/` contains the Vite React application, reusable components, layouts, pages, services, hooks, utilities, and the static route manifest. `backend/` contains the FastAPI application, API routes, core settings/security/dependencies, SQLAlchemy models, schemas, services, Alembic migrations, bootstrap command, and tests.

## Database setup

Production and standard development are documented for PostgreSQL. Create a database and user, then set `DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg://brightloop:password@localhost:5432/brightloop`. The SQLAlchemy layer also supports SQLite for isolated tests and a compatible MySQL DSN if you use a managed environment that provides one.

The initialized managed preview database is MySQL-compatible. It can be used with the injected `DATABASE_URL`; the application normalizes a generic `mysql://` URL to PyMySQL automatically. A PostgreSQL deployment remains the recommended external production target from the original specification. Schema changes are always made through Alembic rather than automatic table creation.

## Environment configuration

Copy `backend/.env.example` to `backend/.env` and replace placeholders locally. Copy `frontend/.env.example` to `frontend/.env` when you need a non-default API base URL. Never commit `.env` files or credentials.

Important backend variables are `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `ACCESS_TOKEN_EXPIRE_MINUTES`, reset-token settings, SMTP settings, `FRONTEND_URL`, the three `BOOTSTRAP_ADMIN_*` values, and billing scheduler settings. `BILLING_SCHEDULER_ENABLED` defaults to `true`; `BILLING_SCHEDULER_INTERVAL_SECONDS` defaults to 3600 and must be at least 60. SMTP is optional in development. Without it, the API returns a preview token only when `ENVIRONMENT=development` and `RESET_PREVIEW_ENABLED=true`; it never claims an email was delivered. In production and staging, the app fails fast if `SECRET_KEY` is missing, `DATABASE_URL` is SQLite, or reset preview is enabled. The frontend installs Tailwind as requested, but the delivered interface intentionally uses the custom CSS design system rather than long utility strings.

The project is validated on Python 3.12. The backend dependency set is intentionally pinned to a Python 3.12-compatible toolchain; newer 3.15 environments may fail during native wheel builds for transitive dependencies such as `PyYAML`. Use the 3.12 interpreter for local setup and validation unless a compatible toolchain is confirmed separately.


## Linux/macOS backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Windows PowerShell backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## First administrator

After `alembic upgrade head`, set `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_EMAIL`, and `BOOTSTRAP_ADMIN_PASSWORD` in `backend/.env`. The password must satisfy the policy: at least 9 characters, one uppercase letter, one lowercase letter, and one special character. Run from `backend/` with the virtual environment active:

```bash
python bootstrap_admin.py
```

The command refuses to create a second administrator and is not an HTTP endpoint. Public registration always creates a CUSTOMER.

## Frontend

Install pnpm 10 if needed, then run:

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend listens on `http://localhost:3000` and proxies `/api`, `/docs`, and `/openapi.json` to FastAPI on port 8000. Build for production with `pnpm build`; preview the build with `pnpm preview`.

## Tests

Backend tests use an isolated in-memory SQLite database and do not touch the configured development database:

```bash
cd backend
pytest
```

Frontend tests, when present, run with:

```bash
cd frontend
pnpm test
```

## Swagger

With FastAPI running, open `http://localhost:8000/docs` or use the proxied frontend origin at `http://localhost:3000/docs`.

## Password reset email

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`. The application sends a link to `/reset-password?token=...` and stores only a SHA-256 token hash. Tokens expire after approximately 30 minutes, are invalidated when a new request is made, and can be used once. Forgot-password responses are intentionally generic so they do not reveal account existence.

## Common fixes

If imports are unresolved in an editor, activate the backend virtual environment and select that interpreter. If migrations cannot connect, verify the SQLAlchemy driver prefix matches the installed driver (`postgresql+psycopg` for PostgreSQL or `mysql+pymysql` for a MySQL-compatible DSN). If the frontend cannot reach the API, confirm FastAPI is listening on port 8000 and that Vite is using the configured proxy. If a browser displays an old route after a build, restart Vite and confirm `frontend/public/manus-routes.json` is served as JSON.

## Phase 2 catalog

Run `alembic upgrade head` to apply the catalog migration. ADMIN and STAFF can create/update/activate/deactivate products, variants, and plans. CUSTOMER accounts can read active, currently available catalog records only; cost prices and internal notes are omitted from customer responses. Products include type, SKU, sales/cost prices, currency, notes, and creator; variants add independent prices and JSON attributes. Product and variant references are protected from deletion. Plans support DAILY, WEEKLY, MONTHLY, and YEARLY billing, minimum quantities, availability dates, pause/renewal/early-closure/auto-close controls, and paginated search/filter/sort APIs. The authenticated dashboard exposes Products and Plans routes backed by these APIs.

## Phase 3 quotations

Run `alembic upgrade head` to apply migration `0003_quotations`. ADMIN and STAFF can create, edit, list, send, and cancel quotations for active CUSTOMER accounts. Customers can view only their own quotations and accept or reject quotations in `SENT` status. Quotation lines snapshot the product, variant, plan, SKU, billing interval, and decimal price at creation time; later catalog changes do not alter existing quotations. Quotation totals use `Decimal` arithmetic and quotation numbers use the `Q-YYYY-000001` format. Quotation acceptance does not activate subscriptions or create invoices or payments.

Quotation APIs are available under `/api/quotations` with paginated list/detail responses and transition endpoints for `/send`, `/accept`, `/reject`, and `/cancel`.

Quotation templates are available under `/api/quotations/templates`. ADMIN and STAFF can create, update, list, activate, and deactivate templates. Templates contain validated plan/product/variant lines and a validity period in days. `POST /api/quotations/from-template` copies the lines and snapshots current eligible catalog prices into a new quotation without mutating the template. Quotation records also support start dates, payment terms, tax rates, tax totals, and automatic expiry of open quotations after `valid_until`.

## Phase 4 subscriptions

Run `alembic upgrade head` to apply migration `0005_subscriptions`. An accepted quotation can be converted once through `POST /api/subscriptions/from-quotation/{quotation_id}`. The conversion creates an ACTIVE subscription and historical subscription lines with the accepted prices, taxes, product/plan names, billing interval, pause rule, and renewal rule. The database enforces one subscription per quotation.

Subscription endpoints:

```text
GET  /api/subscriptions
GET  /api/subscriptions/{subscription_id}
POST /api/subscriptions/from-plan/{plan_id}
POST /api/subscriptions/from-quotation/{quotation_id}
POST /api/subscriptions/{subscription_id}/activate
POST /api/subscriptions/{subscription_id}/pause
POST /api/subscriptions/{subscription_id}/resume
POST /api/subscriptions/{subscription_id}/renew
POST /api/subscriptions/{subscription_id}/close
POST /api/subscriptions/process-due
```

Customers can select an active plan in **Choose a Plan**. `POST /api/subscriptions/from-plan/{plan_id}` accepts `{"quantity": 1}` (quantity must meet the plan minimum) and creates an accepted quotation, an ACTIVE subscription, and its first issued invoice in one transaction. The response includes both `subscription` and `invoice`. The purchased subscription appears in the customer's Subscriptions page and the invoice appears in Invoices. Customers can also accept a staff-sent quotation; the frontend then converts it to a subscription and creates the first invoice. No payment gateway is connected, so payments must still be recorded by ADMIN/STAFF.

Subscription statuses are `ACTIVE`, `PAUSED`, and `CLOSED`. ACTIVE subscriptions may be paused when every historical line permits pausing; the owning customer or ADMIN/STAFF can pause or resume them. ADMIN/STAFF retain activate, renew, close, and due-processing permissions. CLOSED subscriptions cannot be reactivated. Renewal advances `last_billing_date` and `next_billing_date` only when every line permits renewal. Daily, weekly, monthly, and yearly billing dates are calculated with calendar-aware month/year handling. Customers can view only their own subscriptions and invoices.

`process_due_subscriptions` is a callable service used by the `/api/subscriptions/process-due` ADMIN/STAFF endpoint. Due processing generates recurring invoices before advancing subscription dates. The FastAPI app also starts an in-process billing scheduler by default: it runs one billing cycle at startup and then repeats at the configured interval. Set `BILLING_SCHEDULER_ENABLED=false` to disable it. The scheduler calls the same idempotent billing service as the manual endpoint; database locking and the invoice subscription-period uniqueness constraint protect repeated processing. Each running API process starts its own scheduler, so use a single API worker/instance for predictable scheduling, or disable this scheduler and invoke the processing endpoint from a dedicated external scheduler in multi-instance deployments.

## Task 3 billing and payments

Run `alembic upgrade head` to apply migration `0006_billing`, which adds invoices, historical invoice lines, discounts, payments, and payment allocations. Billing APIs are under `/api/billing`:

```text
GET  /api/billing/invoices
GET  /api/billing/invoices/{invoice_id}
GET  /api/billing/analytics?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
POST /api/billing/invoices/generate/{subscription_id}
POST /api/billing/invoices/process-due
POST /api/billing/invoices/{invoice_id}/issue
POST /api/billing/invoices/{invoice_id}/void
GET  /api/billing/payments
GET  /api/billing/payments/{payment_id}
POST /api/billing/payments
GET  /api/billing/discounts
POST /api/billing/discounts
POST /api/billing/discounts/{discount_id}/activate
POST /api/billing/discounts/{discount_id}/deactivate
```

Only ACTIVE subscriptions can generate invoices. PAUSED and CLOSED subscriptions are rejected. Invoice periods are protected by a database uniqueness constraint, so repeated billing calls do not create duplicates. The first invoice period begins on the subscription start date; later periods begin on the previous billing boundary. Invoice lines preserve subscription historical prices and taxes. Invoices are issued immediately by default; `POST /invoices/generate/{subscription_id}` accepts `{"issue_immediately": false}` to create a draft, which can later be issued through `/issue`. Unpaid invoices may be voided; paid or partially paid invoices cannot be voided.

Discounts support fixed and percentage values, validity windows, minimum-subtotal thresholds, and global usage limits; a fixed discount requires its currency. One discount can be attached to an invoice. Discount use is counted when an invoice is generated, including when generated as a draft. Payments support partial allocation and update `amount_paid`, `amount_due`, and invoice status transactionally. A payment does not mark an invoice paid unless the outstanding balance reaches zero. Invoice due dates currently default to 30 days after issue; quotation payment terms are copied as display text and are not interpreted to determine the due date.

ADMIN and STAFF can generate/issue/void invoices, manage discounts, record payments, and view revenue analytics. Authenticated customers can list and view only their own invoices and payments; analytics is not available to customers. The analytics endpoint defaults to the last 30 days of confirmed payments, accepts optional `date_from` and `date_to` filters, and returns paid revenue and current outstanding balances grouped by currency, subscription status counts, and the five latest confirmed payments in the selected range. Amounts in different currencies are never combined. The in-process billing scheduler is enabled by default; alternatively, disable it and invoke `/api/billing/invoices/process-due` or `/api/subscriptions/process-due` from an external scheduler. No payment gateway is configured.

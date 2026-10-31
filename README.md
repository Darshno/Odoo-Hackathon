# Brightloop Subscription Management System

Brightloop is a Phase 1 full-stack foundation for subscription operations. It includes a polished public landing page, real email/password authentication, password reset, role-based authorization, explicit first-admin bootstrap, admin user management, profile management, and honest role-specific dashboards. Products, plans, invoices, payments, and analytics are intentionally deferred to Phase 2.

## Stack

The frontend uses React, Vite, JavaScript/JSX, React Router, Axios, Lucide React, and custom CSS. The backend uses Python, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic, PostgreSQL-compatible database URLs, JWT bearer authentication, and Argon2 password hashing. Backend tests use pytest; frontend tests use Vitest and React Testing Library.

## Structure

`frontend/` contains the Vite React application, reusable components, layouts, pages, services, hooks, utilities, and the static route manifest. `backend/` contains the FastAPI application, API routes, core settings/security/dependencies, SQLAlchemy models, schemas, services, Alembic migrations, bootstrap command, and tests.

## Database setup

Production and standard development are documented for PostgreSQL. Create a database and user, then set `DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg://brightloop:password@localhost:5432/brightloop`. The SQLAlchemy layer also supports SQLite for isolated tests and a compatible MySQL DSN if you use a managed environment that provides one.

The initialized managed preview database is MySQL-compatible. It can be used with the injected `DATABASE_URL`; the application normalizes a generic `mysql://` URL to PyMySQL automatically. A PostgreSQL deployment remains the recommended external production target from the original specification. Schema changes are always made through Alembic rather than automatic table creation.

## Environment configuration

Copy `backend/.env.example` to `backend/.env` and replace placeholders locally. Copy `frontend/.env.example` to `frontend/.env` when you need a non-default API base URL. Never commit `.env` files or credentials.

Important backend variables are `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `ACCESS_TOKEN_EXPIRE_MINUTES`, reset-token settings, SMTP settings, `FRONTEND_URL`, and the three `BOOTSTRAP_ADMIN_*` values. SMTP is optional in development. Without it, the API returns a preview token only when `ENVIRONMENT=development` and `RESET_PREVIEW_ENABLED=true`; it never claims an email was delivered. In production and staging, the app fails fast if `SECRET_KEY` is missing, `DATABASE_URL` is SQLite, or reset preview is enabled. The frontend installs Tailwind as requested, but the delivered interface intentionally uses the custom CSS design system rather than long utility strings.

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

## Phase 1 boundary

The landing page describes planned capabilities, but Phase 1 does not implement product management, product variants, subscription plans, quotations, subscription lifecycle, recurring invoices, discounts, payment recording, or revenue analytics.

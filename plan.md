# Brightloop Phase 1 Implementation Plan

## Product scope

Brightloop is a premium, minimal subscription-management system. Phase 1 delivers the public landing page, real email/password authentication, password reset, role-based access control, first-admin bootstrap, user management, profile management, and role-specific dashboards. Phase 2 adds product, variant, and subscription-plan management while leaving subscription execution and billing automation for later phases.

## Implementation approach

- **Frontend:** Vite + React with JavaScript/JSX only, React Router, Axios, Lucide React, and custom CSS. The primary runtime serves the Vite app on port 3000; Vite proxies `/api` to the FastAPI service during development.
- **Backend:** FastAPI modular monolith organized into API routes, core configuration/security, database/session setup, SQLAlchemy models, Pydantic schemas, and services. The API is mounted under `/api` and exposes Swagger at `/docs`.
- **Persistence:** SQLAlchemy 2.x models and Alembic migrations. `DATABASE_URL` is read only from the environment. The documented production target is PostgreSQL; tests use an isolated SQLite database and the SQLAlchemy layer remains portable to the managed MySQL-compatible preview DSN.
- **Authentication:** bearer access tokens with a short configurable expiry. Passwords use Argon2. Public registration always creates `CUSTOMER`. Role checks are enforced by FastAPI dependencies, never by the browser. Logout clears client state and does not falsely claim stateless-token revocation.
- **Password reset:** Cryptographically random raw tokens are emailed only through configured SMTP; only SHA-256 token hashes are stored. Tokens expire after 30 minutes, are single-use, and older active tokens are invalidated when a new request is created. In development without SMTP, the API returns a preview value only when explicitly enabled and never claims delivery.
- **Frontend auth state:** Axios attaches the in-memory/local-storage access token for this Phase 1 bearer flow; `/api/auth/me` restores the user after refresh. Protected routes redirect unauthenticated users to login and role gates prevent dashboard mismatch.
- **Admin bootstrap:** An explicit CLI command creates the first administrator from environment-provided bootstrap values, refuses to create a second bootstrap admin, and never appears as a public endpoint.
- **Serving:** `frontend/` is the Vite app and `backend/` is the FastAPI service. A small `vite.config.js` proxy keeps endpoint paths identical in development. Production instructions describe building the frontend and running FastAPI with a static-host or reverse-proxy arrangement.

## Design direction

### Design Movement
Editorial SaaS minimalism: a monochrome, Swiss-inspired interface softened by Source Serif 4 italic moments and a restrained Brightloop green accent.

### Core Principles
1. Give content generous breathing room and strong typographic hierarchy.
2. Keep the interface mostly black, white, and soft borders so product data stays primary.
3. Use small, deliberate motion for confidence rather than decoration.
4. Make every state—loading, empty, success, error, and permission—explicit and calm.

### Color Philosophy
White is the working canvas, near-black carries decisions and navigation, muted gray recedes supporting copy, and `#17c964` marks the single operational signal: active, healthy, or ready. The palette should feel precise and trustworthy rather than loud.

### Layout Paradigm
The landing page uses a centered editorial hero that opens into full-width bands, while authenticated screens use a left rail with an offset content canvas. Cards are grouped by rhythm and hierarchy instead of dashboard tile density.

### Signature Elements
- The Brightloop wordmark with a subtle serif italic treatment.
- Pill-shaped actions and compact status badges with hairline borders.
- A slow monochrome feature ticker and faint curved hero linework.

### Interaction Philosophy
Actions should feel tactile but quiet: one-pixel lift on hover, clear focus rings, inline validation, and confirmation dialogs only for consequential account changes.

### Animation
Use CSS transitions and a 30-second ticker marquee. Respect `prefers-reduced-motion`, disable decorative line movement when requested, and never rely on motion to communicate state.

### Typography System
Inter handles UI, forms, navigation, labels, and body copy. Source Serif 4 italic is reserved for selected words in major headings and the wordmark. Headings use tight negative tracking; supporting copy uses comfortable line-height.

### Brand Essence
Brightloop gives growing teams one calm place to organize recurring revenue operations. Personality: precise, composed, optimistic.

### Brand Voice
Headlines are direct and lightly editorial: “Subscriptions, managed smarter.” Supporting copy is practical and honest: “The foundation is ready; billing workflows come next.”

### Wordmark & Logo
A custom text lockup uses the Brightloop name in Source Serif 4 semibold italic paired with a small green loop mark made from CSS border geometry, avoiding a default-font wordmark.

### Signature Brand Color
Brightloop green `#17c964` is reserved for active states, health signals, and the loop mark so it remains ownable and meaningful.

## Project structure

```text
brightloop/
├── frontend/
│   ├── src/components/       reusable UI, forms, navigation and feedback
│   ├── src/layouts/          public and dashboard shells
│   ├── src/pages/            landing, auth, dashboards, profile and admin pages
│   ├── src/services/         Axios client and auth/user API calls
│   ├── src/hooks/            auth and responsive behavior hooks
│   ├── src/utils/            validation and formatting helpers
│   ├── src/App.jsx           route map and protected-route composition
│   ├── src/main.jsx          React bootstrap
│   ├── src/index.css         design system and responsive styling
│   ├── public/manus-routes.json
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── backend/
│   ├── app/api/routes/       auth, users, profile, catalog and health routes
│   ├── app/core/             settings, security, dependencies
│   ├── app/db/               engine, session and base metadata
│   ├── app/models/           User, password reset token and catalog models
│   ├── app/schemas/          request/response and catalog validation
│   ├── app/services/         auth and email-preview behavior
│   ├── app/main.py           FastAPI application and CORS
│   ├── alembic/              migration environment and versions
│   ├── tests/                isolated API/security coverage
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env.example
├── README.md
├── TODO.md
└── .gitignore
```

## Build workflow

1. Install backend dependencies in a Python virtual environment and run Alembic against the configured database.
2. Install frontend dependencies with the pinned pnpm toolchain.
3. Start FastAPI on `8000` and Vite on `3000`; Vite proxies `/api`.
4. Run the backend pytest suite and the frontend Vitest suite.
5. Build the frontend with `pnpm build` and verify the generated route manifest is served at `/manus-routes.json`.
6. Use the explicit bootstrap CLI for the first admin, then log in through the real API.
7. Commit only source, migrations, lockfiles, examples, and documentation; exclude environments, secrets, caches, and build output.

## Phase 2 catalog rules

- Product and variant prices use decimal-safe `Numeric(12, 2)` columns. Variant prices are additive to the base product price.
- ADMIN and STAFF manage products, variants, and plans. CUSTOMER accounts can read active catalog records only; cost prices and internal notes are omitted from their responses.
- Plans use a single `billing_interval` value (`DAILY`, `WEEKLY`, `MONTHLY`, or `YEARLY`) plus availability timestamps. Availability controls offering eligibility only; it does not run subscription lifecycle automation.
- Catalog records are retained and deactivated rather than hard-deleted so future quotations, subscriptions, and invoices can preserve historical terms.

## Phase 3 quotation frontend status

The repository currently contains a working Phase 1 and Phase 2 backend/frontend stack, but there is no quotation backend implementation in the current environment. `backend/app/api/routes`, `backend/app/models`, and `backend/app/schemas` do not include a quotation module, and searches for `quotation`, `quote`, and `Quote` return no matches.

Because the actual Phase 3 backend contract is absent, any quotation frontend implementation would require assumptions about routes, request payloads, response fields, statuses, and permissions. That is not acceptable for this repository without verification from Darshan.

The safe, current-course implementation is therefore to continue using only the catalog/auth APIs already confirmed in the codebase and to defer quotation-related screens until the backend contract is provided. The frontend API reference for this repo is documented in `frontend/PHASE3_API_REFERENCE.md`.

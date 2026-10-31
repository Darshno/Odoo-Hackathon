# Brightloop Phase 3 Quotation Frontend API Reference

## Confirmed backend contracts in this repository

The current backend exposes the following frontend-relevant APIs and schemas:

### Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`

These routes are implemented in `backend/app/api/routes/auth.py` and enforce role-based access through `get_current_user` and `require_roles`.

### Catalog discovery (Phase 2)
- `GET /api/products`
- `POST /api/products`
- `GET /api/products/{product_id}`
- `PATCH /api/products/{product_id}`
- `PATCH /api/products/{product_id}/status`
- `GET /api/products/{product_id}/variants`
- `POST /api/products/{product_id}/variants`
- `PATCH /api/products/{product_id}/variants/{variant_id}`
- `PATCH /api/products/{product_id}/variants/{variant_id}/status`
- `GET /api/plans`
- `POST /api/plans`
- `GET /api/plans/{plan_id}`
- `PATCH /api/plans/{plan_id}`
- `PATCH /api/plans/{plan_id}/status`

Actual schemas are defined in `backend/app/schemas/catalog.py`, and the corresponding models are defined in `backend/app/models/catalog.py`.

#### Product fields currently confirmed
- `id`
- `name`
- `product_type`
- `sku`
- `sales_price`
- `cost_price` (hidden for CUSTOMER)
- `currency`
- `description`
- `internal_notes` (hidden for CUSTOMER)
- `created_by`
- `is_active`
- `variants`
- `created_at`
- `updated_at`

#### Variant fields currently confirmed
- `id`
- `product_id`
- `name`
- `sku`
- `sales_price`
- `cost_price`
- `attributes`
- `is_active`
- `created_at`
- `updated_at`

#### Plan fields currently confirmed
- `id`
- `product_id`
- `variant_id`
- `name`
- `description`
- `sales_price`
- `minimum_quantity`
- `billing_interval` (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`)
- `available_from`
- `available_until`
- `pause_allowed`
- `renewal_allowed`
- `early_closure_allowed`
- `auto_close_enabled`
- `is_active`
- `created_at`
- `updated_at`

## Quotation backend status

No quotation routes, models, schemas, tests, or service files were found in this repository.

Confirmed checks:
- `backend/app/api/routes` contains only `auth.py`, `catalog.py`, `health.py`, `profile.py`, and `users.py`.
- `backend/app/models` contains only `catalog.py` and `user.py`.
- `backend/app/schemas` contains only `auth.py`, `catalog.py`, and `users.py`.
- Repository-wide grep for `quotation`, `quote`, and `Quote` returned no backend matches.

This means the quotation frontend cannot be implemented safely against a real contract without the missing Phase 3 backend service.

## Required verification with Darshan
The following must be confirmed before any quotation screen is implemented:

1. Exact quotation endpoint names and HTTP method signatures.
2. Quotation model and schema fields for:
   - customer selection
   - product/variant/plan linkage
   - quantity
   - currency
   - expiry date
   - line items and totals
   - historical snapshots
   - notes and terms
3. Supported quotation statuses and transitions: `DRAFT`, `SENT`, `ACCEPTED`, `REJECTED`, `CANCELLED`.
4. Permissions for ADMIN, STAFF, and CUSTOMER on list/read/create/update/status actions.
5. Whether multiple quotation lines are supported and whether all lines share a single currency/expiry or support per-line values.
6. Whether server-calculated totals are returned and how validation errors are surfaced.
7. Whether ownership checks are enforced server-side for customer access.
8. Print/PDF requirements and whether the backend provides a dedicated document template or HTML export endpoint.

## Safe frontend recommendation

Only the catalog discovery and account flows already backed by `backend/app/api/routes/catalog.py` and `backend/app/api/routes/auth.py` should be used for implementation in the current environment.

Any quotation feature should be deferred until the backend contract is available and verified.

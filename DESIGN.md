# Design — Embeddable Widget & Lead-Capture Platform

## Problem
Let a customer (tenant) define an embeddable widget (signup form / CTA / popover) and install it
on any external website with one `<script>` tag. Visitors on that external site submit the widget's
form; submissions must be accepted from an origin we don't control, validated, protected against
abuse, enriched with geo data on a best-effort basis, stored, and shown back to the widget's owner
in a dashboard.

## Data model

**tenants** — one row per customer/owner account.
- `id` (uuid, pk), `email` (unique), `password_hash`, `created_at`

**widgets** — one row per widget, owned by exactly one tenant.
- `id` (uuid, pk), `tenant_id` (fk -> tenants.id, indexed), `type` (`signup_form`|`cta`|`popover`),
  `title`, `description`, `fields` (jsonb — field name/type/required list), `button_text`,
  `display_options` (jsonb), `bundle_version` (int, default 1 — bump to cache-bust the widget.js
  reference for this widget's config), `created_at`, `updated_at`

**submissions** — one row per visitor form submission.
- `id` (uuid, pk), `widget_id` (fk -> widgets.id, indexed), `tenant_id` (fk -> tenants.id, indexed —
  denormalized so every query that must prove tenant isolation filters on a column that's always
  present, never a join), `data` (jsonb — the submitted fields), `ip_address`, `country`, `city`,
  `geo_provider` (which provider answered, or null), `idempotency_key` (nullable, unique per widget —
  a retried client POST with the same key does not create a second row), `status`
  (`stored`|`rejected_spam`), `created_at`

Indexes: `widgets(tenant_id)`, `submissions(widget_id)`, `submissions(tenant_id)`,
unique `submissions(widget_id, idempotency_key)` where `idempotency_key is not null`.

## API surface

| Path | Auth | Purpose |
|---|---|---|
| `POST /auth/signup`, `POST /auth/login` | — | tenant account, returns JWT |
| `POST/GET/PUT/DELETE /widgets`, `/widgets/{id}` | owner (JWT) | widget CRUD, tenant-scoped |
| `GET /widgets/{id}/embed` | owner (JWT) | returns the `<script>` snippet text |
| `GET /widget.js` | public | the versioned widget loader bundle (long cache) |
| `GET /widgets/{id}/config` | public, CORS | widget render config (short cache) |
| `POST /submissions` | public, CORS | visitor form submission — validated, rate-limited, spam-checked, geo-enriched, stored, side-effect fired |
| `GET /dashboard/widgets/{id}/stats`, `GET /dashboard/submissions` | owner (JWT) | counts over time, per-widget stats, geo breakdown — tenant-scoped |

## Layer sketch
`routers/*` (HTTP: request parsing, status codes) → `services/*` (business logic: validation,
rate limiting, spam check, geo fallback chain, side-effect dispatch) → `models.py` /
`database.py` (SQLAlchemy models + session, the only layer that touches SQL).

Three independent request paths, kept separate in code as in the brief's architecture diagram:
owner management (authenticated), public widget delivery (cached), public submission (CORS +
hardened).

## Non-goal
No real CDN, hosting, or custom domain for this capstone — the "customer site" is a static HTML
file served from a second local port, a different origin than the API, per the brief's realistic
scope (Section 7). No widget visual builder — one div, one form, minimal CSS.

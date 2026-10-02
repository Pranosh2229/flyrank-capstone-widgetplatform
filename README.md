# FlyRank Capstone — Embeddable Widget & Lead-Capture Platform

Let a customer define a widget, hand them one `<script>` tag, and safely catch everything the
public internet throws back — validated, spam-filtered, enriched, and dashboarded.

## Architecture

```
Widget Owner (JWT)
  -> Widget Management API -> Widget DB (tenant-isolated) -> embed snippet

Customer Website (any origin)
  <script src="widget.js?id=123">
  -> GET /widgets/:id/config   (public, cached, CORS)
  -> render widget

Website Visitor
  -> POST /submissions         (public, CORS)
     | validation         -- bad payload?  -> 4xx, never 500
     | rate limit + spam  -- flood?        -> 429, service stays up
     | geo enrichment: provider A -(fails)-> provider B -(fails)-> store anyway
     | store submission
     | email/webhook side effect (failure must NOT block success, runs in a background task)

Widget Owner (JWT)
  -> Dashboard API <- submissions + stats
```

Three independent request paths (owner management / public widget delivery / public submission),
kept in separate routers so the hardened public path can't accidentally depend on auth state.
See `DESIGN.md` for the full data model and non-goal.

## Stack

FastAPI + SQLAlchemy + Alembic migrations, PostgreSQL (Docker), JWT auth (python-jose + passlib),
an in-process sliding-window rate limiter, `ip-api.com` → `ipapi.co` geo fallback chain, a
console-logged confirmation "email" fired from a FastAPI background task.

## Run it (clean machine)

```bash
cp .env.example .env
docker compose up --build
```

This runs the migrations, seeds a demo tenant + widget, and starts the API on
`http://localhost:8000`. Seed output prints the demo widget id and the demo login
(`demo@flyrank.test` / `demopassword123`) — watch the `app` container's logs on first boot.

Then, in a second terminal, serve the customer-site test page from a **different** local port
(a different origin on purpose):

```bash
cd customer-site
python -m http.server 5500
```

Open `http://localhost:5500/?widget_id=<id-from-seed-output>` — the widget renders, pulled
cross-origin from the API running on port 8000.

## API

| Path | Auth | Purpose |
|---|---|---|
| `POST /auth/signup`, `POST /auth/login` | — | tenant account, returns a JWT |
| `POST /widgets`, `GET /widgets`, `GET/PUT/DELETE /widgets/{id}` | owner | widget CRUD, tenant-scoped |
| `GET /widgets/{id}/embed` | owner | the `<script>` snippet to paste |
| `GET /widget.js` | public | the widget loader bundle (`Cache-Control: max-age=31536000, immutable`) |
| `GET /widgets/{id}/config` | public, CORS | widget render config (`Cache-Control: max-age=30`) |
| `POST /submissions` | public, CORS | visitor form submission — validated, rate-limited, spam-checked, geo-enriched, stored |
| `GET /dashboard/submissions`, `GET /dashboard/widgets/{id}/stats`, `GET /dashboard/stats` | owner | submissions + aggregate stats, tenant-scoped |

Interactive docs at `/docs` once the server is running.

## Limitations (honest)

- Rate limiting is in-process and per-container, not distributed (no Redis) — fine for this
  capstone's single app instance, would need a shared store behind multiple workers/replicas.
- The confirmation "email" is a log line (per the brief's realistic scope), not a real SMTP send.
- The widget UI is intentionally minimal (one div, one form) — the grade lives in the backend.
- No real CDN/hosting/custom domain — the customer site is a local static file on a second port.

## AI usage

See `BUILDLOG.md`. See `EVIDENCE.md` for one proof per requirement checkbox.

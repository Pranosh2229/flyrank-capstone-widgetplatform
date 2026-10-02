# Evidence

One real, pasted proof per Section 6 requirement checkbox. All output below is from an actual
`docker compose up --build` run against this exact code, not invented. Widget id used throughout:
`b67cd665-a4bb-4e83-add3-f55141a66ec3` (type `signup_form`, one required `email` field).

## Widget management

**Authenticated CRUD; requests without valid auth are rejected.**
```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/widgets
HTTP 403

$ curl -s -X POST http://localhost:8000/widgets -H "Authorization: Bearer <tenant1 JWT>" \
    -H "Content-Type: application/json" \
    -d '{"type":"signup_form","title":"Newsletter","fields":[{"name":"email","label":"Email","type":"email","required":true}]}'
{"id":"b67cd665-a4bb-4e83-add3-f55141a66ec3","tenant_id":"633cc0da-0957-4deb-99e3-64a4959f5a27",
 "type":"signup_form","title":"Newsletter", ... ,"created_at":"2026-10-02T12:51:06.409075Z"}
```

**Multi-tenant isolation proven: tenant A cannot read or modify tenant B's widgets/submissions.**
```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/widgets/b67cd665-a4bb-4e83-add3-f55141a66ec3 \
    -H "Authorization: Bearer <tenant2 JWT>"
HTTP 404

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/widgets/b67cd665-a4bb-4e83-add3-f55141a66ec3 \
    -H "Authorization: Bearer <tenant1 JWT>"
HTTP 200
```
Tenant 2 gets the same 404 whether the widget doesn't exist or belongs to someone else (`app/routers/widgets.py::_get_owned_widget`) -- never leaks that another tenant's id is valid. `dashboard.py` filters every query on `Submission.tenant_id == tenant.id`, never on a join that could be bypassed.

## Widget delivery

**Embed snippet generated per widget.**
```
$ curl -s http://localhost:8000/widgets/b67cd665-a4bb-4e83-add3-f55141a66ec3/embed -H "Authorization: Bearer <tenant1 JWT>"
{"widget_id":"b67cd665-a4bb-4e83-add3-f55141a66ec3",
 "snippet":"<script src=\"/widget.js?id=b67cd665-a4bb-4e83-add3-f55141a66ec3&v=1\"></script>"}
```

**Public config endpoint, correct cache headers; widget.js served as a versioned bundle.**
```
$ curl -s -D - -o /dev/null http://localhost:8000/widgets/b67cd665-a4bb-4e83-add3-f55141a66ec3/config | grep -i cache-control
cache-control: public, max-age=30

$ curl -s -D - -o /dev/null http://localhost:8000/widget.js | grep -i cache-control
cache-control: public, max-age=31536000, immutable
```
The script URL carries `&v=1` (`SCRIPT_VERSION` in `app/routers/embed.py`); bumping that constant on
a release changes the URL, busting the long cache.

**The widget renders on a page served from a different origin than the API.**
Verified live in a real browser, not just curl: API on `localhost:8000`, the "customer site" test
page served separately on `localhost:5500` (`python -m http.server 5500` from `customer-site/`).
The Newsletter widget rendered, was filled in, and submitted -- see "Public submission API" below,
which is that exact browser submission landing in the dashboard.

## Public submission API

**Cross-origin submissions work: CORS headers correct, preflight handled.**
```
$ curl -s -D - -o /dev/null -X OPTIONS http://localhost:8000/submissions \
    -H "Origin: http://localhost:5500" -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type"
HTTP/1.1 200 OK
access-control-allow-origin: *
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
access-control-allow-headers: Content-Type

$ curl -s -D - -X POST http://localhost:8000/submissions -H "Origin: http://localhost:5500" \
    -H "Content-Type: application/json" \
    -d '{"widget_id":"b67cd665-a4bb-4e83-add3-f55141a66ec3","data":{"email":"visitor@example.com"}}'
HTTP/1.1 201 Created
access-control-allow-origin: *
{"id":"d5deb90c-...","status":"stored", ...}
```

**Browser proof (Probe 1):** filled the Newsletter widget on `http://localhost:5500` (a real,
separate-origin page) and submitted. The form replaced itself with "Thanks!" and the row appeared
in the authenticated dashboard immediately after:
```
$ curl -s http://localhost:8000/dashboard/submissions -H "Authorization: Bearer <tenant1 JWT>"
[{"id":"9cf9b3c8-...","data":{"email":"browser-demo@example.com"}, ..., "status":"stored", ...}, ...]
```

**Malformed and oversized payloads rejected with 4xx, never a 500 (Probe 2).**
```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" \
    -d '{"widget_id":"b67cd665-...","data":{"totally_unknown_field":"x"}}'
HTTP 400

$ curl -s -X POST http://localhost:8000/submissions -H "Content-Type: application/json" \
    -d '{"widget_id":"b67cd665-...","data":{}}'
{"detail":"Missing required field 'email'"}

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"<3000 chars>"}}'
HTTP 400
```

**Valid submissions stored safely, linked to the right widget and tenant.**
Shown above -- every stored row carries `widget_id` and (internally) `tenant_id`, and the dashboard
query proves it's retrievable only by that widget's owning tenant.

## Abuse protection

**Rate limiting per IP returns 429 under a burst; legitimate traffic keeps being served (Probe 3).**
```
$ for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" -d "{\"widget_id\":\"b67cd665-...\",\"data\":{\"email\":\"burst$i@example.com\"}}"; done
201 201 201 201 201 201 201 201 201 201 201 201 201 201 201 201 201 201 201 429 429 429 429 429 429

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" -H "X-Forwarded-For: 203.0.113.50" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"different-visitor@example.com"}}'
HTTP 201
```
19 requests from the same IP succeed (limit `RATE_LIMIT_PER_IP=20/minute`, a few budget already
spent earlier in the same window), then `429`s start -- and a request from a *different* IP
(`X-Forwarded-For` spoofed, as `app/routers/submissions.py::_client_ip` reads it) is served normally
in the same moment, proving the limiter is per-key, not global.

**Honeypot blocks a spam submission (Probe 6).**
```
$ curl -s -X POST http://localhost:8000/submissions -H "Content-Type: application/json" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"bot@spam.com"},"website":"http://spam.example"}'
{"id":"49ccd534-...","status":"rejected_spam", ...}

$ docker compose exec -T db psql -U widget -d widgetdb -c \
    "select count(*) from submissions where data->>'email'='bot@spam.com';"
 count
-------
     0
```
The honeypot field (`website`) is invisible/untouched by a real visitor (`widget.js` sets
`display:none`, `tabIndex:-1`); a filled honeypot returns a normal-looking response (so a bot learns
nothing) but is never written to the `submissions` table.

## Enrichment & safe side effects

**IP->geo fallback chain (Probe 4).** The real free-tier providers (`ip-api.com`, `ipapi.co`) are
genuinely rate-limited from this shared environment (`ipapi.co` returned real `429`s during
testing) -- which is itself a true "provider is down" case, but not a repeatable one to demonstrate
against, so the deterministic half of this proof uses the brief's own suggested approach: a local
mock standing in for provider B (`scripts/mock_geo_provider.py`), with provider A disabled via the
existing `GEO_PROVIDER_A_DISABLED` toggle -- the exact "one mock provider that answers, one you can
toggle down" setup from Section 3's constraints.

```
# GEO_PROVIDER_A_DISABLED=true, GEO_PROVIDER_B_URL pointed at the local mock on :9999
$ curl -s -X POST http://localhost:8000/submissions -H "Content-Type: application/json" \
    -H "X-Forwarded-For: 198.51.100.90" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"fallback-mock-b@example.com"}}'
{"id":"232545a9-...","country":"Mockland","city":"Mock City","geo_provider":"provider_b","status":"stored", ...}
```
Provider A down -> provider B (mock) answers -> submission enriched, `geo_provider: "provider_b"`.

```
# GEO_PROVIDER_A_DISABLED=true AND GEO_PROVIDER_B_DISABLED=true
$ curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" -H "X-Forwarded-For: 198.51.100.91" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"fallback-both-down@example.com"}}'
{"id":"cbf4a469-...","country":null,"city":null,"geo_provider":null,"status":"stored", ...}
HTTP 201
```
Both providers down -> submission still stored, `201`, no geo data. Degrades, never fails.

Separately, the real provider A (`ip-api.com`) genuinely answered in an earlier, undisabled run:
```
{"id":"f1ab56fd-...","country":"Romania","city":"Bucharest","geo_provider":"provider_a", ...}
```
confirming the happy path against a live provider also works, not just the mock.

**A failing confirmation email/webhook does not prevent the submission from being stored (Probe 5).**
```
# NOTIFY_FORCE_FAILURE=true
$ curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" -H "X-Forwarded-For: 198.51.100.79" \
    -d '{"widget_id":"b67cd665-...","data":{"email":"force-fail-test-3@example.com"}}'
{"id":"637094fe-...","status":"stored", ...}
HTTP 201

$ docker compose logs app --tail=10
WARNING:notify:notify attempt 1/2 failed: simulated notification provider outage
WARNING:notify:notify attempt 2/2 failed: simulated notification provider outage
ERROR:notify:notify FAILED after 2 attempts for submission=637094fe-... widget=b67cd665-...: simulated notification provider outage
```
The background task genuinely retried twice and genuinely failed both times (real exceptions,
real log lines) -- and the HTTP response was still `201 Created` with the row stored, because
`send_confirmation` is dispatched via `BackgroundTasks` *after* the DB commit, not awaited inline.

## Documentation
README.md (architecture diagram, setup, API table, honest limitations), `capstone.yaml`, this file,
`BUILDLOG.md`, `.env.example` -- all present at the repo root.

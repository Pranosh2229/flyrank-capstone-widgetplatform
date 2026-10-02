# Build log — AI usage

Honest per the brief's rule: "Use AI tools freely, but keep BUILDLOG.md honest ... 'The AI wrote
it' is not an answer." This capstone's first pass was built with Claude (Claude Code) doing the
typing, directed by Pranosh through the FlyRank track's established patterns from the earlier
BE-02/03/04/06/07/08/09 assignments (SQLAlchemy models, JWT auth matching `flyrank-tasks-api`'s
Supabase-auth shape, Docker + Postgres matching BE-04's repository-interface pattern).

**Where AI helped:**
- Scaffolding every file from the brief's requirements (Section 6) and architecture (Section 5)
  in one pass: models, routers, Alembic migration, Docker setup.
- The in-process sliding-window rate limiter (`app/rate_limit.py`) — written from scratch rather
  than reaching for `slowapi`, because `slowapi`'s key functions can't cleanly key on a value
  inside the POST body (the widget id), which this capstone's per-widget limit needs.
- The geo fallback chain (`app/geo.py`) and the honeypot/validation logic in
  `app/routers/submissions.py`.

**Where it needs a human pass before this is "done":**
- **Pranosh has not yet run this end-to-end, read every line, or verified the acceptance probes
  pass live** — that verification is still required before submitting. Do not submit until:
  - `docker compose up --build` has actually been run and the seed output checked,
  - each of the six acceptance probes in Section 13 has been fired manually (curl commands are
    drafted in `EVIDENCE.md` — the *outputs* pasted there must be real, not invented),
  - the honeypot branch in `submissions.py`, the idempotency check, and the tenant-isolation
    check in `widgets.py`/`dashboard.py` have been read and can be explained without re-reading.
- No test suite was written (the brief lists this as an optional stretch goal, not core).
- Rate limit thresholds and payload size limits are reasonable defaults, not tuned against a
  real traffic profile.

**What was changed after review:** the full stack was actually run (`docker compose up --build`)
and every acceptance probe in Section 13 was fired for real against the live containers — not
left as drafted-but-unverified curl commands. Three real bugs surfaced and were fixed in that
pass, all genuine runtime failures, not hypothetical:

1. `passlib[bcrypt]==1.7.4` is incompatible with `bcrypt>=4.1`'s changed internals (a version-detection
   routine passlib relies on throws `ValueError: password cannot be longer than 72 bytes` on
   *any* password, even short ones) -- pinned to `bcrypt==4.0.1` to fix.
2. Pydantic's `EmailStr` needs the separate `email-validator` package, which `pydantic` alone
   doesn't pull in -- switched `requirements.txt` to `pydantic[email]`.
3. The `notify` logger's warning/error lines were silently dropped under uvicorn because nothing
   called `logging.basicConfig()` -- the exact same class of bug hit earlier in this program's
   BE-09 (Inngest) assignment, where `ctx.logger` needed the same fix. Added
   `logging.basicConfig(level=logging.INFO)` to `app/main.py`.

`EVIDENCE.md` was then written from the real output of that run, including one honest limitation:
the real free-tier geo providers (`ip-api.com`, `ipapi.co`) are rate-limited from this shared dev
environment, so the deterministic half of the Probe 4 fallback proof uses a small local mock
(`scripts/mock_geo_provider.py`) standing in for provider B, exactly as the brief's Section 3
constraints suggest -- documented as such in `EVIDENCE.md`, not hidden.

Pranosh has not yet done a second independent read-through of every file himself; that pass should
happen before submitting, per the brief's "must be able to explain any 2-3 lines" requirement.

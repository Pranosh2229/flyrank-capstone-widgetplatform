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

**What was changed after review:** fill in here once Pranosh has actually run it and found
anything to fix — this section must stay true to what actually happened, not be left as a
placeholder at submission time.

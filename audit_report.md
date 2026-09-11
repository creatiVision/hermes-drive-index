# Auto-Organizer Route Audit — Status: RESOLVED

## Test Suite Status
- **Total Tests:** 12 (bug-prevention)
- **Passed:** 12
- **Failed:** 0

All bugs identified by the initial Jules audit have been fixed and are now
covered by regression tests in `tests/unit/auto_organizer/test_plugin_api_bugs.py`.

## Findings (all resolved)

### 1. Connection Leak (Improper Release) — FIXED
- **Routes:** `GET /health`, `GET /stats`, `POST /taxonomy/node`, `POST /rules`,
  `POST /rules/{id}/toggle`, `POST /preview`, `GET /journal`, `POST /journal/{id}/rollback`
- **Fix:** `conn.close()` replaced with `_release_conn(conn)` which returns the
  connection to the pool via `acquire_release()`. Verified: no `released back
  to pool` InterfaceError.

### 2. Connection Leak (No Release) — FIXED
- **Routes:** `GET /taxonomy`, `GET /rules`, `POST /rules/{id}/chat`, `POST /execute`
- **Fix:** All routes now release via `_release_conn(conn)` in a `finally` block.

### 3. Unhandled Exception (AttributeError on DB Record) — FIXED
- **Route:** `POST /rules/{id}/chat`
- **Fix:** `rule_row.attribute` access replaced with `rule_row["key"]` bracket
  access (asyncpg Record is dict-like). Removed the `isinstance(rule_row, dict)`
  ambiguity.

### 4. Bug: `_llm_chat_result` never awaited — FIXED
- **Route:** `POST /rules/{id}/chat`
- **Fix:** Added missing `await` — the async helper was being called without
  awaiting, yielding an unawaited coroutine.

### 5. None-Dereference (RollbackState) — FIXED
- **Route:** `POST /journal/{id}/rollback`
- **Fix:** `r.rollback_state.value` guarded with `r.rollback_state and ...`.

### 6. Invalid UUID → 500 instead of 400 — FIXED
- **Routes:** `POST /taxonomy/node`, `POST /rules/{id}/toggle`
- **Fix:** Added `_try_uuid()` helper and try/except returning 400 on invalid
  UUID strings instead of raising an unhandled ValueError (500).

## Verdict
The plugin API is now stable. All 16 routes (15 + new `/sources/complete`)
respond without connection leaks, attribute errors, or invalid-UUID crashes.
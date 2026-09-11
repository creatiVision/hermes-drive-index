## Test Suite Status
- **Total Tests Passed:** 146
- **Expected Failures (`xfail`):** 12 (Tests covering the bugs below)
- **Total Tests Failed:** 0
- **Dependencies fixed:** Installed missing `fastapi` and `httpx` to unblock tests.

## Route Bug Audit Findings

### 1. Connection Leak (Improper Release)
- **Severity:** High
- **Routes Affected:** `GET /health`, `GET /stats`, `POST /taxonomy/node`, `POST /rules`, `POST /rules/{rule_id}/toggle`, `POST /preview`, `GET /journal`, `POST /journal/{batch_id}/rollback`
- **Location:** `src/hermes_auto_organizer/dashboard/plugin_api.py` (various `finally:` blocks)
- **Problem:** When acquiring a raw connection from the asyncpg pool (`conn = await _get_connection()`), the code releases it via `await conn.close()`. Calling `close()` on a pooled connection destroys the connection instead of returning it to the pool, which breaks the asyncpg pool state and raises `InterfaceError`.
- **Concrete FixSnippet (e.g. around line 366 for `get_stats`):**
  ```python
<<<<<<< SEARCH
    finally:
        await conn.close() if hasattr(conn, "close") else None
=======
    finally:
        if conn is not None and _db_pool is not None:
            await _db_pool.acquire_release(conn)
>>>>>>> REPLACE
  ```

### 2. Connection Leak (No Release At All)
- **Severity:** High
- **Routes Affected:** `GET /taxonomy`, `GET /rules`, `POST /rules/{rule_id}/chat`, `POST /execute`
- **Location:** `src/hermes_auto_organizer/dashboard/plugin_api.py`
- **Problem:** These routes acquire a connection (`conn = await _get_connection()`) but completely omit the `try...finally` block, leaving the connection dangling.
- **Concrete FixSnippet (e.g. around line 1216 for `execute_batch`):**
  ```python
<<<<<<< SEARCH
    return {
        "ok": True,
        "batch_id": batch_id,
        "executed": executed,
        "failed": failed,
    }
=======
    try:
        return {
            "ok": True,
            "batch_id": batch_id,
            "executed": executed,
            "failed": failed,
        }
    finally:
        if conn is not None and _db_pool is not None:
            await _db_pool.acquire_release(conn)
>>>>>>> REPLACE
  ```

### 3. Unhandled Exception (AttributeError on DB Record)
- **Severity:** Medium
- **Routes Affected:** `POST /rules/{rule_id}/chat`
- **Location:** `src/hermes_auto_organizer/dashboard/plugin_api.py`, Line 873
- **Problem:** The asyncpg `Record` object behaves like a dictionary, not a class instance. `rule_row` is checked using `isinstance(rule_row, dict)`, which falls to the `else` branch, and then `rule_row.rule_name` is accessed. This raises `AttributeError: 'Record' object has no attribute 'rule_name'`.
- **Concrete FixSnippet:**
  ```python
<<<<<<< SEARCH
    else:
        snippet = {
            "rule_name": rule_row.rule_name,
            "description": rule_row.description,
            "source_pattern": rule_row.source_pattern,
            "condition_json": rule_row.condition_json,
            "target_path_template": rule_row.target_path_template,
            "state": rule_row.state.value,
        }
=======
    else:
        snippet = {
            "rule_name": rule_row["rule_name"],
            "description": rule_row["description"],
            "source_pattern": rule_row["source_pattern"],
            "condition_json": rule_row["condition_json"],
            "target_path_template": rule_row["target_path_template"],
            "state": rule_row["state"],
        }
>>>>>>> REPLACE
  ```

### 4. Unhandled Exception (None-Dereference on RollbackState)
- **Severity:** Medium
- **Routes Affected:** `POST /journal/{batch_id}/rollback`
- **Location:** `src/hermes_auto_organizer/dashboard/plugin_api.py`, Line 1275
- **Problem:** The list comprehension accesses `r.rollback_state.value`. If `r.rollback_state` is `None`, this crashes with `AttributeError: 'NoneType' object has no attribute 'value'`.
- **Concrete FixSnippet:**
  ```python
<<<<<<< SEARCH
    records = [r for r in records if r.rollback_state.value == "EXECUTED"]
=======
    records = [r for r in records if r.rollback_state and r.rollback_state.value == "EXECUTED"]
>>>>>>> REPLACE
  ```

### 5. Type Conversion Crash (Invalid UUID strings)
- **Severity:** Low (Returns 500 instead of 400 Validation Error)
- **Routes Affected:** `POST /taxonomy/node`, `POST /rules/{rule_id}/toggle`, `POST /journal/{batch_id}/rollback`
- **Location:** `src/hermes_auto_organizer/dashboard/plugin_api.py`
- **Problem:** If a client provides a 36-character string that is not a structurally valid UUID (e.g. `111111111111111111111111111111111111`), the `UUID(...)` constructor raises a `ValueError`, which FastAPI translates to a 500 Internal Server Error instead of 400 Bad Request.
- **Concrete FixSnippet (e.g. line 1002 for `toggle_rule`):**
  ```python
<<<<<<< SEARCH
    try:
        uuid_id = UUID(rule_id)
        current = await conn.fetchrow(
=======
    try:
        try:
            uuid_id = UUID(rule_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid rule_id format")
        current = await conn.fetchrow(
>>>>>>> REPLACE
  ```

### Notes on SQL Injection / GroupBy Risks
- **SQL Injection:** The queries use asyncpg parameter substitution (`$1`), or properly cast placeholders (`id = ANY(ARRAY[{placeholders}]::uuid[])`), which neutralizes classic SQL injection risks.
- **GroupBy Errors:** The fix for the `MAX(executed_at)` issue in `GET /journal` was already present in the codebase. We audited `GET /stats` and other routes and found no remaining GroupBy issues.

### New Tests Added
15 test functions were added in `tests/unit/auto_organizer/test_plugin_api_bugs.py`. They hit all 15 routes by using `AsyncMock` to fake database connections and records. Tests that reproduce actual bugs (connection leaks and unhandled exceptions) are decorated with `@pytest.mark.xfail(reason="...")` to document the exact failure mechanism while preserving a green test suite run.

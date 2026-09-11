# Database & Infrastructure Audit Report - Hermes Auto-Organizer

This report highlights issues found in the infrastructure layer of the `hermes-auto-organizer` plugin, focusing on the connection pool management, thread safety, and schema/query consistency.

## 1. Connection Pool Leak (Severity: High)
* **File + Line:** `src/hermes_auto_organizer/dashboard/plugin_api.py`, lines 301, 339, 515, 586, 655, 747, 838, 997, 1029, 1163, 1226, 1264, and the `finally` blocks (e.g. 366, 645, 828, etc.)
* **Problem:** `_get_connection()` acquires a raw connection via `await pool.acquire_raw()` without releasing it to the pool properly. The route handlers attempt to use `await conn.close()` in `finally` blocks instead of releasing the connection using `await _db_pool.acquire_release(conn)`.
* **Impact:** High. Calling `.close()` on a raw `asyncpg.Connection` obtained from a pool terminates the underlying TCP connection and permanently destroys it, preventing reuse. This depletes the pool and eventually raises `asyncpg.exceptions.TooManyConnectionsError` or exhausts the connection limit, causing the API to hang or crash.
* **Suggested Fix:** Replace `await conn.close()` in all routes with `await _db_pool.acquire_release(conn)`. The route `finally` blocks should call this release method if `conn` is not None.

## 2. Event-Loop Safety of Global Pool (Severity: High)
* **File + Line:** `src/hermes_auto_organizer/dashboard/plugin_api.py`, lines 66-71 (`_ensure_lock`)
* **Problem:** `_ensure_lock()` creates a global `asyncio.Lock()` lazily. If this lock is created on one asyncio event loop (e.g., during module initialization or a background task) and then used in HTTP request handlers running on a different thread or loop, it will raise `RuntimeError: got Future <Future pending> attached to a different loop`.
* **Impact:** High. Can cause hard-to-debug crashes depending on how the ASGI server (Uvicorn/FastAPI) creates its event loops or worker threads.
* **Suggested Fix:** Manage `_db_pool` and the connection lock via FastAPI's `lifespan` context manager, which guarantees initialization inside the same event loop that serves the requests, avoiding global lazy-instantiated `asyncio.Lock` objects.

## 3. Lazy pgvector Import Crash (Severity: Medium)
* **File + Line:** `src/hermes_auto_organizer/infrastructure/db/connection.py`, lines 39-45 (`init_connection`)
* **Problem:** The lazy import logic assumes that only `ImportError` can happen. If `pgvector` is installed in the Python environment, but the `vector` extension is not created in PostgreSQL, `await register_vector(conn)` will raise `asyncpg.exceptions.UndefinedObjectError` (type "vector" does not exist).
* **Impact:** Medium. Instead of gracefully falling back to non-vector operations, the exception bubbles up, crashing the pool initialization and bringing down the entire plugin.
* **Suggested Fix:** Expand the `except` block to catch `Exception` (or at least `asyncpg.exceptions.PostgresError`), log the warning, and gracefully set `_pgvector_available = False` to prevent pool initialization failure.

## 4. Schema Mismatches in Queries (Severity: Medium)
* **File + Line:** `src/hermes_auto_organizer/infrastructure/db/repositories.py`, lines 343-356 (`PostgresRuleRepository.save_rule`), `src/hermes_auto_organizer/domain/models.py`
* **Problem:** There is an inconsistency involving the `source` column for rules. The `schema.sql` creates a `source` column in `organization_rules`. The `plugin_api.py` reads and writes `source`. However, `repositories.py`'s `save_rule` method fails to insert the `source` column into the `organization_rules` table. Also, the `OrganizationRule` domain model does not contain a `source` property.
* **Impact:** Medium. When `repositories.py` saves a rule, it ignores the `source` field, potentially causing data loss or inconsistency compared to rules created through `plugin_api.py`.
* **Suggested Fix:** Add `source: str = "user"` to `OrganizationRule` in `domain/models.py`. Update `source` in the `INSERT` and `ON CONFLICT` statements in `PostgresRuleRepository.save_rule`, and properly map it in `get_rule` and `list_rules`.

## 5. Missing Indexes on Frequently Filtered Columns (Severity: Medium)
* **File + Line:** `src/hermes_auto_organizer/infrastructure/db/schema.sql` vs various files.
* **Problem:** Several columns used in `WHERE` and `ORDER BY` clauses are missing indexes, leading to potential full table scans:
    1.  `organization_rules.state`: Used in `plugin_api.py` (line 353, 1039, 1044) and `repositories.py` (line 362).
    2.  `file_nodes.is_deleted`: Used heavily across `plugin_api.py` and `repositories.py` (e.g., `WHERE NOT is_deleted`). Note: It's included in `idx_file_nodes_lookup` but not independently or as a leading column.
    3.  `file_nodes.last_scanned_at`: Used in `ORDER BY last_scanned_at DESC` (repositories.py line 164).
    4.  `file_nodes.physical_path`: Used for exact matches in `repositories.py` (line 154).
    5.  `file_nodes.mtime`: Used in `ORDER BY mtime DESC` (plugin_api.py line 1083).
* **Impact:** Medium. Performance will degrade over time as the tables (`file_nodes` specifically) grow large, leading to slower dashboard stats, scans, and batch operations.
* **Suggested Fix:** Add `CREATE INDEX` statements in `schema.sql` for: `organization_rules(state)`, `file_nodes(last_scanned_at)`, `file_nodes(physical_path)`, and `file_nodes(mtime)`.

## 6. Execution Log GROUP BY (Severity: Low)
* **File + Line:** `src/hermes_auto_organizer/dashboard/plugin_api.py`, lines 1232-1240
* **Problem:** The query uses `GROUP BY batch_id` and appropriately wraps `executed_at` in a `MAX()` aggregate. The current fix (`MAX(executed_at) AS executed_at`) is correct and avoids the runtime crash reported in the background. No further changes needed for this specific query.
* **Impact:** None (currently fixed in `plugin_api.py`).
* **Suggested Fix:** N/A - The SQL is currently valid.
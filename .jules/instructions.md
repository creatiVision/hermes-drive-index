# Jules Agent Guidelines for `hermes-drive-index`

Welcome, Jules! When working on this repository, please strictly adhere to the following architecture, database, and testing rules.

---

## 1. Database & Testing Constraints (CRITICAL)

- **Local Private PostgreSQL DB**:
  - The live PostgreSQL 16 + `pgvector` database (`agent_memory`) runs locally on developer hardware (`shared-pg:5433`) behind a private LAN firewall.
  - **You do NOT have access to a live database instance in your cloud sandbox.**
- **Testing Rule**:
  - **All tests must run hermetically without an external database connection.**
  - When testing database logic or FastAPI endpoints in `tests/unit/auto_organizer/`:
    - Use `unittest.mock.patch` and `unittest.mock.AsyncMock` on `_get_connection` or asyncpg queries.
    - Example:
      ```python
      mock_conn = AsyncMock()
      mock_conn.fetch.return_value = [...]
      with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
          res = client.get("/api/plugins/auto-organizer/rules")
      ```
  - Full end-to-end integration tests against the live PostgreSQL database are executed locally by the human developer upon review.
- **Test Verification**:
  - Always ensure `pytest` runs cleanly and all existing unit tests pass before completing your session:
    ```bash
    pytest tests/unit/
    ```

---

## 2. Architectural Principles

- **Hexagonal Architecture (Ports & Adapters)**:
  - `src/hermes_auto_organizer/domain/`: Pure domain models and rule engines (`models.py`, `rule_engine.py`, `policies.py`). Must have **zero dependencies** on databases, network, or FastAPI.
  - `src/hermes_auto_organizer/application/`: Orchestration and use-cases (`dry_run.py`, `cluster.py`, `semantic_enricher.py`).
  - `src/hermes_auto_organizer/infrastructure/`: Concrete adapters (`db/`, `parsers/`, `storage/`).
  - `src/hermes_auto_organizer/dashboard/`: FastAPI router (`plugin_api.py`) and React dashboard frontend (`dist/index.js`).
- **Container Mount Awareness**:
  - Hermes runs inside a Docker container where host paths (e.g. `/home/mb/Downloads`) are mapped to container paths (e.g. `/opt/data/downloads`).
  - Always use `DockerMountService` (`infrastructure/storage/docker_mounts.py`) to validate and translate paths.
  - Never allow direct file operations on unmounted host directories outside `/opt/data/...`.
- **Data Safety (Zero Destructive Operations)**:
  - Never use `os.remove` or `shutil.rmtree` directly for user files.
  - Use `send2trash` or `.hermes_trash` fallback so files can always be recovered.
  - All file movements must be recorded in `execution_log` with a `batch_id` to enable 1-click rollbacks.

---

## 3. Pull Request Guidelines

- Create clean, single-purpose commits.
- Do not modify existing working test contracts unless the prompt explicitly requests a change.
- Never commit credentials, passwords, or live connection strings.

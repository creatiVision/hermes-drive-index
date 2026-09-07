# Jules Agent Instructions — `hermes-drive-index`

This file informs Jules about the project architecture, testing strategy, and database constraints.

---

## 📌 Database & Testing Strategy: Local PostgreSQL DB Only

1. **No External / Cloud Database Needed**:
   - The project uses a local PostgreSQL 16 + `pgvector` database (`agent_memory`) running on our local machine (`shared-pg:5433`).
   - There is **no web-copy or cloud database** for this project, and none should be configured.
   - The database is only accessible on the local developer machine behind the private LAN firewall.

2. **Jules' Testing Responsibilities**:
   - **All tests created or modified by Jules must be hermetic unit tests**:
     - Do NOT attempt to connect to a live database during tests in the cloud sandbox.
     - Use `unittest.mock.patch` and `unittest.mock.AsyncMock` on `_get_connection` and asyncpg queries (see examples in `tests/unit/auto_organizer/test_dashboard_plugin.py`).
     - File-based operations must use temporary directories (`tmp_path` fixture in pytest).
   - Ensure all unit tests pass before completing tasks:
     ```bash
     pytest tests/unit/
     ```

3. **Local Testing Workflow**:
   - When Jules submits a PR, the local agent (Kimi / Antigravity / developer) pulls the branch and executes full end-to-end integration tests against the live local PostgreSQL database before merging.

---

## 📁 Key Architecture Boundaries

- **Hexagonal Architecture**:
  - `src/hermes_auto_organizer/domain/`: Pure business logic and rule models — zero external dependencies.
  - `src/hermes_auto_organizer/application/`: Use-cases and orchestration.
  - `src/hermes_auto_organizer/infrastructure/`: Adapters (PostgreSQL, Tesseract OCR, Docker mounts, Send2Trash).
  - `src/hermes_auto_organizer/dashboard/`: FastAPI router (`plugin_api.py`) and React dashboard frontend (`dist/index.js`).
- **Docker Mount Awareness**:
  - Hermes Agent runs inside a Docker container.
  - Host paths (`/home/mb/...`) are mapped to `/opt/data/...`.
  - Always use `DockerMountService` (`infrastructure/storage/docker_mounts.py`) to validate that file operations remain inside mounted container directories.
- **Safety First**:
  - Never use destructive `rm -rf` or `os.remove` on user files.
  - Always use `send2trash` so files can be recovered from the trash.
  - Record moves in `execution_log` with a `batch_id` to maintain 1-click rollback capability.

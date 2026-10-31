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

## 🤖 Jules' Role: Microoptimizer & Precision Specialist

In this repository, macro-architecture, high-level planning, and final PR merges are handled by the local coordinator (Antigravity/Kimi). Jules acts as the **Microoptimizer**, with four specialized operational modes:

### 1. 🛠️ Grundskills (Base Coding & Test Discipline)
- **Hermetic Testing**: All tests must be self-contained unit tests (`pytest tests/unit/`) using `unittest.mock.AsyncMock` for database queries and `tmp_path` for files. Zero network or live DB calls.
- **Contract Preservation**: Never break existing API schemas or test assertions.
- **Atomic Commits**: Small, clean, single-purpose commits with explanatory messages.

### 2. 🎨 Design Optimizer (UI/UX & Accessibility Polish)
- **WCAG 2.1 AA Contrast Enforcement**: Minimum 4.5:1 contrast ratio for normal text. Zero dark-on-dark or transparent text.
- **Intentional Aesthetic (from `ui-ux-pro-max` & `frontend-design`)**: Use clear design tokens, consistent spacing (4px / 8px / 16px grid), robust dark mode palettes, and explicit font styling.
- **Platform Inversion Defense**: Enforce `-webkit-text-fill-color` and explicit background colors on `<select>`, `<input>`, `<button>`, and `<textarea>` elements to prevent OS/GTK/browser theme overrides.

### 3. 🛡️ Security Optimizer (Isolation & Vulnerability Defense)
- **Docker Mount Verification**: Ensure every local path operation passes through `DockerMountService` (`infrastructure/storage/docker_mounts.py`) to prevent host-path escapes outside container mounts (`/opt/...`).
- **Zero Destructive Deletes**: Never use raw `os.remove` or `rm -rf`. Always use `send2trash` or `.hermes_trash` staging.
- **Injection Defense**: All PostgreSQL queries must use parameterized placeholders (`$1, $2`), never f-string interpolation.
- **Secret Sanitization**: Never commit or log API keys, tokens, or live credentials.

### 4. ⚡ Code Optimizer (Refactoring, Typing & Performance)
- **Hexagonal Boundary Enforcement**: Pure domain logic in `domain/` (zero I/O), orchestration in `application/`, adapters in `infrastructure/`, HTTP in `dashboard/`.
- **Typing & Async Hygiene**: Full type hints (`typing.Optional`, `typing.List`, `pydantic.BaseModel`), efficient `async`/`await` patterns, zero unhandled coroutine warnings.
- **Rollback Safety**: Maintain 1-click rollback integrity by ensuring all file move actions log into `execution_log` with a `batch_id`.

---

## 📁 Key Architecture Boundaries

- **Hexagonal Architecture**:
  - `src/hermes_auto_organizer/domain/`: Pure business logic and rule models — zero external dependencies.
  - `src/hermes_auto_organizer/application/`: Use-cases and orchestration.
  - `src/hermes_auto_organizer/infrastructure/`: Adapters (PostgreSQL, Tesseract OCR, Docker mounts, Send2Trash).
  - `src/hermes_auto_organizer/dashboard/`: FastAPI router (`plugin_api.py`) and React dashboard frontend (`dist/index.js`).
- **Docker Mount Awareness**:
  - Hermes Agent runs inside a Docker container.
  - Host paths (`/home/mb/...`) are mapped to `/opt/...`.
  - Always use `DockerMountService` (`infrastructure/storage/docker_mounts.py`) to validate that file operations remain inside mounted container directories.
- **Safety First**:
  - Never use destructive `rm -rf` or `os.remove` on user files.
  - Always use `send2trash` so files can be recovered from the trash.
  - Record moves in `execution_log` with a `batch_id` to maintain 1-click rollback capability.


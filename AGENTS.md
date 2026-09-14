# AGENTS.md — Hermes Auto-Organizer & Drive Index

This file is written for AI coding agents and new contributors. It assumes no
prior knowledge of the repository. It describes what the project is, how it is
built and tested, how the code is organized, and the development conventions
you must follow while working here.

The **main repository** is `https://github.com/creatiVision/hermes-drive-index`
(authoritative fork; `upstream` points to
`https://github.com/gregoryhorn/hermes-drive-index`). Treat `origin` as the
source of truth when working.

---

## 1. Project Overview

This repository contains **two Python packages** in one `src/`-layout project,
plus a **web dashboard plugin** and a set of **agent skills**:

1. **`hermes_drive_index`** (v0.1.0) — the retained core: a private, local
   Google Drive full-text search index built on **SQLite FTS5**, plus local
   drive indexing, selective-sync planning, OCR, and file-organization/cleanup
   helper tools. This is the original `hermes-drive-index` package by
   Gregory Horn, extended (Apache 2.0 Section 4(b) modifications).
2. **`hermes_auto_organizer`** (v0.2.0) — the main extension: an autonomous,
   rule-based file organizer with **PostgreSQL 16 + pgvector (HNSW)** for
   semantic clustering, an atomic execution engine with LIFO rollback, an
   Obsidian Vault visualizer, disk analysis/triage, LAN-mesh and remote-SSH
   node inspection.
3. **Dashboard plugin** — a FastAPI router (`plugin_api.py`) plus a bundled
   React frontend (`dist/index.js`, `dist/style.css`) mounted by the Hermes
   Agent web dashboard at `http://localhost:9119/organizer` (route prefix
   `/api/plugins/auto-organizer/`).
4. **`skills/`** — standalone agent skill definitions
   (`auto-organize-downloads`, `duplicate-detector`, `file-organizer`,
   `intelligent-document-organizer`, `old-file-cleanup`). These are Markdown
   prompts, not Python.

The core design idea ("Dual-State Architecture"): the system scans the current
on-disk reality (`S_now`), groups files by semantic embedding into a proposed
target ontology (`S_ideal`), and forces an LLM to act only as a *compiler* that
produces deterministic match-and-move rules. **No file is ever moved without an
explicit user-approved rule and a prior dry-run.**

Key constraints that define this codebase:

- **Zero data loss**: permanent `rm` / `os.remove` / `shutil.rmtree` on user
  files is forbidden. Local deletes use `send2trash` (fallback: a `.Trash` or
  `.hermes_trash` staging dir). Every executed move is journaled to an
  `execution_log` table with a `batch_id` so it can be rolled back (LIFO).
- **Hermetic tests**: unit tests must never touch a live database or network.
  DB-adjacent tests mock `_get_connection` / asyncpg with `unittest.mock`.
- **Hexagonal architecture**: `domain/` must stay free of I/O and framework
  imports; dependencies point inward.

---

## 2. Tech Stack

- **Language**: Python >= 3.11 (local `.venv` currently runs 3.13; CI pins 3.11).
- **Build system**: setuptools via `pyproject.toml`; `src/` layout
  (`[tool.setuptools.packages.find] where = ["src"]`); managed with `uv`
  (`uv.lock` present), wheel/sdist via `python -m build`.
  - Version is **single-sourced**: `hermes_drive_index.__version__`
    (`src/hermes_drive_index/__init__.py`) for the drive-index package;
    `hermes_auto_organizer.__version__` for the organizer.
- **Runtime deps (core)**: `pypdf>=4`, `python-docx>=1`.
- **Optional extras** (`pyproject.toml`):
  - `test`: `pytest>=8`
  - `dev`: `pytest>=8`, `ruff>=0.8`
  - `ocr`: `ocrmypdf>=15` (needs system `tesseract`)
  - `organizer`: `asyncpg>=0.29`, `pgvector>=0.2`, `ezdxf>=1.1`,
    `mutagen>=1.47`, `send2trash>=1.8`
  - `fastapi` + `httpx` are needed for the dashboard API and its tests (CI
    installs them explicitly: `pip install -e '.[test,organizer]' fastapi httpx`).
- **Databases**:
  - `hermes_auto_organizer` → local **PostgreSQL 16 + `pgvector`** (HNSW,
    `vector_cosine_ops`). Live instance: `shared-pg:5433`, database
    `agent_memory` (localhost only, private LAN). Schema in
    `src/hermes_auto_organizer/infrastructure/db/schema.sql`.
  - `hermes_drive_index` → **SQLite FTS5** index file (default
    `~/.hermes/drive_index/personal_files/index.db`).
- **CLI tools exposed as console scripts**: `hermes-drive-index` and
  `hermes-organizer`.
- **Hermes plugin entry points** (`[project.entry-points."hermes_agent.plugins"]`):
  `drive_index` → `hermes_drive_index.hermes_adapter`;
  `auto_organizer` → `hermes_auto_organizer.adapters.hermes_tools`.
- **Google Drive access** (drive-index package): reuses the existing
  `google_api.build_service("drive", "v3")` helper from the configured
  `google_api_dir` (default `~/.hermes/skills/productivity/google-workspace/scripts`),
  with stored OAuth credentials. No custom retry/backoff/throttling in this
  package — transient failures are recorded per-file (`status='failed'`).
- **Optional helper binaries** (not Python deps): `ffprobe` (video),
  `dwg2dxf` (CAD fallback), `ocrmypdf`, `tesseract` (OCR).

---

## 3. Build, Install & Test Commands

All commands run from the repository root. A `.venv` virtualenv is present.

```bash
# Install (editable, with test + dev extras)
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,test]'
# Add organizer extras + dashboard deps (CI does this):
pip install -e '.[test,organizer]' fastapi httpx

# Run the full unit test suite (all tests are hermetic; no DB/network needed)
.venv/bin/pytest -q
# or: pytest tests/unit/

# Lint (ruff is a dev extra)
.venv/bin/ruff check .

# Build wheel/sdist (needs `pip install build`)
python -m build

# Verify console scripts + plugin entry points resolve from a fresh wheel
python -m venv /tmp/verify-venv && /tmp/verify-venv/bin/pip install dist/*.whl
/tmp/verify-venv/bin/hermes-drive-index --version
```

**CI** (`.github/workflows/ci.yml`) runs on push/PR with Python 3.11:
- `test` job: `pip install -e '.[test,organizer]' fastapi httpx` then `pytest`.
- `package` job: builds wheel, installs into a clean venv, asserts the
  `hermes-drive-index` console script and the `drive_index` plugin entry point
  resolve.
- `status-check` job: gates on `test` + `package` both succeeding.

**Local helper scripts** (`scripts/`):
- `collect_real_world_metrics.py` — aggregates public (sanitized) index
  metrics; never includes document names, paths, IDs, snippets, or personal
  data. `--dry-run` prints without writing.
- `collect_system_filesystem_tree.py` — collects system filesystem tree data.
- `test_web_ui.js` — headless Chrome (CDP) smoke test for the dashboard at
  `http://127.0.0.1:9119/organizer`; captures screenshots to `/tmp/`.
- `verify_and_release_pr.py` — PR gatekeeper: conflict check
  (`git merge-tree --write-tree`), full pytest in an isolated worktree, wheel
  build check, posts a review comment, optionally squash-merges
  (`--pr N --merge` / `--dry-run`).

**Database migrations** (organizer package only):

```bash
python -m hermes_auto_organizer.infrastructure.db.migrations
```

---

## 4. Repository Layout & Module Map

```
src/
├── hermes_auto_organizer/          # Main extension (PostgreSQL + pgvector)
│   ├── __init__.py                 # __version__ = "0.2.0"
│   ├── config.py                   # AppConfig: db / embedding / vault / execution
│   ├── domain/                     # PURE domain: zero I/O, zero framework imports
│   │   ├── models.py               # StorageRoot, FileNode, FileExtraction,
│   │   │                           #   FileEmbedding, OrganizationRule, MoveIntent,
│   │   │                           #   ExecutionRecord, TrashCandidate, LanDeviceNode, ...
│   │   ├── policies.py             # BoundaryPolicy (path containment), CollisionPolicy,
│   │   │                           #   RuleStatePolicy (state machine), DiskCleaningPolicy
│   │   └── rule_engine.py          # Modular rule conditions (source_folder/timeframe/
│   │                               #   keyword/extension/file_size) + resolve_destination_path
│   ├── application/                # Use cases & orchestration
│   │   ├── ports/                  # Abstract Protocols (storage, repository, extractors,
│   │   │                           #   visualizer, disk_analyzer_port, profiler_port,
│   │   │                           #   ssh_node_port)
│   │   ├── services/               # semantic_enricher.py
│   │   └── use_cases/              # cluster, dry_run, disk_analyzer, lan_mesh_service,
│   │                               #   ssh_node_service, subtree_profiler_service,
│   │                               #   symlink_migrator
│   ├── infrastructure/             # Concrete adapters
│   │   ├── db/                     # connection.py (asyncpg pool + pgvector),
│   │   │                           #   migrations.py, repositories.py, schema.sql
│   │   ├── storage/                # local_scanner, hashing (two-tier: xxh64 probe +
│   │   │                           #   streamed SHA-256), atomic_runner (EXDEV + LIFO
│   │   │                           #   rollback), docker_mounts, fast_disk_scanner,
│   │   │                           #   gdrive_ingest, lan_mesh_scanner, migration_service,
│   │   │                           #   metadata_writer, ssh_node_inspector, recursive_profiler
│   │   ├── parsers/                # cad_parser (ezdxf), doc_parser (pypdf/python-docx),
│   │   │                           #   image_parser, media_parser (mutagen/ffprobe),
│   │   │                           #   composite (router/dispatcher)
│   │   └── obsidian/               # vault_sync (Markdown dashboards), extended_graph_exporter
│   ├── adapters/                   # Inbound driving adapters
│   │   ├── cli.py                  # hermes-organizer console script
│   │   └── hermes_tools.py         # Hermes RPC tool definitions (register_tools)
│   └── dashboard/
│       ├── plugin_api.py           # FastAPI APIRouter (health, stats, mounts, roots,
│       │                           #   rules, dry-run, execute, rollback, taxonomy, sync, ...)
│       ├── manifest.json           # Dashboard plugin manifest (name auto-organizer,
│       │                           #   entry dist/index.js, api plugin_api.py)
│       └── dist/                   # Bundled React frontend (index.js, style.css)
│
├── hermes_drive_index/             # Retained core (SQLite FTS5)
│   ├── __init__.py                 # __version__ = "0.1.0", public re-exports
│   ├── api.py                      # Public façade: build_index, incremental_update,
│   │                               #   reindex_metadata_only, search, status,
│   │                               #   find_duplicates, flag_old_files, ...
│   ├── config.py                   # Precedence: explicit overrides > env
│   │                               #   (HERMES_DRIVE_INDEX_*) > TOML > defaults
│   ├── cli.py                      # hermes-drive-index console script
│   ├── core/                       # Pure indexing logic; MUST NOT import Hermes modules
│   │   ├── crawler.py              # Drive crawl + download/export (paginated, pageSize=1000)
│   │   ├── extract.py              # Text extraction + chunking (2400 chars / 250 overlap)
│   │   ├── ocr.py                  # External ocrmypdf / tesseract wrappers (opt-in)
│   │   ├── index.py                # SQLite schema (files/chunks/chunks_fts/runs), SCHEMA_VERSION
│   │   ├── manifest.py             # plan_incremental_actions (pure, network-free)
│   │   ├── models.py               # DriveFile, INDEXABLE_MIMES, is_indexable
│   │   ├── orchestrator.py         # build/update/search/status orchestration
│   │   ├── search.py               # FTS5 query + status
│   │   ├── cleaner.py              # classify_old_files, detect_duplicates,
│   │   │                           #   plan_document_structure, plan_download_organization
│   │   ├── local_index.py          # index_local_directory (SQLite)
│   │   ├── local_scanner.py        # scan_local_directory, LocalFile, safe_trash
│   │   ├── organize.py             # Drive auto-organization rules (OrganizeConfig)
│   │   ├── organizer_workflow.py   # intent_check, access_check, analyse_first,
│   │   │                           #   propose_plan, validate_approval, execute_on_approval
│   │   ├── sync.py / sync_state.py # Selective sync planning (SyncMapping, SyncPlan)
│   │   └── utils.py
│   ├── drive/                      # Google auth/client seams (Protocol-based, mockable)
│   └── hermes_adapter/             # THIN Hermes integration ONLY
│       ├── __init__.py             # register(ctx) entry point
│       └── tools.py                # JSON-safe handlers + TOOL_SPECS schemas
│
├── hermes_drive_index.egg-info/    # Build artifact (untracked, gitignored)
```

Tests live under `tests/unit/` (`tests/unit/` for FTS5/CLI/organizer-workflow
tests, `tests/unit/auto_organizer/` for the organizer package and dashboard
API). `scripts/`, `docs/`, `skills/`, `examples/` are at the root.

---

## 5. Runtime Architecture

### 5.1 Drive index (SQLite FTS5) — `hermes_drive_index`

- **CLI**: `hermes-drive-index <build|update|incremental|status|doctor|search|duplicates|cleanup-old|organize-downloads|organize-documents|organize-analyze|organize-plan|organize-execute|index-local|sync-plan|benchmark-ocr>`.
  Global flags `--config`, `--root-folder-id`, `--db-path`, `--base-dir`,
  `--ocr`, `--no-ocr`, `--ocr-pdf-arg`, `--ocr-image` override config.
- **Build flow** (`core/orchestrator.py:build_index`): crawl Drive from the
  configured root → write `index.new.db` → atomically swap it in; failed files
  keep a `failed` status row; metrics to `last_build_metrics.json`.
- **Incremental update** (`incremental_update`): fresh crawl, manifest-diff
  (`plan_incremental_actions`) deciding `delete` / `skip` / `metadata_only` /
  `reindex` / `unchanged`, applied in one SQLite transaction. Pure metadata
  reindex (`reindex_metadata_only`) retries `indexed_metadata` rows. There is
  **no** Drive Changes-API resume path.
- **Search**: FTS5 with rank; `search(query, top_k)`; Hermes adapter clamps
  `top_k` to 1–25.
- **Indexability** is MIME-driven (`core/models.py`): PDF, text/*, DOCX, legacy
  DOC (metadata-only), Google Docs/Sheets/Slides, JSON; folders/videos skipped;
  images only with `ocr_image_enabled`.
- **OCR** is opt-in (default off): `ocrmypdf --skip-text` for empty PDF text,
  `tesseract <img> stdout` for images; both wrapped with 120 s timeouts and
  return `None` on failure (never raise).

**Hermes adapter contract** (stable, do not break):
every handler returns a JSON **string** with top-level `success` bool and
`package_version` on both success and error paths; errors never propagate as
exceptions. Tool names/schemas are byte-stable: `drive_index_search`,
`drive_index_status`, `drive_index_update`, plus the file-organizer skill tools
(`file_organizer_*`, `duplicate_detector`, `old_file_cleanup`,
`auto_organize_downloads`, `intelligent_document_organizer`,
`local_drive_index`, `selective_sync_plan`).

**Import boundary (test-enforced by `tests/unit/test_import_boundaries.py`)**:
`core/` and `api.py` must NOT import `hermes_adapter/` or Hermes-only modules
(`hermes_constants`, `model_tools`, `toolsets`, `tools.registry`). The only
touch-point is the *soft* `hermes_constants` import in `config.py`, which
degrades gracefully to `~/.hermes` outside Hermes.

### 5.2 Auto-organizer (PostgreSQL + pgvector) — `hermes_auto_organizer`

- **Config**: environment-driven via `config.py` —
  `HERMES_DB_HOST/PORT/USER/PASSWORD/NAME/SSL/MIN_POOL/MAX_POOL`,
  `HERMES_EMBED_MODEL/DIM/BATCH`, `HERMES_OBSIDIAN_VAULT`,
  `HERMES_MAX_BATCH_SIZE`, `HERMES_USE_TRASH`.
- **Database**: `DatabaseConnectionPool` (asyncpg + `register_vector`). Schema
  (see `infrastructure/db/schema.sql`): `storage_roots`, `file_nodes`,
  `file_extractions` (keyed by `content_sha256`), `file_embeddings` (vector(1536),
  HNSW index, unique `(content_sha256, model_name)`), `structural_anomalies`,
  `organization_rules`, `execution_log`.
- **Content-Hash Cache Pattern** (`infrastructure/storage/hashing.py`): Tier 1
  O(1) probe = 4 KB head + 4 KB tail xxHash64 (`xxhash` if present, else
  truncated SHA-256); Tier 2 = streamed 64 KB-chunk SHA-256. Extractions are
  keyed by SHA-256 so renames/moves cost zero re-extraction.
- **Pipelines** (use cases in `application/use_cases/`):
  - `disk_analyzer.py` — progressive directory drill-down + trash-candidate
    validation (enforces `DiskCleaningPolicy` boundaries, nested-candidate
    dedup).
  - `cluster.py` — anomaly detection (dump zones, orphans, misplaced clusters,
    exact duplicates).
  - `dry_run.py` — resolve destination paths + collision detection, emits
    `MoveIntent`s.
  - `lan_mesh_service.py` — multi-device LAN topology (5 hosts), Syncthing
    folder awareness, root-partition triage with LIFO rollback.
  - `symlink_migrator.py`, `ssh_node_service.py`, `subtree_profiler_service.py`
    — symlink-based disk migration and remote SSH node inspection.
- **Atomic execution** (`infrastructure/storage/atomic_runner.py`):
  pre-move SHA-256 check → move (or cross-device
  copy-to-temp → verify → `rename` → trash source) → post-move hash
  verification → attach xattr metadata → `ExecutionRecord`. Rollback restores
  the file only if the recorded hash still matches.
- **Dashboard API** (`dashboard/plugin_api.py`): FastAPI `APIRouter` with
  endpoints for health/stats/mounts/roots/anomalies/rules (CRUD + test),
  dry-run (in-memory `_DRY_RUN_CACHE`), execute, rollback, taxonomy
  approve/nodes, sync mappings + plan/execute, filesystem-tree node-switch,
  profiler/routes. Path translation helpers (`to_user_path`) map container
  `/opt/data/...` paths to host `/media/...` paths.
- **Obsidian visualizer** (`infrastructure/obsidian/vault_sync.py`): writes
  `📊 Current State Overview.md`, `📋 Pending Moves.md`, `🗺️ Ideal Taxonomy Map.md`,
  `⚠️ Redundancies and Conflicts.md` under `<vault>/Auto-Organizer/`.
- **Hermes tools** (`adapters/hermes_tools.py`): minimal but honest — several
  handlers are currently **stubs** returning `"success"` with zero counts
  (`get_anomalies`, `dry_run`, `approve_rule`). The real automation surfaces are
  the dashboard API and the `hermes-drive-index` CLI. Do not assume a tool
  performs side effects without checking the implementation.

### 5.3 Agent skills

`skills/*/SKILL.md` are instructions for the connected agent (not imported by
Python). They follow a strict workflow: intent check → access check → analyse
first → propose plan → **wait for explicit user approval** → execute; dry-run
mode; honesty rules (no undo, never invent files, never guess contents from
names). The `file-organizer` skill wording ("I execute... on explicit approval")
predates the stronger safety model above — prefer the codebase invariants when
they conflict.

---

## 6. Development Conventions

### Safety invariants (highest priority — never violate)

1. **No permanent deletion of user files.** Use `send2trash` /
   `.hermes_trash` / `.Trash` staging. Raw `os.remove` / `rm -rf` /
   `shutil.rmtree` on user content is forbidden.
2. **Every move is journaled** to `execution_log` with a `batch_id`; rollback
   must stay possible (verify-by-hash before restoring).
3. **Path containment.** Validate destinations against storage roots
   (`BoundaryPolicy.assert_contained`) and container mounts
   (`DockerMountService` in `infrastructure/storage/docker_mounts.py`). Hermes
   runs in a container where host `/home/mb/...` ↔ container `/opt/data/...`;
   never operate on unmounted host paths. `DiskCleaningPolicy` rejects
   critical system paths and mount roots as cleanup targets.
4. **Collisions are never overwritten.** `CollisionPolicy.resolve_collision_path`
   produces `{name}_conflict_{timestamp}_{hash}.{ext}`.
5. **SQL parameterization.** All PostgreSQL queries use `$1, $2` placeholders
   (asyncpg), never f-string interpolation.
6. **No secrets in the repo.** Never commit/print OAuth tokens, DB passwords,
   folder IDs, or live connection strings. `.gitignore` excludes
   `*token*.json`, `*client_secret*.json`, `credentials*.json`, `.env`, `*.db`,
   `config.toml`, `*manifest*.json` (with whitelist exceptions).

### Architecture rules

- **Hexagonal boundaries** (`hermes_auto_organizer`): `domain/` = pure models
  + policies, zero I/O and zero framework imports; `application/` = use cases
  and ports (Protocols); `infrastructure/` = concrete adapters (asyncpg,
  parsers, filesystem); `dashboard/` = HTTP layer only; `adapters/` = inbound
  CLI/Hermes.
  Tests in `tests/unit/test_import_boundaries.py` enforce that `core/` (drive
  index) never imports Hermes modules.
- **Typing & async hygiene**: full type hints everywhere, `from __future__ import
  annotations`, frozen/slots dataclasses for domain models, `async`/`await` for
  all I/O (asyncpg, scanners, FastAPI). No unhandled coroutine warnings.
- **Config precedence** (drive index): explicit overrides > `HERMES_DRIVE_INDEX_*`
  env vars > local TOML `config.toml` > built-in defaults. The organizer uses
  `HERMES_*` env vars (see 5.2).

### Code style

- Python 3.11+, type-hinted; mostly 4-space indentation, docstrings on every
  module and public class/function; Apache 2.0 header on new files
  (model on existing files).
- `ruff` is the configured linter (dev extra). No pre-commit hook is
  configured.
- Comments in this repo are occasionally German; **match the surrounding
  language** of the file you edit. Code identifiers and commit messages are in
  English.

### Git workflow

- Small, atomic, single-purpose commits with conventional-commit style
  prefixes commonly seen in history: `feat(scope):`, `fix(scope):`,
  `ci(gatekeeper):`, `⚡ Bolt: ...` (perf), `🎨 Palette: ...` (UI/a11y).
- Feature branches off `main`; PRs reviewed via the gatekeeper
  (`scripts/verify_and_release_pr.py`) or CI status check; squash merges.
- The `AGENTS.md` files for agent behavior: `JULES.md` and `.jules/instructions.md`
  describe the "Jules = Microoptimizer" workflow (hermetic tests, contract
  preservation, atomic commits). `SKILL.md` at the root is the agent-facing
  `file-organizer` skill.

---

## 7. Testing Strategy

- **All unit tests must be hermetic**: no live PostgreSQL, no network, no real
  Google Drive. Use:
  - `unittest.mock.patch` / `AsyncMock` on `_get_connection` and asyncpg
    fetches (see `tests/unit/auto_organizer/test_dashboard_plugin.py` for the
    canonical pattern, including the autouse `_reset_db_pool` fixture that
    resets the module-level `_db_pool` singleton between tests).
  - `tmp_path` (pytest) for any file-based operation.
- Run the whole suite with `.venv/bin/pytest -q` (currently **180 passed**,
  ~15 s). CI runs `pytest` on Python 3.11 with `.[test,organizer]` + `fastapi`
  + `httpx`.
- Notable suites:
  - `tests/unit/test_public_data_guard.py` — scans the repo for committed
    secrets/DBs/private patterns (see Security); keep it green.
  - `tests/unit/test_import_boundaries.py` — enforces the core→adapter
    dependency rule.
  - `tests/unit/auto_organizer/test_scanner_optimization_pr15.py` — scanner
    performance regression benchmark (1,000 files).
  - `tests/unit/test_ocr_benchmark.py`, `test_schema_version.py`,
    `test_search_dedup.py`, `test_incremental_plan.py` (drive index).
- End-to-end integration against the live `agent_memory` DB and real Drive is
  done manually by the local developer; it is not part of CI.

---

## 8. Security Considerations

- **The local index is sensitive data.** SQLite FTS content can contain full
  text from private Google Drive documents. Treat `index.db`, cached downloads,
  and manifests as sensitive. `.gitignore` excludes all `*.db` / `*.sqlite*` /
  `*manifest*.json` / token / credential files.
- **Never commit**: index databases, OAuth tokens or client secrets, real
  folder IDs, real manifests/golden queries, crawl logs/reports, DB passwords,
  or live DSNs. `tests/unit/test_public_data_guard.py` enforces this by
  scanning the repo; keep it passing and extend
  `HERMES_DRIVE_INDEX_PRIVATE_GUARD_PATTERNS` for local-only checks.
- **Logs and status output** should prefer aggregate counts and paths over
  document snippets. Debug output may contain sensitive content — keep it out
  of committed fixtures.
- **Known hazard**: `src/hermes_auto_organizer/dashboard/plugin_api.py` reads
  defaults for `HERMES_DB_PASSWORD` with a hard-coded fallback value and builds
  a DSN at import time. Prefer real environment configuration; do not reuse or
  propagate that fallback, and never print connection strings.
- **Optional OCR and external binaries** are invoked via subprocess with
  timeouts; missing tools degrade gracefully (metadata-only indexing), never
  crash.
- **External network tools and external fetches are disabled** in this
  environment; do not rely on them.

---

## 9. Useful Reference Points

- `docs/architecture.md` — deep dive on the drive-index package (layering,
  config precedence, Drive API calls/rate limits, OCR pipeline, schema
  versioning, deleted/trashed/renamed handling, adapter contract).
- `docs/migration.md` — migrating from a prototype / direct site-packages
  wrapper to the packaged CLI + plugin (includes rollback).
- `docs/security.md` — the short, canonical privacy policy for this repo.
- `docs/real-world-metrics.md` — what aggregate metrics may be published and
  what must stay private.
- `docs/plans/phase-e-package-plugin-architecture.md` — packaging hardening
  plan (much of it now implemented).
- `README.md` — user-facing features, installation, CLI usage, and the web
  dashboard user guide.
- `examples/config.example.toml` — documented example drive-index config.
<!--
Modifications Copyright (c) 2026 creatiVision
Original Work Copyright (c) Gregory Horn and contributors
Licensed under the Apache License, Version 2.0 (the "License").
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
In accordance with Section 4(b) of the Apache 2.0 License, this file and the repository
have been modified to expand the project from hermes-drive-index into hermes-auto-organizer.
-->

# Hermes Auto-Organizer

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL_17_%2B_pgvector_0.8.6-336791)](https://github.com/pgvector/pgvector)
[![Hermes Agent](https://img.shields.io/badge/Hermes_Agent-plugin-8a2be2)](https://github.com/NousResearch/hermes-agent)

> Autonomous, rule-based file management and semantic clustering for the Hermes Agent.

---

## Attribution & Project Lineage

This project is an authorized fork and extension of [`hermes-drive-index`](https://github.com/gregoryhorn/hermes-drive-index), originally created by **Gregory Horn and contributors** under the Apache License, Version 2.0.

- **Upstream Repository:** https://github.com/gregoryhorn/hermes-drive-index
- **Fork & Extension:** Developed by **creatiVision** under the Apache License, Version 2.0.
- **Prominent Notice of Modifications:** Substantial modifications include multi-root local/cloud storage auto-organization, PostgreSQL + pgvector semantic persistence, multi-modal parsers (CAD, PDF, audio, video), atomic execution with LIFO rollback, and a tabbed dashboard UI.
- Original `LICENSE` is retained; attribution details in `NOTICE`.

---

## What It Does

Hermes Auto-Organizer scans your local drives, extracts metadata from files (PDFs, CAD drawings, audio, video, images), stores everything in PostgreSQL with pgvector embeddings, and helps you create rules to automatically organize files into a clean target hierarchy.

**The workflow is simple:**
1. **Scan** — select source folders, index files into the DB
2. **Approve** — review the target taxonomy tree
3. **Rule** — create or adopt AI-suggested rules (with natural-language chat)
4. **Preview** — dry-run simulation shows exactly what moves where
5. **Execute** — atomic moves with one-click rollback

---

## Dashboard UI — Tabbed Dashboard

The dashboard at `http://localhost:9119/organizer` has a left rail with 6 tabs:

| Tab | What you do |
|-----|-------------|
| 📁 Quellen | Select source folders from the host filesystem tree, trigger scanning. **Path autocomplete** while typing + **clickable breadcrumb** navigation |
| 📊 Übersicht | Overview cards: file count, size, duplicates, disk usage |
| 🗺️ Taxonomie | Approve/edit the target folder hierarchy tree |
| 📋 Regeln | Manage rules — each rule has a thought-process summary and an AI chat input for natural-language modification |
| ▶ Vorschau | Dry-run preview table: Source → Destination, with status badges. Execute button at bottom |
| 📜 Journal | Execution history with one-click rollback per batch |

**Design principles:**
- No canvas visualizations — trees and tables only
- One action per tab
- German UI labels
- Color badges: 🟢 approved, 🟡 proposed, ⚪ excluded
- Settings (gear icon): DB status, Docker mounts, pgvector indicator

---

## API — 16 Routes

Base path: `/api/plugins/auto-organizer/`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | DB + pgvector status |
| GET | `/stats` | Overview numbers |
| GET | `/mounts` | Docker mount list |
| GET | `/sources/tree` | Host-filesystem tree (from cached JSON) |
| GET | `/sources/complete` | Path autocomplete suggestions + breadcrumbs for a typed prefix |
| POST | `/sources/scan` | Trigger indexing of selected sources |
| GET | `/taxonomy` | Target hierarchy from `taxonomy_nodes` table |
| POST | `/taxonomy/node` | Create/update/approve a taxonomy node |
| GET | `/rules` | All rules (DB + AI-suggested), with thought-process |
| POST | `/rules` | Create or update a rule |
| POST | `/rules/{id}/chat` | AI chat for one rule (natural-language modification) |
| POST | `/rules/{id}/toggle` | Enable/disable a rule |
| POST | `/preview` | Dry-run simulation (persisted to `plugin_state`) |
| POST | `/execute` | Execute approved batch |
| GET | `/journal` | Execution history |
| POST | `/journal/{id}/rollback` | Rollback a batch |

All state is persisted in PostgreSQL (`plugin_state` table) — no in-memory stores that vanish on restart.

---

## Architecture (Hexagonal / Ports & Adapters)

```
src/hermes_auto_organizer/
├── domain/               # Pure business entities, zero I/O
│   ├── models.py         # 11 dataclasses + 9 enums
│   ├── policies.py       # Collision, Boundary, RuleState policies
│   └── rule_engine.py    # Modular condition evaluator (AND/OR)
│
├── application/          # Use cases & port contracts
│   ├── ports/            # Storage, Repository, Extractor, Visualizer protocols
│   └── use_cases/        # AnomalyDetector, DryRunEngine
│       └── services/     # SemanticEnricher (LLM + heuristic fallback)
│
├── infrastructure/       # Outbound concrete adapters
│   ├── db/               # asyncpg pool + pgvector, 4 repositories, schema.sql (9 tables)
│   ├── storage/          # LocalFilesystemScanner, DockerMountService, AtomicExecutionRunner, hashing, xattr
│   ├── parsers/          # Composite: CAD (ezdxf), PDF (pypdf+OCR), Image (tesseract), Media (mutagen+ffprobe)
│   └── obsidian/         # Optional Markdown dashboard writer
│
├── adapters/             # Inbound driving adapters
│   ├── cli.py            # hermes-organizer CLI
│   └── hermes_tools.py   # 4 Hermes Agent RPC tools
│
├── dashboard/            # Web plugin
│   ├── manifest.json     # Plugin metadata (tab /organizer)
│   ├── dist/index.js     # React frontend (37KB, tabbed dashboard)
│   └── plugin_api.py     # 15 FastAPI routes
│
├── config.py             # 5 dataclass configs (Database/Embedding/Vault/Execution/App)
└── __init__.py
```

---

## Database

PostgreSQL 17 + pgvector 0.8.6, running in the `shared-pg` Docker container (port 5433).

**9 tables:**
- `storage_roots` — registered source directories
- `file_nodes` — indexed files with two-tier hashes
- `file_extractions` — content metadata (summary, parsed fields)
- `file_embeddings` — pgvector embeddings (HNSW index)
- `structural_anomalies` — duplicates, dump-zone files, misplaced clusters
- `organization_rules` — match conditions + target templates
- `execution_log` — atomic move ledger with rollback state
- `plugin_state` — key-value JSONB store (replaces all in-memory state)
- `taxonomy_nodes` — hierarchical target folder tree

---

## Installation & Setup

### Requirements
- Python 3.11+
- PostgreSQL 17 with `pgvector` extension (`shared-pg` Docker container)
- Optional: `ffprobe`, `tesseract` (for media/OCR parsing)

### 1. Install
```bash
cd /media/xchg/skripts/skripts-ai/hermes_gdrive_index_fork+localdrives
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,test]'
```

### 2. Configure
Environment variables (set in `docker-compose.yaml` for the Hermes container):
```bash
HERMES_DB_HOST=localhost
HERMES_DB_PORT=5433
HERMES_DB_USER=pgadmin
HERMES_DB_PASSWORD=...
HERMES_DB_NAME=hermes_organizer
```

### 3. Run migrations
```bash
python -m hermes_auto_organizer.infrastructure.db.migrations
```

### 4. Enable plugin
In Hermes `config.yaml`:
```yaml
plugins:
  enabled:
    - auto-organizer
```

### 5. Deploy to Hermes container
```bash
# Sync plugin code to container mount
rsync -a --delete src/hermes_auto_organizer/ \
  /media/xchg/ai-agents-workspaces/hermes/.hermes/plugins/auto-organizer/dashboard/hermes_auto_organizer/

# Install pgvector in container venv (survives until next image update)
docker exec hermes-dashboard /opt/hermes/.venv/bin/python -m pip install pgvector

# Restart dashboard
cd /media/xchg/ai-agents-workspaces/hermes/docker && docker compose up -d hermes-dashboard
```

The lazy pgvector import in `connection.py` ensures the plugin loads even if pgvector is missing — DB features just degrade gracefully.

---

## CLI Usage

```bash
# Scan and index a local storage root
hermes-organizer ingest --root /media/work-data/002_cv-projects --name projects

# Export status to Obsidian vault
hermes-organizer sync-obsidian

# Dry-run a rule
hermes-organizer dry-run --rule-id <UUID>
```

---

## Changelog

### v1.0.0 (2026-09) — Architecture redesign + stability fixes

**Architecture** (refactor to tabbed dashboard):
- Backend: **44 → 15 API routes**, all in-memory `_STORE` dicts moved to PostgreSQL `plugin_state` table
- Frontend: **428KB → 37KB**, 4-step wizard replaced with a 6-tab left-rail dashboard (Quellen / Übersicht / Taxonomie / Regeln / Vorschau / Journal), canvas visualizations removed
- DB: 9 tables (`plugin_state`, `taxonomy_nodes` added), `organization_rules.source` column

**Stability fixes** (deployed & verified live in `hermes-dashboard` container):
- **Pool connection leak** — `_get_connection()` released connections back to the pool before the caller used them, causing `InterfaceError: connection has been released back to the pool` on all DB routes. Fixed via `acquire_raw()`/`acquire_release()` on `DatabaseConnectionPool`; `_get_connection()` now returns a live connection.
- **SQL GROUP BY error** — `GET /journal` referenced `executed_at` without aggregation; fixed to `MAX(executed_at)`.
- **React hook crash on tab switch** — Hermes Dashboard's React reconciler crashed when unmounting/mounting components at the same tree position; fixed by rendering all tabs simultaneously (CSS `display` toggle).
- **Plugin registration** — added `window.__HERMES_PLUGINS__.register()` + onload fallback so the plugin registers reliably.

**Features**:
- **Path autocomplete + breadcrumb (Quellen tab)** — new `GET /sources/complete` endpoint returns autocomplete suggestions + breadcrumb segments for a typed path prefix; the Quellen tab shows a live dropdown while typing and a clickable breadcrumb bar.
- **PR #11 audit fixes** — `rule_chat` AttributeError (Record accessed as attribute + missing `await`), UUID validation returning 400, rollback `None` dereference; all covered by `tests/unit/auto_organizer/test_plugin_api_bugs.py` (12 regression tests).

**Known limitations:**
- `pgvector` Python package must be `pip install`ed in the container venv (lost on image rebuild); the lazy import in `connection.py` ensures the plugin still loads without it (vector features degrade gracefully).
- DB state lives in `shared-pg` (port 5433) — external to the Hermes image, survives updates.

---

## Testing

```bash
.venv/bin/pytest -q
```

Unit tests cover domain models, policies, hashing, path validation, and the 15 API routes (mocked connections). Run targeted suite:
```bash
.venv/bin/pytest tests/unit/auto_organizer/ -q   # backend/plugin tests
```

---

## Vault Documentation

Detailed documentation lives in the Obsidian Vault:
`03-Entities/Services/Hermes-Auto-Organizer.md`

Includes: architecture, DB schema, deployment steps, change log (v0.3→v1.0).

---

## Branch Status

- `feat/source-lan-tree-ai-chat` — Active development branch (not merged to main)
- `main` — Protected (required PR checks + approval)
- Recent commits:
  - `08047b0` — Fix: onload fallback for plugin registration
  - `71ba858` — Fix: pool connection leak (acquire_raw), journal GROUP BY
  - `0b9ab58` — Fix: React hook crash (render tabs via display toggle)
  - `3c442fc` — Fix: Hermes plugin registration pattern + vault docs
  - `7d6f549` — Phase 4: Tests + Bug Fixes
  - `fe2ea90` — Phase 3: Config cleanup, README
  - `2bd3455` — Phase 2: Frontend rewrite (Tabbed Dashboard, 428KB→37KB)
  - `dde9e72` — Phase 1: 44→15 Routes, In-Memory→DB

---

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

- Original Work Copyright (c) Gregory Horn and contributors
- Modifications Copyright (c) 2026 creatiVision

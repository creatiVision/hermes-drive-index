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
| 📁 Quellen | Select source folders from the host filesystem tree, trigger scanning |
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

## API — 15 Routes

Base path: `/api/plugins/auto-organizer/`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | DB + pgvector status |
| GET | `/stats` | Overview numbers |
| GET | `/mounts` | Docker mount list |
| GET | `/sources/tree` | Host-filesystem tree (from cached JSON) |
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
│   ├── dist/index.js     # React frontend (36KB, tabbed dashboard)
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

## Testing

```bash
.venv/bin/pytest -q
```

143 tests pass.

---

## Vault Documentation

Detailed documentation lives in the Obsidian Vault:
`03-Entities/Services/Hermes-Auto-Organizer.md`

Includes: architecture, DB schema, deployment steps, change log (v0.3→v0.4).

---

## Branch Status

- `feat/source-lan-tree-ai-chat` — Active development branch (not merged to main)
- `main` — Protected (required PR checks + approval)
- Commits:
  - `dde9e72` — Phase 1: 44→15 Routes, In-Memory→DB
  - `2bd3455` — Phase 2: Frontend rewrite (Tabbed Dashboard, 428KB→36KB)
  - `fe2ea90` — Phase 3: Config cleanup, README
  - `7d6f549` — Phase 4: Tests + Bug Fixes

---

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

- Original Work Copyright (c) Gregory Horn and contributors
- Modifications Copyright (c) 2026 creatiVision

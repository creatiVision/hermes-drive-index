<!--
Modifications Copyright (c) 2026 creatiVision
Original Work Copyright (c) Gregory Horn and contributors
Licensed under the Apache License, Version 2.0 (the "License").
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
In accordance with Section 4(b) of the Apache 2.0 License, this file and the repository
have been modified to expand the project from hermes-drive-index into hermes-auto-organizer.
-->

# Hermes Auto-Organizer & Drive Index

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL_16_%2B_pgvector_HNSW-336791)](https://github.com/pgvector/pgvector)
[![SQLite FTS5](https://img.shields.io/badge/legacy_search-SQLite_FTS5-00bcd4)](https://www.sqlite.org/fts5.html)
[![Hermes Agent](https://img.shields.io/badge/Hermes_Agent-plugin-8a2be2)](https://github.com/NousResearch/hermes-agent)

> **Autonomous, rule-based file management, semantic clustering, and private document search engine for the NousResearch Hermes Agent.**

---

## Attribution & Project Lineage

This project is an authorized fork and extension of [`hermes-drive-index`](https://github.com/gregoryhorn/hermes-drive-index), originally created by **Gregory Horn and contributors** under the Apache License, Version 2.0.

- **Upstream Repository:** https://github.com/gregoryhorn/hermes-drive-index
- **Fork & Extension:** Developed by **creatiVision** under the Apache License, Version 2.0.
- **Prominent Notice of Modifications:** In compliance with Section 4 of the Apache 2.0 License, substantial modifications and additions have been introduced:
  1. Expansion from Google Drive FTS5 indexing into a full multi-root, local and cloud storage auto-organizer (`hermes-auto-organizer`).
  2. Dual-State Architecture ($\mathcal{S}_{\text{now}} \xrightarrow{\mathcal{R}} \mathcal{S}_{\text{ideal}}$) powered by semantic clustering and deterministic rule compilation.
  3. Relational and vector persistence layer utilizing **PostgreSQL 16 + pgvector with HNSW indexing**.
  4. Content-Hash Cache Pattern (two-tier probe + streamed SHA-256) for zero-redundancy multi-modal extraction.
  5. Multi-modal parsers for CAD/drawings (`.dwg`, `.dxf`), documents (`.pdf`, `.docx`), audio stems (`mutagen`), and video containers (`ffprobe`).
  6. Interactive Obsidian Vault integration (real-time Markdown dashboards, taxonomy maps, and dry-run checklists).
  7. Atomic execution engine featuring cross-device (`EXDEV`) copy-verify-trash and full LIFO rollback ledger.
  8. Full retention of original Google Drive search, local drive indexing, selective sync, and cleanup skills.
  9. Original `LICENSE` is retained in full; attribution details are recorded in `NOTICE`.

---

## Why Hermes Auto-Organizer?

Modern workflows scatter critical documents across local partitions (NVMe, SSDs, external backup drives), network mounts, and Google Drive accounts. Traditional indexing aids lookup, but storage inevitably deteriorates into cluttered "dump zones" (`~/Downloads`, `~/Desktop`) with broken hierarchies, near-duplicates, and untracked versions.

**Hermes Auto-Organizer solves this without permitting chaotic, hallucinated file moves:**

```
       [ Local Drives / GDrive / Network Mounts ]
                          │
                          ▼ (Background Ingestion Worker)
               [ Multi-Modal Parsers ]
                          │
                          ▼
            [ PostgreSQL + pgvector DB ]
           /                            \
(Now-State Metadata)             (Content Embeddings)
           \                            /
            ▼                          ▼
       [ Structural Analyzer & Cluster Engine ]
                          │
                          ▼
        [ Synthesized "Ideal Tree" Ontology ]
                          │
                          ▼
          [ Obsidian Vault Sync & Visualizer ]
                          │
                          ▼ (Hermes Interactive Chat)
             [ User Rule Approval Loop ]
                          │
             [ Approved Rules Store ]
                          │
                          ▼
                 [ Dry-Run Manifest ]
                          │ (User Approves Chunk)
                          ▼
             [ Atomic Execution Engine ]
                          │
            [ LIFO Rollback Audit Buffer ]
```

1. **The "Now-State" ($\mathcal{S}_{\text{now}}$):** Physical reality across all storage roots (paths, hashes, sizes, MIME types, metadata).
2. **The "Ideal Tree" ($\mathcal{S}_{\text{ideal}}$):** Synthesized target ontology derived by clustering semantic file embeddings and learning historical path naming conventions.
3. **The Deterministic Bridge ($\mathcal{R}$):** The system **never** permits unconstrained, hallucinated file moves. The LLM acts solely as a compiler from semantic clusters into deterministic match-and-move rules that require explicit user approval via Hermes chat before execution.

---

## Key Features

### 1. Storage Intelligence & Ingestion
- **Multi-Root Support:** Ingest and index local directories, external mounts, and Google Drive roots under unified namespaces.
- **Two-Tier Content Addressing:** Fast change-detection probe ($O(1)$ head/tail `xxHash64` + size + mtime) paired with streamed chunked `SHA-256` for exact deduplication.
- **Content-Hash Extraction Cache:** Heavy operations (PDF parsing, OCR, CAD layer extraction, LLM summaries) are keyed by SHA-256—moving or renaming a 500 MB file incurs **zero** re-extraction or re-embedding cost.
- **Multi-Modal Extractors:**
  - *CAD / Architecture:* `.dwg`, `.dxf` via `ezdxf` and fallback converter.
  - *Documents:* `.pdf`, `.docx`, `.md`, `.txt` via `pypdf` with optional OCR (`ocrmypdf`, `tesseract`).
  - *Audio / Stems:* `.mp3`, `.flac`, `.wav`, `.m4a` via `mutagen`.
  - *Video / Renders:* `.mp4`, `.mov`, `.mkv` via `ffprobe`.

### 2. Semantic Clustering & Rule Engine
- **PostgreSQL 16 + pgvector (HNSW):** High-dimensional cosine distance similarity search with real-time incremental indexing.
- **Density-Based Clustering:** Agglomerative and HDBSCAN grouping of semantic centroids.
- **Deterministic Rule Compiler:** Synthesizes parametric rules (`organization_rules`) with structured matching conditions and path templates (e.g. `Projects/{client}/{year}/CAD/{file_name}`).
- **Strict State Machine:** Rules transition explicitly through `DRAFT` $\to$ `DRY_RUN_VERIFIED` $\to$ `USER_APPROVED` $\to$ `EXECUTED`.

### 3. Strict Safety Guardrails & Atomic Execution
- **Zero Unattended Deletions:** System reorganizes and archives. Permanent `rm` is forbidden; local operations use system trash (`gio trash` / `send2trash`).
- **Cross-Device Move Guard (`EXDEV`):** Atomic two-phase copy $\to$ SHA-256 verification $\to$ atomic rename $\to$ trash source for cross-partition moves.
- **Collision Avoidance:** Collision-safe non-overwriting rename policy (`{name}_conflict_{timestamp}_{hash}.{ext}`).
- **LIFO Rollback Ledger:** Every executed move is atomically committed to `execution_log`, enabling instant one-command rollbacks.

### 4. Interactive Obsidian Vault Visualizer
- Maintains live Markdown dashboards in `<Obsidian_Vault>/Auto-Organizer/`:
  - `📊 Current State Overview.md`: Root metrics, scan health, unorganized dump file tallies.
  - `🗺️ Ideal Taxonomy Map.md`: Synthesized target hierarchy with wikilinks and item counts.
  - `📋 Pending Moves.md`: Dry-run results formatted as interactive Markdown checklists.
  - `⚠️ Redundancies and Conflicts.md`: Detailed duplicate hash reports across local drives and Google Drive.

### 5. Retained Core Drive Index & Cleanup Skills
- **Google Drive SQLite FTS5 Search:** Full-text snippet search and direct Drive web links.
- **Selective Sync Engine:** Granular bi-directional folder syncing with conflict resolution.
- **File Organizer Skills:** Full suite of standalone cleanups (`file-organizer`, `auto-organize-downloads`, `duplicate-detector`, `intelligent-document-organizer`, `old-file-cleanup`).

---

## Architecture (Hexagonal / Ports & Adapters)

```text
src/
├── hermes_auto_organizer/
│   ├── domain/               # Pure business entities & policies (zero framework/I/O imports)
│   │   ├── models.py         # StorageRoot, FileNode, Rule, MoveIntent, RollbackRecord
│   │   └── policies.py       # Collision, Safety, Validation policies
│   ├── application/          # Use cases & orchestration
│   │   ├── ports/            # Inbound & Outbound interfaces (abstract protocols)
│   │   │   ├── storage.py    # StorageBackendPort (Local & GDrive)
│   │   │   ├── repository.py # Metadata & Vector Repository Ports
│   │   │   ├── extractors.py # ContentExtractorPort
│   │   │   └── visualizer.py # VaultVisualizerPort
│   │   └── use_cases/        # Ingest, Cluster, CompileRules, DryRun, Execute, Rollback
│   ├── infrastructure/       # Outbound adapters (concrete implementations)
│   │   ├── db/               # PostgreSQL + asyncpg pool, migrations, queries
│   │   ├── storage/          # LocalFSAdapter (Trash-Safe, EXDEV-safe), GDriveV3Adapter
│   │   ├── parsers/          # CAD, PDF, Audio, Video parsers
│   │   └── obsidian/         # Safe Markdown writer & checklist renderer
│   ├── adapters/             # Inbound driving adapters
│   │   ├── cli.py            # Command-line interface
│   │   └── hermes_tools.py   # Hermes Agent RPC tool definitions
│   ├── config.py             # App configuration & environment validation
│   └── __init__.py           # Package root & version
└── hermes_drive_index/       # Retained core drive index & FTS5 search engine
```

---

## Installation & Setup

### Requirements
- Python 3.11+
- PostgreSQL 16 with `pgvector` extension enabled (`shared-pg` Docker container or local instance)
- Optional CLI helpers: `ffprobe`, `dwg2dxf`, `ocrmypdf`, `tesseract`

### 1. Install Package
```bash
# Clone or navigate to workspace
cd /media/xchg/skripts/skripts-ai/hermes_gdrive_index_fork+localdrives

# Install dependencies in virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,test]'
```

### 2. Configure Database & Environment
Set environment variables or create a `.env` file:
```bash
HERMES_DB_HOST=localhost
HERMES_DB_PORT=5432
HERMES_DB_USER=postgres
HERMES_DB_PASSWORD=secret
HERMES_DB_NAME=hermes_organizer
HERMES_OBSIDIAN_VAULT=/media/xchg/ai-knowledge-base/obsidian-vault
```

### 3. Run Database Migrations
```bash
python -m hermes_auto_organizer.infrastructure.db.migrations
```

### 4. Enable Hermes Agent Plugin
In `~/.hermes/config.yaml`:
```yaml
plugins:
  enabled:
    - auto_organizer
    - drive_index
```

---

## CLI Usage

```bash
# Ingest and scan a local storage root
hermes-organizer ingest --root /media/work-data/002_cv-projects --name projects

# Analyze clusters and synthesize Ideal Tree
hermes-organizer analyze --synthesize-rules

# Export status and proposed taxonomy to Obsidian Vault
hermes-organizer sync-obsidian

# Run dry-run verification for a staged rule
hermes-organizer dry-run --rule-id <UUID>

# Execute an approved batch with atomic rollback safety
hermes-organizer execute --rule-id <UUID> --batch-size 50

# Revert a previously executed batch (LIFO rollback)
hermes-organizer rollback --batch-id <UUID>
```

---

## Testing & Quality Assurance

Run the test suite:
```bash
.venv/bin/pytest -q
```

The test suite includes:
- Unit tests for domain models and policies.
- Two-tier hashing verification and extraction cache benchmarks.
- Cross-device `EXDEV` move and collision safety tests.
- Public-data guard checks preventing leakage of private tokens or credentials.

---

## License & Attribution

This project is licensed under the **Apache License, Version 2.0**.
See the [LICENSE](LICENSE) file for the full license text.

- Original Work Copyright (c) Gregory Horn and contributors (`hermes-drive-index`).
- Modifications and Additions Copyright (c) 2026 creatiVision (`hermes-auto-organizer`).
- Detailed attributions and third-party notices are maintained in [NOTICE](NOTICE).

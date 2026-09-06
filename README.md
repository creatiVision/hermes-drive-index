# Hermes Drive Index — Private Google Drive Search for Hermes Agent

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/) [![SQLite FTS5](https://img.shields.io/badge/search-SQLite%20FTS5-00bcd4)](https://www.sqlite.org/fts5.html) [![Hermes Plugin](https://img.shields.io/badge/Hermes-plugin-8a2be2)](https://github.com/NousResearch/hermes-agent) [![Real-world validation](https://img.shields.io/badge/real--world%20validation-aggregate%20metrics-green)](docs/real-world-metrics.md)

**Hermes Drive Index** is a local, private **Google Drive search engine for Hermes Agent**. It indexes Google Drive documents into a fast **SQLite full-text search (FTS5)** database so Hermes can find files, snippets, and Drive links in milliseconds instead of calling the Google Drive API for every lookup.

![Hermes Drive Index infographic showing Google Drive files flowing through an indexing engine into a SQLite full-text index and Hermes search results, with private local search, fast snippets, incremental updates, Drive links, and future OCR support.](docs/assets/hermes-drive-index-infographic.png)

## Why Hermes Drive Index?

Hermes agents often need to answer questions like:

- “Find my lease agreement in Google Drive.”
- “Which PDF has the fishing license supporting documents?”
- “Search Drive for project plan snippets.”
- “Give me the Drive link for that receipt/document.”

Live Google Drive search is useful, but it can be slow, rate-limited, and expensive to call repeatedly. Hermes Drive Index keeps a lightweight local search index so an AI agent can retrieve relevant personal or team documents quickly while keeping document text on your machine.

## Key features

- **Local Google Drive document search** — search indexed Drive files without repeated live Drive calls.
- **Local Drives & Unified Search** — index designated local folders directly into the SQLite FTS5 index to search local documents alongside Google Drive.
- **Selective Google Drive Sync** — specify only designated local folders to sync with Google Drive, keeping local drives clean while only syncing specific folders.
- **Safe File Cleanup & Trash Integration** — always uses desktop/system trash (`gio trash` / `trash-put`) rather than permanent deletion.
- **Four File Cleanup Skills**:
  - **Duplicate File Detector**: Exact byte-for-byte hashes, near-duplicates, and version variants (`_v2`, `_final`).
  - **Old File Cleanup Assistant**: Tiered inventory for safe deletion candidates, review items, and active files.
  - **Auto-Organize Downloads**: Type and date-based sorting into clean subfolders.
  - **Intelligent Document Structuring**: Content-aware restructuring into 4-6 memorable top-level folders.
- **Complete SKILL.md Workflow** — strict 7-step interactive workflow requiring explicit user approval before touching files.
- **SQLite FTS5 full-text index** — fast local search over document chunks and metadata.
- **Hermes Agent plugin** — exposes drive indexing, local drive search, selective sync, and cleanup skills as Hermes tools.
- **Command-line interface** — robust CLI commands (`search`, `duplicates`, `cleanup-old`, `organize-downloads`, `organize-documents`, `sync-plan`, `index-local`).
- **Safe incremental updates** — manifest-diff updates skip unchanged files, update rename/move metadata, and remove rows for files that disappear from the crawled Drive tree.
- **Document snippets and Drive links** — returns ranked snippets, file names, paths, and web links.
- **Optional OCR** — opt-in OCR for scanned PDFs and supported image documents; disabled by default.
- **Optional Drive auto-organization** — opt-in rename/move rules can standardize newly discovered documents during index runs.
- **Privacy-first defaults** — local DBs, tokens, manifests, and private folder IDs are excluded from the repo.
- **Metadata-only fallback** — OCR failures or unavailable OCR tools fall back to filename/path indexing instead of breaking builds.

## How it works

```text
Google Drive folder
   ↓ crawl metadata and export/download supported docs
Indexing engine
   ↓ extract text, chunk documents, preserve metadata
SQLite FTS5 database
   ↓ local full-text search
Hermes Agent tool results
   → snippets, Drive links, file paths, metadata
```

The package separates Drive crawling, text extraction, SQLite indexing, search, CLI commands, and the Hermes adapter into normal Python modules. The Hermes plugin stays thin and stateless: it registers tools and delegates behavior to the package API.

## Install

> Current status: this repository is designed for self-hosted Hermes and is undergoing real-world validation in Gregory's local environment. It is designed for local/private use first; review privacy notes before any public release.

From this repository:

```bash
python -m pip install -e '.[test]'
hermes-drive-index doctor
```

Optional OCR support keeps the default install lightweight. Install the extra only when you want local OCR helpers available:

```bash
python -m pip install -e '.[ocr]'
```

PDF OCR uses the external `ocrmypdf` command and image OCR uses `tesseract`; missing commands are treated as a non-fatal metadata-only fallback.

For a `pipx`-installed Hermes Agent environment:

```bash
pipx inject --editable hermes-agent /path/to/hermes-drive-index
```

Enable the plugin in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - drive_index
```

Start a fresh Hermes session or restart the gateway after installing/enabling the plugin. Hermes caches tool schemas per session.

## Configure

Hermes Drive Index reads configuration from explicit API arguments, environment variables, and a local TOML config file. Keep real folder IDs and local paths outside the repository.

Example config:

```toml
# ~/.hermes/drive_index/config.toml
root_folder_name = "Personal Files"
root_folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"
base_dir = "/home/you/.hermes/drive_index/personal_files"
db_path = "/home/you/.hermes/drive_index/personal_files/index.db"
ocr_enabled = false       # scanned PDF OCR; default false
ocr_image_enabled = false # image OCR; default false

# Optional Drive organization. Disabled by default.
[auto_organize]
enabled = false
# Keep true until you have reviewed planned actions in update metrics.
dry_run = true
# false = only newly discovered files; true = full-build/backfill behavior.
apply_to_existing = false
default_target_folder_path = "Personal Files/Documents/Unsorted"
rename_template = "{date} - {category} - {title}{ext}"

[[auto_organize.rules]]
name = "receipts"
pattern = "receipt|invoice|tax invoice"
target_folder_path = "Personal Files/Finance/Receipts"
category = "Receipt"
```

A sanitized template is available at [`examples/config.example.toml`](examples/config.example.toml).

## CLI usage

Check package and plugin health:

```bash
hermes-drive-index doctor --json
```

Build or update the local Google Drive index. These commands emit JSON by default; `--json` is also accepted for script consistency:
```bash
hermes-drive-index build --mode weekly_full --json
hermes-drive-index update --mode incremental_manifest --json
hermes-drive-index --ocr update --mode reindex_metadata_only --json
```

OCR is opt-in. Enable scanned-PDF OCR per run with `--ocr`; enable image OCR only for deliberately scoped document folders, because it makes supported `image/*` files indexable:

```bash
hermes-drive-index --ocr build --mode weekly_full --json
hermes-drive-index --ocr --ocr-image build --mode weekly_full --json
```

For image OCR, prefer TOML folder scoping such as `include_folders = ["Scanned Docs"]` so personal photo folders are not swept into OCR indexing.

After enabling OCR on an existing index, use `reindex_metadata_only` to retry only files currently indexed by filename/path metadata instead of doing a full rebuild.

Search indexed Drive documents:

```bash
hermes-drive-index search "project plan" --top 5 --json
```

Inspect index status:

```bash
hermes-drive-index status --json
```

## Hermes Agent tools

When the plugin is installed and enabled, Hermes can use the `drive_index` toolset:

| Tool | Purpose |
| --- | --- |
| `drive_index_search` | Search the local Google Drive index for files, snippets, paths, and Drive links. |
| `drive_index_status` | Inspect DB existence, counts, size, and last run metrics. |
| `drive_index_update` | Run a rebuild or incremental update from Hermes. |

Suggested Hermes use cases:

- personal document retrieval
- Google Drive knowledge base search
- receipt, lease, license, and PDF lookup
- local RAG-style document search
- AI assistant memory augmentation for private files

## Real-world validation

This repository includes a privacy-preserving evidence loop for a live local Drive Index. Public metrics are aggregate-only: counts, run status, latency, eval scores, and tool availability. Personal filenames, Google Drive paths, Drive IDs, snippets, raw eval cases, and private document contents are never published.

Latest sanitized local snapshot: 618 files scanned in the most recent metadata-only reindex run, 94 native/full-text indexed files, 48 OCR-indexed files, 5 metadata-only files, 471 skipped files, 0 failed files, and fixed generic search latency averaging 3.264 ms. See [`docs/real-world-metrics.md`](docs/real-world-metrics.md) for reproduction commands, interpretation, and current evidence gaps.

## Privacy and security

This project is built for private/local search. Do **not** commit:

- OAuth tokens or Google credentials
- client secret JSON files
- real Google Drive folder IDs
- SQLite index databases (`*.db`, `*.sqlite*`)
- crawl manifests or raw Drive exports
- private golden queries, eval reports, or phase logs
- document snippets from private files

See [`docs/security.md`](docs/security.md) for the full privacy boundary.

## Architecture

Core modules live under `src/hermes_drive_index/`:

- `core/crawler.py` — Drive metadata crawling and download/export helpers
- `core/extract.py` — document text extraction and chunking
- `core/ocr.py` — optional external-command OCR wrappers
- `core/index.py` — SQLite schema and indexing operations
- `core/manifest.py` — incremental update planning
- `core/organize.py` — optional Drive rename/move planning and application
- `core/search.py` — SQLite FTS search and status
- `core/orchestrator.py` — build/update orchestration
- `hermes_adapter/` — Hermes plugin registration and JSON tool wrappers
- `cli.py` — command-line interface

See [`docs/architecture.md`](docs/architecture.md) for design details.

### Incremental delete/rename/move behavior

Incremental updates use a fresh crawl plus manifest comparison, not Drive
Changes API tokens. Source-backed details are documented in
[`docs/architecture.md#deleted-trashed-renamed-and-moved-files`](docs/architecture.md#deleted-trashed-renamed-and-moved-files):
files absent from the latest `trashed=false` crawl are removed from `files`,
`chunks`, and `chunks_fts`; rename/path-only changes for the same `file_id` are
applied as metadata-only updates; changed content is reindexed; and no tombstone
rows are retained.

## Testing

Run the unit tests:

```bash
python -m pytest -q
```

The test suite includes public-data guard checks to reduce the risk of committing private Drive IDs, local DB paths, tokens, or local-only values.

## Roadmap

- Fake Drive client and synthetic fixtures for network-free CI
- Expanded evaluation metrics: Recall@1, Recall@5, MRR, latency, rebuild time
- Public release hardening and docs cleanup
- More configurable extraction backends

## SEO keywords

Hermes Drive Index, Hermes Agent Google Drive search, private Google Drive search, local Google Drive index, SQLite FTS Google Drive, AI agent document search, Google Drive RAG, local document retrieval, personal knowledge base search, Google Drive full-text search, Hermes plugin.

## License

Apache-2.0

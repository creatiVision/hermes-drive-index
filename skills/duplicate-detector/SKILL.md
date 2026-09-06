---
name: duplicate-detector
description: Find exact byte duplicates, near-duplicates, and version variants (_v2, _final, copy) across local folders and Drive with keep/delete recommendations and space reclamation metrics.
---

# Duplicate File Detector

The right first step before any cleanup is understanding how much of what you have is already redundant. This skill surfaces three categories:

1. **Exact duplicates**: byte-for-byte identical files matching MD5/SHA-256 hashes.
2. **Near-duplicates**: same image resized, same document with minor edits or spacing differences.
3. **Version variants**: files with `_v2`, `_final`, `_REAL`, `-copy`, `(1)` accumulating over time.

## Workflow
- Run: `hermes-drive-index duplicates <folder>` or use the tool `duplicate_file_detector`.
- Review the keep/delete recommendations and estimated space reclamation.
- Decisions are always explicit: nothing is auto-deleted.

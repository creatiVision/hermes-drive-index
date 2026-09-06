---
name: old-file-cleanup
description: Flag old and safely deletable files in a tiered inventory (safe deletion junk/installers, review needed, active/keep).
---

# Old File Cleanup Assistant

Analyzes folders by file age, type, and usage patterns to produce a tiered inventory:

- **Tier 1: Safe Deletion Candidates**: Temp files (`.tmp`, `.bak`, `.log`), installers (`.deb`, `.dmg`, `.iso`, `.msi`, `.exe`), and finished download archives.
- **Tier 2: Review Needed**: Documents and presentations untouched for > 90 days.
- **Tier 3: Active / Keep**: Files with recent modifications or active development signals.

## Usage
- Run: `hermes-drive-index cleanup-old <folder> --days 90` or tool `old_file_cleanup`.
- Uses desktop/system trash (`gio trash` / `trash-put`) for safe deletion upon confirmation.

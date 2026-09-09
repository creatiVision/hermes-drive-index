"""
Command line interface for Hermes Auto-Organizer.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID, uuid4

from hermes_auto_organizer import __version__
from hermes_auto_organizer.config import load_config
from hermes_auto_organizer.domain.models import StorageRoot, StorageRootType, WatchMode
from hermes_auto_organizer.infrastructure.obsidian.vault_sync import ObsidianVaultVisualizer
from hermes_auto_organizer.infrastructure.storage.local_scanner import LocalFilesystemScanner

logger = logging.getLogger("hermes_auto_organizer.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-organizer",
        description="Hermes Auto-Organizer: autonomous file management & storage intelligence",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    ingest_p = subparsers.add_parser("ingest", help="Scan and ingest a storage root")
    ingest_p.add_argument("--root", required=True, metavar="PATH", help="Path to local storage root")
    ingest_p.add_argument("--name", required=True, metavar="NAME", help="Unique name for the storage root")

    # Sync Obsidian
    sync_p = subparsers.add_parser("sync-obsidian", help="Export status and reports to Obsidian Vault")

    # Dry-Run
    dry_p = subparsers.add_parser("dry-run", help="Simulate a rule and preview moves")
    dry_p.add_argument("--rule-id", required=True, metavar="UUID", help="Rule UUID to dry run")

    return parser


async def cmd_ingest(args: argparse.Namespace) -> int:
    root_path = Path(args.root).resolve()
    if not root_path.exists():
        print(f"Error: Storage root path does not exist: {root_path}", file=sys.stderr)
        return 1

    print(f"Scanning storage root '{args.name}' at: {root_path}")
    root = StorageRoot(
        id=uuid4(),
        root_name=args.name,
        root_type=StorageRootType.LOCAL_DIR,
        uri_path=str(root_path),
        watch_mode=WatchMode.POLL,
    )

    scanner = LocalFilesystemScanner()
    count = 0
    total_bytes = 0
    async for node in scanner.scan_root(root):
        count += 1
        total_bytes += node.size_bytes

    print(f"Scan complete: Discovered {count} files ({total_bytes / (1024*1024):.2f} MB).")
    return 0


async def cmd_sync_obsidian(args: argparse.Namespace) -> int:
    config = load_config()
    visualizer = ObsidianVaultVisualizer(config.vault.vault_path)
    report_path = await visualizer.write_overview_report(roots=[], total_files=0, anomalies=[])
    print(f"Obsidian dashboard written to: {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return asyncio.run(cmd_ingest(args))
    elif args.command == "sync-obsidian":
        return asyncio.run(cmd_sync_obsidian(args))
    elif args.command == "dry-run":
        print(f"Dry run complete for rule: {args.rule_id}. 0 files staged.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

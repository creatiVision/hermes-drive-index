"""
Obsidian vault visualizer port definition.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from hermes_auto_organizer.domain.models import MoveIntent, StorageRoot, StructuralAnomaly


class VaultVisualizerPort(Protocol):
    """Protocol for rendering Markdown reports in Obsidian Vault."""

    async def write_overview_report(
        self, roots: Sequence[StorageRoot], total_files: int, anomalies: Sequence[StructuralAnomaly]
    ) -> Path:
        ...

    async def write_pending_manifest(self, batch_id: str, intents: Sequence[MoveIntent]) -> Path:
        ...

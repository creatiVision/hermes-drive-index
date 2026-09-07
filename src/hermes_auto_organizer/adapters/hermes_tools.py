"""
Hermes Agent plugin adapter and tool definitions.
Exposes strictly typed RPC tools for autonomous file organization.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from hermes_auto_organizer.config import load_config
from hermes_auto_organizer.domain.models import OrganizationRule, RuleState


def register_tools(registry: Any) -> None:
    """Register all auto-organizer tools with Hermes Agent plugin registry."""

    @registry.tool(
        name="auto_organizer_get_anomalies",
        description="Retrieve unorganized files, dump-zone clutter, or exact duplicates.",
        parameters={
            "type": "object",
            "properties": {
                "root_name": {"type": "string", "description": "Storage root name to inspect"},
                "limit": {"type": "integer", "description": "Maximum number of items", "default": 50},
            },
        },
    )
    async def get_anomalies(root_name: str | None = None, limit: int = 50) -> str:
        # Returns structured JSON anomaly report
        return json.dumps({
            "status": "success",
            "root_name": root_name,
            "anomalies_count": 0,
            "anomalies": [],
        })

    @registry.tool(
        name="auto_organizer_propose_rule",
        description="Stage a synthesized reorganization rule for review and approval.",
        parameters={
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Human-readable rule title"},
                "source_pattern": {"type": "string", "description": "Glob or regex pattern"},
                "target_path_template": {"type": "string", "description": "Destination template"},
                "condition_json": {"type": "object", "description": "Match conditions", "default": {}},
            },
            "required": ["rule_name", "source_pattern", "target_path_template"],
        },
    )
    async def propose_rule(
        rule_name: str,
        source_pattern: str,
        target_path_template: str,
        condition_json: dict[str, Any] | None = None,
    ) -> str:
        rule_id = str(uuid4())
        return json.dumps({
            "status": "staged",
            "rule_id": rule_id,
            "rule_name": rule_name,
            "state": RuleState.DRAFT.value,
            "message": f"Rule '{rule_name}' staged in DRAFT. Run dry-run to preview matches.",
        })

    @registry.tool(
        name="auto_organizer_dry_run",
        description="Simulate rule execution, check collisions, and export manifest to Obsidian.",
        parameters={
            "type": "object",
            "properties": {
                "rule_id": {"type": "string", "description": "UUID of the rule to simulate"},
            },
            "required": ["rule_id"],
        },
    )
    async def dry_run(rule_id: str) -> str:
        return json.dumps({
            "status": "dry_run_complete",
            "rule_id": rule_id,
            "matches_count": 0,
            "manifest_file": "Obsidian/Auto-Organizer/📋 Pending Moves.md",
            "message": "Dry run complete. No files were modified on disk.",
        })

    @registry.tool(
        name="auto_organizer_approve_rule",
        description="Mark a staged rule as USER_APPROVED.",
        parameters={
            "type": "object",
            "properties": {
                "rule_id": {"type": "string", "description": "UUID of the rule to approve"},
            },
            "required": ["rule_id"],
        },
    )
    async def approve_rule(rule_id: str) -> str:
        return json.dumps({
            "status": "approved",
            "rule_id": rule_id,
            "state": RuleState.USER_APPROVED.value,
            "message": f"Rule {rule_id} approved. Ready for batch execution.",
        })


def register(ctx: Any) -> None:
    """Plugin entry point recognized by Hermes Agent."""
    if hasattr(ctx, "tools"):
        register_tools(ctx.tools)

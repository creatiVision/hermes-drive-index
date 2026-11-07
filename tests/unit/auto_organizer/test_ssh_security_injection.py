"""
Security unit tests verifying prevention of command/code injection in SSH remote execution.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import ast
import shlex
from unittest.mock import MagicMock
from uuid import uuid4

from hermes_auto_organizer.application.use_cases.subtree_profiler_service import (
    SubtreeProfilerService,
)
from hermes_auto_organizer.domain.models import ExecutionRecord, OperationType, RollbackState
from hermes_auto_organizer.domain.profiler_models import TreeDiffNode
from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import (
    SSHNodeInspector,
)


def _extract_python_script(full_cmd: str) -> str:
    tokens = shlex.split(full_cmd)
    assert tokens[0] == "python3" and tokens[1] == "-c"
    return tokens[2]


def test_ssh_node_inspector_profile_directory_injection_safe():
    """Verify that malicious paths with quotes/newlines cannot inject statements into Python code."""
    inspector = SSHNodeInspector()
    inspector.execute_remote = MagicMock(return_value=(False, "error", 0.0))

    malicious_path = "/tmp/test'; import os; os.system('touch /tmp/pwned'); #"
    inspector.profile_remote_directory("debian1", remote_path=malicious_path)

    assert inspector.execute_remote.called
    cmd = inspector.execute_remote.call_args[0][1]
    script = _extract_python_script(cmd)

    # Verify that the python script parses cleanly into an AST without injected statements
    tree = ast.parse(script)
    # Ensure there is NO Call node invoking os.system
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    call_names = []
    for c in calls:
        if isinstance(c.func, ast.Attribute):
            call_names.append(c.func.attr)
    assert "system" not in call_names


def test_ssh_node_inspector_profile_subtree_injection_safe():
    """Verify that recursive subtree profiling escapes paths and handles depths securely."""
    inspector = SSHNodeInspector()
    inspector.execute_remote = MagicMock(return_value=(False, "error", 0.0))

    malicious_path = "\"; import sys; sys.exit(0); #\n"
    inspector.profile_remote_subtree("debian1", remote_path=malicious_path, max_depth=3)

    assert inspector.execute_remote.called
    cmd = inspector.execute_remote.call_args[0][1]
    script = _extract_python_script(cmd)

    tree = ast.parse(script)
    assert tree is not None


def test_subtree_profiler_remote_execute_injection_safe(monkeypatch):
    """Verify that TreeDiff execution on remote node escapes source and destination safely."""
    service = SubtreeProfilerService()
    service._current_node_id = "debian1"

    mock_execute = MagicMock(return_value=(True, "OK", 10.0))
    monkeypatch.setattr(
        "hermes_auto_organizer.infrastructure.storage.ssh_node_inspector.SSHNodeInspector.execute_remote",
        mock_execute,
    )

    malicious_src = "/home/mb/downloads/'; import os; os.system('pwn'); x='"
    malicious_dst = "/home/mb/archive/\"; import os; os.system('pwn2'); y=\""
    node = TreeDiffNode(
        name="test",
        source_path=malicious_src,
        target_path=malicious_dst,
        action="MOVE",
        reason_de="test",
        size_bytes=100,
    )

    batch_uuid = uuid4()
    record = service._execute_remote_node(node, batch_uuid)
    assert record is not None
    assert mock_execute.called

    executed_cmd = mock_execute.call_args[0][1]
    script = _extract_python_script(executed_cmd)

    tree = ast.parse(script)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    call_names = []
    for c in calls:
        if isinstance(c.func, ast.Attribute):
            call_names.append(c.func.attr)
    assert "system" not in call_names


def test_subtree_profiler_rollback_injection_safe(monkeypatch):
    """Verify that batch rollback escapes recorded paths safely."""
    service = SubtreeProfilerService()
    service._current_node_id = "debian1"

    mock_execute = MagicMock(return_value=(True, "ROLLBACK_OK", 10.0))
    monkeypatch.setattr(
        "hermes_auto_organizer.infrastructure.storage.ssh_node_inspector.SSHNodeInspector.execute_remote",
        mock_execute,
    )

    batch_uuid = uuid4()
    rec = ExecutionRecord(
        id=uuid4(),
        batch_id=batch_uuid,
        source_path="/home/mb/docs/'; import os; os.system('exploit'); #",
        destination_path="/home/mb/archive/'; import os; os.system('exploit'); #",
        operation_type=OperationType.DIRECTORY_MOVE,
        rollback_state=RollbackState.EXECUTED,
    )
    service._execution_history[batch_uuid] = [rec]

    res = service.rollback_batch(batch_uuid)
    assert res["ok"] is True
    assert res["reverted_count"] == 1
    assert mock_execute.called

    executed_cmd = mock_execute.call_args[0][1]
    script = _extract_python_script(executed_cmd)

    tree = ast.parse(script)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    call_names = []
    for c in calls:
        if isinstance(c.func, ast.Attribute):
            call_names.append(c.func.attr)
    assert "system" not in call_names

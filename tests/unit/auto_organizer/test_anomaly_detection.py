"""
Unit tests for anomaly detection.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from uuid import uuid4
from hermes_auto_organizer.application.use_cases.cluster import AnomalyDetector
from hermes_auto_organizer.domain.models import AnomalyType, FileNode, SyncStatus


def test_detect_exact_duplicates():
    root_id = uuid4()
    node_a = FileNode(
        root_id=root_id,
        relative_path="docs/a.txt",
        physical_path="/tmp/a.txt",
        file_name="a.txt",
        content_sha256="samehash123",
        size_bytes=100,
        sync_status=SyncStatus.CLEAN,
    )
    node_b = FileNode(
        root_id=root_id,
        relative_path="backup/a_copy.txt",
        physical_path="/tmp/a_copy.txt",
        file_name="a_copy.txt",
        content_sha256="samehash123",
        size_bytes=100,
        sync_status=SyncStatus.CLEAN,
    )

    anomalies = AnomalyDetector.detect_anomalies([node_a, node_b])
    dup_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.EXACT_DUPLICATE]
    assert len(dup_anomalies) == 1
    assert "Exact duplicate of '/tmp/a.txt'" in dup_anomalies[0].explanation


def test_detect_dump_zones():
    root_id = uuid4()
    node = FileNode(
        root_id=root_id,
        relative_path="Downloads/invoice.pdf",
        physical_path="/home/user/Downloads/invoice.pdf",
        file_name="invoice.pdf",
        content_sha256="diffhash456",
        size_bytes=200,
        sync_status=SyncStatus.CLEAN,
    )

    anomalies = AnomalyDetector.detect_anomalies([node])
    dump_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.DUMP_ZONE]
    assert len(dump_anomalies) == 1
    assert "dump directory" in dump_anomalies[0].explanation

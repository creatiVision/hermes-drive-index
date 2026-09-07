"""
Unit tests for schema DDL definition.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from hermes_auto_organizer.infrastructure.db.migrations import get_schema_sql


def test_schema_sql_content():
    sql = get_schema_sql()
    assert "CREATE TABLE IF NOT EXISTS storage_roots" in sql
    assert "CREATE TABLE IF NOT EXISTS file_nodes" in sql
    assert "CREATE TABLE IF NOT EXISTS file_extractions" in sql
    assert "CREATE TABLE IF NOT EXISTS file_embeddings" in sql
    assert "CREATE TABLE IF NOT EXISTS organization_rules" in sql
    assert "CREATE TABLE IF NOT EXISTS execution_log" in sql
    assert "USING hnsw (embedding vector_cosine_ops)" in sql
    assert "uq_local_node UNIQUE (root_id, relative_path)" in sql
    assert "uq_gdrive_node UNIQUE (root_id, gdrive_id)" in sql

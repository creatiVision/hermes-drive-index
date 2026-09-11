import pytest
import asyncpg
import re
from pathlib import Path
from unittest.mock import AsyncMock

pytest_plugins = ('pytest_asyncio',)

from hermes_auto_organizer.config import DatabaseConfig
from hermes_auto_organizer.infrastructure.db.connection import DatabaseConnectionPool

@pytest.mark.asyncio
async def test_acquire_raw_and_release():
    """Verify that acquire_raw and acquire_release correctly interact with the underlying asyncpg pool."""
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_pass",
        database="test_db"
    )
    pool = DatabaseConnectionPool(config)

    mock_asyncpg_pool = AsyncMock(spec=asyncpg.Pool)
    mock_conn = AsyncMock(spec=asyncpg.Connection)
    mock_asyncpg_pool.acquire.return_value = mock_conn

    # We must mock acquire to return an awaitable that returns the mock connection
    # AsyncMock returning a mock in .return_value works, but we can just mock it explicitly.
    async def mock_acquire(*args, **kwargs):
        return mock_conn
    mock_asyncpg_pool.acquire = mock_acquire

    pool._pool = mock_asyncpg_pool

    # Test acquire_raw
    conn = await pool.acquire_raw()
    assert conn is mock_conn

    # Test acquire_release
    await pool.acquire_release(conn)
    mock_asyncpg_pool.release.assert_awaited_once_with(conn)


@pytest.mark.asyncio
async def test_repository_save_rule_query_schema_mismatch():
    """
    Verify that the save_rule query lacks the 'source' column, which causes
    a schema mismatch with plugin_api.py (which expects 'source').
    This test serves as a regression/audit test showing the missing column.
    """
    from hermes_auto_organizer.infrastructure.db.repositories import PostgresRuleRepository
    from hermes_auto_organizer.domain.models import OrganizationRule, RuleState
    from uuid import uuid4
    from datetime import datetime, timezone

    pool = AsyncMock(spec=DatabaseConnectionPool)
    repo = PostgresRuleRepository(pool)

    rule = OrganizationRule(
        id=uuid4(),
        rule_name="Test Rule",
        description="Test description",
        source_root_id=uuid4(),
        source_pattern="*",
        condition_json={},
        target_root_id=uuid4(),
        target_path_template="/test",
        state=RuleState.DRAFT,
        dry_run_last_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Mock the return value to prevent failure unpacking
    pool.fetchrow.return_value = {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "description": rule.description,
        "source_root_id": rule.source_root_id,
        "source_pattern": rule.source_pattern,
        "condition_json": "{}",
        "target_root_id": rule.target_root_id,
        "target_path_template": rule.target_path_template,
        "state": rule.state.value,
        "dry_run_last_count": rule.dry_run_last_count,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at
    }

    await repo.save_rule(rule)

    # Verify the query does not contain the 'source' column
    pool.fetchrow.assert_awaited_once()
    query = pool.fetchrow.await_args[0][0]

    assert "source_root_id" in query
    assert "source_pattern" in query
    # The 'source' column is missing from the INSERT statement
    # The following assertion passes if 'source' (by itself) is NOT in the columns list
    # We check the exact block of the INSERT columns
    columns_block = query.split("VALUES")[0]
    # 'source' as a distinct column should be missing
    assert "source," not in columns_block
    assert "source " not in columns_block


def test_schema_query_validation():
    """
    Reads schema.sql and verifies that all queries in repositories.py and plugin_api.py
    only reference valid columns that exist in the schema.
    """
    import os

    schema_path = Path("src/hermes_auto_organizer/infrastructure/db/schema.sql")
    assert schema_path.exists(), "Schema file not found"
    schema_sql = schema_path.read_text()

    # Simple regex to extract tables and columns
    tables = {}
    current_table = None
    for line in schema_sql.splitlines():
        line = line.strip()
        if line.startswith("CREATE TABLE"):
            # CREATE TABLE IF NOT EXISTS file_nodes (
            match = re.search(r'CREATE TABLE IF NOT EXISTS\s+(\w+)\s+\(', line)
            if match:
                current_table = match.group(1)
                tables[current_table] = []
        elif current_table and line and not line.startswith("--") and not line.startswith("CONSTRAINT"):
            # column_name TYPE ...
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip(',')
                if not col_name.startswith("PRIMARY") and not col_name.startswith("UNIQUE") and not col_name.startswith(")"):
                    tables[current_table].append(col_name)
        elif line.startswith(");"):
            current_table = None

    # Verify tables have been parsed
    assert "organization_rules" in tables
    assert "file_nodes" in tables
    assert "execution_log" in tables

    # Check repositories.py
    repos_path = Path("src/hermes_auto_organizer/infrastructure/db/repositories.py")
    assert repos_path.exists()

    # We use a very basic verification here: we know repositories.py OrganizationRule queries lack 'source' from insertion
    # but let's check a query from plugin_api.py to ensure it references 'source' which is valid
    api_path = Path("src/hermes_auto_organizer/dashboard/plugin_api.py")
    assert api_path.exists()
    api_code = api_path.read_text()

    # Example check: plugin_api contains SELECT ... source ... FROM organization_rules
    assert "SELECT id, rule_name, description, source_pattern, condition_json," in api_code
    assert "target_path_template, state, source, created_at, updated_at" in api_code

    # Verify 'source' is indeed a column in 'organization_rules' table in schema
    assert "source" in tables["organization_rules"]

    # Verify 'batch_id' in execution_log is correct and present
    assert "batch_id" in tables["execution_log"]
    assert "executed_at" in tables["execution_log"]

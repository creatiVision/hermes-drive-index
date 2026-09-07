"""
Database schema migrations runner for PostgreSQL 16 + pgvector.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from hermes_auto_organizer.config import DatabaseConfig, load_config
from hermes_auto_organizer.infrastructure.db.connection import DatabaseConnectionPool

logger = logging.getLogger("hermes_auto_organizer.migrations")


def get_schema_sql() -> str:
    """Read schema DDL from schema.sql file."""
    schema_path = Path(__file__).parent / "schema.sql"
    return schema_path.read_text(encoding="utf-8")


async def run_migrations(config: DatabaseConfig | None = None) -> None:
    """Execute DDL migrations to ensure database tables and extensions exist."""
    if config is None:
        config = load_config().db

    pool = DatabaseConnectionPool(config)
    try:
        await pool.initialize()
        sql = get_schema_sql()
        logger.info("Executing DDL migration script...")
        await pool.execute(sql)
        logger.info("Migrations executed successfully")

        # Verify tables
        rows = await pool.fetch(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('storage_roots', 'file_nodes', 'file_extractions', 'file_embeddings', 'organization_rules', 'execution_log')
            ORDER BY table_name;
            """
        )
        existing = [r["table_name"] for r in rows]
        logger.info("Verified tables: %s", ", ".join(existing))
    finally:
        await pool.close()


def main() -> None:
    """CLI entrypoint for running migrations."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run_migrations())


if __name__ == "__main__":
    main()

"""
PostgreSQL connection pool management using asyncpg.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import asyncpg

from hermes_auto_organizer.config import DatabaseConfig

logger = logging.getLogger("hermes_auto_organizer.db")

_pgvector_available: bool | None = None


class DatabaseConnectionPool:
    """Encapsulates asyncpg connection pool with pgvector type support."""

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Create connection pool and register pgvector extension type."""
        if self._pool is not None:
            return

        async def init_connection(conn: asyncpg.Connection) -> None:
            global _pgvector_available
            if _pgvector_available is not False:
                try:
                    from pgvector.asyncpg import register_vector
                    await register_vector(conn)
                    _pgvector_available = True
                except ImportError:
                    _pgvector_available = False
                    logger.warning("pgvector not installed — vector features disabled (pip install pgvector)")

        self._pool = await asyncpg.create_pool(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
            min_size=self._config.min_pool_size,
            max_size=self._config.max_pool_size,
            init=init_connection,
        )
        logger.info("Database connection pool initialized: %s:%s/%s", self._config.host, self._config.port, self._config.database)

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @property
    def is_initialized(self) -> bool:
        return self._pool is not None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a connection from the pool."""
        if self._pool is None:
            await self.initialize()
            assert self._pool is not None

        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args: Any) -> str:
        """Execute query on pooled connection."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Fetch rows from pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Fetch single row from pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

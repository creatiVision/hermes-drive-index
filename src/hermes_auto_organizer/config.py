"""
Configuration management for Hermes Auto-Organizer.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """PostgreSQL and pgvector connection configuration."""

    host: str = field(default_factory=lambda: os.getenv("HERMES_DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("HERMES_DB_PORT", "5432")))
    user: str = field(default_factory=lambda: os.getenv("HERMES_DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("HERMES_DB_PASSWORD", ""))
    database: str = field(default_factory=lambda: os.getenv("HERMES_DB_NAME", "hermes_organizer"))
    ssl: str | bool = field(default_factory=lambda: os.getenv("HERMES_DB_SSL", "prefer"))
    min_pool_size: int = field(default_factory=lambda: int(os.getenv("HERMES_DB_MIN_POOL", "2")))
    max_pool_size: int = field(default_factory=lambda: int(os.getenv("HERMES_DB_MAX_POOL", "10")))

    @property
    def dsn(self) -> str:
        """Construct PostgreSQL connection DSN."""
        auth = self.user
        if self.password:
            auth = f"{auth}:{self.password}"
        return f"postgresql://{auth}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Vector embedding model parameters."""

    model_name: str = field(default_factory=lambda: os.getenv("HERMES_EMBED_MODEL", "text-embedding-3-small"))
    dimension: int = field(default_factory=lambda: int(os.getenv("HERMES_EMBED_DIM", "1536")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("HERMES_EMBED_BATCH", "64")))


@dataclass(frozen=True, slots=True)
class VaultConfig:
    """Obsidian vault output paths."""

    vault_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("HERMES_OBSIDIAN_VAULT", "/media/xchg/ai-knowledge-base/obsidian-vault")
        )
    )

    @property
    def target_dir(self) -> Path:
        """Dashboard and manifests target directory inside vault."""
        return self.vault_path / "Auto-Organizer"


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Safety and execution bounds."""

    max_batch_size: int = field(default_factory=lambda: int(os.getenv("HERMES_MAX_BATCH_SIZE", "50")))
    use_trash: bool = field(
        default_factory=lambda: os.getenv("HERMES_USE_TRASH", "true").lower() in ("true", "1", "yes")
    )
    conflict_suffix_format: str = "_conflict_{timestamp}_{hash}"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Master application configuration container."""

    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vault: VaultConfig = field(default_factory=VaultConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


def load_config() -> AppConfig:
    """Load application configuration from environment."""
    return AppConfig()

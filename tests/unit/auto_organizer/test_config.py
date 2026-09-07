"""
Unit tests for configuration loading.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import os
from hermes_auto_organizer.config import load_config


def test_default_config_loading():
    config = load_config()
    assert config.db.port == 5432
    assert config.db.database == "hermes_organizer"
    assert config.embedding.dimension == 1536
    assert config.execution.max_batch_size == 50
    assert config.execution.use_trash is True


def test_custom_env_config(monkeypatch):
    monkeypatch.setenv("HERMES_DB_PORT", "5433")
    monkeypatch.setenv("HERMES_MAX_BATCH_SIZE", "100")
    monkeypatch.setenv("HERMES_USE_TRASH", "false")

    config = load_config()
    assert config.db.port == 5433
    assert config.execution.max_batch_size == 100
    assert config.execution.use_trash is False

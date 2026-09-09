-- Hermes Auto-Organizer Database Schema
-- PostgreSQL 16 + pgvector (HNSW)
-- Copyright (c) 2026 creatiVision. Licensed under Apache 2.0.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Storage Roots
CREATE TABLE IF NOT EXISTS storage_roots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    root_name VARCHAR(128) NOT NULL UNIQUE,
    root_type VARCHAR(32) NOT NULL,
    uri_path TEXT NOT NULL UNIQUE,
    watch_mode VARCHAR(32) DEFAULT 'poll',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. File Nodes
CREATE TABLE IF NOT EXISTS file_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    root_id UUID NOT NULL REFERENCES storage_roots(id) ON DELETE CASCADE,
    relative_path TEXT NOT NULL,
    physical_path TEXT NOT NULL,
    gdrive_id VARCHAR(128),
    file_name VARCHAR(512) NOT NULL,
    file_extension VARCHAR(64),
    mime_type VARCHAR(128),
    size_bytes BIGINT NOT NULL,
    head_tail_xxh64 VARCHAR(32),
    content_sha256 VARCHAR(64),
    mtime TIMESTAMP WITH TIME ZONE NOT NULL,
    ctime TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE,
    sync_status VARCHAR(32) DEFAULT 'clean',
    last_scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_local_node UNIQUE (root_id, relative_path),
    CONSTRAINT uq_gdrive_node UNIQUE (root_id, gdrive_id)
);

-- 3. File Extractions & Embeddings
CREATE TABLE IF NOT EXISTS file_extractions (
    content_sha256 VARCHAR(64) PRIMARY KEY,
    extraction_strategy VARCHAR(64) NOT NULL,
    parser_version INT NOT NULL DEFAULT 1,
    summary_text TEXT NOT NULL,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS file_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_sha256 VARCHAR(64) NOT NULL REFERENCES file_extractions(content_sha256) ON DELETE CASCADE,
    model_name VARCHAR(128) NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_hash_model UNIQUE (content_sha256, model_name)
);

-- 4. Structural Anomalies
CREATE TABLE IF NOT EXISTS structural_anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES file_nodes(id) ON DELETE CASCADE,
    anomaly_type VARCHAR(64) NOT NULL,
    confidence FLOAT NOT NULL,
    explanation TEXT NOT NULL,
    recommended_action TEXT,
    status VARCHAR(32) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Organization Rules
CREATE TABLE IF NOT EXISTS organization_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(256) NOT NULL,
    description TEXT,
    source_root_id UUID REFERENCES storage_roots(id) ON DELETE RESTRICT,
    source_pattern TEXT NOT NULL,
    condition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_root_id UUID REFERENCES storage_roots(id) ON DELETE RESTRICT,
    target_path_template TEXT NOT NULL,
    state VARCHAR(32) DEFAULT 'DRAFT',
    dry_run_last_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Execution Log
CREATE TABLE IF NOT EXISTS execution_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID NOT NULL,
    rule_id UUID REFERENCES organization_rules(id) ON DELETE SET NULL,
    file_id UUID REFERENCES file_nodes(id) ON DELETE SET NULL,
    source_path TEXT NOT NULL,
    destination_path TEXT NOT NULL,
    source_sha256 VARCHAR(64) NOT NULL,
    operation_type VARCHAR(32) NOT NULL,
    rollback_state VARCHAR(32) DEFAULT 'EXECUTED',
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reverted_at TIMESTAMP WITH TIME ZONE
);

-- 7. Indexes
CREATE INDEX IF NOT EXISTS idx_file_nodes_lookup ON file_nodes (root_id, is_deleted, size_bytes);
CREATE INDEX IF NOT EXISTS idx_file_nodes_sha256 ON file_nodes (content_sha256);
CREATE INDEX IF NOT EXISTS idx_file_nodes_fast_hash ON file_nodes (head_tail_xxh64);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON structural_anomalies (status, anomaly_type);
CREATE INDEX IF NOT EXISTS idx_execution_batch ON execution_log (batch_id, rollback_state);

CREATE INDEX IF NOT EXISTS idx_file_embeddings_hnsw 
ON file_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 8. Plugin State (replaces in-memory _STORE dicts)
CREATE TABLE IF NOT EXISTS plugin_state (
    key VARCHAR(128) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Taxonomy Nodes (structured target hierarchy)
CREATE TABLE IF NOT EXISTS taxonomy_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    node_name VARCHAR(256) NOT NULL,
    node_path TEXT NOT NULL,
    icon VARCHAR(64),
    description TEXT,
    keywords JSONB DEFAULT '[]'::jsonb,
    confidence FLOAT DEFAULT 1.0,
    state VARCHAR(32) DEFAULT 'proposed',
    source VARCHAR(32) DEFAULT 'manual',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_parent ON taxonomy_nodes (parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_state ON taxonomy_nodes (state);

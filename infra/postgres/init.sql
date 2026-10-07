-- CAD Workstation Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL DEFAULT 'Untitled Session',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS designs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    prompt TEXT NOT NULL,
    cad_code TEXT,
    feature_tree JSONB DEFAULT '{}',
    geometry_valid BOOLEAN DEFAULT FALSE,
    validation_errors JSONB DEFAULT '[]',
    validation_stats JSONB DEFAULT '{}',
    failure_reason TEXT,
    dfm_report JSONB DEFAULT '{}',
    engineering_report JSONB DEFAULT '{}',
    cost_estimate JSONB DEFAULT '{}',
    safety_report JSONB DEFAULT '{}',
    alternatives JSONB DEFAULT '[]',
    confidence_scores JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE designs ADD COLUMN IF NOT EXISTS validation_errors JSONB DEFAULT '[]';
ALTER TABLE designs ADD COLUMN IF NOT EXISTS validation_stats JSONB DEFAULT '{}';
ALTER TABLE designs ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'PENDING';

CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID REFERENCES designs(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    confidence FLOAT DEFAULT 0.0,
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS export_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID REFERENCES designs(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_designs_session ON designs(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_design ON agent_logs(design_id);
CREATE INDEX IF NOT EXISTS idx_exports_design ON export_artifacts(design_id);

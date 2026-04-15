-- Context Catch Snapshot Version Table
-- Purpose: Store compressed context snapshots for session recovery (disaster recovery)

CREATE TABLE IF NOT EXISTS context_snapshots (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    compressed_summary JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_snapshots_session_version
    ON context_snapshots(session_id, version DESC);

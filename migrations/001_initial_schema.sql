-- Migration: 001_initial_schema.sql
-- Description: Initial database schema for AI Interview Platform
-- Created: 2026-04-04
-- Requires: PostgreSQL 14+ with pgvector extension

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension (for vector embeddings)
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- Users Table (预留多租户)
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for users
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_created_at ON users(created_at);

-- =============================================================================
-- Resumes Table
-- =============================================================================
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_path VARCHAR(500),
    parsed_content JSONB,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for resumes
CREATE INDEX ix_resumes_user_id ON resumes(user_id);
CREATE INDEX ix_resumes_created_at ON resumes(created_at);

-- =============================================================================
-- Projects Table
-- =============================================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    name VARCHAR(200),
    repo_path VARCHAR(500),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for projects
CREATE INDEX ix_projects_resume_id ON projects(resume_id);
CREATE INDEX ix_projects_created_at ON projects(created_at);

-- =============================================================================
-- Knowledge Base Table (RAG Knowledge)
-- =============================================================================
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50),
    skill_point VARCHAR(200),
    content TEXT,
    embedding_id INTEGER,  -- References pgvector embedding table
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for knowledge_base
CREATE INDEX ix_knowledge_base_project_id ON knowledge_base(project_id);
CREATE INDEX ix_knowledge_base_skill_point ON knowledge_base(skill_point);
CREATE INDEX ix_knowledge_base_type ON knowledge_base(type);
CREATE INDEX ix_knowledge_base_embedding_id ON knowledge_base(embedding_id);

-- =============================================================================
-- Interview Sessions Table
-- =============================================================================
CREATE TABLE interview_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    mode VARCHAR(50) DEFAULT 'free' NOT NULL,  -- 'free' or 'training'
    feedback_mode VARCHAR(50) DEFAULT 'recorded' NOT NULL,  -- 'realtime' or 'recorded'
    status VARCHAR(50) DEFAULT 'active' NOT NULL,  -- 'active', 'completed', 'cancelled'
    started_at TIMESTAMP DEFAULT NOW() NOT NULL,
    ended_at TIMESTAMP
);

-- Indexes for interview_sessions
CREATE INDEX ix_interview_sessions_user_id ON interview_sessions(user_id);
CREATE INDEX ix_interview_sessions_resume_id ON interview_sessions(resume_id);
CREATE INDEX ix_interview_sessions_status ON interview_sessions(status);
CREATE INDEX ix_interview_sessions_started_at ON interview_sessions(started_at);

-- =============================================================================
-- Q&A History Table
-- =============================================================================
CREATE TABLE qa_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    series INTEGER DEFAULT 1 NOT NULL,
    question_number INTEGER DEFAULT 1 NOT NULL,
    question TEXT,
    user_answer TEXT,
    standard_answer TEXT,
    feedback TEXT,
    deviation_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for qa_history
CREATE INDEX ix_qa_history_session_id ON qa_history(session_id);
CREATE INDEX ix_qa_history_series ON qa_history(series);
CREATE INDEX ix_qa_history_created_at ON qa_history(created_at);

-- =============================================================================
-- Interview Feedback Table
-- =============================================================================
CREATE TABLE interview_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    overall_score FLOAT,
    strengths JSONB,  -- Array of strength strings
    weaknesses JSONB,  -- Array of weakness strings
    suggestions JSONB,  -- Array of suggestion strings
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for interview_feedback
CREATE INDEX ix_interview_feedback_session_id ON interview_feedback(session_id);
CREATE INDEX ix_interview_feedback_created_at ON interview_feedback(created_at);

-- =============================================================================
-- pgvector Embeddings Table (for RAG vector search)
-- =============================================================================
-- This table stores vector embeddings for knowledge base content
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    embedding VECTOR(1536) NOT NULL,  -- OpenAI text-embedding-3-small dimension
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Index for vector similarity search (HNSW is recommended for pgvector)
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- Comments for documentation
-- =============================================================================
COMMENT ON TABLE users IS 'User accounts (multi-tenant support reserved)';
COMMENT ON TABLE resumes IS 'Parsed resume data';
COMMENT ON TABLE projects IS 'Project experiences from resume';
COMMENT ON TABLE knowledge_base IS 'RAG knowledge entries for interview questions';
COMMENT ON TABLE interview_sessions IS 'Interview session tracking';
COMMENT ON TABLE qa_history IS 'Individual Q&A records during interview';
COMMENT ON TABLE interview_feedback IS 'Final interview feedback and evaluation';
COMMENT ON TABLE embeddings IS 'Vector embeddings for semantic search';

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================================================
-- Grant permissions (adjust role name as needed)
-- =============================================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

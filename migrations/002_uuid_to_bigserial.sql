-- Migration: 002_uuid_to_bigserial.sql
-- Description: 将 UUID 主键迁移到 BIGSERIAL，只在 users 表保留 uuid 列
-- Created: 2026-04-10
-- Requires: PostgreSQL 14+
-- Direction: 升级迁移（不可逆，需备份）

BEGIN;

-- =============================================================================
-- 阶段 1: 创建所有序列
-- =============================================================================

CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE SEQUENCE IF NOT EXISTS resumes_id_seq;
CREATE SEQUENCE IF NOT EXISTS projects_id_seq;
CREATE SEQUENCE IF NOT EXISTS knowledge_base_id_seq;
CREATE SEQUENCE IF NOT EXISTS interview_sessions_id_seq;
CREATE SEQUENCE IF NOT EXISTS qa_history_id_seq;
CREATE SEQUENCE IF NOT EXISTS interview_feedback_id_seq;

-- =============================================================================
-- 阶段 2: 修改 users 表（唯一保留 uuid 列的表）
-- =============================================================================

-- 添加新列
ALTER TABLE users ADD COLUMN id_new BIGSERIAL;
ALTER TABLE users ADD COLUMN uuid_new UUID;

-- 填充数据：uuid_new = 原 id，id_new = 序列
UPDATE users SET
    uuid_new = id,
    id_new = nextval('users_id_seq');

-- 设置序列当前值
SELECT setval('users_id_seq', (SELECT MAX(id_new) FROM users));

-- 删除旧列和约束
ALTER TABLE users DROP CONSTRAINT users_pkey;
ALTER TABLE users DROP COLUMN id;
ALTER TABLE users DROP COLUMN uuid;

-- 重命名新列
ALTER TABLE users ADD COLUMN uuid UUID;
UPDATE users SET uuid = uuid_new;
ALTER TABLE users DROP COLUMN uuid_new;
ALTER TABLE users ALTER COLUMN uuid SET NOT NULL;

ALTER TABLE users ADD COLUMN id BIGSERIAL;
UPDATE users SET id = id_new;
ALTER TABLE users DROP COLUMN id_new;

-- 设置序列默认值和所有权
ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');
ALTER SEQUENCE users_id_seq OWNED BY users.id;

-- 恢复主键和约束
ALTER TABLE users ADD PRIMARY KEY (id);
ALTER TABLE users ADD CONSTRAINT users_uuid_key UNIQUE (uuid);

-- =============================================================================
-- 阶段 3: 修改 resumes 表
-- =============================================================================

-- 添加新列
ALTER TABLE resumes ADD COLUMN id_new BIGSERIAL;
ALTER TABLE resumes ADD COLUMN user_id_new BIGINT;

-- 生成新 id
UPDATE resumes SET id_new = nextval('resumes_id_seq');
SELECT setval('resumes_id_seq', (SELECT MAX(id_new) FROM resumes));

-- 通过 users.uuid 映射获取新的 user_id
UPDATE resumes r SET user_id_new = u.id
FROM users u
WHERE r.user_id = u.uuid;

-- 删除旧列和约束
ALTER TABLE resumes DROP CONSTRAINT resumes_pkey;
ALTER TABLE resumes DROP CONSTRAINT resumes_user_id_fkey;
ALTER TABLE resumes DROP COLUMN id;
ALTER TABLE resumes DROP COLUMN user_id;

-- 重命名新列
ALTER TABLE resumes ADD COLUMN id BIGSERIAL;
ALTER TABLE resumes ADD COLUMN user_id BIGINT;

UPDATE resumes SET id = id_new;
UPDATE resumes SET user_id = user_id_new;

ALTER TABLE resumes DROP COLUMN id_new;
ALTER TABLE resumes DROP COLUMN user_id_new;

-- 设置约束
ALTER TABLE resumes ALTER COLUMN id SET DEFAULT nextval('resumes_id_seq');
ALTER TABLE resumes ALTER COLUMN user_id SET NOT NULL;
ALTER SEQUENCE resumes_id_seq OWNED BY resumes.id;
ALTER TABLE resumes ADD PRIMARY KEY (id);
ALTER TABLE resumes ADD CONSTRAINT resumes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 4: 修改 projects 表
-- =============================================================================

ALTER TABLE projects ADD COLUMN id_new BIGSERIAL;
ALTER TABLE projects ADD COLUMN resume_id_new BIGINT;

UPDATE projects SET id_new = nextval('projects_id_seq');
SELECT setval('projects_id_seq', (SELECT MAX(id_new) FROM projects));

-- 通过 resumes.uuid 映射获取新的 resume_id
UPDATE projects p SET resume_id_new = r.id
FROM resumes r
WHERE p.resume_id = r.uuid;

ALTER TABLE projects DROP CONSTRAINT projects_pkey;
ALTER TABLE projects DROP CONSTRAINT projects_resume_id_fkey;
ALTER TABLE projects DROP COLUMN id;
ALTER TABLE projects DROP COLUMN resume_id;

ALTER TABLE projects ADD COLUMN id BIGSERIAL;
ALTER TABLE projects ADD COLUMN resume_id BIGINT;

UPDATE projects SET id = id_new;
UPDATE projects SET resume_id = resume_id_new;

ALTER TABLE projects DROP COLUMN id_new;
ALTER TABLE projects DROP COLUMN resume_id_new;

ALTER TABLE projects ALTER COLUMN id SET DEFAULT nextval('projects_id_seq');
ALTER TABLE projects ALTER COLUMN resume_id SET NOT NULL;
ALTER SEQUENCE projects_id_seq OWNED BY projects.id;
ALTER TABLE projects ADD PRIMARY KEY (id);
ALTER TABLE projects ADD CONSTRAINT projects_resume_id_fkey FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 5: 修改 knowledge_base 表
-- =============================================================================

ALTER TABLE knowledge_base ADD COLUMN id_new BIGSERIAL;
ALTER TABLE knowledge_base ADD COLUMN project_id_new BIGINT;

UPDATE knowledge_base SET id_new = nextval('knowledge_base_id_seq');
SELECT setval('knowledge_base_id_seq', (SELECT MAX(id_new) FROM knowledge_base));

-- 通过 projects.uuid 映射获取新的 project_id
UPDATE knowledge_base kb SET project_id_new = p.id
FROM projects p
WHERE kb.project_id = p.uuid;

ALTER TABLE knowledge_base DROP CONSTRAINT knowledge_base_pkey;
ALTER TABLE knowledge_base DROP CONSTRAINT knowledge_base_project_id_fkey;
ALTER TABLE knowledge_base DROP COLUMN id;
ALTER TABLE knowledge_base DROP COLUMN project_id;

ALTER TABLE knowledge_base ADD COLUMN id BIGSERIAL;
ALTER TABLE knowledge_base ADD COLUMN project_id BIGINT;

UPDATE knowledge_base SET id = id_new;
UPDATE knowledge_base SET project_id = project_id_new;

ALTER TABLE knowledge_base DROP COLUMN id_new;
ALTER TABLE knowledge_base DROP COLUMN project_id_new;

ALTER TABLE knowledge_base ALTER COLUMN id SET DEFAULT nextval('knowledge_base_id_seq');
ALTER TABLE knowledge_base ALTER COLUMN project_id SET NOT NULL;
ALTER SEQUENCE knowledge_base_id_seq OWNED BY knowledge_base.id;
ALTER TABLE knowledge_base ADD PRIMARY KEY (id);
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 6: 修改 interview_sessions 表
-- =============================================================================

ALTER TABLE interview_sessions ADD COLUMN id_new BIGSERIAL;
ALTER TABLE interview_sessions ADD COLUMN user_id_new BIGINT;
ALTER TABLE interview_sessions ADD COLUMN resume_id_new BIGINT;

UPDATE interview_sessions SET id_new = nextval('interview_sessions_id_seq');
SELECT setval('interview_sessions_id_seq', (SELECT MAX(id_new) FROM interview_sessions));

-- 通过 users.uuid 和 resumes.uuid 映射获取新的 user_id 和 resume_id
UPDATE interview_sessions s SET
    user_id_new = u.id,
    resume_id_new = r.id
FROM users u, resumes r
WHERE s.user_id = u.uuid AND s.resume_id = r.uuid;

ALTER TABLE interview_sessions DROP CONSTRAINT interview_sessions_pkey;
ALTER TABLE interview_sessions DROP CONSTRAINT interview_sessions_user_id_fkey;
ALTER TABLE interview_sessions DROP CONSTRAINT interview_sessions_resume_id_fkey;
ALTER TABLE interview_sessions DROP COLUMN id;
ALTER TABLE interview_sessions DROP COLUMN user_id;
ALTER TABLE interview_sessions DROP COLUMN resume_id;

ALTER TABLE interview_sessions ADD COLUMN id BIGSERIAL;
ALTER TABLE interview_sessions ADD COLUMN user_id BIGINT;
ALTER TABLE interview_sessions ADD COLUMN resume_id BIGINT;

UPDATE interview_sessions SET id = id_new;
UPDATE interview_sessions SET user_id = user_id_new;
UPDATE interview_sessions SET resume_id = resume_id_new;

ALTER TABLE interview_sessions DROP COLUMN id_new;
ALTER TABLE interview_sessions DROP COLUMN user_id_new;
ALTER TABLE interview_sessions DROP COLUMN resume_id_new;

ALTER TABLE interview_sessions ALTER COLUMN id SET DEFAULT nextval('interview_sessions_id_seq');
ALTER TABLE interview_sessions ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE interview_sessions ALTER COLUMN resume_id SET NOT NULL;
ALTER SEQUENCE interview_sessions_id_seq OWNED BY interview_sessions.id;
ALTER TABLE interview_sessions ADD PRIMARY KEY (id);
ALTER TABLE interview_sessions ADD CONSTRAINT interview_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE interview_sessions ADD CONSTRAINT interview_sessions_resume_id_fkey FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 7: 修改 qa_history 表
-- =============================================================================

ALTER TABLE qa_history ADD COLUMN id_new BIGSERIAL;
ALTER TABLE qa_history ADD COLUMN session_id_new BIGINT;

UPDATE qa_history SET id_new = nextval('qa_history_id_seq');
SELECT setval('qa_history_id_seq', (SELECT MAX(id_new) FROM qa_history));

-- 通过 interview_sessions.uuid 映射获取新的 session_id
UPDATE qa_history qh SET session_id_new = s.id
FROM interview_sessions s
WHERE qh.session_id = s.uuid;

ALTER TABLE qa_history DROP CONSTRAINT qa_history_pkey;
ALTER TABLE qa_history DROP CONSTRAINT qa_history_session_id_fkey;
ALTER TABLE qa_history DROP COLUMN id;
ALTER TABLE qa_history DROP COLUMN session_id;

ALTER TABLE qa_history ADD COLUMN id BIGSERIAL;
ALTER TABLE qa_history ADD COLUMN session_id BIGINT;

UPDATE qa_history SET id = id_new;
UPDATE qa_history SET session_id = session_id_new;

ALTER TABLE qa_history DROP COLUMN id_new;
ALTER TABLE qa_history DROP COLUMN session_id_new;

ALTER TABLE qa_history ALTER COLUMN id SET DEFAULT nextval('qa_history_id_seq');
ALTER TABLE qa_history ALTER COLUMN session_id SET NOT NULL;
ALTER SEQUENCE qa_history_id_seq OWNED BY qa_history.id;
ALTER TABLE qa_history ADD PRIMARY KEY (id);
ALTER TABLE qa_history ADD CONSTRAINT qa_history_session_id_fkey FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 8: 修改 interview_feedback 表
-- =============================================================================

ALTER TABLE interview_feedback ADD COLUMN id_new BIGSERIAL;
ALTER TABLE interview_feedback ADD COLUMN session_id_new BIGINT;

UPDATE interview_feedback SET id_new = nextval('interview_feedback_id_seq');
SELECT setval('interview_feedback_id_seq', (SELECT MAX(id_new) FROM interview_feedback));

-- 通过 interview_sessions.uuid 映射获取新的 session_id
UPDATE interview_feedback fb SET session_id_new = s.id
FROM interview_sessions s
WHERE fb.session_id = s.uuid;

ALTER TABLE interview_feedback DROP CONSTRAINT interview_feedback_pkey;
ALTER TABLE interview_feedback DROP CONSTRAINT interview_feedback_session_id_fkey;
ALTER TABLE interview_feedback DROP COLUMN id;
ALTER TABLE interview_feedback DROP COLUMN session_id;

ALTER TABLE interview_feedback ADD COLUMN id BIGSERIAL;
ALTER TABLE interview_feedback ADD COLUMN session_id BIGINT;

UPDATE interview_feedback SET id = id_new;
UPDATE interview_feedback SET session_id = session_id_new;

ALTER TABLE interview_feedback DROP COLUMN id_new;
ALTER TABLE interview_feedback DROP COLUMN session_id_new;

ALTER TABLE interview_feedback ALTER COLUMN id SET DEFAULT nextval('interview_feedback_id_seq');
ALTER TABLE interview_feedback ALTER COLUMN session_id SET NOT NULL;
ALTER SEQUENCE interview_feedback_id_seq OWNED BY interview_feedback.id;
ALTER TABLE interview_feedback ADD PRIMARY KEY (id);
ALTER TABLE interview_feedback ADD CONSTRAINT interview_feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE;

-- =============================================================================
-- 阶段 9: 重建索引
-- =============================================================================

REINDEX TABLE users;
REINDEX TABLE resumes;
REINDEX TABLE projects;
REINDEX TABLE knowledge_base;
REINDEX TABLE interview_sessions;
REINDEX TABLE qa_history;
REINDEX TABLE interview_feedback;

-- =============================================================================
-- 阶段 10: 添加注释
-- =============================================================================

COMMENT ON COLUMN users.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN users.uuid IS '用户外部标识符（API 使用）';
COMMENT ON COLUMN resumes.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN resumes.user_id IS '外键 -> users.id (BIGINT)';
COMMENT ON COLUMN projects.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN projects.resume_id IS '外键 -> resumes.id (BIGINT)';
COMMENT ON COLUMN knowledge_base.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN knowledge_base.project_id IS '外键 -> projects.id (BIGINT)';
COMMENT ON COLUMN interview_sessions.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN interview_sessions.user_id IS '外键 -> users.id (BIGINT)';
COMMENT ON COLUMN interview_sessions.resume_id IS '外键 -> resumes.id (BIGINT)';
COMMENT ON COLUMN qa_history.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN qa_history.session_id IS '外键 -> interview_sessions.id (BIGINT)';
COMMENT ON COLUMN interview_feedback.id IS '内部主键（BIGSERIAL）';
COMMENT ON COLUMN interview_feedback.session_id IS '外键 -> interview_sessions.id (BIGINT)';

COMMIT;



-- Full Database Schema for Sinhala Ed Assistant
-- Generated based on SQLAlchemy models

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR NOT NULL UNIQUE,
    full_name VARCHAR,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 2. Resource Files
CREATE TABLE resource_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    original_filename VARCHAR,
    storage_path VARCHAR,
    mime_type VARCHAR,
    size_bytes BIGINT,
    source_type VARCHAR, -- Enum: 'user_upload', 'url', 'system'
    language VARCHAR,
    document_embedding JSON,
    embedding_model VARCHAR,
    extracted_text VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 3. Rubrics
CREATE TABLE rubrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR,
    description TEXT,
    rubric_type VARCHAR,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 4. Rubric Criteria
CREATE TABLE rubric_criteria (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rubric_id UUID NOT NULL REFERENCES rubrics(id),
    criterion VARCHAR,
    weight_percentage FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 5. Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    mode VARCHAR NOT NULL, -- Enum: 'learning', 'evaluation'
    channel VARCHAR NOT NULL, -- Enum: 'text', 'voice', 'mixed'
    title VARCHAR,
    description VARCHAR,
    grade INTEGER,
    subject VARCHAR,
    rubric_id UUID REFERENCES rubrics(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 6. Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id),
    role VARCHAR NOT NULL, -- Enum: 'user', 'assistant', 'system'
    modality VARCHAR NOT NULL, -- Enum: 'text', 'voice'
    content TEXT,
    grade_level VARCHAR, -- Enum
    audio_url VARCHAR,
    transcript TEXT,
    audio_duration_sec NUMERIC,
    model_name VARCHAR,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 7. Resource Chunks
CREATE TABLE resource_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    chunk_index INTEGER,
    content TEXT,
    content_length INTEGER,
    token_count INTEGER,
    embedding VECTOR(768),
    embedding_model VARCHAR,
    start_char INTEGER,
    end_char INTEGER
);

-- 8. Message Context Chunks
CREATE TABLE message_context_chunks (
    id BIGSERIAL PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES messages(id),
    chunk_id UUID NOT NULL REFERENCES resource_chunks(id),
    similarity_score NUMERIC,
    rank INTEGER
);

-- 9. Message Attachments
CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    display_name VARCHAR,
    attachment_type VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 10. Message Safety Reports
CREATE TABLE message_safety_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id),
    missing_concepts VARCHAR,
    extra_concepts VARCHAR,
    flagged_sentences VARCHAR,
    reasoning VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 11. Session Resources
CREATE TABLE session_resources (
    session_id UUID NOT NULL REFERENCES chat_sessions(id),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    label VARCHAR,
    PRIMARY KEY (session_id, resource_id)
);

-- 12. Evaluation Sessions
CREATE TABLE evaluation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id),
    rubric_id UUID REFERENCES rubrics(id),
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 13. Evaluation Resources
CREATE TABLE evaluation_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_session_id UUID NOT NULL REFERENCES evaluation_sessions(id),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    role VARCHAR
);

-- 14. Paper Config
CREATE TABLE paper_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_session_id UUID NOT NULL REFERENCES evaluation_sessions(id),
    paper_part VARCHAR,
    subject_name VARCHAR,
    medium VARCHAR,
    weightage NUMERIC(5, 2),
    total_main_questions INTEGER,
    selection_rules JSONB,
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 15. User Evaluation Contexts
CREATE TABLE user_evaluation_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    active_syllabus_id UUID REFERENCES resource_files(id),
    active_question_paper_id UUID REFERENCES resource_files(id),
    active_rubric_id UUID REFERENCES rubrics(id),
    active_paper_config JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 16. Question Papers
CREATE TABLE question_papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_session_id UUID NOT NULL REFERENCES evaluation_sessions(id),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    extracted_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 17. Questions
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_paper_id UUID NOT NULL REFERENCES question_papers(id),
    question_number VARCHAR,
    question_text TEXT,
    max_marks INTEGER,
    shared_stem TEXT,
    inherits_shared_stem_from VARCHAR
);

-- 18. Sub Questions
CREATE TABLE sub_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES questions(id),
    parent_sub_question_id UUID REFERENCES sub_questions(id),
    label VARCHAR,
    sub_question_text TEXT,
    max_marks INTEGER
);

-- 19. Answer Documents
CREATE TABLE answer_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_session_id UUID NOT NULL REFERENCES evaluation_sessions(id),
    resource_id UUID NOT NULL REFERENCES resource_files(id),
    student_identifier VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 20. Evaluation Results
CREATE TABLE evaluation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    answer_document_id UUID NOT NULL REFERENCES answer_documents(id),
    total_score NUMERIC,
    overall_feedback TEXT,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 21. Question Scores
CREATE TABLE question_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_result_id UUID NOT NULL REFERENCES evaluation_results(id),
    sub_question_id UUID NOT NULL REFERENCES sub_questions(id),
    awarded_marks NUMERIC,
    feedback TEXT
);

-- 22. Refresh Tokens
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 23. Password Reset Tokens
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

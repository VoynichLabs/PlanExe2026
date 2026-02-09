-- Create plan corpus + metrics tables for ranking pipeline

-- Enable pgvector for embedding similarity
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS plan_corpus (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    json_path TEXT,
    owner_id UUID,
    json_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    embedding VECTOR(768)
);

CREATE TABLE IF NOT EXISTS plan_metrics (
    plan_id UUID PRIMARY KEY REFERENCES plan_corpus(id) ON DELETE CASCADE,
    novelty_score INT,
    prompt_quality INT,
    technical_completeness INT,
    feasibility INT,
    impact_estimate INT,
    kpis JSONB NOT NULL DEFAULT '{}'::jsonb,
    overall_likert INT GENERATED ALWAYS AS (
        ((novelty_score + prompt_quality + technical_completeness + feasibility + impact_estimate) / 5)
    ) STORED,
    elo FLOAT DEFAULT 1500,
    bucket_id INT,
    review_comment TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rate_limit (
    api_key TEXT PRIMARY KEY,
    last_ts TIMESTAMPTZ,
    count INT DEFAULT 0
);

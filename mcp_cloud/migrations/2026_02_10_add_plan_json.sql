-- Add plan JSON storage for dynamic KPI comparisons

ALTER TABLE plan_corpus
    ADD COLUMN IF NOT EXISTS json_data JSONB;

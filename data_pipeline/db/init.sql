-- data_pipeline/db/init.sql

CREATE TABLE IF NOT EXISTS markets (
    token_id   TEXT PRIMARY KEY,
    slug       TEXT NOT NULL,
    question   TEXT NOT NULL,
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_history (
    time       TIMESTAMPTZ NOT NULL,
    token_id   TEXT        NOT NULL REFERENCES markets(token_id),
    price      NUMERIC(6,4) NOT NULL
);

SELECT create_hypertable('price_history', 'time', if_not_exists => TRUE);

-- Unique constraint to prevent duplicate inserts on re-run
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'price_history_unique'
          AND conrelid = 'price_history'::regclass
    ) THEN
        ALTER TABLE price_history
            ADD CONSTRAINT price_history_unique UNIQUE (time, token_id);
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS anomaly_events (
    id          SERIAL PRIMARY KEY,
    token_id    TEXT        NOT NULL REFERENCES markets(token_id),
    detected_at TIMESTAMPTZ NOT NULL,
    event_type  TEXT        NOT NULL,
    severity    TEXT        NOT NULL,
    detail      JSONB
);

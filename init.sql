CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS trades (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalies (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    z_score DOUBLE PRECISION NOT NULL,
    rolling_mean DOUBLE PRECISION NOT NULL,
    rolling_stddev DOUBLE PRECISION NOT NULL
);

SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);
SELECT create_hypertable('anomalies', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_symbol_time ON anomalies (symbol, time DESC);
CREATE TABLE trades (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION,
    quantity DOUBLE PRECISION
);
SELECT create_hypertable('trades', 'time');
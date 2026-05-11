import json
import os
import statistics
from collections import defaultdict, deque
from datetime import datetime, timezone

import psycopg2
from kafka import KafkaConsumer

TOPIC = os.getenv("KAFKA_TOPIC", "market_data")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "market_data")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
ROLLING_WINDOW = int(os.getenv("ROLLING_WINDOW", "100"))
Z_SCORE_THRESHOLD = float(os.getenv("Z_SCORE_THRESHOLD", "3.0"))


def get_db():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    connection.autocommit = True
    return connection


def ensure_schema(cursor):
    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            time TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            quantity DOUBLE PRECISION NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS anomalies (
            time TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            z_score DOUBLE PRECISION NOT NULL,
            rolling_mean DOUBLE PRECISION NOT NULL,
            rolling_stddev DOUBLE PRECISION NOT NULL
        );
        """
    )
    cursor.execute("SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);")
    cursor.execute("SELECT create_hypertable('anomalies', 'time', if_not_exists => TRUE);")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, time DESC);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_anomalies_symbol_time ON anomalies (symbol, time DESC);"
    )


def parse_trade(message):
    symbol = message["symbol"]
    price = float(message["price"])
    quantity = float(message["qty"])
    event_time = datetime.fromtimestamp(message["timestamp"] / 1000, tz=timezone.utc)
    return symbol, price, quantity, event_time


def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    windows = defaultdict(lambda: deque(maxlen=ROLLING_WINDOW))
    db = get_db()
    cursor = db.cursor()
    ensure_schema(cursor)

    print("Processor started. Waiting for messages...")
    print(
        f"Kafka={KAFKA_BROKER} Topic={TOPIC} Window={ROLLING_WINDOW} "
        f"Threshold={Z_SCORE_THRESHOLD}"
    )

    for message in consumer:
        symbol, current_price, quantity, event_time = parse_trade(message.value)
        cursor.execute(
            "INSERT INTO trades (time, symbol, price, quantity) VALUES (%s, %s, %s, %s)",
            (event_time, symbol, current_price, quantity),
        )

        price_window = windows[symbol]
        price_window.append(current_price)

        if len(price_window) < ROLLING_WINDOW:
            print(f"Warming up {symbol}: {len(price_window)}/{ROLLING_WINDOW}")
            continue

        rolling_mean = statistics.mean(price_window)
        rolling_stddev = statistics.stdev(price_window) + 1e-9
        z_score = (current_price - rolling_mean) / rolling_stddev

        if abs(z_score) >= Z_SCORE_THRESHOLD:
            cursor.execute(
                """
                INSERT INTO anomalies (
                    time, symbol, price, quantity, z_score, rolling_mean, rolling_stddev
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_time,
                    symbol,
                    current_price,
                    quantity,
                    z_score,
                    rolling_mean,
                    rolling_stddev,
                ),
            )
            print(
                f"ANOMALY {symbol} price={current_price:.2f} "
                f"z_score={z_score:.2f} time={event_time.isoformat()}"
            )
        else:
            print(
                f"NORMAL {symbol} price={current_price:.2f} "
                f"z_score={z_score:.2f} time={event_time.isoformat()}"
            )


if __name__ == "__main__":
    main()

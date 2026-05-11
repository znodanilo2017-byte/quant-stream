import json
import time
from collections import defaultdict, deque
from datetime import datetime

import numpy as np
from kafka import KafkaConsumer
import psycopg2

# ================= CONFIG =================
TOPIC = "market_data"
KAFKA_BROKER = "localhost:9092"

ROLLING_WINDOW = 30  # seconds
VOLATILITY_P90 = 0.002
TRADE_COUNT_P90 = 50
RANGE_SPIKE = 0.004

# ================= STATE =================
current_candle = defaultdict(lambda: {
    "second": None,
    "open": None,
    "high": None,
    "low": None,
    "close": None,
    "volume": 0.0,
    "trades": 0
})

history = defaultdict(lambda: deque(maxlen=ROLLING_WINDOW))

# ================= DB =================
def get_db():
    conn = psycopg2.connect(
        host="localhost",
        database="market",
        user="postgres",
        password="postgres"
    )
    conn.autocommit = True
    return conn

# ================= LOGIC =================
def classify_regime(candles):
    closes = np.array([c["close"] for c in candles])
    returns = np.diff(closes) / closes[:-1]

    volatility = np.std(returns)
    trade_count = candles[-1]["trades"]
    price_range = (candles[-1]["high"] - candles[-1]["low"]) / candles[-1]["open"]

    if price_range > RANGE_SPIKE:
        return "SPIKE", volatility, trade_count, price_range

    if volatility > VOLATILITY_P90 and trade_count > TRADE_COUNT_P90:
        return "VOLATILE", volatility, trade_count, price_range

    if trade_count < 5:
        return "QUIET", volatility, trade_count, price_range

    return "NORMAL", volatility, trade_count, price_range

# ================= MAIN =================
def run():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_regime (
            time TIMESTAMPTZ,
            symbol TEXT,
            regime TEXT,
            volatility DOUBLE PRECISION,
            trades INTEGER,
            price_range DOUBLE PRECISION
        );
    """)

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="latest",
        value_deserializer=lambda x: json.loads(x.decode())
    )

    print("🚀 Market Regime Processor running")

    for msg in consumer:
        e = msg.value
        symbol = e["symbol"]
        price = float(e["price"])
        qty = float(e["qty"])
        ts = datetime.fromtimestamp(e["timestamp"])

        sec = ts.replace(microsecond=0)
        candle = current_candle[symbol]

        # ---- NEW SECOND ----
        if candle["second"] != sec:
            if candle["second"] is not None:
                history[symbol].append(candle.copy())

                if len(history[symbol]) >= 10:
                    regime, vol, trades, pr = classify_regime(history[symbol])

                    cur.execute(
                        "INSERT INTO market_regime VALUES (%s,%s,%s,%s,%s,%s)",
                        (sec, symbol, regime, vol, trades, pr)
                    )

            current_candle[symbol] = {
                "second": sec,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": qty,
                "trades": 1
            }

        else:
            candle["high"] = max(candle["high"], price)
            candle["low"] = min(candle["low"], price)
            candle["close"] = price
            candle["volume"] += qty
            candle["trades"] += 1

if __name__ == "__main__":
    run()
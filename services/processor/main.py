import os
import json
import psycopg2
import joblib
import pandas as pd
import pandas_ta as ta
import numpy as np
from kafka import KafkaConsumer
from collections import deque, defaultdict
from datetime import datetime
import time

# --- CONFIG ---
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'redpanda:9092')
TOPIC = 'market_data'
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'market_data')
MODEL_PATH = "model_v2.pkl"

# --- STATE MANAGEMENT ---
# History buffer for ML (Stores 1-second candles)
candle_history = defaultdict(lambda: deque(maxlen=50))

# Temporary buffer to build the CURRENT candle
current_candle_state = defaultdict(lambda: {
    'open': None, 'high': -float('inf'), 'low': float('inf'), 
    'close': None, 'volume': 0.0, 'last_second': None
})

# --- DATABASE FUNCTION (Ось те, що зникло) ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, 
            database=DB_NAME, 
            user=DB_USER, 
            password=DB_PASS
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return None

class SmartDetector:
    def __init__(self, model_path):
        self.model = None
        print(f"🧠 Loading V2 ML Model from {model_path}...")
        try:
            self.model = joblib.load(model_path)
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ CRITICAL: Model not found ({e}). Did you run training?")
            raise e

    def update_candle_and_analyze(self, symbol, price, volume, timestamp_dt):
        """
        Aggregates trades into 1-second candles. 
        Only runs ML prediction when a second closes.
        """
        state = current_candle_state[symbol]
        
        # Round down to the nearest second
        current_second = timestamp_dt.replace(microsecond=0)

        # 1. Initialize state if new
        if state['last_second'] is None:
            state['last_second'] = current_second
            state['open'] = price
        
        # 2. Check if we moved to a NEW second
        prediction_result = False
        
        if current_second > state['last_second']:
            # --- CANDLE CLOSED! ---
            # Save the COMPLETED candle to history
            candle_history[symbol].append({
                'price': state['close'],
                'volume': state['volume']
            })
            
            # Run Prediction on the history
            prediction_result = self._predict(symbol)
            
            # Reset state for the new second
            state['last_second'] = current_second
            state['open'] = price
            state['high'] = price
            state['low'] = price
            state['close'] = price
            state['volume'] = volume
        else:
            # --- SAME SECOND (UPDATE CURRENT) ---
            state['high'] = max(state['high'], price)
            state['low'] = min(state['low'], price)
            state['close'] = price
            state['volume'] += volume

        return prediction_result

    def _predict(self, symbol):
        # Need 20 seconds of data for Volatility calculation
        if len(candle_history[symbol]) < 20:
            return False

        # Convert to DataFrame
        df = pd.DataFrame(candle_history[symbol])

        # Feature Engineering
        try:
            df['rsi'] = ta.rsi(df['price'], length=14)
            df['volatility'] = df['price'].rolling(20).std()
            df['vol_change'] = df['volume'].pct_change()

            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            
            latest = df.iloc[-1]

            if np.isnan(latest['rsi']) or np.isnan(latest['volatility']) or np.isnan(latest['vol_change']):
                return False

            features = [[latest['rsi'], latest['volatility'], latest['vol_change']]]
            # Отримуємо "сиру" оцінку (score)
            scores = self.model.decision_function(features)
            score = scores[0]

            # Виводимо score в логи, щоб ти бачив його (ВАЖЛИВО!)
            print(f"[DEBUG] Anomaly Score: {score:.4f}")

            # Встановлюємо ручний поріг.
            # Спробуй 0.05 або навіть 0.1 (чим вище число, тим більше аномалій)
            # Стандартний поріг моделі зазвичай десь біля 0.0 або від'ємний.
            # Якщо поставити +0.05, ми будемо вважати аномалією навіть трохи "нормальні" дані.
            manual_threshold = 0.05 

            if score < manual_threshold:
                is_anomaly = True
            else:
                is_anomaly = False

            return is_anomaly
            

        except Exception as e:
            print(f"⚠️ Calculation Error: {e}")
            return False

def run_processor():
    # 1. Initialize DB
    conn = get_db_connection()
    while not conn:
        print("⏳ Waiting for Database...")
        time.sleep(5)
        conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure table has is_anomaly column
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_anomaly BOOLEAN DEFAULT FALSE;")
    except: pass

    # 2. Initialize Model
    detector = SmartDetector(MODEL_PATH)

    # 3. Connect to Kafka
    print("⏳ Connecting to Kafka...")
    consumer = KafkaConsumer(
        TOPIC, 
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("🚀 V2 Processor Started (1s Aggregation + Isolation Forest)...")

    for msg in consumer:
        try:
            event = msg.value
            
            # Normalize Data
            symbol = event.get('symbol') or event.get('s')
            price = float(event.get('price') or event.get('p', 0))
            qty = float(event.get('quantity') or event.get('volume') or event.get('q', 0))
            
            # Timestamp Parsing
            raw_time = event.get('time') or event.get('timestamp') or event.get('T') or event.get('E')
            if raw_time:
                ts = float(raw_time)
                if ts > 10000000000: ts /= 1000.0 
                event_time = datetime.fromtimestamp(ts)
            else:
                event_time = datetime.now()

            # Filter for BTC only
            if "BTC" not in symbol:
                    continue
            
            # --- AGGREGATE & DETECT ---
            is_anomaly = detector.update_candle_and_analyze(symbol, price, qty, event_time)

            if is_anomaly:
                usd_val = price * qty
                print(f"🚨 ANOMALY: {symbol} | Price: {price} | Vol: {usd_val:.2f}")

            # --- SAVE TO DB ---
            cursor.execute(
                "INSERT INTO trades (time, symbol, price, quantity, is_anomaly) VALUES (%s, %s, %s, %s, %s)", 
                (event_time, symbol, price, qty, is_anomaly)
            )

        except Exception as e:
            print(f"⚠️ Error processing msg: {e}")
            if conn.closed:
                conn = get_db_connection()
                cursor = conn.cursor()

if __name__ == "__main__":
    run_processor()
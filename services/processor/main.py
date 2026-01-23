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
MODEL_PATH = "services/processor/model_v2.pkl" # Double check this path matches where Docker puts it

# --- STATE MANAGEMENT ---
candle_history = defaultdict(lambda: deque(maxlen=50))
current_candle_state = defaultdict(lambda: {
    'open': None, 'high': -float('inf'), 'low': float('inf'), 
    'close': None, 'volume': 0.0, 'last_second': None
})

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
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
            print(f"❌ CRITICAL: Model not found ({e}).")
            # We don't raise here to keep the container alive for debugging, 
            # but in prod you should raise.
            pass 

    def update_candle_and_analyze(self, symbol, price, volume, timestamp_dt):
        state = current_candle_state[symbol]
        current_second = timestamp_dt.replace(microsecond=0)

        # 1. Initialize state
        if state['last_second'] is None:
            state['last_second'] = current_second
            state['open'] = price
        
        # Default return (No anomaly, Score 0)
        prediction_result = (False, 0.0) 
        
        # 2. Check for NEW second
        if current_second > state['last_second']:
            # Save closed candle
            candle_history[symbol].append({
                'price': state['close'],
                'volume': state['volume']
            })
            
            # Run Prediction
            prediction_result = self._predict(symbol)
            
            # Reset state
            state['last_second'] = current_second
            state['open'] = price
            state['high'] = price
            state['low'] = price
            state['close'] = price
            state['volume'] = volume
        else:
            # Update current candle
            state['high'] = max(state['high'], price)
            state['low'] = min(state['low'], price)
            state['close'] = price
            state['volume'] += volume

        return prediction_result

    def _predict(self, symbol):
        # FIX 1: Not enough data -> Return Tuple
        if len(candle_history[symbol]) < 20:
            return False, 0.0

        if self.model is None:
             return False, 0.0

        try:
            df = pd.DataFrame(candle_history[symbol])
            df['rsi'] = ta.rsi(df['price'], length=14)
            df['volatility'] = df['price'].rolling(20).std()
            df['vol_change'] = df['volume'].pct_change()
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            
            latest = df.iloc[-1]

            # FIX 2: Bad data -> Return Tuple
            if np.isnan(latest['rsi']) or np.isnan(latest['volatility']) or np.isnan(latest['vol_change']):
                return False, 0.0

            features = [[latest['rsi'], latest['volatility'], latest['vol_change']]]
            
            scores = self.model.decision_function(features)
            score = scores[0]
            
            # Debug Print
            print(f"[DEBUG] {symbol} Score: {score:.4f}")

            manual_threshold = 0.05 
            is_anomaly = score < manual_threshold

            # FIX 3: Success -> Return Tuple
            return is_anomaly, score

        except Exception as e:
            print(f"⚠️ Calculation Error: {e}")
            # FIX 4: Error -> Return Tuple
            return False, 0.0

def run_processor():
    conn = get_db_connection()
    while not conn:
        print("⏳ Waiting for Database...")
        time.sleep(5)
        conn = get_db_connection()
    cursor = conn.cursor()

    # Auto-Migration
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_anomaly BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS anomaly_score DOUBLE PRECISION DEFAULT 0;")
        conn.commit()
    except: pass

    detector = SmartDetector(MODEL_PATH)

    print("⏳ Connecting to Kafka...")
    consumer = KafkaConsumer(
        TOPIC, 
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("🚀 Processor V2 Running...")

    for msg in consumer:
        try:
            event = msg.value
            symbol = event.get('symbol') or event.get('s')
            
            if "BTC" not in symbol: continue

            price = float(event.get('price') or event.get('p', 0))
            qty = float(event.get('quantity') or event.get('volume') or event.get('q', 0))
            
            raw_time = event.get('time') or event.get('timestamp') or event.get('T') or event.get('E')
            if raw_time:
                ts = float(raw_time)
                if ts > 10000000000: ts /= 1000.0 
                event_time = datetime.fromtimestamp(ts)
            else:
                event_time = datetime.now()

            # --- THE CRITICAL FIX ---
            # Now update_candle_and_analyze ALWAYS returns (bool, float)
            is_anomaly, score = detector.update_candle_and_analyze(symbol, price, qty, event_time)

            if is_anomaly:
                usd_val = price * qty
                print(f"🚨 ANOMALY: {symbol} | Score: {score:.3f}")

            cursor.execute(
                "INSERT INTO trades (time, symbol, price, quantity, is_anomaly, anomaly_score) VALUES (%s, %s, %s, %s, %s, %s)", 
                (event_time, symbol, price, qty, is_anomaly, score)
            )

        except Exception as e:
            # If unpacked failed before, it won't fail now.
            print(f"⚠️ Error loop: {e}")
            if conn.closed:
                conn = get_db_connection()
                cursor = conn.cursor()

if __name__ == "__main__":
    run_processor()
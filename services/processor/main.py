import json
import os
import psycopg2
import joblib
import numpy as np
from kafka import KafkaConsumer
from datetime import datetime
import pandas as pd
import time

# Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'redpanda:9092')
TOPIC = 'market_data'
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
MODEL_PATH = "isolation_forest.pkl"

class AnomalyDetector:
    def __init__(self, model_path):
        self.model = None
        self.last_prices = {} 
        
        print(f"🧠 Loading ML Model from {model_path}...")
        try:
            self.model = joblib.load(model_path)
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"⚠️ WARNING: Model not found ({e}). Using Dummy Logic.")

    def is_anomaly(self, symbol, current_price, quantity):
        # Оновлення ціни
        last_price = self.last_prices.get(symbol)
        self.last_prices[symbol] = current_price

        if last_price is None or not self.model:
            return False

        # --- Розрахунок Features (Має бути ідентичним до train_model.py) ---
        
        # 1. price_return
        price_return = (current_price - last_price) / last_price
        
        # 2. amount_usd (Рахуємо долари!)
        amount_usd = current_price * quantity
        
        # 3. amount_usd_log
        amount_usd_log = np.log1p(amount_usd)

        # --- Фільтр шуму ---
        # Ігноруємо дрібні зміни
        if abs(price_return) < 0.00005 and amount_usd < 50000:
            return False

        # --- Передбачення ---
        # Створюємо DataFrame з ТИМИ САМИМИ назвами колонок
        features = pd.DataFrame(
            [[price_return, amount_usd_log]], 
            columns=['price_return', 'amount_usd_log'] # <--- ПЕРЕВІРЕНО
        )

        try:
            prediction = self.model.predict(features)[0]
            return bool(prediction == -1)
        except:
            return False
        
def get_db_connection():
    try:
        conn = psycopg2.connect(host=DB_HOST, database="market_data", user="postgres", password="password")
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return None

def run_strategy():
    detector = AnomalyDetector(MODEL_PATH)

    print("⏳ Connecting to Kafka...")
    consumer = None
    for i in range(10): # Retry loop
        try:
            consumer = KafkaConsumer(
                TOPIC, bootstrap_servers=KAFKA_BROKER, auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            break
        except:
            time.sleep(2)
            
    if not consumer: return
    
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_anomaly BOOLEAN DEFAULT FALSE;")
    except: pass

    print("🚀 Processor Started (Smart USD Mode)...")

    for msg in consumer:
        try:
            event = msg.value
            symbol = event.get('symbol') or event.get('s')
            price = float(event.get('price') or event.get('p', 0))
            qty = float(event.get('quantity') or event.get('volume') or event.get('qty') or event.get('q', 0))
            
            # Timestamp parsing
            raw_time = event.get('time') or event.get('timestamp') or event.get('T') or event.get('E')
            if raw_time:
                ts = float(raw_time)
                if ts > 10000000000: ts /= 1000.0
                event_time = datetime.fromtimestamp(ts)
            else:
                event_time = datetime.now()

            # --- DETECT ---
            is_anomaly = detector.is_anomaly(symbol, price, qty)

            if is_anomaly:
                # Рахуємо суму для красивого логу
                usd_val = price * qty
                print(f"🚨 ANOMALY: {symbol} | ${usd_val:.2f} | Price: {price}")

            # --- SAVE ---
            cursor.execute(
                "INSERT INTO trades (time, symbol, price, quantity, is_anomaly) VALUES (%s, %s, %s, %s, %s)", 
                (event_time, symbol, price, qty, is_anomaly)
            )
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            if conn.closed:
                conn = get_db_connection()
                cursor = conn.cursor()

if __name__ == "__main__":
    run_strategy()
import json
import os
import psycopg2
import requests
from kafka import KafkaConsumer
from collections import deque
import time

# Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'redpanda:9092')
TOPIC = 'market_data'
DB_HOST = os.getenv('DB_HOST', 'timescaledb')

# Telegram Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST, 
        database="market_data", 
        user="postgres", 
        password="password"
    )
    conn.autocommit = True # 👈 FORCE SAVE IMMEDIATELY
    return conn

def run_strategy():
    print("⏳ Connecting to Kafka...")
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest', # Read everything
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    print("🧠 Quant Engine Started... (Auto-Commit ON)")

    for msg in consumer:
        try:
            event = msg.value
            symbol = event['symbol']
            price = event['price']
            qty = event['qty']
            
            # Print to logs so we know it's trying
            print(f"📥 Saving: {symbol} ${price}") 

            # 👈 NUCLEAR FIX: Use NOW() instead of calculating timestamp
            cursor.execute(
                "INSERT INTO trades (time, symbol, price, quantity) VALUES (NOW(), %s, %s, %s)", 
                (symbol, price, qty)
            )
            # No conn.commit() needed because autocommit is True
            
        except Exception as e:
            print(f"❌ DATA ERROR: {e}")
            # Reconnect if DB dropped
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
            except:
                pass

if __name__ == "__main__":
    run_strategy()

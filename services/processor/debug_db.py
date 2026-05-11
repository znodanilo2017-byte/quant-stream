import psycopg2
import os
import time

# Force the connection params
DB_HOST = "timescaledb"
DB_NAME = "market_data"
DB_USER = "postgres"
DB_PASS = "password"

print("1. Connecting to DB...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True # Force auto-save
    cursor = conn.cursor()
    print("   ✅ Connected.")

    print("2. Attempting INSERT...")
    cursor.execute("""
        INSERT INTO trades (time, symbol, price, quantity) 
        VALUES (NOW(), 'DEBUG_TEST', 50000.0, 1.0);
    """)
    print("   ✅ Insert executed.")

    print("3. Checking Count...")
    cursor.execute("SELECT count(*) FROM trades;")
    count = cursor.fetchone()[0]
    print(f"   📊 Current Row Count: {count}")

except Exception as e:
    print(f"   ❌ ERROR: {e}")

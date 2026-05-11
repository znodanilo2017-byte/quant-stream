import psycopg2
import os
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_NAME = os.getenv("DB_NAME", "market_data")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "password")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

print("1. Connecting to DB...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
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

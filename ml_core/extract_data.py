import pandas as pd
import psycopg2
import os

# Offline helper for ML experiments. Not part of the production pipeline.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "market_data")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "password")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

def extract_training_data():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    query = """
    SELECT time, symbol, price, quantity 
    FROM trades 
    WHERE symbol = 'BTCUSDT' 
      AND time > NOW() - INTERVAL '7 days'
    ORDER BY time ASC
    """

    print("Loading data from trades table...")
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("WARNING: DataFrame is empty! Check if ingestor is running.")
        return

    print(f"Loaded {len(df)} rows.")
    
    output_path = "training_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    extract_training_data()
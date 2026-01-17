import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

# 1. Назви монет
SYMBOLS = ["BTCUSDT", "ETHUSDT"] 

all_data = []
print("📡 Fetching REAL market data (USD Based)...")

for symbol in SYMBOLS:
    try:
        url = "https://api.binance.com/api/v3/trades"
        params = {"symbol": symbol, "limit": 1000}
        r = requests.get(url, params=params)
        df = pd.DataFrame(r.json())
        
        # Типи даних
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        
        # --- ВАЖЛИВА НАЗВА 1: amount_usd ---
        df['amount_usd'] = df['price'] * df['qty']
        
        df['prev_price'] = df['price'].shift(1)
        df = df.dropna()
        
        # --- ВАЖЛИВА НАЗВА 2: price_return ---
        df['price_return'] = (df['price'] - df['prev_price']) / df['prev_price']
        
        # --- ВАЖЛИВА НАЗВА 3: amount_usd_log ---
        df['amount_usd_log'] = np.log1p(df['amount_usd'])
        
        # Зберігаємо ТІЛЬКИ ці дві колонки
        all_data.append(df[['price_return', 'amount_usd_log']])
        print(f"✅ {symbol} loaded.")
        
    except Exception as e:
        print(f"❌ Error {symbol}: {e}")

# Тренування
full_df = pd.concat(all_data, ignore_index=True)
print(f"📊 Training on {len(full_df)} trades.")

# contamination=0.005 (0.5% аномалій)
model = IsolationForest(n_estimators=100, contamination=0.005, random_state=42)

# Передаємо колонки з правильними назвами
model.fit(full_df[['price_return', 'amount_usd_log']])

joblib.dump(model, 'isolation_forest.pkl')
print("💾 Model saved: isolation_forest.pkl")
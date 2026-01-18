import pandas as pd
import numpy as np
import pandas_ta as ta
from sklearn.ensemble import IsolationForest
import joblib

CSV_FILE = "ml_core/BTCUSDT-trades-2025-12.csv" # Path to your CSV file

print("⏳ Loading CSV (This might take a minute)...")
# OPTIMIZATION: engine='pyarrow' is faster for large CSVs if installed, 
# otherwise default is fine.
df = pd.read_csv(
    CSV_FILE, 
    names=["id", "price", "qty", "quote_qty", "time", "is_buyer_maker", "is_best_match"],
    usecols=["price", "qty", "time"]
)

print("⚙️ Aggregating to 1-second candles...")
df['time'] = pd.to_datetime(df['time'], unit='us')
df = df.set_index('time').sort_index()

# Resample to 1s
ohlc = df['price'].resample('1s').ohlc()
ohlc['volume'] = df['qty'].resample('1s').sum()

# Clean up empty intervals (no trades in that second)
ohlc = ohlc.dropna()

print(f"📊 Candles generated: {len(ohlc)}")

print("🧠 Calculating Technical Indicators...")
# 1. RSI
ohlc['rsi'] = ta.rsi(ohlc['close'], length=14)

# 2. Volatility (Standard Deviation)
# Note: 20 seconds is very fast. If it's too noisy, try 60 or 300.
ohlc['volatility'] = ohlc['close'].rolling(20).std()

# 3. Volume Momentum
ohlc['vol_change'] = ohlc['volume'].pct_change()

# --- CRITICAL FIX: Handle Infinity ---
ohlc.replace([np.inf, -np.inf], np.nan, inplace=True)
ohlc.dropna(inplace=True)

print(f"📉 Training Data Size: {len(ohlc)} rows")

# Prepare X
X = ohlc[['rsi', 'volatility', 'vol_change']].values

print("🏋️ Training Smart Model (Isolation Forest)...")
model = IsolationForest(
    n_estimators=100,
    contamination=0.001, # Adjusted to 0.1% (Crypto is noisy, 0.5% might be too many alerts)
    random_state=42,
    n_jobs=-1
)
model.fit(X)

# Save
joblib.dump(model, "model_v2.pkl")
print("✅ Model saved as model_v2.pkl")

# --- Verification ---
ohlc['anomaly'] = model.predict(X)
n_anomalies = len(ohlc[ohlc['anomaly'] == -1])
print(f"🔎 Found {n_anomalies} anomalies in historical data.")
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from sqlalchemy import create_engine

# 1. SETUP
st.set_page_config(page_title="⚡ Quant Monitor", layout="wide")
DB_HOST = os.getenv('DB_HOST', 'localhost')

# 2. DATA FETCHING
def get_data():
    # A. Use SQLAlchemy (The "Server" Fix for stability)
    db_user = "postgres"
    db_pass = "password"
    db_port = "5432"
    db_name = "market_data"
    
    # Connect
    engine = create_engine(f'postgresql://{db_user}:{db_pass}@{DB_HOST}:{db_port}/{db_name}')
    
    # B. Use the 5-Minute Window (The "PC" Fix for better visuals)
    query = """
    SELECT time, symbol, price 
    FROM trades 
    WHERE time > NOW() - INTERVAL '5 minutes'
    ORDER BY time ASC
    """
    
    # C. Execute safely
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    return df

# 3. UI LAYOUT
st.title("⚡ Real-Time Arbitrage Monitor")
st.caption("Tracking BTC vs ETH Correlation Spreads")

placeholder = st.empty()

# 4. MAIN LOOP
while True:
    try:
        df = get_data()
        
        if not df.empty:
            with placeholder.container():
                # Convert time
                df['time'] = pd.to_datetime(df['time'])
                
                # Normalize prices to compare percentage change
                # (Find the first price in this 5-minute window to use as baseline)
                btc_data = df[df['symbol']=='BTCUSDT']
                eth_data = df[df['symbol']=='ETHUSDT']
                
                if not btc_data.empty and not eth_data.empty:
                    btc_start = btc_data['price'].iloc[0]
                    eth_start = eth_data['price'].iloc[0]
                    
                    df['normalized_price'] = df.apply(
                        lambda row: (row['price'] - btc_start)/btc_start if row['symbol']=='BTCUSDT' 
                        else (row['price'] - eth_start)/eth_start, axis=1
                    )

                    # Metrics (Latest Price)
                    latest_btc = btc_data['price'].iloc[-1]
                    latest_eth = eth_data['price'].iloc[-1]
                    
                    kpi1, kpi2, kpi3 = st.columns(3)
                    kpi1.metric("BTC Price", f"${latest_btc:,.2f}")
                    kpi2.metric("ETH Price", f"${latest_eth:,.2f}")
                    
                    # Chart
                    fig = px.line(df, x='time', y='normalized_price', color='symbol', 
                                  title="Relative Performance (Last 5 Mins)")
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{time.time()}")
                else:
                    st.warning("Waiting for both BTC and ETH data streams...")
                
        else:
            st.info("Waiting for data stream to start...")
            
        time.sleep(1)
        
    except Exception as e:
        st.error(f"Connection retry... ({e})")
        time.sleep(2)
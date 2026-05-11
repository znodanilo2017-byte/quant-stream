from kafka import KafkaConsumer
import json
from collections import deque
import statistics

# ================= CONFIG =================

TOPIC = "market_data"
KAFKA_BROKER = "localhost:9092"

ROLLING_WINDOW = 100 
Z_SCORE_THRESHOLD = 3.0

# ================= MAIN =================

def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )
    price_window = deque(maxlen=ROLLING_WINDOW)

    db = get_db()
    cursor = db.cursor()

    print("🚀 Processor started. Waiting for messages...")
    for message in consumer:
        # Expected structure of data: {'symbol': str, 'price': float, 'timestamp': str, ...}
        data = message.value
        
        # 1. Price from incoming data  
        current_price = float(data['price'])
        symbol = data['symbol']

        # 2. Update rolling window
        price_window.append(current_price)

        # 3. Only classify regime if we have enough data
        if len(price_window) < ROLLING_WINDOW:
            print(f"⏳ Збираємо дані для аналізу... ({len(price_window)}/{ROLLING_WINDOW})")
            continue

    
        # Рахуємо середнє значення (Mean)
        mean_price = statistics.mean(price_window)
        
        # Рахуємо стандартне відхилення (StdDev). 
        # Додаємо мікроскопічне число (1e-9), щоб уникнути помилки ділення на нуль, якщо всі 100 цін однакові
        stdev_price = statistics.stdev(price_window) + 1e-9
        
        # 4. Обчислюємо Z-Score за класичною формулою: Z = (X - Mean) / StdDev
        z_score = (current_price - mean_price) / stdev_price
        
        # 5. Перевіряємо, чи не пробила ціна наш поріг
        if abs(z_score) > Z_SCORE_THRESHOLD:
            print(f"🚨 АНОМАЛІЯ [{symbol}] | Ціна: {current_price} | Z-Score: {z_score:.2f}")
        else:
            # Звичайний лог для розуміння, що система працює
            print(f"✅ Норма [{symbol}] | Ціна: {current_price} | Z-Score: {z_score:.2f}")
        

if __name__ == "__main__":
    main()

        # Here you would process the data, update state, classify regime, etc.
        # For this example, we'll just insert the raw data into the DB.


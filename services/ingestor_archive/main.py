import asyncio
import json
import os
import logging
from aiohttp import ClientSession
from aiokafka import AIOKafkaProducer

# --- CONFIG (Адаптовано для тестування) ---
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:19092')
TOPIC = 'market_data'
# Забираємо URL з середовища, як робили в Rust
BINANCE_WS = os.getenv('WS_URL', "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CryptoIngestor")

async def ingest():
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
    await producer.start() 
    
    try:
        while True:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(BINANCE_WS) as ws:
                        logger.info(f"🔌 Connected to: {BINANCE_WS}")
                        
                        async for msg in ws:
                            if msg.type == 1: # Text frame
                                raw = json.loads(msg.data)
                                data = raw['data']
                                
                                event = {
                                    "symbol": data['s'],
                                    "price": float(data['p']),
                                    "qty": float(data['q']),
                                    "timestamp": data['T']
                                }
                                
                                payload = json.dumps(event).encode('utf-8')
                                
                                # --- ВИПРАВЛЕННЯ АРХІТЕКТУРИ ---
                                # Використовуємо .send() замість .send_and_wait(), 
                                # щоб не блокувати цикл читання з WebSocket
                                await producer.send(TOPIC, payload)
                                
            except Exception as e:
                logger.error(f"Connection lost: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
    finally:
        await producer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(ingest())
    except KeyboardInterrupt:
        pass
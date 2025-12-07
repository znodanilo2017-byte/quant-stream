import asyncio
import json
import os
import logging
from aiohttp import ClientSession
from kafka import KafkaProducer

# Config
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:19092')
TOPIC = 'market_data'
BINANCE_WS = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CryptoIngestor")

async def ingest():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    while True:
        try:
            async with ClientSession() as session:
                async with session.ws_connect(BINANCE_WS) as ws:
                    logger.info(f"🔌 Connected to Binance Firehose")
                    
                    async for msg in ws:
                        if msg.type == 1: # Text frame
                            raw = json.loads(msg.data)
                            data = raw['data']
                            
                            event = {
                                "symbol": data['s'],      # BTCUSDT
                                "price": float(data['p']),
                                "qty": float(data['q']),
                                "timestamp": data['T']    # Unix ms
                            }
                            producer.send(TOPIC, event)
                            
        except Exception as e:
            logger.error(f"Connection lost: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(ingest())
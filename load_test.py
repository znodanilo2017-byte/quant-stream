import asyncio
import websockets
import json
import time
import random

async def fake_binance_stream(websocket):
    print("🚀 Rust Ingestor connected! Starting load test...")
    messages_sent = 0
    start_time = time.time()
    
    try:
        while True:
            # Генеруємо фейковий JSON у форматі Binance
            fake_trade = {
                "data": {
                    "s": random.choice(["BTCUSDT", "ETHUSDT"]),
                    "p": str(round(random.uniform(50000, 70000), 2)),
                    "q": str(round(random.uniform(0.001, 2.0), 5)),
                    "T": int(time.time() * 1000)
                }
            }
            
            await websocket.send(json.dumps(fake_trade))
            messages_sent += 1
            
            # Логування швидкості кожні 10 тисяч повідомлень
            if messages_sent % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"🔥 Sent {messages_sent} messages. Current rate: {10000/elapsed:.2f} msg/sec")
                start_time = time.time() # Reset timer
                
            # Штучна затримка (закоментуй await asyncio.sleep(0), щоб отримати МАКСИМАЛЬНУ швидкість)
            # await asyncio.sleep(0.0001) 

    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed by client (Rust Ingestor died or stopped).")

async def main():
    # Запускаємо фейковий сервер на порту 8765
    async with websockets.serve(fake_binance_stream, "localhost", 8765):
        print("🟢 Fake Binance WS Server running on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
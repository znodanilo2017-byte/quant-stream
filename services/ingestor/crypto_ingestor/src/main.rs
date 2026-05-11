use std::env;
use std::time::Duration;
use dotenv::dotenv;
use log::{info, error, warn};
use futures_util::{StreamExt}; 

use rdkafka::config::ClientConfig;
use rdkafka::producer::{FutureProducer, FutureRecord};

use serde::{Deserialize, Serialize};
use serde_json;

use tokio::time::sleep;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};
use url::Url;

// Runtime configuration shared across the local demo and VM deployment path.
const TOPIC: &str = "market_data";

// Parse the Binance stream envelope and normalize it before publishing.
#[derive(Debug, Deserialize)]
struct BinanceStreamMsg {
    data: BinanceTradeData,
}

#[derive(Debug, Deserialize)]
struct BinanceTradeData {
    s: String, // Symbol
    p: String, // Price (string in JSON)
    q: String, // Quantity (string in JSON)

    #[serde(rename = "T")]
    t: i64,    // Timestamp
}

#[derive(Debug, Serialize)]
struct CleanTradeEvent {
    symbol: String,
    price: f64,
    qty: f64,

    timestamp: i64,
}

/// Creates and returns a Kafka `FutureProducer` using the provided broker address.
///
/// # Arguments
///
/// * `broker` - A string slice that holds the address of the Kafka broker.
///
/// # Returns
///
/// * `FutureProducer` - An asynchronous Kafka producer instance.
fn create_producer(broker: &str) -> Result<FutureProducer, rdkafka::error::KafkaError> {
    ClientConfig::new()
        .set("bootstrap.servers", broker)
        .set("message.timeout.ms", "5000")
        .create()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenv().ok();
    env_logger::init();
    
    let kafka_broker = env::var("KAFKA_BROKER")
        .unwrap_or_else(|_| "localhost:19092".to_string());

    let binance_ws_url = env::var("WS_URL")
        .unwrap_or_else(|_| "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/ethusdt@trade".to_string());

    let url = Url::parse(&binance_ws_url)
        .expect("Invalid WS_URL format");
    
    info!("Rust ingestor starting.");
    info!("Kafka broker: {}, topic: {}", kafka_broker, TOPIC);

    let producer = match create_producer(&kafka_broker) {
        Ok(p) => p,
        Err(e) => {
            error!("Failed to create Kafka producer: {}", e);
            std::process::exit(1);
        }
    };

    loop {
        info!("Connecting to Binance websocket.");
        
        match connect_async(url.clone()).await {
            Ok((ws_stream, _)) => {
                info!("Connected to Binance websocket.");
                let (_, mut read) = ws_stream.split();

                while let Some(msg) = read.next().await {
                    match msg {
                       Ok(Message::Text(text)) => {
                            // 1. Parse JSON
                            let parsed = match serde_json::from_str::<BinanceStreamMsg>(&text) {
                                Ok(v) => v,
                                Err(e) => {
                                    warn!("JSON parse failed: {}", e);
                                    continue;
                                }
                            };

                            let data = parsed.data;

                            // 2. Validate numeric fields
                            let price: f64 = match data.p.parse() {
                                Ok(v) => v,
                                Err(_) => {
                                    warn!("Invalid price: {}", data.p);
                                    continue;
                                }
                            };

                            let qty: f64 = match data.q.parse() {
                                Ok(v) => v,
                                Err(_) => {
                                    warn!("Invalid qty: {}", data.q);
                                    continue;
                                }
                            };

                            // 3. Transform
                            let event = CleanTradeEvent {
                                symbol: data.s,
                                price,
                                qty,
                                timestamp: data.t,
                            };

                            // 4. Send to Kafka
                            let payload = serde_json::to_string(&event).unwrap();

                            if let Err((e, _)) = producer
                                .send(
                                    FutureRecord::to(TOPIC)
                                        .payload(&payload)
                                        .key(&event.symbol),
                                    Duration::from_secs(0),
                                )
                                .await
                            {
                                error!("Kafka send failed: {}", e);
                            }
                        }
                        Ok(Message::Close(_)) => {
                            warn!("Server closed connection");
                            break;
                        }
                        Err(e) => {
                            error!("WS Error: {}", e);
                            break;
                        }
                        _ => {} // Ignore Pings/Pongs (handled automatically)
                    }
                }
            }
            Err(e) => {
                error!("Connection failed: {}", e);
            }
        }

        info!("Reconnecting in 5 seconds.");
        sleep(Duration::from_secs(5)).await;
    }
}

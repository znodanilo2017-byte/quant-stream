## ⚡ QuantStream: Real-Time Arbitrage Engine

QuantStream is a high-frequency, event-driven analytics pipeline built to detect statistical arbitrage opportunities in cryptocurrency markets (focused on BTC/ETH correlation spreads).

Unlike traditional polling bots, QuantStream uses a streaming-first architecture capable of ingesting 800+ trades per second with sub-second latency, deployed as a cloud-native distributed system on AWS.

⸻

## 🎥 Live Demo

▶️ 
<video controls src="Live_Demo.mov" title="Live Demo"></video>

⸻

## 🏗 System Architecture

QuantStream follows a “Smart Pipes, Dumb Endpoints” design to ensure high decoupling, fault tolerance, and scalability.

Component	Technology	Role
Ingestion Layer	Python (Asyncio / Aiohttp)	Connects to Binance WebSockets and normalizes raw trades into unified JSON events.
Message Broker	Redpanda (Kafka API)	High-performance C++ broker that buffers streams, absorbs backpressure, and prevents data loss.
Processing Engine	Python (Pandas / Deque)	Maintains rolling 60-second windows and computes real-time correlation spreads.
Storage Layer	TimescaleDB	Time-series optimized PostgreSQL extension supporting 1,000+ inserts/sec.
Visualization	Streamlit	Live dashboard for spreads, indicators, and system health.
Infrastructure	Terraform	Reproducible IaC provisioning EC2, networking, and security configuration.

![Architecture Diagram](Diagram.png)

⸻

## 🚀 Key Features
	•	Real-Time Anomaly Detection: Flags BTC/ETH correlation divergence >0.5% within 60 seconds.
	•	Zero-Downtime Reliability: If TimescaleDB is unavailable, the ingest layer continues streaming with Redpanda buffering.
	•	Instant Alerts: Sends Telegram notifications when a trading signal or anomaly is detected.
	•	Memory-Efficient: Tuned for smaller AWS instances (c7i, t3.medium) using Linux swap and Docker resource limits.

⸻

## 🛠 Installation & Deployment

Prerequisites
	•	Docker & Docker Compose
	•	Terraform (for AWS deployment)
	•	AWS CLI configured with active credentials

⸻

## 1. Local Setup


# Clone the repository
git clone https://github.com/yourusername/quant-platform.git
cd quant-platform

# Configure secrets
cp .env.example .env
# Add TELEGRAM_TOKEN and CHAT_ID to .env


⸻

## 2. Launch the Stack

docker-compose up -d --build


⸻

## 3. Initialize the Database

The database schema is automatically provisioned on the first launch via `init.sql`.

To reset the data and re-initialize:
```bash
docker-compose down -v
docker-compose up -d

⸻

## ☁️ Cloud Deployment (AWS)

Terraform automates provisioning of a reproducible environment.

cd infrastructure/terraform

# Initialize + preview
terraform init
terraform plan

# Deploy to eu-central-1
terraform apply

EC2 instances automatically install Docker and Git via user_data scripts.

⸻

## 🔮 Future Roadmap (Defense Tech Pivot)

Although optimized for financial streaming, the architecture is domain-agnostic. Upcoming iterations will adapt the pipeline for UAV telemetry and anomaly detection:
	•	Protocol Swap: Replace Binance WebSocket with MAVLink.
	•	Logic Update: Substitute arbitrage signals with geofence, battery, and sensor anomaly analytics.
	•	Hardware Integration: Support for Pixhawk/ArduPilot and hardware-in-the-loop simulation.

⸻

## 👤 Author

Danylo Yuzefchyk
Systems Engineer & MLOps Specialist
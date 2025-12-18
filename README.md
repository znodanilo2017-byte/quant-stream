## ⚡ QuantStream: Real-Time Arbitrage Engine

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Tech Stack](https://img.shields.io/badge/stack-Python_|_Redpanda_|_TimescaleDB-blue)
![Infrastructure](https://img.shields.io/badge/infra-Terraform_|_AWS_EC2-orange)

**QuantStream** is a high-frequency event-driven pipeline designed to detect statistical arbitrage opportunities in cryptocurrency markets (BTC/ETH correlations).

Unlike standard API-polling bots, this engine utilizes a **streaming architecture** capable of ingesting and processing 800+ trade events per second with sub-second latency. It is deployed as a cloud-native distributed system on AWS.

⸻

## 🎥 Live Demo

▶️ 
<video controls src="Live_Demo.mov" title="Live Demo"></video>

⸻

The system is built on the **"Smart Pipes, Dumb Endpoints"** philosophy, ensuring decoupling and fault tolerance.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Ingestion Layer** | **Python (Asyncio/Aiohttp)** | Connects to Binance WebSockets. Normalizes raw trade streams into standard JSON events. |
| **Message Broker** | **Redpanda (Kafka API)** | High-performance C++ streaming platform. Buffers data to handle backpressure and prevent data loss. |
| **Processing Engine** | **Python (Pandas/Deque)** | Consumes streams. Maintains in-memory rolling windows (60s). Calculates correlation spreads in real-time. |
| **Storage Layer** | **TimescaleDB** | PostgreSQL extension optimized for high-velocity time-series data. Handles 1,000+ inserts/sec. |
| **Visualization** | **Streamlit** | Live operational dashboard for visualizing spreads and system health. |
| **Infrastructure** | **Terraform** | Fully reproducible Infrastructure as Code (IaC). Provisions AWS EC2, Security Groups, and Networking. |

---

![Architecture Diagram](Diagram.png)

⸻

## 📂 Project Structure

```bash
quant-platform/
├── dashboard/           # Streamlit Visualization App
├── infrastructure/      # Terraform Cloud Configuration
│   └── terraform/       # AWS Provisioning Scripts
├── services/
│   ├── ingestor/        # WebSocket Connector (Binance -> Kafka)
│   └── processor/       # Quant Logic (Kafka -> DB + Telegram)
├── docker-compose.yml   # Container Orchestration
└── .env                 # API Secrets (Not committed)
```

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
```
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
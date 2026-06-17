# Objective 3 — Performance Optimisation, Scalability Validation & Comparative Benchmarking

**Research**: Blockchain-Enabled Cloud Anomaly Detection System  
**Scholar**: Gaddam Srikanth Reddy (24EG305A08)  
**Institution**: Anurag University, Hyderabad  

---

## Overview

This module implements the third research objective: holistic performance optimisation of the integrated CNN-LSTM-Transformer anomaly detection + Hyperledger Fabric blockchain logging framework. It includes:

- **Selective Logging & Event Prioritisation Engine** — Multi-criterion priority scoring (confidence, severity, asset value, recency)
- **Batch Processing with Merkle Tree Aggregation** — Groups events into Merkle trees, submits only root hash on-chain
- **Asynchronous Kafka-based Logging Pipeline** — Decouples detection latency from blockchain commit latency
- **Scalability Load Testing** — Simulates 100–10,000 cloud instances, 100–10,000 events/sec via Locust
- **Comparative Benchmarking** — Benchmarks against ML-only, blockchain-only, and hybrid baselines
- **Prometheus + Grafana Observability** — Real-time metrics collection and dashboarding

---

## Quick Start

### Requirements
```bash
python --version        # Python 3.14.5
docker --version        # Docker 24+
docker compose version  # Docker Compose v2
```

### Setup
```bash
git clone https://github.com/verlopat/005-obj-3.git
cd 005-obj-3

# Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### Run (all modules in sequence)
```bash
python3 Main.py
```

### Run with Docker (Kafka + Prometheus + Grafana)
```bash
docker compose up -d
python3 Main.py
```

---

## Project Structure

```
005-obj-3/
├── Main.py                          # Orchestrator — runs all modules end-to-end
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── src/
│   ├── config.py                    # Centralised configuration loader
│   ├── logger.py                    # Structured logging setup
│   ├── event_schema.py              # Shared SecurityEvent dataclass
│   ├── priority_engine.py           # Selective logging + priority scoring
│   ├── merkle_batcher.py            # Merkle tree batch aggregation
│   ├── kafka_pipeline.py            # Async Kafka producer/consumer pipeline
│   ├── blockchain_client.py         # Hyperledger Fabric stub / mock client
│   ├── load_generator.py            # Synthetic cloud event load generator
│   ├── scalability_tester.py        # Scalability test harness (100–10k instances)
│   ├── benchmark.py                 # Comparative benchmarking against baselines
│   └── metrics_exporter.py          # Prometheus metrics exporter
├── tests/
│   ├── test_priority_engine.py
│   ├── test_merkle_batcher.py
│   └── test_benchmark.py
└── results/
    └── .gitkeep                     # Auto-populated with CSV and JSON reports
```

---

## Success Metrics (KPIs)

| # | Metric | Target |
|---|--------|--------|
| 1 | End-to-End Detection+Logging Latency | ≤ 800 ms (99th percentile) |
| 2 | Framework Scalability | Linear throughput up to 10,000 instances |
| 3 | On-Chain Storage Reduction | ≥ 80% vs full logging |
| 4 | CPU Overhead (vs detection-only) | ≤ 15% additional |
| 5 | F1 + Latency vs baselines | Pareto-superior |
| 6 | 24hr Stress Test Stability | Zero event loss, zero crashes |

---

## Technology Stack

| Component | Tool |
|-----------|------|
| Message Queue | Apache Kafka (via kafka-python) |
| Merkle Aggregation | pymerkle |
| Blockchain Client | Hyperledger Fabric SDK (mock for simulation) |
| Load Testing | Locust |
| Observability | Prometheus + Grafana |
| Orchestration | Docker Compose + Kubernetes HPA (config included) |
| ML Baselines | scikit-learn (Random Forest, SVM, LSTM stub) |

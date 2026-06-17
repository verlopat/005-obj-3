"""Centralised configuration loader — reads from .env via python-dotenv."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_HIGH: str        = os.getenv("KAFKA_TOPIC_HIGH", "sec_events_high")
    KAFKA_TOPIC_MEDIUM: str      = os.getenv("KAFKA_TOPIC_MEDIUM", "sec_events_medium")
    KAFKA_TOPIC_LOW: str         = os.getenv("KAFKA_TOPIC_LOW", "sec_events_low")

    # Blockchain
    BLOCKCHAIN_MOCK: bool        = os.getenv("BLOCKCHAIN_MOCK", "true").lower() == "true"
    FABRIC_PEER_ENDPOINT: str    = os.getenv("FABRIC_PEER_ENDPOINT", "localhost:7051")
    FABRIC_CHANNEL: str          = os.getenv("FABRIC_CHANNEL", "security-channel")
    FABRIC_CHAINCODE: str        = os.getenv("FABRIC_CHAINCODE", "seclogger")

    # Priority Engine weights
    W_CONFIDENCE: float          = float(os.getenv("W_CONFIDENCE", "0.35"))
    W_SEVERITY: float            = float(os.getenv("W_SEVERITY", "0.35"))
    W_ASSET_VALUE: float         = float(os.getenv("W_ASSET_VALUE", "0.20"))
    W_RECENCY: float             = float(os.getenv("W_RECENCY", "0.10"))
    THRESHOLD_HIGH: float        = float(os.getenv("THRESHOLD_HIGH", "0.75"))
    THRESHOLD_MEDIUM: float      = float(os.getenv("THRESHOLD_MEDIUM", "0.45"))

    # Merkle Batcher
    BATCH_WINDOW_MS: int         = int(os.getenv("BATCH_WINDOW_MS", "300"))
    BATCH_MAX_SIZE: int          = int(os.getenv("BATCH_MAX_SIZE", "100"))

    # Load Generator
    LOAD_INSTANCES_START: int    = int(os.getenv("LOAD_INSTANCES_START", "100"))
    LOAD_INSTANCES_END: int      = int(os.getenv("LOAD_INSTANCES_END", "10000"))
    LOAD_EVENTS_PER_SEC: int     = int(os.getenv("LOAD_EVENTS_PER_SEC", "1000"))
    ANOMALY_RATIO: float         = float(os.getenv("ANOMALY_RATIO", "0.05"))

    # Prometheus
    PROMETHEUS_PORT: int         = int(os.getenv("PROMETHEUS_PORT", "8000"))

    # General
    LOG_LEVEL: str               = os.getenv("LOG_LEVEL", "INFO")
    RESULTS_DIR: str             = os.getenv("RESULTS_DIR", "results")

config = Config()

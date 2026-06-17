"""Prometheus Metrics Exporter.

Exposes key framework metrics for Grafana dashboarding.
Starts an HTTP server on PROMETHEUS_PORT.
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# ── Metrics ────────────────────────────────────────────────────────────────────
events_total = Counter(
    "obj3_events_total",
    "Total security events processed",
    ["tier"]
)

blockchain_tx_total = Counter(
    "obj3_blockchain_tx_total",
    "Total blockchain transactions committed"
)

detection_latency = Histogram(
    "obj3_detection_latency_ms",
    "Detection pipeline latency in milliseconds",
    buckets=[10, 25, 50, 100, 200, 400, 800, 1600]
)

blockchain_latency = Histogram(
    "obj3_blockchain_commit_latency_ms",
    "Blockchain commit latency in milliseconds",
    buckets=[10, 50, 100, 250, 500, 1000, 2000]
)

storage_reduction_gauge = Gauge(
    "obj3_storage_reduction_pct",
    "Percentage of on-chain storage saved vs full logging"
)

active_instances_gauge = Gauge(
    "obj3_active_instances",
    "Number of actively monitored cloud instances"
)


def start_metrics_server() -> None:
    try:
        start_http_server(config.PROMETHEUS_PORT)
        logger.info(f"[Metrics] Prometheus exporter running on :{config.PROMETHEUS_PORT}")
    except OSError as e:
        logger.warning(f"[Metrics] Could not start Prometheus server: {e}")


def record_event(tier: str) -> None:
    events_total.labels(tier=tier).inc()


def record_blockchain_tx(latency_ms: float) -> None:
    blockchain_tx_total.inc()
    blockchain_latency.observe(latency_ms)


def record_detection_latency(latency_ms: float) -> None:
    detection_latency.observe(latency_ms)


def update_storage_reduction(pct: float) -> None:
    storage_reduction_gauge.set(pct)


def update_active_instances(n: int) -> None:
    active_instances_gauge.set(n)

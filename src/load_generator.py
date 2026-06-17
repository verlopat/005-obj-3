"""Synthetic Cloud Event Load Generator.

Simulates cloud telemetry from N instances at a given events/sec rate.
Anomaly ratio controls the fraction of genuinely malicious events.
"""
import random
import time
import hashlib
import json
from src.event_schema import SecurityEvent, SEVERITY_MAP, ASSET_VALUE_MAP
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

ATTACK_CLASSES = ["DDoS", "insider", "privilege_esc", "port_scan"]
SEVERITY_LEVELS = list(SEVERITY_MAP.keys())
ASSET_IDS       = list(ASSET_VALUE_MAP.keys())


def _make_raw_payload(asset_id: str, class_label: str) -> dict:
    return {
        "src_ip":       f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "dst_port":     random.choice([22, 80, 443, 3306, 5432, 8080]),
        "bytes_in":     random.randint(64, 65535),
        "bytes_out":    random.randint(64, 65535),
        "duration_ms":  random.randint(1, 5000),
        "protocol":     random.choice(["TCP", "UDP", "ICMP"]),
        "asset_id":     asset_id,
        "class_label":  class_label,
    }


def generate_event(anomaly: bool = False, asset_id: str | None = None) -> SecurityEvent:
    """Generate a single synthetic SecurityEvent."""
    asset      = asset_id or random.choice(ASSET_IDS)
    label      = random.choice(ATTACK_CLASSES) if anomaly else "normal"
    confidence = round(random.uniform(0.70, 0.99), 4) if anomaly else round(random.uniform(0.01, 0.30), 4)
    severity   = random.choice(["critical", "high"]) if anomaly else random.choice(["low", "info"])

    event = SecurityEvent(
        asset_id     = asset,
        class_label  = label,
        confidence   = confidence,
        severity     = severity,
        model_version= "v1.0.0",
    )
    raw = _make_raw_payload(asset, label)
    event.compute_payload_hash(raw)
    event.storage_pointer = f"ipfs://Qm{hashlib.md5(event.payload_hash.encode()).hexdigest()[:40]}"
    return event


def burst(n_events: int, anomaly_ratio: float = config.ANOMALY_RATIO) -> list[SecurityEvent]:
    """Generate a burst of n_events with the given anomaly ratio."""
    events = []
    for _ in range(n_events):
        is_anomaly = random.random() < anomaly_ratio
        events.append(generate_event(anomaly=is_anomaly))
    return events


def stream(n_instances: int, events_per_sec: int, duration_sec: int = 5) -> list[SecurityEvent]:
    """Generate a stream simulating n_instances at events_per_sec for duration_sec."""
    total_events = events_per_sec * duration_sec
    logger.info(f"[LoadGen] Generating {total_events} events | instances={n_instances} | rate={events_per_sec}/s")
    return burst(total_events, config.ANOMALY_RATIO)

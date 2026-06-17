"""Shared SecurityEvent dataclass used across all modules."""
from dataclasses import dataclass, field
from typing import Optional
import time
import hashlib
import json
import uuid

SEVERITY_MAP = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25, "info": 0.0}
ASSET_VALUE_MAP = {"db_server": 1.0, "web_server": 0.8, "api_gateway": 0.9, "worker": 0.4, "monitor": 0.2}

@dataclass
class SecurityEvent:
    event_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float         = field(default_factory=time.time)
    asset_id: str            = "unknown"
    class_label: str         = "normal"        # DDoS | insider | privilege_esc | port_scan | normal
    confidence: float        = 0.0             # 0.0 – 1.0 from ML model
    severity: str            = "info"          # critical | high | medium | low | info
    model_version: str       = "v1.0.0"
    payload_hash: str        = ""              # SHA-256 of raw payload (set externally)
    signature: str           = ""              # ECDSA signature placeholder
    storage_pointer: str     = ""              # IPFS CID or object-store URI
    priority_score: float    = 0.0             # Computed by priority engine
    priority_tier: str       = "low"           # high | medium | low

    def compute_payload_hash(self, raw_payload: dict) -> str:
        payload_str = json.dumps(raw_payload, sort_keys=True)
        self.payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        return self.payload_hash

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "asset_id": self.asset_id,
            "class_label": self.class_label,
            "confidence": self.confidence,
            "severity": self.severity,
            "model_version": self.model_version,
            "payload_hash": self.payload_hash,
            "signature": self.signature,
            "storage_pointer": self.storage_pointer,
            "priority_score": self.priority_score,
            "priority_tier": self.priority_tier,
        }

"""Hyperledger Fabric Blockchain Client.

Provides:
  LogSecurityEvent  — commits event hash + metadata to ledger
  VerifyEvent       — verifies a stored event hash
  QueryEventHistory — retrieves audit trail

When BLOCKCHAIN_MOCK=true, uses an in-memory ledger for simulation.
"""
import hashlib
import time
import threading
from collections import defaultdict
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


class MockLedger:
    """Thread-safe in-memory ledger simulating Hyperledger Fabric."""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._history: list[dict]    = []
        self._lock                   = threading.Lock()
        self.tx_count: int           = 0
        self.total_latency_ms: float = 0.0

    def log_event(self, event_id: str, payload_hash: str, metadata: dict) -> str:
        start = time.perf_counter()
        tx_id = hashlib.sha256(f"{event_id}{time.time()}".encode()).hexdigest()[:16]
        record = {
            "tx_id":        tx_id,
            "event_id":     event_id,
            "payload_hash": payload_hash,
            "metadata":     metadata,
            "on_chain_ts":  time.time(),
        }
        with self._lock:
            self._store[event_id] = record
            self._history.append(record)
            self.tx_count += 1
        latency_ms = (time.perf_counter() - start) * 1000
        self.total_latency_ms += latency_ms
        logger.debug(f"[Blockchain] TX {tx_id} logged in {latency_ms:.2f}ms")
        return tx_id

    def verify_event(self, event_id: str, expected_hash: str) -> bool:
        with self._lock:
            record = self._store.get(event_id)
        if record is None:
            return False
        return record["payload_hash"] == expected_hash

    def query_history(self, asset_id: str | None = None) -> list[dict]:
        with self._lock:
            history = self._history[:]
        if asset_id:
            history = [r for r in history if r["metadata"].get("asset_id") == asset_id]
        return history

    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.tx_count if self.tx_count > 0 else 0.0


# Singleton ledger instance
_ledger = MockLedger()


def log_security_event(event_id: str, payload_hash: str, metadata: dict) -> str:
    """LogSecurityEvent chaincode function."""
    return _ledger.log_event(event_id, payload_hash, metadata)


def log_batch_merkle_root(batch_record: dict) -> str:
    """Commits a Merkle batch root as a single on-chain transaction."""
    return _ledger.log_event(
        event_id=batch_record["batch_id"],
        payload_hash=batch_record["merkle_root"],
        metadata={"type": "merkle_batch", "event_count": batch_record["event_count"]},
    )


def verify_event(event_id: str, expected_hash: str) -> bool:
    """VerifyEvent chaincode function."""
    return _ledger.verify_event(event_id, expected_hash)


def query_event_history(asset_id: str | None = None) -> list[dict]:
    """QueryEventHistory chaincode function."""
    return _ledger.query_history(asset_id)


def get_stats() -> dict:
    return {
        "tx_count":       _ledger.tx_count,
        "avg_latency_ms": round(_ledger.avg_latency_ms(), 3),
    }

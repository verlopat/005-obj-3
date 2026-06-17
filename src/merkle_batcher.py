"""Batch Processing with Merkle Tree Aggregation.

Groups medium-priority events into configurable time windows,
builds a Merkle tree over their payload hashes, and returns
only the Merkle root for on-chain commitment.
"""
import hashlib
import time
from src.event_schema import SecurityEvent
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def build_merkle_tree(hashes: list[str]) -> dict:
    """Build a binary Merkle tree and return root + tree layers."""
    if not hashes:
        return {"root": "", "layers": []}

    layer = hashes[:]
    layers = [layer[:]]

    while len(layer) > 1:
        if len(layer) % 2 == 1:          # duplicate last leaf if odd count
            layer.append(layer[-1])
        next_layer = []
        for i in range(0, len(layer), 2):
            combined = _sha256(layer[i] + layer[i + 1])
            next_layer.append(combined)
        layer = next_layer
        layers.append(layer[:])

    return {"root": layer[0], "layers": layers, "leaf_count": len(hashes)}


def verify_membership(leaf_hash: str, merkle_root: str, layers: list[list[str]]) -> bool:
    """Verify a single leaf hash belongs to the Merkle tree."""
    if not layers:
        return False
    current = leaf_hash
    for layer in layers[:-1]:
        idx = layer.index(current) if current in layer else -1
        if idx == -1:
            return False
        if idx % 2 == 0:
            sibling = layer[idx + 1] if idx + 1 < len(layer) else current
        else:
            sibling = layer[idx - 1]
        current = _sha256(current + sibling) if idx % 2 == 0 else _sha256(sibling + current)
    return current == merkle_root


class MerkleBatcher:
    """Accumulates medium-priority events, flushes batches on window or size trigger."""

    def __init__(self):
        self._buffer: list[SecurityEvent] = []
        self._window_start: float = time.time()
        self.batches_committed: int = 0
        self.events_batched: int = 0

    def add(self, event: SecurityEvent) -> None:
        self._buffer.append(event)

    def should_flush(self) -> bool:
        elapsed_ms = (time.time() - self._window_start) * 1000
        return (
            len(self._buffer) >= config.BATCH_MAX_SIZE
            or elapsed_ms >= config.BATCH_WINDOW_MS
        )

    def flush(self) -> dict | None:
        """Build Merkle tree from buffered events, reset buffer, return batch record."""
        if not self._buffer:
            return None

        hashes = [e.payload_hash or e.event_id for e in self._buffer]
        tree   = build_merkle_tree(hashes)

        batch_record = {
            "batch_id":    _sha256(str(time.time())),
            "merkle_root": tree["root"],
            "event_count": tree["leaf_count"],
            "timestamp":   time.time(),
            "layers":      tree["layers"],
        }

        self.batches_committed += 1
        self.events_batched    += len(self._buffer)
        logger.info(
            f"[MerkleBatcher] Batch #{self.batches_committed} | "
            f"{tree['leaf_count']} events | root={tree['root'][:16]}..."
        )

        self._buffer = []
        self._window_start = time.time()
        return batch_record

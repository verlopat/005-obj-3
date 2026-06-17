"""Selective Logging & Event Prioritisation Engine.

Priority Score = W_confidence * confidence
               + W_severity   * severity_norm
               + W_asset      * asset_value_norm
               + W_recency    * recency_norm

Tiers:
  score >= THRESHOLD_HIGH   -> HIGH   (immediate on-chain)
  score >= THRESHOLD_MEDIUM -> MEDIUM (Merkle batch queue)
  score <  THRESHOLD_MEDIUM -> LOW    (off-chain retention only)
"""
import time
from collections import defaultdict
from src.event_schema import SecurityEvent, SEVERITY_MAP, ASSET_VALUE_MAP
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# Track last event time per asset for recency scoring
_last_event_time: dict[str, float] = defaultdict(float)
RECENCY_DECAY_SECONDS = 60.0   # event within last 60s scores 1.0, decays linearly


def compute_recency_score(asset_id: str, now: float) -> float:
    last = _last_event_time[asset_id]
    if last == 0.0:
        return 0.0
    elapsed = now - last
    return max(0.0, 1.0 - elapsed / RECENCY_DECAY_SECONDS)


def score_event(event: SecurityEvent) -> SecurityEvent:
    """Compute priority_score and assign priority_tier to the event in-place."""
    now = time.time()

    severity_norm  = SEVERITY_MAP.get(event.severity.lower(), 0.0)
    asset_norm     = ASSET_VALUE_MAP.get(event.asset_id.lower(), 0.5)
    recency_norm   = compute_recency_score(event.asset_id, now)

    score = (
        config.W_CONFIDENCE * event.confidence
        + config.W_SEVERITY   * severity_norm
        + config.W_ASSET_VALUE * asset_norm
        + config.W_RECENCY     * recency_norm
    )

    event.priority_score = round(score, 4)

    if score >= config.THRESHOLD_HIGH:
        event.priority_tier = "high"
    elif score >= config.THRESHOLD_MEDIUM:
        event.priority_tier = "medium"
    else:
        event.priority_tier = "low"

    _last_event_time[event.asset_id] = now
    logger.debug(f"[PriorityEngine] {event.event_id[:8]} | score={score:.4f} | tier={event.priority_tier}")
    return event


def route_events(events: list[SecurityEvent]) -> tuple[list, list, list]:
    """Score and split events into HIGH, MEDIUM, LOW tiers."""
    high, medium, low = [], [], []
    for e in events:
        score_event(e)
        if e.priority_tier == "high":
            high.append(e)
        elif e.priority_tier == "medium":
            medium.append(e)
        else:
            low.append(e)
    logger.info(f"[PriorityEngine] Routed {len(events)} events -> HIGH={len(high)} MEDIUM={len(medium)} LOW={len(low)}")
    return high, medium, low

"""Asynchronous Kafka-based Logging Pipeline.

Producer: writes SecurityEvent JSON to the appropriate Kafka topic by tier.
Consumer: reads from topics and feeds events to the blockchain client.

Kafka is optional — falls back to an in-process queue if Kafka is unavailable
(BLOCKCHAIN_MOCK=true handles this gracefully for simulation runs).
"""
import json
import queue
import threading
import time
from src.event_schema import SecurityEvent
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# In-process fallback queues (used when Kafka is not running)
_fallback_queues: dict[str, queue.Queue] = {
    config.KAFKA_TOPIC_HIGH:   queue.Queue(),
    config.KAFKA_TOPIC_MEDIUM: queue.Queue(),
    config.KAFKA_TOPIC_LOW:    queue.Queue(),
}

_kafka_available = False

try:
    from kafka import KafkaProducer as _KafkaProducer
    from kafka import KafkaConsumer as _KafkaConsumer
    _kafka_available = True
except Exception:
    pass


def _topic_for_tier(tier: str) -> str:
    return {
        "high":   config.KAFKA_TOPIC_HIGH,
        "medium": config.KAFKA_TOPIC_MEDIUM,
        "low":    config.KAFKA_TOPIC_LOW,
    }.get(tier, config.KAFKA_TOPIC_LOW)


class EventProducer:
    """Sends SecurityEvents to Kafka (or fallback queue) by priority tier."""

    def __init__(self):
        self._producer = None
        if _kafka_available:
            try:
                self._producer = _KafkaProducer(
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    retries=3,
                )
                logger.info("[EventProducer] Kafka producer connected.")
            except Exception as exc:
                logger.warning(f"[EventProducer] Kafka unavailable ({exc}), using fallback queue.")

    def send(self, event: SecurityEvent) -> None:
        topic = _topic_for_tier(event.priority_tier)
        payload = event.to_dict()
        if self._producer:
            self._producer.send(topic, value=payload)
        else:
            _fallback_queues[topic].put(payload)
        logger.debug(f"[EventProducer] Sent event {event.event_id[:8]} -> {topic}")

    def flush(self) -> None:
        if self._producer:
            self._producer.flush()


class EventConsumer(threading.Thread):
    """Background thread consuming events and dispatching to a callback."""

    def __init__(self, topics: list[str], callback, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.topics     = topics
        self.callback   = callback
        self.stop_event = stop_event
        self.consumed   = 0

    def run(self) -> None:
        consumer = None
        if _kafka_available:
            try:
                consumer = _KafkaConsumer(
                    *self.topics,
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    consumer_timeout_ms=500,
                    auto_offset_reset="earliest",
                    group_id="obj3-consumer-group",
                )
            except Exception:
                consumer = None

        while not self.stop_event.is_set():
            if consumer:
                for msg in consumer:
                    self.callback(msg.value)
                    self.consumed += 1
                    if self.stop_event.is_set():
                        break
            else:
                for topic in self.topics:
                    try:
                        item = _fallback_queues[topic].get_nowait()
                        self.callback(item)
                        self.consumed += 1
                    except queue.Empty:
                        pass
                time.sleep(0.01)

        logger.info(f"[EventConsumer] Stopped. Total consumed: {self.consumed}")

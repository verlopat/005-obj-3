"""Unit tests for the priority scoring engine."""
import pytest
from src.event_schema import SecurityEvent
from src.priority_engine import score_event


def _make_event(confidence: float, severity: str, asset_id: str) -> SecurityEvent:
    e = SecurityEvent(confidence=confidence, severity=severity, asset_id=asset_id)
    e.compute_payload_hash({"dummy": "payload"})
    return e


def test_high_confidence_critical_is_high_tier():
    e = _make_event(0.95, "critical", "db_server")
    score_event(e)
    assert e.priority_tier == "high"
    assert e.priority_score >= 0.75


def test_low_confidence_info_is_low_tier():
    e = _make_event(0.05, "info", "monitor")
    score_event(e)
    assert e.priority_tier == "low"


def test_medium_confidence_medium_severity():
    e = _make_event(0.55, "medium", "worker")
    score_event(e)
    assert e.priority_tier in ["medium", "high"]


def test_score_sum_bounded():
    e = _make_event(1.0, "critical", "api_gateway")
    score_event(e)
    assert 0.0 <= e.priority_score <= 1.0

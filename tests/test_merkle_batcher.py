"""Unit tests for Merkle batcher and tree construction."""
import pytest
from src.merkle_batcher import build_merkle_tree, verify_membership, MerkleBatcher
from src.event_schema import SecurityEvent


def test_merkle_root_deterministic():
    hashes = ["abc", "def", "ghi", "jkl"]
    t1 = build_merkle_tree(hashes)
    t2 = build_merkle_tree(hashes)
    assert t1["root"] == t2["root"]


def test_merkle_single_leaf():
    t = build_merkle_tree(["only_leaf"])
    assert t["root"] == "only_leaf"
    assert t["leaf_count"] == 1


def test_merkle_empty():
    t = build_merkle_tree([])
    assert t["root"] == ""


def test_membership_verification():
    hashes = ["aaa", "bbb", "ccc", "ddd"]
    t = build_merkle_tree(hashes)
    assert verify_membership("aaa", t["root"], t["layers"])


def test_batcher_flush_returns_batch():
    batcher = MerkleBatcher()
    for i in range(5):
        e = SecurityEvent()
        e.payload_hash = f"hash_{i}"
        batcher.add(e)
    batch = batcher.flush()
    assert batch is not None
    assert batch["event_count"] == 5
    assert len(batch["merkle_root"]) == 64  # SHA-256 hex length

"""Scalability Test Harness.

Progressively scales monitored instances from LOAD_INSTANCES_START to LOAD_INSTANCES_END,
records end-to-end latency, throughput, blockchain TPS, CPU and memory overhead.
"""
import time
import os
import json
import csv
import psutil
from src.load_generator import stream
from src.priority_engine import route_events
from src.merkle_batcher import MerkleBatcher
from src import blockchain_client as bc
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

SCALE_STEPS = [100, 500, 1_000, 2_000, 5_000, 10_000]


def _run_scale_step(n_instances: int, events_per_sec: int = 1_000) -> dict:
    batcher = MerkleBatcher()
    proc    = psutil.Process(os.getpid())

    cpu_before = proc.cpu_percent(interval=None)
    mem_before = proc.memory_info().rss / 1024 / 1024  # MB
    t_start    = time.perf_counter()

    events = stream(n_instances, events_per_sec, duration_sec=2)
    high, medium, low = route_events(events)

    # HIGH — immediate on-chain
    for e in high:
        bc.log_security_event(e.event_id, e.payload_hash, e.to_dict())

    # MEDIUM — Merkle batch
    for e in medium:
        batcher.add(e)
        if batcher.should_flush():
            batch = batcher.flush()
            if batch:
                bc.log_batch_merkle_root(batch)
    # flush remaining
    remaining = batcher.flush()
    if remaining:
        bc.log_batch_merkle_root(remaining)

    t_end      = time.perf_counter()
    cpu_after  = proc.cpu_percent(interval=None)
    mem_after  = proc.memory_info().rss / 1024 / 1024

    elapsed_ms     = (t_end - t_start) * 1000
    total_events   = len(events)
    on_chain_txs   = len(high) + batcher.batches_committed
    storage_saved  = 1 - (on_chain_txs / max(total_events, 1))
    blockchain_tps = bc.get_stats()["tx_count"] / max((t_end - t_start), 0.001)

    result = {
        "instances":          n_instances,
        "total_events":       total_events,
        "high_events":        len(high),
        "medium_events":      len(medium),
        "low_events":         len(low),
        "on_chain_txs":       on_chain_txs,
        "storage_reduction": round(storage_saved * 100, 2),
        "elapsed_ms":         round(elapsed_ms, 2),
        "throughput_eps":     round(total_events / max(elapsed_ms / 1000, 0.001), 1),
        "blockchain_tps":     round(blockchain_tps, 1),
        "avg_bc_latency_ms":  round(bc.get_stats()["avg_latency_ms"], 3),
        "cpu_overhead_pct":   round(cpu_after - cpu_before, 2),
        "mem_mb":             round(mem_after, 2),
    }
    logger.info(
        f"[ScalabilityTest] instances={n_instances:>6} | "
        f"events={total_events:>6} | "
        f"storage_saved={result['storage_reduction']}% | "
        f"latency={elapsed_ms:.1f}ms | "
        f"bc_tps={result['blockchain_tps']}"
    )
    return result


def run_scalability_tests() -> list[dict]:
    logger.info("[ScalabilityTest] Starting scalability sweep ...")
    results = []
    for n in SCALE_STEPS:
        if n < config.LOAD_INSTANCES_START or n > config.LOAD_INSTANCES_END:
            continue
        results.append(_run_scale_step(n, config.LOAD_EVENTS_PER_SEC))

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    csv_path  = os.path.join(config.RESULTS_DIR, "scalability_results.csv")
    json_path = os.path.join(config.RESULTS_DIR, "scalability_results.json")

    if results:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)

    logger.info(f"[ScalabilityTest] Results saved -> {csv_path}")
    return results

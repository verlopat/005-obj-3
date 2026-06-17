"""Main.py — Objective 3 Orchestrator

Runs all components end-to-end in sequence:
  1. Start Prometheus metrics server
  2. Generate synthetic load (small demo burst)
  3. Priority scoring and routing
  4. Merkle batching for MEDIUM events
  5. Blockchain commit (mock) for HIGH and MEDIUM batches
  6. Run scalability sweep (100 → 10,000 instances)
  7. Run comparative benchmark vs baselines
  8. Print summary report
"""
import os
import time
import json
from rich.console import Console
from rich.table import Table
from rich import box

from src.config import config
from src.logger import get_logger
from src.metrics_exporter import (
    start_metrics_server, record_event,
    update_storage_reduction, update_active_instances
)
from src.load_generator import burst
from src.priority_engine import route_events
from src.merkle_batcher import MerkleBatcher
from src import blockchain_client as bc
from src.scalability_tester import run_scalability_tests
from src.benchmark import run_benchmark

logger  = get_logger("Main")
console = Console()


def run_demo_pipeline(n_events: int = 500) -> dict:
    """Quick demo: generate events, score, batch, commit."""
    console.rule("[bold cyan]Demo Pipeline")
    events  = burst(n_events)
    high, medium, low = route_events(events)

    for e in high:
        record_event("high")
        bc.log_security_event(e.event_id, e.payload_hash, e.to_dict())

    batcher = MerkleBatcher()
    for e in medium:
        record_event("medium")
        batcher.add(e)
        if batcher.should_flush():
            batch = batcher.flush()
            if batch:
                bc.log_batch_merkle_root(batch)
    remaining = batcher.flush()
    if remaining:
        bc.log_batch_merkle_root(remaining)

    for e in low:
        record_event("low")

    on_chain = len(high) + batcher.batches_committed
    reduction = round((1 - on_chain / max(n_events, 1)) * 100, 1)
    update_storage_reduction(reduction)
    update_active_instances(n_events)

    stats = bc.get_stats()
    return {
        "total_events":       n_events,
        "high":               len(high),
        "medium":             len(medium),
        "low":                len(low),
        "on_chain_txs":       on_chain,
        "storage_reduction":  f"{reduction}%",
        "blockchain_tx_count": stats["tx_count"],
        "avg_bc_latency_ms":  stats["avg_latency_ms"],
    }


def print_summary(demo: dict, scale_results: list, bench_results: list) -> None:
    """Rich-formatted summary table."""
    console.rule("[bold green]Objective 3 — Summary Report")

    # Demo pipeline
    t = Table(title="Demo Pipeline Results", box=box.ROUNDED)
    for k, v in demo.items():
        t.add_column(k, style="cyan")
    t.add_row(*[str(v) for v in demo.values()])
    console.print(t)

    # Scalability
    if scale_results:
        st = Table(title="Scalability Sweep", box=box.ROUNDED)
        for k in scale_results[0].keys():
            st.add_column(k, style="yellow")
        for row in scale_results:
            st.add_row(*[str(v) for v in row.values()])
        console.print(st)

    # Benchmark
    if bench_results:
        bt = Table(title="Comparative Benchmark", box=box.ROUNDED)
        for k in bench_results[0].keys():
            bt.add_column(k, style="magenta")
        for row in bench_results:
            bt.add_row(*[str(v) for v in row.values()])
        console.print(bt)

    console.print(f"\n[green]Results saved to:[/green] [bold]{config.RESULTS_DIR}/[/bold]")


if __name__ == "__main__":
    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    # 1. Start Prometheus metrics server
    start_metrics_server()

    # 2–5. Demo pipeline run
    demo_stats = run_demo_pipeline(n_events=500)

    # 6. Scalability sweep
    console.rule("[bold yellow]Scalability Tests")
    scale_results = run_scalability_tests()

    # 7. Comparative benchmark
    console.rule("[bold magenta]Comparative Benchmark")
    bench_results = run_benchmark()

    # 8. Summary
    print_summary(demo_stats, scale_results, bench_results)

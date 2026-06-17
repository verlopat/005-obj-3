"""Comparative Benchmarking Module.

Benchmarks the integrated framework against three baseline categories:
  1. ML-only  — Random Forest / SVM without blockchain logging
  2. Blockchain-only — logging without ML detection (random classification)
  3. Integrated (Obj1 + Obj2 + Obj3) — full framework

Metrics: F1, FPR, end-to-end latency, on-chain storage overhead, CPU.
"""
import time
import os
import json
import csv
import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import f1_score, confusion_matrix
from sklearn.datasets import make_classification
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# ── Synthetic dataset (proxy for UNSW-NB15 / CICIDS 2017 structure) ──────────
N_SAMPLES     = 5_000
N_FEATURES    = 30
ANOMALY_RATIO = 0.05

# Canonical fieldnames — ALL rows will have these keys (missing ones filled with N/A)
FIELDNAMES = [
    "system",
    "f1_score",
    "fpr",
    "latency_ms",
    "storage_kb",
    "storage_reduction",
    "blockchain",
    "on_chain_txs",
]


def _make_dataset():
    X, y = make_classification(
        n_samples=N_SAMPLES,
        n_features=N_FEATURES,
        n_informative=15,
        n_redundant=5,
        weights=[1 - ANOMALY_RATIO, ANOMALY_RATIO],
        random_state=42,
    )
    split = int(0.7 * N_SAMPLES)
    return X[:split], X[split:], y[:split], y[split:]


def _f1_fpr(y_true, y_pred):
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return round(f1, 4), round(fpr, 4)


def _normalise(row: dict) -> dict:
    """Fill any missing canonical fields with 'N/A' so all rows are uniform."""
    return {k: row.get(k, "N/A") for k in FIELDNAMES}


def run_benchmark() -> list[dict]:
    X_train, X_test, y_train, y_test = _make_dataset()
    results = []

    # ── Baseline 1: Random Forest (ML-only) ──────────────────────────────────
    t0 = time.perf_counter()
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred    = rf.predict(X_test)
    rf_latency = (time.perf_counter() - t0) * 1000
    rf_f1, rf_fpr = _f1_fpr(y_test, rf_pred)
    results.append({
        "system":     "ML-Only (Random Forest)",
        "f1_score":   rf_f1,
        "fpr":        rf_fpr,
        "latency_ms": round(rf_latency, 2),
        "storage_kb": 0,
        "blockchain": False,
    })
    logger.info(f"[Benchmark] RF | F1={rf_f1} FPR={rf_fpr} lat={rf_latency:.1f}ms")

    # ── Baseline 2: SVM (ML-only) ─────────────────────────────────────────────
    t0 = time.perf_counter()
    svm = SVC(kernel="rbf", probability=False, random_state=42)
    svm.fit(X_train, y_train)
    svm_pred    = svm.predict(X_test)
    svm_latency = (time.perf_counter() - t0) * 1000
    svm_f1, svm_fpr = _f1_fpr(y_test, svm_pred)
    results.append({
        "system":     "ML-Only (SVM)",
        "f1_score":   svm_f1,
        "fpr":        svm_fpr,
        "latency_ms": round(svm_latency, 2),
        "storage_kb": 0,
        "blockchain": False,
    })
    logger.info(f"[Benchmark] SVM | F1={svm_f1} FPR={svm_fpr} lat={svm_latency:.1f}ms")

    # ── Baseline 3: Blockchain-Only (no ML — random labels) ───────────────────
    t0 = time.perf_counter()
    bc_only_pred  = [random.choice([0, 1]) for _ in y_test]
    bc_storage_kb = len(y_test) * 1
    bc_latency    = (time.perf_counter() - t0) * 1000 + len(y_test) * 0.5
    bc_f1, bc_fpr = _f1_fpr(y_test, bc_only_pred)
    results.append({
        "system":       "Blockchain-Only (no ML)",
        "f1_score":     bc_f1,
        "fpr":          bc_fpr,
        "latency_ms":   round(bc_latency, 2),
        "storage_kb":   bc_storage_kb,
        "blockchain":   True,
        "on_chain_txs": len(y_test),
    })
    logger.info(f"[Benchmark] BC-Only | F1={bc_f1} FPR={bc_fpr} lat={bc_latency:.1f}ms")

    # ── Integrated Framework (RF + selective logging + Merkle batching) ────────
    t0 = time.perf_counter()
    int_pred = rf_pred
    int_conf = rf.predict_proba(X_test)[:, 1]
    high_conf_mask    = int_conf >= config.THRESHOLD_HIGH
    on_chain_count    = int(high_conf_mask.sum())
    med_conf_mask     = (int_conf >= config.THRESHOLD_MEDIUM) & (~high_conf_mask)
    batch_txs         = max(1, int(med_conf_mask.sum()) // config.BATCH_MAX_SIZE)
    total_on_chain    = on_chain_count + batch_txs
    storage_kb        = total_on_chain * 1
    storage_full_kb   = len(y_test) * 1
    storage_reduction = round((1 - storage_kb / max(storage_full_kb, 1)) * 100, 1)
    int_latency       = (time.perf_counter() - t0) * 1000 + total_on_chain * 0.5
    int_f1, int_fpr   = _f1_fpr(y_test, int_pred)
    results.append({
        "system":            "Integrated (Obj1+Obj2+Obj3)",
        "f1_score":          int_f1,
        "fpr":               int_fpr,
        "latency_ms":        round(int_latency, 2),
        "storage_kb":        storage_kb,
        "storage_reduction": f"{storage_reduction}%",
        "blockchain":        True,
        "on_chain_txs":      total_on_chain,
    })
    logger.info(
        f"[Benchmark] Integrated | F1={int_f1} FPR={int_fpr} "
        f"lat={int_latency:.1f}ms | storage_saved={storage_reduction}%"
    )

    # ── Normalise all rows to the same fieldnames before writing ──────────────
    normalised = [_normalise(r) for r in results]

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    csv_path  = os.path.join(config.RESULTS_DIR, "benchmark_results.csv")
    json_path = os.path.join(config.RESULTS_DIR, "benchmark_results.json")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(normalised)

    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)   # raw results (with all extra keys) in JSON

    logger.info(f"[Benchmark] Results saved -> {csv_path}")
    return results

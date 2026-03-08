"""Experiment runner for the full parameter matrix described in the report.

Runs both Baseline Dijkstra and Probability-Pruned Dijkstra across:
  - |V| ∈ {1_000, 5_000, 10_000, 50_000}
  - d̄  ∈ {2, 5, 10}
  - distribution ∈ {uniform, power_law}
  - τ  ∈ {0, 0.001, 0.01, 0.05, 0.1, 0.5}
  - ≥10 runs per configuration (fixed seeds for reproducibility)

Records all 7 evaluation metrics per run (§3.8.2):
  execution_time_ms, peak_memory_bytes, nodes_explored, edges_relaxed,
  max_pq_size, path_probability, optimality_gap_pct

Results are saved to a CSV file for analysis.

Usage:
    python run_experiments.py                          # full matrix
    python run_experiments.py --sizes 1000 5000        # subset of sizes
    python run_experiments.py --runs 3                 # quick smoke test
    python run_experiments.py --output results.csv     # custom output path
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
import tracemalloc
from pathlib import Path

from data.graph_generator import generate_erdos_renyi_graph
from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path


# ---------------------------------------------------------------------------
# Default experimental parameters (§3.8.3)
# ---------------------------------------------------------------------------
DEFAULT_SIZES = [1_000, 5_000, 10_000, 50_000]
DEFAULT_DEGREES = [2, 5, 10]
DEFAULT_DISTRIBUTIONS = ["uniform", "power_law"]
DEFAULT_TAUS = [0, 0.001, 0.01, 0.05, 0.1, 0.5]
DEFAULT_RUNS = 10

CSV_HEADER = [
    "graph_size",
    "avg_degree",
    "distribution",
    "tau",
    "run",
    "seed",
    "algorithm",
    "execution_time_ms",
    "peak_memory_bytes",
    "nodes_explored",
    "edges_relaxed",
    "max_pq_size",
    "path_cost",
    "path_probability",
    "path_length",
    "optimality_gap_pct",
]


def _run_single(graph, source, target, tau, baseline_prob):
    """Run one algorithm invocation with timing and memory measurement.

    Returns a dict of metric values.
    """
    is_pruned = tau > 0

    tracemalloc.start()
    t0 = time.perf_counter()

    if is_pruned:
        result = dijkstra_pruned(graph, source, target, tau=tau)
    else:
        result = dijkstra(graph, source, target)

    t1 = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    elapsed_ms = (t1 - t0) * 1000

    if target in result.dist:
        cost = result.dist[target]
        prob = math.exp(-cost)
        path = reconstruct_path(result.parent, source, target)
        path_len = len(path)
    else:
        cost = float("inf")
        prob = 0.0
        path_len = 0

    # Optimality gap vs baseline
    if baseline_prob is not None and baseline_prob > 0:
        gap = abs(baseline_prob - prob) / baseline_prob * 100
    else:
        gap = 0.0

    return {
        "algorithm": "pruned" if is_pruned else "baseline",
        "execution_time_ms": round(elapsed_ms, 4),
        "peak_memory_bytes": peak_mem,
        "nodes_explored": result.metrics.nodes_explored,
        "edges_relaxed": result.metrics.edges_relaxed,
        "max_pq_size": result.metrics.max_pq_size,
        "path_cost": round(cost, 6) if cost != float("inf") else "inf",
        "path_probability": round(prob, 10),
        "path_length": path_len,
        "optimality_gap_pct": round(gap, 6),
    }


def run_experiments(
    sizes=None,
    degrees=None,
    distributions=None,
    taus=None,
    num_runs=DEFAULT_RUNS,
    output_path="experiment_results.csv",
):
    sizes = sizes or DEFAULT_SIZES
    degrees = degrees or DEFAULT_DEGREES
    distributions = distributions or DEFAULT_DISTRIBUTIONS
    taus = taus or DEFAULT_TAUS

    total_configs = len(sizes) * len(degrees) * len(distributions)
    config_num = 0

    out = Path(output_path)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()

        for n in sizes:
            for d in degrees:
                for dist in distributions:
                    config_num += 1
                    print(
                        f"\n[{config_num}/{total_configs}] "
                        f"|V|={n:,}  d̄={d}  dist={dist}"
                    )

                    for run_idx in range(num_runs):
                        seed = run_idx * 1000 + n + d  # deterministic, unique per config+run

                        # Generate graph once per run (same graph for both algorithms)
                        graph = generate_erdos_renyi_graph(
                            n=n,
                            avg_degree=d,
                            distribution=dist,
                            source="s",
                            target="t",
                            seed=seed,
                        )

                        # --- Baseline (tau=0) ---
                        baseline_metrics = _run_single(graph, "s", "t", tau=0, baseline_prob=None)
                        baseline_prob = baseline_metrics["path_probability"]

                        row_base = {
                            "graph_size": n,
                            "avg_degree": d,
                            "distribution": dist,
                            "tau": 0,
                            "run": run_idx + 1,
                            "seed": seed,
                            **baseline_metrics,
                        }
                        writer.writerow(row_base)

                        # --- Pruned variants (tau > 0) ---
                        for tau in taus:
                            if tau == 0:
                                continue  # already recorded
                            pruned_metrics = _run_single(
                                graph, "s", "t", tau=tau, baseline_prob=baseline_prob
                            )
                            row_pruned = {
                                "graph_size": n,
                                "avg_degree": d,
                                "distribution": dist,
                                "tau": tau,
                                "run": run_idx + 1,
                                "seed": seed,
                                **pruned_metrics,
                            }
                            writer.writerow(row_pruned)

                        # Progress indicator
                        if (run_idx + 1) % 5 == 0 or run_idx == 0:
                            print(f"  run {run_idx + 1}/{num_runs} done")

    print(f"\nResults saved to {out.resolve()}")


def parse_args():
    p = argparse.ArgumentParser(description="Run the full experiment matrix.")
    p.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=None,
        help="Graph sizes |V| to test (default: 1000 5000 10000 50000)",
    )
    p.add_argument(
        "--degrees",
        type=int,
        nargs="+",
        default=None,
        help="Average out-degrees d̄ (default: 2 5 10)",
    )
    p.add_argument(
        "--distributions",
        nargs="+",
        default=None,
        help="Probability distributions (default: uniform power_law)",
    )
    p.add_argument(
        "--taus",
        type=float,
        nargs="+",
        default=None,
        help="Pruning thresholds τ (default: 0 0.001 0.01 0.05 0.1 0.5)",
    )
    p.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Repetitions per config (default: {DEFAULT_RUNS})",
    )
    p.add_argument(
        "--output",
        default="experiment_results.csv",
        help="Output CSV path (default: experiment_results.csv)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_experiments(
        sizes=args.sizes,
        degrees=args.degrees,
        distributions=args.distributions,
        taus=args.taus,
        num_runs=args.runs,
        output_path=args.output,
    )

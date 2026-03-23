"""Experiment runner for the full parameter matrix described in the report.

Runs both Baseline Dijkstra and Probability-Pruned Dijkstra across:
  - graph_type ∈ {erdos_renyi, layered}
  - |V| ∈ {1_000, 5_000, 10_000}  (pass --sizes 50000 for larger)
  - d̄  ∈ {2, 5, 10}
  - distribution ∈ {uniform, power_law}
  - τ  ∈ {0, 0.001, 0.01, 0.05, 0.1, 0.5}
  - ≥10 runs per configuration (deterministic seeds via hashlib for reproducibility)

Records all 7 evaluation metrics per run (§3.8.2):
  execution_time_ms, peak_memory_bytes, nodes_explored, edges_relaxed,
  max_pq_size, path_probability, optimality_gap_pct

Results are saved to a CSV file for analysis.

Usage:
    python run_experiments.py                          # full matrix (both graph types)
    python run_experiments.py --graph-types erdos_renyi  # ER only
    python run_experiments.py --sizes 1000 5000        # subset of sizes
    python run_experiments.py --runs 3                 # quick smoke test
    python run_experiments.py --output results.csv     # custom output path
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import time
import tracemalloc
from pathlib import Path

from data.graph_generator import generate_erdos_renyi_graph, generate_layered_graph
from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path


# ---------------------------------------------------------------------------
# Default experimental parameters (§3.8.3)
# ---------------------------------------------------------------------------
DEFAULT_GRAPH_TYPES = ["erdos_renyi", "layered"]
DEFAULT_SIZES = [1_000, 5_000, 10_000]
DEFAULT_DEGREES = [2, 5, 10]
DEFAULT_DISTRIBUTIONS = ["uniform", "power_law"]
DEFAULT_TAUS = [0, 0.001, 0.01, 0.05, 0.1, 0.5]
DEFAULT_RUNS = 10

_GRAPH_GENERATORS = {
    "erdos_renyi": generate_erdos_renyi_graph,
    "layered": generate_layered_graph,
}

CSV_HEADER = [
    "graph_type",
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
    "edges_examined",
    "edges_relaxed",
    "max_pq_size",
    "path_cost",
    "path_probability",
    "path_length",
    "path_found",
    "optimality_gap_pct",
]


def _run_single(graph, source, target, tau, baseline_cost):
    """Run one algorithm invocation with timing and memory measured separately.

    Timing is measured without tracemalloc overhead; memory is measured in a
    second pass so that tracing instrumentation does not corrupt the stopwatch.

    Returns a dict of metric values.
    """
    is_pruned = tau > 0
    _algo = dijkstra_pruned if is_pruned else dijkstra
    _kwargs = dict(graph=graph, start=source, goal=target)
    if is_pruned:
        _kwargs["tau"] = tau

    # --- Pass 1: timing (no tracemalloc) ---
    t0 = time.perf_counter()
    result = _algo(**_kwargs)
    t1 = time.perf_counter()

    # --- Pass 2: memory (separate run) ---
    tracemalloc.start()
    _algo(**_kwargs)
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

    # Optimality gap vs baseline (cost-based to avoid FP rounding noise)
    path_found = path_len > 0
    if baseline_cost is not None and baseline_cost < float("inf") and path_found:
        gap = abs(cost - baseline_cost) / baseline_cost * 100 if baseline_cost > 0 else 0.0
    elif baseline_cost is not None and baseline_cost < float("inf") and not path_found:
        gap = 100.0  # sentinel: no path found by pruned variant
    else:
        gap = 0.0

    return {
        "algorithm": "pruned" if is_pruned else "baseline",
        "execution_time_ms": round(elapsed_ms, 4),
        "peak_memory_bytes": peak_mem,
        "nodes_explored": result.metrics.nodes_explored,
        "edges_examined": result.metrics.edges_examined,
        "edges_relaxed": result.metrics.edges_relaxed,
        "max_pq_size": result.metrics.max_pq_size,
        "path_cost": round(cost, 6),
        "path_probability": round(prob, 10),
        "path_length": path_len,
        "path_found": int(path_found),
        "optimality_gap_pct": round(gap, 6),
        "_raw_cost": cost,  # unrounded, for baseline comparison
    }


def run_experiments(
    graph_types=None,
    sizes=None,
    degrees=None,
    distributions=None,
    taus=None,
    num_runs=DEFAULT_RUNS,
    output_path="results/experiment_results.csv",
):
    graph_types = graph_types or DEFAULT_GRAPH_TYPES
    sizes = sizes or DEFAULT_SIZES
    degrees = degrees or DEFAULT_DEGREES
    distributions = distributions or DEFAULT_DISTRIBUTIONS
    taus = taus or DEFAULT_TAUS

    total_configs = len(graph_types) * len(sizes) * len(degrees) * len(distributions)
    config_num = 0

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()

        for gtype in graph_types:
            gen_fn = _GRAPH_GENERATORS[gtype]

            for n in sizes:
                for d in degrees:
                    for dist in distributions:
                        config_num += 1
                        print(
                            f"\n[{config_num}/{total_configs}] "
                            f"{gtype}  |V|={n:,}  d̄={d}  dist={dist}"
                        )

                        for run_idx in range(num_runs):
                            seed = int(hashlib.md5(f"{run_idx}_{n}_{d}_{gtype}_{dist}".encode()).hexdigest(), 16) & 0xFFFFFFFF

                            graph = gen_fn(
                                n=n,
                                avg_degree=d,
                                distribution=dist,
                                source="s",
                                target="t",
                                seed=seed,
                            )

                            # --- Baseline (tau=0) ---
                            baseline_metrics = _run_single(graph, "s", "t", tau=0, baseline_cost=None)
                            baseline_raw_cost = baseline_metrics.pop("_raw_cost")

                            row_base = {
                                "graph_type": gtype,
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
                                    continue
                                pruned_metrics = _run_single(
                                    graph, "s", "t", tau=tau, baseline_cost=baseline_raw_cost
                                )
                                pruned_metrics.pop("_raw_cost", None)
                                row_pruned = {
                                    "graph_type": gtype,
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
                                f.flush()

    print(f"\nResults saved to {out.resolve()}")


def parse_args():
    p = argparse.ArgumentParser(description="Run the full experiment matrix.")
    p.add_argument(
        "--graph-types",
        nargs="+",
        default=None,
        choices=["erdos_renyi", "layered"],
        help="Graph types to test (default: erdos_renyi layered)",
    )
    p.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=None,
        help="Graph sizes |V| to test (default: 1000 5000 10000)",
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
        default="results/experiment_results.csv",
        help="Output CSV path (default: results/experiment_results.csv)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_experiments(
        graph_types=args.graph_types,
        sizes=args.sizes,
        degrees=args.degrees,
        distributions=args.distributions,
        taus=args.taus,
        num_runs=args.runs,
        output_path=args.output,
    )

"""Run Dijkstra experiments on real-world clickstream datasets.

Usage:
    python run_real_experiments.py [--retailrocket-sessions N] [--recsys-sessions N]

Outputs results/real_data_results.csv  with columns:
    dataset, nodes, edges, source, target, tau,
    baseline_cost, baseline_prob, baseline_nodes_explored,
    baseline_edges_examined, baseline_edges_relaxed, baseline_ms,
    pruned_cost, pruned_prob, pruned_nodes_explored,
    pruned_edges_examined, pruned_edges_relaxed, pruned_ms,
    path_found, speedup, optimality_gap_pct
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import time
from pathlib import Path

from data.real_data_loader import load_retailrocket, load_recsys2015, dataset_summary
from src.preprocessing import extract_transitions, compute_transition_statistics
from src.graph_builder import build_weighted_graph
from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path


TAU_VALUES = [0.0001, 0.001, 0.01, 0.1, 0.5]
NUM_PAIRS = 20  # source-target pairs per dataset


def _pick_pairs(graph, rng, n=NUM_PAIRS):
    """Pick n random (source, target) pairs that are reachable."""
    nodes = list(graph.keys())
    popular = sorted(nodes, key=lambda nd: len(graph[nd]), reverse=True)
    # Choose sources from top-20 popular nodes
    sources = popular[: min(20, len(popular))]
    pairs = []
    attempts = 0
    while len(pairs) < n and attempts < n * 50:
        src = rng.choice(sources)
        tgt = rng.choice(nodes)
        if src == tgt:
            attempts += 1
            continue
        # Quick reachability check
        res = dijkstra(graph, src, tgt)
        if tgt in res.dist:
            pairs.append((src, tgt))
        attempts += 1
    return pairs


def run_dataset(name, df, output_rows, rng):
    transitions = extract_transitions(df)
    _, probs = compute_transition_statistics(transitions)
    graph = build_weighted_graph(probs)

    n_nodes = len(graph)
    n_edges = sum(len(v) for v in graph.values())
    print(f"  {name}: {n_nodes:,} nodes, {n_edges:,} edges")

    pairs = _pick_pairs(graph, rng, n=NUM_PAIRS)
    print(f"  Found {len(pairs)} reachable pairs")

    for src, tgt in pairs:
        # Baseline
        t0 = time.perf_counter()
        res_base = dijkstra(graph, src, tgt)
        t_base = (time.perf_counter() - t0) * 1000

        base_cost = res_base.dist.get(tgt, float("inf"))
        base_prob = math.exp(-base_cost) if base_cost < float("inf") else 0.0

        for tau in TAU_VALUES:
            t0 = time.perf_counter()
            res_pr = dijkstra_pruned(graph, src, tgt, tau=tau)
            t_pr = (time.perf_counter() - t0) * 1000

            pr_cost = res_pr.dist.get(tgt, float("inf"))
            pr_prob = math.exp(-pr_cost) if pr_cost < float("inf") else 0.0
            found = tgt in res_pr.dist

            if found and base_prob > 0:
                gap = abs(base_prob - pr_prob) / base_prob * 100
            else:
                gap = None

            speedup = t_base / t_pr if t_pr > 0 else float("inf")

            output_rows.append({
                "dataset": name,
                "nodes": n_nodes,
                "edges": n_edges,
                "source": src,
                "target": tgt,
                "tau": tau,
                "baseline_cost": round(base_cost, 6),
                "baseline_prob": f"{base_prob:.10f}",
                "baseline_nodes_explored": res_base.metrics.nodes_explored,
                "baseline_edges_examined": res_base.metrics.edges_examined,
                "baseline_edges_relaxed": res_base.metrics.edges_relaxed,
                "baseline_ms": round(t_base, 3),
                "pruned_cost": round(pr_cost, 6) if found else "",
                "pruned_prob": f"{pr_prob:.10f}" if found else "",
                "pruned_nodes_explored": res_pr.metrics.nodes_explored,
                "pruned_edges_examined": res_pr.metrics.edges_examined,
                "pruned_edges_relaxed": res_pr.metrics.edges_relaxed,
                "pruned_ms": round(t_pr, 3),
                "path_found": found,
                "speedup": round(speedup, 2),
                "optimality_gap_pct": round(gap, 6) if gap is not None else "",
            })


def main():
    parser = argparse.ArgumentParser(description="Real-data Dijkstra experiments")
    parser.add_argument("--retailrocket-sessions", type=int, default=None,
                        help="Cap RetailRocket sessions (default: all)")
    parser.add_argument("--recsys-sessions", type=int, default=50000,
                        help="Cap RecSys 2015 sessions (default: 50000)")
    parser.add_argument("--pairs", type=int, default=20,
                        help="Number of source-target pairs per dataset")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    global NUM_PAIRS
    NUM_PAIRS = args.pairs

    rng = random.Random(args.seed)
    rows = []

    # ----- RetailRocket (event-level funnel) -----
    print("Loading RetailRocket (event-level)...")
    df_rr = load_retailrocket(granularity="event",
                              max_sessions=args.retailrocket_sessions)
    run_dataset("RetailRocket-event", df_rr, rows, rng)

    # ----- RetailRocket (item-level — large graph) -----
    print("Loading RetailRocket (item-level, 50K sessions)...")
    df_rr_item = load_retailrocket(granularity="item", max_sessions=50000)
    run_dataset("RetailRocket-item", df_rr_item, rows, rng)

    # ----- RecSys 2015 (item-level) -----
    print("Loading RecSys 2015 (%s sessions)..." %
          (f"{args.recsys_sessions:,}" if args.recsys_sessions else "all"))
    df_rc = load_recsys2015(max_sessions=args.recsys_sessions)
    run_dataset("RecSys2015", df_rc, rows, rng)

    # ----- Write CSV -----
    out = Path("results/real_data_results.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out}")

    # Quick summary
    found_count = sum(1 for r in rows if r["path_found"])
    total = len(rows)
    print(f"Path-found rate: {found_count}/{total} ({found_count/total*100:.1f}%)")
    gaps = [r["optimality_gap_pct"] for r in rows if r["optimality_gap_pct"] != ""]
    if gaps:
        print(f"Max optimality gap: {max(gaps):.6f}%")


if __name__ == "__main__":
    main()

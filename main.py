from __future__ import annotations

import argparse
import heapq
import math
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.dijkstra import dijkstra_search, reconstruct_path, DijkstraResult
from src.graph_builder import build_weighted_graph
from src.preprocessing import compute_transition_statistics, extract_transitions


Graph = Dict[str, List[Tuple[str, float]]]


def load_dataset(data_path: Path) -> pd.DataFrame:
    """Load clickstream data from CSV."""
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")
    return pd.read_csv(data_path)


def run_search_with_metrics(
    graph: Graph, source: str, target: str, tau: float = 0.0, label: str = "Search"
) -> DijkstraResult:
    """Run Dijkstra with timing and memory tracking."""
    tracemalloc.start()
    start_time = time.perf_counter()
    
    result = dijkstra_search(graph, source, target, tau=tau)
    
    end_time = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    execution_time_ms = (end_time - start_time) * 1000
    
    print("=" * 50)
    print(f"{label.upper()} ({'baseline' if tau <= 0 else f'tau={tau}'})")
    print("=" * 50)
    
    if target not in result.dist:
        print(f"No path found from {source} to {target}.")
    else:
        path = reconstruct_path(result.parent, source, target)
        cost = result.dist[target]
        prob = math.exp(-cost)

        print(f"Path: {' -> '.join(path)}")
        print(f"\nTotal Cost (log-space): {cost:.4f}")
        print(f"Path Probability:       {prob:.6f}")
        
        m = result.metrics
        print(f"\nMetrics:")
        print(f"  Nodes explored:    {m.nodes_explored}")
        print(f"  Edges examined:    {m.edges_examined}")
        print(f"  Edges relaxed:     {m.edges_relaxed}")
        print(f"  Max PQ size:       {m.max_pq_size}")
        print(f"  Execution time:    {execution_time_ms:.3f} ms")
        print(f"  Peak memory:       {peak_mem / 1024:.2f} KB")

    return result


def k_shortest_simple_paths(
    graph: Graph,
    source: str,
    target: str,
    k: int,
    max_path_len: int | None = None,
) -> List[Tuple[float, List[str]]]:
    """Best-first search for top-k simple paths by total weight."""
    if k <= 0:
        return []

    if max_path_len is None:
        max_path_len = max(2, len(graph) + 1)

    pq: List[Tuple[float, List[str]]] = [(0.0, [source])]
    results: List[Tuple[float, List[str]]] = []

    while pq and len(results) < k:
        cost, path = heapq.heappop(pq)
        node = path[-1]

        if node == target:
            results.append((cost, path))
            continue

        if len(path) >= max_path_len:
            continue

        for neighbor, weight in graph.get(node, []):
            if neighbor in path:
                continue
            heapq.heappush(pq, (cost + weight, path + [neighbor]))

    return results


def export_graph_image(graph: Graph, output_path: Path) -> None:
    """Export a visualization of the graph to a file."""
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        print("Warning: Graph export requires `networkx` and `matplotlib`. Skipping visualization.")
        return

    g = nx.DiGraph()
    for source, neighbors in graph.items():
        for target, weight in neighbors:
            g.add_edge(source, target, weight=round(weight, 3))

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(g, seed=42)
    nx.draw(g, pos, with_labels=True, node_size=1800, font_size=8, arrows=True)
    edge_labels = nx.get_edge_attributes(g, "weight")
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=7)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find most probable customer journey paths using Dijkstra."
    )
    parser.add_argument(
        "--data",
        default="data/enhanced_synthetic_journey.csv",
        help="Path to CSV clickstream data",
    )
    parser.add_argument("--source", default="Home", help="Start node")
    parser.add_argument("--target", default="Checkout", help="Target node")
    parser.add_argument("--k", type=int, default=1, help="Number of top paths to return")
    parser.add_argument(
        "--tau",
        type=float,
        default=0.0,
        help="Pruning threshold tau (0 = baseline only)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional image output path for graph visualization",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)

    # 1. Load Data
    try:
        df = load_dataset(data_path)
    except FileNotFoundError:
        from data.synthetic_data_generator import SyntheticJourneyGenerator
        print(f"Dataset not found. Generating synthetic data at {data_path}...")
        df = SyntheticJourneyGenerator(avg_session_length=12).generate(num_sessions=2000)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(data_path, index=False)

    # 2. Build Graph
    transitions = extract_transitions(df)
    _, transition_probs = compute_transition_statistics(transitions)
    graph = build_weighted_graph(transition_probs)

    if args.source not in graph or args.target not in graph:
        print(f"Error: Source '{args.source}' or Target '{args.target}' not found in data.")
        return

    # 3. Execute Search
    if args.k <= 1:
        res_base = run_search_with_metrics(graph, args.source, args.target, tau=0.0, label="Baseline")
        
        if args.tau > 0:
            print()
            res_pruned = run_search_with_metrics(graph, args.source, args.target, tau=args.tau, label="Pruned")
            
            # Show optimality gap
            if args.target in res_base.dist and args.target in res_pruned.dist:
                gap = abs(res_pruned.dist[args.target] - res_base.dist[args.target])
                gap_pct = (gap / res_base.dist[args.target] * 100) if res_base.dist[args.target] > 0 else 0
                print(f"\n  Optimality gap:    {gap_pct:.4f}%")
    else:
        if args.tau > 0:
            print(f"Warning: --tau {args.tau} is ignored when --k > 1.")
        
        paths = k_shortest_simple_paths(graph, args.source, args.target, args.k)
        print(f"Top {len(paths)} Paths:")
        for i, (cost, path) in enumerate(paths, start=1):
            print(f"{i}. {' -> '.join(path)} (Cost: {cost:.4f}, Prob: {math.exp(-cost):.6f})")

    # 4. Optional Visualization
    if args.output:
        export_graph_image(graph, Path(args.output))
        print(f"\nGraph visualization saved to {args.output}")


if __name__ == "__main__":
    main()

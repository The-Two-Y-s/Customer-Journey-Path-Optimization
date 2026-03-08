from __future__ import annotations

import argparse
import heapq
import math
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path, DijkstraResult
from src.graph_builder import build_weighted_graph
from src.preprocessing import compute_transition_statistics, extract_transitions


Graph = Dict[str, List[Tuple[str, float]]]


def load_dataset(data_path: Path) -> pd.DataFrame:
	if not data_path.exists():
		raise FileNotFoundError(f"Dataset not found: {data_path}")
	return pd.read_csv(data_path)


def format_path(path: List[str]) -> str:
	return " -> ".join(path)


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
	try:
		import matplotlib.pyplot as plt
		import networkx as nx
	except Exception as exc:
		raise RuntimeError(
			"Graph export requires `networkx` and `matplotlib`. Install them first."
		) from exc

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


def print_result(result: DijkstraResult, source: str, target: str, label: str = "Optimal") -> None:
	"""Print path, cost, probability, and metrics for a single Dijkstra run."""
	if target not in result.dist:
		print(f"No path found from {source} to {target}.")
		return

	path = reconstruct_path(result.parent, source, target)
	cost = result.dist[target]
	prob = math.exp(-cost)

	print(f"{label} Path:")
	print(format_path(path))
	print(f"\nTotal Cost (log-space): {cost:.4f}")
	print(f"Path Probability:       {prob:.6f}")
	m = result.metrics
	print(f"\nMetrics:")
	print(f"  Nodes explored:    {m.nodes_explored}")
	print(f"  Edges relaxed:     {m.edges_relaxed}")
	print(f"  Max PQ size:       {m.max_pq_size}")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Find most probable customer journey paths using Dijkstra."
	)
	parser.add_argument(
		"--data",
		default="enhanced_synthetic_journey.csv",
		help="Path to CSV clickstream data (default: enhanced_synthetic_journey.csv)",
	)
	parser.add_argument("--source", default="Home", help="Start node")
	parser.add_argument("--target", default="Checkout", help="Target node")
	parser.add_argument("--k", type=int, default=1, help="Number of top paths to return")
	parser.add_argument(
		"--tau",
		type=float,
		default=0.0,
		help="Pruning threshold tau for Pruned Dijkstra (0 = baseline only)",
	)
	parser.add_argument(
		"--output",
		default=None,
		help="Optional image output path for graph visualization (e.g., output.png)",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	data_path = Path(args.data)

	try:
		df = load_dataset(data_path)
	except FileNotFoundError:
		from data.synthetic_data_generator import SyntheticJourneyGenerator

		print(f"Dataset not found at {data_path}. Generating synthetic data...")
		generator = SyntheticJourneyGenerator(avg_session_length=12)
		df = generator.generate(num_sessions=2000)
		data_path = Path("enhanced_synthetic_journey.csv")
		df.to_csv(data_path, index=False)
		print(f"Generated dataset at {data_path}")

	transitions = extract_transitions(df)
	_, transition_probs = compute_transition_statistics(transitions)
	graph = build_weighted_graph(transition_probs)

	if args.source not in graph:
		raise ValueError(f"Source node '{args.source}' not found in graph")

	if args.k <= 1:
		# --- Baseline Dijkstra ---
		tracemalloc.start()
		t0 = time.perf_counter()
		result_baseline = dijkstra(graph, args.source, args.target)
		t1 = time.perf_counter()
		_, peak_mem = tracemalloc.get_traced_memory()
		tracemalloc.stop()

		print("=" * 50)
		print("BASELINE DIJKSTRA")
		print("=" * 50)
		print_result(result_baseline, args.source, args.target, label="Optimal")
		print(f"  Execution time:    {(t1 - t0) * 1000:.3f} ms")
		print(f"  Peak memory:       {peak_mem / 1024:.2f} KB")

		# --- Pruned Dijkstra (if tau > 0) ---
		if args.tau > 0:
			tracemalloc.start()
			t0 = time.perf_counter()
			result_pruned = dijkstra_pruned(graph, args.source, args.target, tau=args.tau)
			t1 = time.perf_counter()
			_, peak_mem = tracemalloc.get_traced_memory()
			tracemalloc.stop()

			print()
			print("=" * 50)
			print(f"PRUNED DIJKSTRA (tau={args.tau})")
			print("=" * 50)
			print_result(result_pruned, args.source, args.target, label="Pruned")
			print(f"  Execution time:    {(t1 - t0) * 1000:.3f} ms")
			print(f"  Peak memory:       {peak_mem / 1024:.2f} KB")

			# Optimality gap
			if args.target in result_baseline.dist and args.target in result_pruned.dist:
				prob_base = math.exp(-result_baseline.dist[args.target])
				prob_pruned = math.exp(-result_pruned.dist[args.target])
				if prob_base > 0:
					gap = abs(prob_base - prob_pruned) / prob_base * 100
					print(f"\n  Optimality gap:    {gap:.4f}%")
	else:
		paths = k_shortest_simple_paths(graph, args.source, args.target, args.k)
		if not paths:
			print(f"No path found from {args.source} to {args.target}.")
		else:
			print(f"Top {len(paths)} Paths:")
			for i, (cost, path) in enumerate(paths, start=1):
				prob = math.exp(-cost)
				print(f"{i}. {format_path(path)} (Cost: {cost:.4f}, Prob: {prob:.6f})")

	if args.output:
		output_path = Path(args.output)
		export_graph_image(graph, output_path)
		print(f"\nGraph visualization saved to {output_path}")


if __name__ == "__main__":
	main()

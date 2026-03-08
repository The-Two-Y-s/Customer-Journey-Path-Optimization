from __future__ import annotations

import argparse
import heapq
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.dijkstra import dijkstra, reconstruct_path
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
		dist, parent = dijkstra(graph, args.source, args.target)
		if args.target not in dist:
			print(f"No path found from {args.source} to {args.target}.")
		else:
			path = reconstruct_path(parent, args.source, args.target)
			print("Optimal Path:")
			print(format_path(path))
			print(f"\nTotal Cost: {dist[args.target]:.2f}")
	else:
		paths = k_shortest_simple_paths(graph, args.source, args.target, args.k)
		if not paths:
			print(f"No path found from {args.source} to {args.target}.")
		else:
			print(f"Top {len(paths)} Paths:")
			for i, (cost, path) in enumerate(paths, start=1):
				print(f"{i}. {format_path(path)} (Cost: {cost:.2f})")

	if args.output:
		output_path = Path(args.output)
		export_graph_image(graph, output_path)
		print(f"Graph visualization saved to {output_path}")


if __name__ == "__main__":
	main()

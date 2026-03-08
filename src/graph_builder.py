from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple


WeightedGraph = Dict[str, List[Tuple[str, float]]]


def build_weighted_graph(transition_probs: Dict[str, Dict[str, float]]) -> WeightedGraph:
	"""Build a weighted adjacency list using w(u,v) = -log(p(u,v))."""
	graph: WeightedGraph = defaultdict(list)

	for source, targets in transition_probs.items():
		for target, prob in targets.items():
			if prob <= 0:
				continue
			graph[source].append((target, -math.log(prob)))

			# Ensure target nodes exist in the adjacency map to avoid missing-key lookups.
			if target not in graph:
				graph[target] = []

	return dict(graph)


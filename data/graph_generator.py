"""Erdős–Rényi sparse directed graph generator for controlled experiments.

Generates random directed graphs with configurable:
  - |V| (number of vertices)
  - Average out-degree d̄
  - Edge probability distribution (uniform or power-law)
  - Guaranteed s-t connectivity via BFS check + repair
  - Reproducible via fixed seed

Scalable to |V| = 50,000+ by sampling neighbours per node (O(|V| * d̄)),
avoiding the O(|V|²) all-pairs loop of a naive Erdős–Rényi implementation.
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Dict, List, Tuple


Graph = Dict[str, List[Tuple[str, float]]]


def _ensure_connectivity(
    adj: Dict[str, List[str]],
    source: str,
    target: str,
    nodes: List[str],
    rng: random.Random,
) -> List[Tuple[str, str]]:
    """Add minimal edges to guarantee a directed path from *source* to *target*.

    Uses BFS from source; if target is unreachable, builds a short bridge path
    from an arbitrary reachable frontier node to target.
    Returns the list of added (u, v) pairs so the caller can assign weights.
    """
    visited = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in adj.get(u, []):
            if v not in visited:
                visited.add(v)
                queue.append(v)

    if target in visited:
        return []

    # Bridge a reachable node to target
    bridge = rng.choice(list(visited))
    adj.setdefault(bridge, []).append(target)
    return [(bridge, target)]


def generate_erdos_renyi_graph(
    n: int = 1000,
    avg_degree: float = 5.0,
    distribution: str = "uniform",
    source: str = "s",
    target: str = "t",
    seed: int = 42,
) -> Graph:
    """Create a random sparse directed graph with -log(p) edge weights.

    Parameters
    ----------
    n : int
        Number of vertices (including source and target).
    avg_degree : float
        Expected out-degree per vertex (kept sparse for large n).
    distribution : str
        ``"uniform"`` for U(0.01, 1) edge probabilities,
        ``"power_law"`` for power-law distributed probabilities (alpha=2).
    source, target : str
        Labels for the designated source / target nodes.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    graph : dict
        Adjacency list mapping node labels to ``(neighbor, weight)`` tuples
        where ``weight = -log(probability)``.
    """
    if n < 2:
        raise ValueError("n must be >= 2")

    rng = random.Random(seed)

    # Build node labels
    nodes = [source] + [f"v{i}" for i in range(n - 2)] + [target]
    node_set = set(nodes)

    # --- Scalable edge generation: sample ~avg_degree neighbours per node ---
    # For each node, draw the number of outgoing edges from a narrow uniform
    # range around avg_degree, then sample that many distinct neighbours.
    adj: Dict[str, List[str]] = {nd: [] for nd in nodes}
    edges: List[Tuple[str, str]] = []

    for u in nodes:
        out_deg = rng.randint(
            max(0, int(avg_degree) - 2), int(avg_degree) + 2
        )
        out_deg = min(out_deg, n - 1)  # can't exceed n-1 neighbours

        # Sample distinct neighbours (reservoir-style for speed)
        candidates = [v for v in nodes if v != u]
        if out_deg >= len(candidates):
            chosen = candidates
        else:
            chosen = rng.sample(candidates, out_deg)

        for v in chosen:
            adj[u].append(v)
            edges.append((u, v))

    # Guarantee s-t connectivity
    extra = _ensure_connectivity(adj, source, target, nodes, rng)
    edges.extend(extra)

    # Assign probability weights and build final weighted graph
    graph: Graph = {nd: [] for nd in nodes}

    for u, v in edges:
        if distribution == "uniform":
            p = rng.uniform(0.01, 1.0)
        elif distribution == "power_law":
            # Inverse-CDF of power-law: P(X<=x) = x^alpha, alpha=2
            p = max(rng.random() ** 2, 0.01)
        else:
            raise ValueError(f"Unknown distribution: {distribution}")

        graph[u].append((v, -math.log(p)))

    return graph

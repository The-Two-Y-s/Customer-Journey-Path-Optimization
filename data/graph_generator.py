"""Graph generators for controlled experiments.

Provides two generator types:

1. **Erdős–Rényi** (``generate_erdos_renyi_graph``):
   Random sparse directed graphs for generic algorithm stress-testing.

2. **Layered / Stage-Based** (``generate_layered_graph``):
   Mimics real customer-journey funnels (Awareness → Consideration →
   Conversion) with primarily forward edges and a configurable backward-edge
   probability to model user loops (e.g. Home → Product → Home).

Both generators support configurable |V|, average out-degree, edge-weight
distributions (uniform / power-law), guaranteed s-t connectivity, and
reproducibility via fixed seeds.  Scalable to |V| = 50,000+.
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


# ---------------------------------------------------------------------------
# Layered / Stage-Based graph generator
# ---------------------------------------------------------------------------

DEFAULT_STAGES = ["Awareness", "Interest", "Consideration", "Intent", "Conversion"]


def generate_layered_graph(
    n: int = 1000,
    avg_degree: float = 5.0,
    distribution: str = "uniform",
    source: str = "s",
    target: str = "t",
    seed: int = 42,
    stages: list[str] | None = None,
    backward_prob: float = 0.15,
) -> Graph:
    """Create a layered directed graph that mimics a customer-journey funnel.

    Nodes are distributed across sequential *stages* (e.g. Awareness →
    Interest → Consideration → Intent → Conversion).  Most edges go
    **forward** (same stage or next stage); a fraction go **backward** to
    model real-world loops (e.g. a user returning from Product to Home).

    Parameters
    ----------
    n : int
        Total number of vertices (including source and target).  Must be >= 2.
    avg_degree : float
        Expected out-degree per vertex.
    distribution : str
        ``"uniform"`` for U(0.01, 1) edge probabilities,
        ``"power_law"`` for power-law distributed probabilities.
    source, target : str
        Labels for the designated source / target nodes.
    seed : int
        Random seed for reproducibility.
    stages : list[str] | None
        Ordered stage names.  Defaults to a 5-stage funnel.
    backward_prob : float
        Probability that an edge is directed *backward* (to a previous stage)
        instead of forward.  0 gives a pure DAG; 0.15 (default) adds
        realistic loops.

    Returns
    -------
    graph : dict
        Adjacency list with ``(neighbor, -log(p))`` edge weights.
    """
    if n < 2:
        raise ValueError("n must be >= 2")

    stages = stages or list(DEFAULT_STAGES)
    num_stages = len(stages)
    rng = random.Random(seed)

    # --- Distribute nodes across stages ---
    # source is placed in stage 0, target in the last stage.
    # Remaining n-2 nodes are allocated roughly evenly, with leftovers
    # sprinkled into middle stages.
    inner = n - 2
    base_per_stage = inner // num_stages
    remainder = inner % num_stages

    stage_nodes: list[list[str]] = [[] for _ in range(num_stages)]
    node_idx = 0
    for s_idx in range(num_stages):
        count = base_per_stage + (1 if s_idx < remainder else 0)
        for _ in range(count):
            stage_nodes[s_idx].append(f"{stages[s_idx]}_{node_idx}")
            node_idx += 1

    # Inject source and target
    stage_nodes[0].insert(0, source)
    stage_nodes[-1].append(target)

    all_nodes: list[str] = [nd for layer in stage_nodes for nd in layer]
    node_to_stage: dict[str, int] = {}
    for s_idx, layer in enumerate(stage_nodes):
        for nd in layer:
            node_to_stage[nd] = s_idx

    # --- Edge generation ---
    adj: Dict[str, List[str]] = {nd: [] for nd in all_nodes}
    edges: list[tuple[str, str]] = []

    for u in all_nodes:
        u_stage = node_to_stage[u]

        out_deg = rng.randint(
            max(1, int(avg_degree) - 2), int(avg_degree) + 2
        )
        out_deg = min(out_deg, len(all_nodes) - 1)

        chosen: list[str] = []
        for _ in range(out_deg):
            if rng.random() < backward_prob and u_stage > 0:
                # Backward edge: pick a node from a previous stage
                prev_stage = rng.randint(0, u_stage - 1)
                pool = stage_nodes[prev_stage]
            else:
                # Forward edge: same stage or next stage(s)
                fwd_stage = min(u_stage + rng.randint(0, 1), num_stages - 1)
                pool = stage_nodes[fwd_stage]

            candidates = [v for v in pool if v != u and v not in chosen]
            if not candidates:
                # Fall back to any forward node
                for fs in range(u_stage, num_stages):
                    candidates = [v for v in stage_nodes[fs] if v != u and v not in chosen]
                    if candidates:
                        break
            if candidates:
                v = rng.choice(candidates)
                chosen.append(v)
                adj[u].append(v)
                edges.append((u, v))

    # Guarantee s-t connectivity
    extra = _ensure_connectivity(adj, source, target, all_nodes, rng)
    edges.extend(extra)

    # Assign probability weights
    graph: Graph = {nd: [] for nd in all_nodes}
    for u, v in edges:
        if distribution == "uniform":
            p = rng.uniform(0.01, 1.0)
        elif distribution == "power_law":
            p = max(rng.random() ** 2, 0.01)
        else:
            raise ValueError(f"Unknown distribution: {distribution}")
        graph[u].append((v, -math.log(p)))

    return graph

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field


@dataclass
class DijkstraMetrics:
    """Execution metrics collected during a Dijkstra run."""
    nodes_explored: int = 0
    edges_relaxed: int = 0
    edges_examined: int = 0
    max_pq_size: int = 0


@dataclass
class DijkstraResult:
    """Full result returned by the Dijkstra search engine."""
    dist: dict[str, float] = field(default_factory=dict)
    parent: dict[str, str] = field(default_factory=dict)
    metrics: DijkstraMetrics = field(default_factory=DijkstraMetrics)


Graph = dict[str, list[tuple[str, float]]]


def dijkstra_search(graph: Graph, start: str, goal: str, tau: float = 0.0) -> DijkstraResult:
    """
    Unified Dijkstra Search Engine.
    
    This function finds the most probable path (shortest path in log-space).
    It optionally supports Probability Pruning via the tau parameter.

    Parameters
    ----------
    graph : Graph
        Adjacency list mapping node labels to (neighbor, weight) tuples.
    start, goal : str
        Source and target node labels.
    tau : float
        Pruning threshold probability. If tau > 0, paths with probability 
        less than tau are discarded. Default 0.0 (baseline).
    """
    if tau < 0:
        raise ValueError(f"tau must be non-negative, got {tau}")

    # Priority queue stores (cumulative_cost, current_node)
    priority_queue = [(0.0, start)]
    best_costs = {start: 0.0}
    parent = {}
    metrics = DijkstraMetrics()
    metrics.max_pq_size = 1

    # Pruning threshold in log-space; tau <= 0 means no pruning.
    pruning_limit = -math.log(tau) if tau > 0 else math.inf

    while priority_queue:
        current_cost, current_node = heapq.heappop(priority_queue)

        if current_node == goal:
            metrics.nodes_explored += 1
            break

        # --- Lazy Deletion (Stale Entry Skip) ---
        # Since Python's heapq doesn't support O(log n) decrease-key, we push 
        # multiple entries for the same node. We only process the one with 
        # the lowest cost and skip the rest.
        if current_cost > best_costs.get(current_node, math.inf):
            continue

        metrics.nodes_explored += 1

        for neighbor, weight in graph.get(current_node, []):
            new_cost = current_cost + weight
            metrics.edges_examined += 1

            # --- Probability Pruning ---
            # If the cumulative log-cost exceeds our pruning limit (T = -log(tau)),
            # we discard the edge immediately.
            if new_cost > pruning_limit:
                continue

            metrics.edges_relaxed += 1

            # Standard relaxation check
            if neighbor not in best_costs or new_cost < best_costs[neighbor]:
                best_costs[neighbor] = new_cost
                parent[neighbor] = current_node
                heapq.heappush(priority_queue, (new_cost, neighbor))
                
                # Update peak memory metric
                if len(priority_queue) > metrics.max_pq_size:
                    metrics.max_pq_size = len(priority_queue)

    return DijkstraResult(dist=best_costs, parent=parent, metrics=metrics)


def reconstruct_path(parent: dict[str, str], start: str, goal: str) -> list[str]:
    """Backtrack through the parent map to recover the s-to-t path."""
    if start == goal:
        return [start]
    if goal not in parent:
        return []

    path = [goal]
    visited: set[str] = {goal}
    cur = goal
    while cur != start:
        cur = parent[cur]
        if cur in visited:
            raise RuntimeError("Cycle detected in parent map during path reconstruction")
        visited.add(cur)
        path.append(cur)
    path.reverse()
    return path
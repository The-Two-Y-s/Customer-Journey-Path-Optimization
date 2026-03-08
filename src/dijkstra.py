from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field


@dataclass
class DijkstraMetrics:
    """Execution metrics collected during a Dijkstra run."""
    nodes_explored: int = 0
    edges_relaxed: int = 0
    max_pq_size: int = 0


@dataclass
class DijkstraResult:
    """Full result returned by both baseline and pruned Dijkstra."""
    dist: dict = field(default_factory=dict)
    parent: dict = field(default_factory=dict)
    metrics: DijkstraMetrics = field(default_factory=DijkstraMetrics)


def dijkstra(graph, start, goal):
    """Baseline Dijkstra (Algorithm 1) with stale-entry skip and metrics."""
    pq = [(0, start)]
    dist = {start: 0}
    parent = {}
    metrics = DijkstraMetrics()
    metrics.max_pq_size = 1

    while pq:
        cost, node = heapq.heappop(pq)

        if node == goal:
            metrics.nodes_explored += 1
            break

        # Stale entry check (lazy deletion)
        if cost > dist.get(node, math.inf):
            continue

        metrics.nodes_explored += 1

        for neighbor, weight in graph.get(node, []):
            new_cost = cost + weight
            metrics.edges_relaxed += 1

            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                parent[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))
                if len(pq) > metrics.max_pq_size:
                    metrics.max_pq_size = len(pq)

    return DijkstraResult(dist=dist, parent=parent, metrics=metrics)


def dijkstra_pruned(graph, start, goal, tau=0.01):
    """Probability-Pruned Dijkstra (Algorithm 2).

    Prunes partial paths whose cumulative probability falls below tau.
    When tau <= 0 the algorithm is identical to the baseline.
    """
    pq = [(0, start)]
    dist = {start: 0}
    parent = {}
    metrics = DijkstraMetrics()
    metrics.max_pq_size = 1

    # Pruning threshold in log-space; tau <= 0 means no pruning.
    T = -math.log(tau) if tau > 0 else math.inf

    while pq:
        cost, node = heapq.heappop(pq)

        if node == goal:
            metrics.nodes_explored += 1
            break

        # Stale entry check
        if cost > dist.get(node, math.inf):
            continue

        metrics.nodes_explored += 1

        for neighbor, weight in graph.get(node, []):
            new_cost = cost + weight
            metrics.edges_relaxed += 1

            # PRUNE: cumulative log-cost exceeds threshold
            if new_cost > T:
                continue

            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                parent[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))
                if len(pq) > metrics.max_pq_size:
                    metrics.max_pq_size = len(pq)

    return DijkstraResult(dist=dist, parent=parent, metrics=metrics)


def reconstruct_path(parent, start, goal):
    """Backtrack through the parent map to recover the s-to-t path."""
    if start == goal:
        return [start]
    if goal not in parent:
        return []

    path = [goal]
    cur = goal
    while cur != start:
        cur = parent[cur]
        path.append(cur)
    path.reverse()
    return path
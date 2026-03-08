"""Critical threshold (tau*) finder.

Sweeps tau values on a given graph, measuring speedup vs optimality gap,
and identifies the critical tau -- the largest tau where the optimality
gap stays below a user-defined tolerance (default 1%).

This formalises Section 1.3 Objective: "find the point where computational
speedup is maximised without a significant drop in path accuracy."
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path


@dataclass
class TauProfile:
    """Metrics collected for a single tau value."""
    tau: float
    nodes_explored: int
    edges_relaxed: int
    path_probability: float
    optimality_gap_pct: float
    speedup_nodes: float  # baseline_nodes / pruned_nodes


@dataclass
class CriticalTauResult:
    """Result of a critical-tau sweep."""
    critical_tau: float | None
    max_speedup_at_critical: float
    profiles: List[TauProfile]
    baseline_nodes: int
    baseline_probability: float


DEFAULT_TAU_SWEEP = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]


def find_critical_tau(
    graph,
    source: str,
    target: str,
    taus: list[float] | None = None,
    gap_tolerance: float = 1.0,
) -> CriticalTauResult:
    """Sweep tau values and find the critical threshold.

    Parameters
    ----------
    graph : dict
        Adjacency list with (neighbour, weight) tuples.
    source, target : str
        Start and end nodes.
    taus : list[float] | None
        Tau values to sweep (ascending). Defaults to a fine-grained list.
    gap_tolerance : float
        Maximum acceptable optimality gap in percent (default 1%).

    Returns
    -------
    CriticalTauResult
        Contains the critical tau, the speedup at that tau, and the full
        profile list for plotting.
    """
    taus = sorted(taus or DEFAULT_TAU_SWEEP)

    # Run baseline
    result_base = dijkstra(graph, source, target)
    if target not in result_base.dist:
        return CriticalTauResult(
            critical_tau=None,
            max_speedup_at_critical=0.0,
            profiles=[],
            baseline_nodes=result_base.metrics.nodes_explored,
            baseline_probability=0.0,
        )

    base_nodes = result_base.metrics.nodes_explored
    base_prob = math.exp(-result_base.dist[target])

    profiles: list[TauProfile] = []

    for tau in taus:
        result_p = dijkstra_pruned(graph, source, target, tau=tau)
        p_nodes = result_p.metrics.nodes_explored

        if target in result_p.dist:
            p_prob = math.exp(-result_p.dist[target])
            gap = abs(base_prob - p_prob) / base_prob * 100 if base_prob > 0 else 0.0
        else:
            p_prob = 0.0
            gap = 100.0

        speedup = base_nodes / p_nodes if p_nodes > 0 else float("inf")

        profiles.append(TauProfile(
            tau=tau,
            nodes_explored=p_nodes,
            edges_relaxed=result_p.metrics.edges_relaxed,
            path_probability=p_prob,
            optimality_gap_pct=round(gap, 6),
            speedup_nodes=round(speedup, 4),
        ))

    # Find critical tau: largest tau where gap <= tolerance
    critical_tau = None
    critical_speedup = 1.0
    for p in reversed(profiles):
        if p.optimality_gap_pct <= gap_tolerance:
            critical_tau = p.tau
            critical_speedup = p.speedup_nodes
            break

    return CriticalTauResult(
        critical_tau=critical_tau,
        max_speedup_at_critical=critical_speedup,
        profiles=profiles,
        baseline_nodes=base_nodes,
        baseline_probability=base_prob,
    )

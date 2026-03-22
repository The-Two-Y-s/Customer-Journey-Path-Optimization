"""Critical threshold (tau*) finder.

Sweeps tau values on a given graph, measuring speedup vs optimality gap,
and identifies the critical tau -- the largest tau where the optimality
gap stays below a user-defined tolerance (default 1%).

This formalises Section 1.3 Objective: "find the point where computational
speedup is maximised without a significant drop in path accuracy."
"""

from __future__ import annotations

import math
import time
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
    speedup_wallclock: float  # baseline_time / pruned_time


@dataclass
class CriticalTauResult:
    """Result of a critical-tau sweep."""
    critical_tau: float | None
    max_speedup_at_critical: float
    profiles: List[TauProfile]
    baseline_nodes: int
    baseline_probability: float


DEFAULT_TAU_SWEEP = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]


def _adaptive_tau_sweep(baseline_prob: float) -> list[float]:
    """Generate tau values that are relevant for the given baseline probability.

    If the baseline probability is very small (e.g. 0.0007), fixed tau values
    like 0.001+ would all prune the optimal path.  This function generates
    tau values as fractions of the baseline probability so that the sweep
    actually explores the interesting trade-off region.
    """
    # Fractions of baseline probability to sweep.  The 1.10 (110%) entry
    # intentionally probes *above* the optimal path probability to identify
    # the cliff point where the pruned algorithm starts failing to find a path.
    fractions = [0.10, 0.30, 0.50, 0.70, 0.90, 0.95, 0.99, 1.0, 1.10]
    adaptive = sorted(set(round(baseline_prob * f, 10) for f in fractions))
    # Filter out zero or negative values
    return [t for t in adaptive if t > 0]


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
    taus_input = taus  # save the user's explicit list (or None)

    # Run baseline with wall-clock timing
    t0 = time.perf_counter()
    result_base = dijkstra(graph, source, target)
    base_time = time.perf_counter() - t0
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

    # If user didn't supply explicit taus, build an adaptive sweep centered
    # on the baseline probability so the sweep is always relevant.
    if taus_input is None:
        taus_list = _adaptive_tau_sweep(base_prob)
    else:
        taus_list = sorted(taus_input)

    profiles: list[TauProfile] = []

    for tau in taus_list:
        t0 = time.perf_counter()
        result_p = dijkstra_pruned(graph, source, target, tau=tau)
        p_time = time.perf_counter() - t0
        p_nodes = result_p.metrics.nodes_explored

        if target in result_p.dist:
            p_prob = math.exp(-result_p.dist[target])
            gap = abs(base_prob - p_prob) / base_prob * 100 if base_prob > 0 else 0.0
        else:
            p_prob = 0.0
            gap = 100.0

        speedup = base_nodes / p_nodes if p_nodes > 0 else float("inf")
        speedup_wc = base_time / p_time if p_time > 0 else float("inf")

        profiles.append(TauProfile(
            tau=tau,
            nodes_explored=p_nodes,
            edges_relaxed=result_p.metrics.edges_relaxed,
            path_probability=p_prob,
            optimality_gap_pct=round(gap, 6),
            speedup_nodes=round(speedup, 4),
            speedup_wallclock=round(speedup_wc, 4),
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

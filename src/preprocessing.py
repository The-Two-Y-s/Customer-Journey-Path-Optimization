from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

import pandas as pd


TransitionCounts = Dict[str, Dict[str, int]]
TransitionProbabilities = Dict[str, Dict[str, float]]


def extract_transitions(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Extract (source, target) transitions from a clickstream dataframe.

    Supported formats:
    - explicit `source` and `target` columns
    - event stream with `session_id` + `state`, ordered by `step` or `timestamp`
    """
    if {"source", "target"}.issubset(df.columns):
        pairs = df[["source", "target"]].dropna()
        return [(str(s), str(t)) for s, t in pairs.itertuples(index=False, name=None)]

    if {"session_id", "state"}.issubset(df.columns):
        order_cols: List[str] = []
        if "step" in df.columns:
            order_cols.append("step")
        elif "timestamp" in df.columns:
            order_cols.append("timestamp")

        if not order_cols:
            raise ValueError(
                "Event-stream format requires either `step` or `timestamp` for ordering."
            )

        transitions: List[Tuple[str, str]] = []
        for _, group in df.sort_values(order_cols).groupby("session_id"):
            states = group["state"].astype(str).tolist()
            transitions.extend(zip(states[:-1], states[1:]))
        return transitions

    raise ValueError(
        "Input data must contain either (`source`, `target`) or (`session_id`, `state`)."
    )


def compute_transition_statistics(
    transitions: Iterable[Tuple[str, str]],
) -> Tuple[TransitionCounts, TransitionProbabilities]:
    """Compute transition counts and P(v|u) probabilities."""
    counts: Dict[str, Counter] = defaultdict(Counter)
    for source, target in transitions:
        counts[source][target] += 1

    count_dict: TransitionCounts = {
        source: dict(target_counts) for source, target_counts in counts.items()
    }

    probs: TransitionProbabilities = {}
    for source, target_counts in count_dict.items():
        total = sum(target_counts.values())
        probs[source] = {target: c / total for target, c in target_counts.items()}

    return count_dict, probs


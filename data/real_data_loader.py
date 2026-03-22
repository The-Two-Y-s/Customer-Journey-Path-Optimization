"""Loaders for real-world clickstream datasets.

Each loader returns a pd.DataFrame with columns:
    session_id  – unique session identifier
    state       – page / event / item identifier
    timestamp   – ordering column (int or datetime string)

This format plugs directly into ``src.preprocessing.extract_transitions``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# RetailRocket  (events.csv: timestamp, visitorid, event, itemid, transactionid)
# Strategy: each visitorid is a session.  State = event type (view / addtocart /
# transaction).  This yields a small behavioural graph (~3 nodes, dense edges)
# showing the dominant user-journey funnel.
# For a richer graph we use "event_itemid" as state (e.g. "view_214536502").
# We offer both granularities.
# ---------------------------------------------------------------------------

def load_retailrocket(
    data_dir: str | Path = "data/real_dataset/retailrocket",
    granularity: str = "event",
    max_sessions: Optional[int] = None,
) -> pd.DataFrame:
    """Load RetailRocket events.csv.

    Parameters
    ----------
    granularity : str
        ``"event"`` – states are event types (view/addtocart/transaction) → ~3 nodes.
        ``"item"``  – states are itemid → large graph (~235K nodes).
        ``"event_item"`` – states are ``"event_itemid"`` → very large graph.
    max_sessions : int or None
        Cap the number of sessions (for quick tests).
    """
    path = Path(data_dir) / "events.csv"
    df = pd.read_csv(path)

    # Standardise column names
    df = df.rename(columns={
        "visitorid": "session_id",
        "timestamp": "timestamp",
    })

    if granularity == "event":
        df["state"] = df["event"]
    elif granularity == "item":
        df["state"] = df["itemid"].astype(str)
    elif granularity == "event_item":
        df["state"] = df["event"] + "_" + df["itemid"].astype(str)
    else:
        raise ValueError(f"Unknown granularity: {granularity!r}")

    if max_sessions is not None:
        keep = df["session_id"].unique()[:max_sessions]
        df = df[df["session_id"].isin(set(keep))]

    return df[["session_id", "state", "timestamp"]].copy()


# ---------------------------------------------------------------------------
# RecSys 2015 YOOCHOOSE  (yoochoose-clicks.dat: SessionId, Timestamp, ItemId, Category)
# Strategy: state = ItemId (item-to-item transitions within a click session).
# ---------------------------------------------------------------------------

def load_recsys2015(
    data_dir: str | Path = "data/real_dataset/recsys2015",
    max_sessions: Optional[int] = None,
) -> pd.DataFrame:
    """Load YOOCHOOSE RecSys 2015 click data.

    The full file is ~33M rows.  When *max_sessions* is set the file is
    read in chunks so that memory usage stays bounded.
    """
    path = Path(data_dir) / "yoochoose-clicks.dat"

    if max_sessions is not None:
        # Stream chunks, collect until we have enough sessions
        chunks = []
        seen_sessions: set = set()
        for chunk in pd.read_csv(
            path,
            header=None,
            names=["session_id", "timestamp", "item_id", "category"],
            dtype={"session_id": int, "item_id": int, "category": str},
            chunksize=500_000,
        ):
            new_ids = set(chunk["session_id"].unique())
            seen_sessions.update(new_ids)
            chunks.append(chunk)
            if len(seen_sessions) >= max_sessions:
                break
        df = pd.concat(chunks, ignore_index=True)
        keep = sorted(seen_sessions)[:max_sessions]
        df = df[df["session_id"].isin(set(keep))]
    else:
        df = pd.read_csv(
            path,
            header=None,
            names=["session_id", "timestamp", "item_id", "category"],
            dtype={"session_id": int, "item_id": int, "category": str},
        )

    df["state"] = df["item_id"].astype(str)

    return df[["session_id", "state", "timestamp"]].copy()


# ---------------------------------------------------------------------------
# Quick summary helper
# ---------------------------------------------------------------------------

def dataset_summary(df: pd.DataFrame) -> dict:
    """Return a dict of key statistics for a loaded dataset."""
    from src.preprocessing import extract_transitions, compute_transition_statistics

    transitions = extract_transitions(df)
    counts, probs = compute_transition_statistics(transitions)

    nodes = set()
    edges = 0
    for src, targets in probs.items():
        nodes.add(src)
        nodes.update(targets.keys())
        edges += len(targets)

    return {
        "sessions": df["session_id"].nunique(),
        "total_events": len(df),
        "unique_states": len(nodes),
        "unique_edges": edges,
        "transitions_extracted": len(transitions),
    }

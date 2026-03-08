import math
import unittest

import pandas as pd

from src.dijkstra import dijkstra, reconstruct_path
from src.graph_builder import build_weighted_graph
from src.preprocessing import compute_transition_statistics, extract_transitions


class TestPreprocessing(unittest.TestCase):
    def test_extract_transitions_from_source_target(self):
        df = pd.DataFrame(
            {
                "source": ["Home", "Search", "Product"],
                "target": ["Search", "Product", "Checkout"],
            }
        )

        transitions = extract_transitions(df)

        self.assertEqual(
            transitions,
            [
                ("Home", "Search"),
                ("Search", "Product"),
                ("Product", "Checkout"),
            ],
        )

    def test_extract_transitions_from_session_state(self):
        df = pd.DataFrame(
            {
                "session_id": [1, 1, 1, 2, 2],
                "step": [1, 2, 3, 1, 2],
                "state": ["Home", "Search", "Checkout", "Home", "Exit"],
            }
        )

        transitions = extract_transitions(df)

        self.assertEqual(
            transitions,
            [
                ("Home", "Search"),
                ("Search", "Checkout"),
                ("Home", "Exit"),
            ],
        )

    def test_compute_transition_statistics(self):
        transitions = [
            ("Home", "Search"),
            ("Home", "Search"),
            ("Home", "Cart"),
        ]

        counts, probs = compute_transition_statistics(transitions)

        self.assertEqual(counts["Home"]["Search"], 2)
        self.assertEqual(counts["Home"]["Cart"], 1)
        self.assertAlmostEqual(probs["Home"]["Search"], 2 / 3)
        self.assertAlmostEqual(probs["Home"]["Cart"], 1 / 3)


class TestGraphAndDijkstra(unittest.TestCase):
    def test_build_weighted_graph_uses_negative_log(self):
        probs = {"Home": {"Checkout": 0.5}}
        graph = build_weighted_graph(probs)

        self.assertIn("Home", graph)
        self.assertIn("Checkout", graph)
        self.assertAlmostEqual(graph["Home"][0][1], -math.log(0.5))

    def test_dijkstra_and_reconstruct_path(self):
        graph = {
            "Home": [("Search", 1.0), ("Checkout", 5.0)],
            "Search": [("Checkout", 1.0)],
            "Checkout": [],
        }

        dist, parent = dijkstra(graph, "Home", "Checkout")
        path = reconstruct_path(parent, "Home", "Checkout")

        self.assertAlmostEqual(dist["Checkout"], 2.0)
        self.assertEqual(path, ["Home", "Search", "Checkout"])

    def test_dijkstra_handles_missing_sink_adjacency(self):
        graph = {
            "Home": [("Checkout", 1.0)],
            # Checkout key intentionally omitted.
        }

        dist, parent = dijkstra(graph, "Home", "Checkout")
        path = reconstruct_path(parent, "Home", "Checkout")

        self.assertAlmostEqual(dist["Checkout"], 1.0)
        self.assertEqual(path, ["Home", "Checkout"])


if __name__ == "__main__":
    unittest.main()

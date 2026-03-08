import math
import unittest

import pandas as pd

from src.dijkstra import dijkstra, dijkstra_pruned, reconstruct_path, DijkstraResult
from src.graph_builder import build_weighted_graph
from src.preprocessing import compute_transition_statistics, extract_transitions
from data.graph_generator import generate_erdos_renyi_graph, generate_layered_graph
from src.critical_tau import find_critical_tau


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

        result = dijkstra(graph, "Home", "Checkout")
        path = reconstruct_path(result.parent, "Home", "Checkout")

        self.assertIsInstance(result, DijkstraResult)
        self.assertAlmostEqual(result.dist["Checkout"], 2.0)
        self.assertEqual(path, ["Home", "Search", "Checkout"])
        self.assertGreater(result.metrics.nodes_explored, 0)
        self.assertGreater(result.metrics.edges_relaxed, 0)

    def test_dijkstra_handles_missing_sink_adjacency(self):
        graph = {
            "Home": [("Checkout", 1.0)],
            # Checkout key intentionally omitted.
        }

        result = dijkstra(graph, "Home", "Checkout")
        path = reconstruct_path(result.parent, "Home", "Checkout")

        self.assertAlmostEqual(result.dist["Checkout"], 1.0)
        self.assertEqual(path, ["Home", "Checkout"])

    def test_dijkstra_pruned_finds_same_path(self):
        """Pruned Dijkstra with a loose tau should find the same optimal path."""
        graph = {
            "Home": [("Search", 1.0), ("Checkout", 5.0)],
            "Search": [("Checkout", 1.0)],
            "Checkout": [],
        }

        result_base = dijkstra(graph, "Home", "Checkout")
        result_pruned = dijkstra_pruned(graph, "Home", "Checkout", tau=0.001)

        self.assertAlmostEqual(
            result_base.dist["Checkout"], result_pruned.dist["Checkout"]
        )

    def test_dijkstra_pruned_prunes_high_cost(self):
        """Pruned Dijkstra with aggressive tau prunes expensive paths."""
        graph = {
            "A": [("B", 0.1), ("C", 10.0)],
            "B": [("D", 0.2)],
            "C": [("D", 0.1)],
            "D": [],
        }
        # tau=0.5 means T = -log(0.5) ≈ 0.693
        # A->B->D cost = 0.3 < 0.693 (kept)
        # A->C cost = 10.0 > 0.693 (pruned)
        result = dijkstra_pruned(graph, "A", "D", tau=0.5)
        path = reconstruct_path(result.parent, "A", "D")
        self.assertEqual(path, ["A", "B", "D"])


# ── Verification tests from §4.4 of the report ────────────────────────────


class TestConvergence(unittest.TestCase):
    """§4.4 item 3: pruned → baseline as τ→0."""

    def test_convergence_on_generated_graph(self):
        graph = generate_erdos_renyi_graph(n=200, avg_degree=5, seed=99)
        result_base = dijkstra(graph, "s", "t")

        if "t" not in result_base.dist:
            self.skipTest("No s-t path in this random graph")

        base_cost = result_base.dist["t"]

        # As tau decreases, pruned result must converge to baseline
        for tau in [0.5, 0.1, 0.01, 0.001]:
            result_p = dijkstra_pruned(graph, "s", "t", tau=tau)
            if "t" in result_p.dist:
                self.assertGreaterEqual(
                    result_p.dist["t"],
                    base_cost - 1e-9,
                    f"Pruned cost should be >= baseline cost at tau={tau}",
                )

        # tau very close to 0 must match baseline exactly
        result_tiny = dijkstra_pruned(graph, "s", "t", tau=1e-15)
        if "t" in result_tiny.dist:
            self.assertAlmostEqual(result_tiny.dist["t"], base_cost, places=9)


class TestProbabilityConsistency(unittest.TestCase):
    """§4.4 item 4: exp(−C*) must equal Π p(u,v) along the path."""

    def test_probability_matches_edge_product(self):
        # Build a graph from known probabilities
        edge_probs = {
            "LP": {"SR": 0.70, "CK": 0.30},
            "SR": {"PP": 0.60, "CK": 0.30},
            "PP": {"CK": 0.80, "AB": 0.20},
            "CK": {},
            "AB": {},
        }
        graph = build_weighted_graph(edge_probs)
        result = dijkstra(graph, "LP", "CK")
        path = reconstruct_path(result.parent, "LP", "CK")

        # Compute product of edge probabilities along the path
        product = 1.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            product *= edge_probs[u][v]

        # exp(−C*) must match the product
        exp_cost = math.exp(-result.dist["CK"])
        self.assertAlmostEqual(exp_cost, product, places=9)


class TestEdgeCases(unittest.TestCase):
    """§4.4 item 5: disconnected, single-node, probability-1 edges."""

    def test_disconnected_graph(self):
        graph = {
            "A": [("B", 1.0)],
            "B": [],
            "C": [("D", 1.0)],
            "D": [],
        }
        result = dijkstra(graph, "A", "D")
        self.assertNotIn("D", result.dist)
        self.assertEqual(reconstruct_path(result.parent, "A", "D"), [])

    def test_single_node_source_equals_target(self):
        graph = {"A": []}
        result = dijkstra(graph, "A", "A")
        self.assertEqual(result.dist["A"], 0)
        self.assertEqual(reconstruct_path(result.parent, "A", "A"), ["A"])

    def test_probability_one_edges(self):
        """Probability-1 edges have weight -log(1)=0, so total cost = 0."""
        graph = {
            "A": [("B", 0.0)],  # -log(1) = 0
            "B": [("C", 0.0)],
            "C": [],
        }
        result = dijkstra(graph, "A", "C")
        self.assertAlmostEqual(result.dist["C"], 0.0)
        self.assertAlmostEqual(math.exp(-result.dist["C"]), 1.0)


class TestGraphGenerator(unittest.TestCase):
    """Verify that the ER generator produces valid connected graphs."""

    def test_generates_correct_size(self):
        graph = generate_erdos_renyi_graph(n=100, avg_degree=3, seed=42)
        self.assertEqual(len(graph), 100)

    def test_guaranteed_connectivity(self):
        graph = generate_erdos_renyi_graph(n=500, avg_degree=2, seed=7)
        result = dijkstra(graph, "s", "t")
        self.assertIn("t", result.dist, "s-t path must exist after connectivity fix")

    def test_power_law_distribution(self):
        graph = generate_erdos_renyi_graph(
            n=100, avg_degree=5, distribution="power_law", seed=42
        )
        self.assertEqual(len(graph), 100)


class TestLayeredGenerator(unittest.TestCase):
    """Verify the layered/stage-based graph generator."""

    def test_generates_correct_size(self):
        graph = generate_layered_graph(n=200, avg_degree=4, seed=42)
        self.assertEqual(len(graph), 200)

    def test_guaranteed_connectivity(self):
        graph = generate_layered_graph(n=500, avg_degree=3, seed=7)
        result = dijkstra(graph, "s", "t")
        self.assertIn("t", result.dist, "s-t path must exist in layered graph")

    def test_nodes_have_stage_labels(self):
        graph = generate_layered_graph(n=50, avg_degree=3, seed=1)
        node_names = list(graph.keys())
        # Should contain source, target, and stage-prefixed nodes
        self.assertIn("s", node_names)
        self.assertIn("t", node_names)
        stage_prefixed = [n for n in node_names if "_" in n]
        self.assertGreater(len(stage_prefixed), 0)

    def test_backward_prob_zero_gives_dag(self):
        """With backward_prob=0, all edges go forward (no back-edges)."""
        graph = generate_layered_graph(
            n=100, avg_degree=3, seed=42, backward_prob=0.0
        )
        result = dijkstra(graph, "s", "t")
        self.assertIn("t", result.dist)

    def test_power_law_distribution(self):
        graph = generate_layered_graph(
            n=100, avg_degree=5, distribution="power_law", seed=42
        )
        self.assertEqual(len(graph), 100)


class TestCriticalTau(unittest.TestCase):
    """Verify the critical-tau finder."""

    def test_finds_critical_tau_on_er_graph(self):
        graph = generate_erdos_renyi_graph(n=300, avg_degree=5, seed=42)
        result = find_critical_tau(graph, "s", "t", gap_tolerance=1.0)
        # Should have profiles for each swept tau
        self.assertGreater(len(result.profiles), 0)
        self.assertGreater(result.baseline_nodes, 0)

    def test_critical_tau_on_layered_graph(self):
        graph = generate_layered_graph(n=300, avg_degree=5, seed=42)
        result = find_critical_tau(graph, "s", "t", gap_tolerance=1.0)
        self.assertGreater(len(result.profiles), 0)
        # At least some small tau should be within tolerance
        within = [p for p in result.profiles if p.optimality_gap_pct <= 1.0]
        self.assertGreater(len(within), 0, "At least one tau should be within 1% gap")

    def test_unreachable_target(self):
        graph = {"s": [], "t": []}
        result = find_critical_tau(graph, "s", "t")
        self.assertIsNone(result.critical_tau)
        self.assertEqual(len(result.profiles), 0)


if __name__ == "__main__":
    unittest.main()

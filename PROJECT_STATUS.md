# Project Status Report

**Project:** Customer Journey Path Optimization
**Course:** AT70.02 Algorithm Design and Analysis, Asian Institute of Technology
**Team:** The Two Y's -- Aye Khin Khin Hpone (Yolanda Lim) st125970, Yosakorn Sirisoot st126512
**Date:** March 27, 2026

---

## 0. Recent Changes (March 27, 2026)

**Response to Professor Feedback:**

Addressed professor's recommendations on novelty, parameter consistency, and claim separation:

- **Parameters Unified:** τ values standardized across synthetic and real-data experiments to [0.001, 0.01, 0.05, 0.1, 0.5], ensuring consistency between report and code.
- **Novelty Framing Revised:** Changed from "original algorithm contribution" to "well-motivated, controlled pruning framework with systematic empirical evaluation." Clarified that the main contributions are: (1) formal all-or-nothing correctness property proof, (2) empirical identification of critical τ, and (3) comprehensive evaluation framework.
- **Theoretical vs. Empirical Claims Separated:** Added explicit section in Chapter 4b distinguishing proven theorems (5 formal results, including convergence and all-or-nothing property) from empirical findings (6 validated results and speedup numbers that are not formally guaranteed for arbitrary graphs) and acknowledged limitations (no formal approximation guarantee for τ > 0).

---

## 1. What Has Been Done

The full implementation, experimentation, and validation phases of the project are complete. Both algorithms (Baseline Dijkstra and Probability-Pruned Dijkstra) are implemented, tested, and evaluated across synthetic and real-world datasets. Results confirm the hypothesis.

### Completed milestones:

- Core algorithm implementation (Algorithms 1 and 2 from the report)
- Log-probability weight transformation (w(u,v) = -log(p(u,v)))
- Stale-entry lazy deletion in both algorithms
- Pruning threshold τ with log-space comparison
- DijkstraMetrics dataclass collecting all 7 evaluation metrics per run
- CLI with --tau parameter, printing path probability and optimality gap
- Timing via time.perf_counter() and memory via tracemalloc (separate passes)
- Erdős–Rényi sparse graph generator scalable to |V| = 50,000 (O(n·d) sampling)
- Layered (stage-based) graph generator with 5-stage funnel and backward edges
- Critical-τ finder with adaptive sweep (110% probe + wall-clock speedup)
- Synthetic experiment runner (2,160 rows across full parameter matrix)
- Real-data experiment runner (840 rows across RetailRocket + RecSys 2015: 300 fixed-τ + 540 adaptive-τ)
- Analysis notebook (5 plots + Wilcoxon signed-rank tests)
- 41 unit tests passing (pytest), including convergence and edge-case coverage
- Deterministic seeds via hashlib.md5 for cross-process reproducibility
- Cost-based optimality gap calculation (eliminates FP rounding noise)

---

## 2. File Inventory

### Source Code

| File | Purpose |
|------|---------|
| `src/dijkstra.py` | Core algorithms. `dijkstra()` (baseline) and `dijkstra_pruned()` (threshold-pruned). `edges_relaxed` counts all edges examined (baseline) or edges surviving τ (pruned). Uses `heapq` and `math`. |
| `src/preprocessing.py` | `extract_transitions()` supports source/target and session_id/state CSV formats. `compute_transition_statistics()` computes MLE probabilities. |
| `src/graph_builder.py` | `build_weighted_graph()` builds adjacency list with -log(p) edges. Ensures sink nodes exist. |
| `src/critical_tau.py` | `find_critical_tau()` identifies largest τ* preserving optimality. Adaptive sweep with 110% probe. Reports both node-count and wall-clock speedup. |
| `main.py` | CLI entry point with --source, --target, --k, --tau, --output flags. |

### Data Generation & Loading

| File | Purpose |
|------|---------|
| `data/synthetic_data_generator.py` | Markov-chain clickstream generator → `enhanced_synthetic_journey.csv`. |
| `data/graph_generator.py` | Erdős–Rényi and Layered generators. O(n·d) sampling, BFS connectivity guarantee, per-node probability normalisation. |
| `data/real_data_loader.py` | `load_retailrocket()` (event/item granularity) and `load_recsys2015()` loaders. |

### Experiment Infrastructure

| File | Purpose |
|------|---------|
| `run_experiments.py` | Synthetic experiment matrix: 2 graph types × 3 sizes × 3 degrees × 2 distributions × 6 τ × 10 runs = 2,160 rows. Separate timing/memory passes. hashlib.md5 seeds. Cost-based gap. |
| `run_real_experiments.py` | Real-data experiments: 3 datasets × 20 pairs × (5 fixed τ + 9 adaptive fractions) = 840 rows. |
| `analysis.ipynb` | Results analysis: 5 plots + Wilcoxon statistical tests → `results/img/`. |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_pipeline.py` | 41 unit tests across 12 test classes covering preprocessing, graph building, both Dijkstra variants, convergence (including edges_relaxed and τ=0 equivalence), probability consistency, edge cases, both generators, probability normalisation, k-shortest paths, real-data loaders, real-data pipeline, and critical-τ finder. |

---

## 3. Current Test Results

```
41 passed in 5.74s
```

All 41 tests pass (pytest). Coverage includes:
- Preprocessing: both CSV formats, probability computation
- Graph building: -log transform, missing sink nodes
- Baseline & Pruned Dijkstra: optimal path, metrics, τ pruning
- Convergence: pruned → baseline as τ → 0 (costs and edges_relaxed)
- Probability consistency: exp(-C*) = Π edge probs along path
- Edge cases: disconnected graph, single node, probability-1 edges
- Erdős–Rényi generator: size, connectivity, power-law
- Layered generator: size, connectivity, stages, DAG mode, power-law
- Probability normalisation: outgoing probs sum to 1 (both generators × both distributions)
- k-shortest simple paths: k=1 matches Dijkstra, ascending cost, disconnected
- Real-data loaders: RetailRocket + RecSys 2015 loading, Dijkstra on real graphs
- Critical-τ finder: ER/Layered graphs, unreachable target

---

## 4. Experimental Results Summary

### Synthetic Data (2,160 rows)

| τ | Wall Speedup | Edge Speedup | Path-Found Rate | Gap (when found) |
|---|-------------|-------------|-----------------|------------------|
| 0.001 | 3.3× | 8.7× | 30.6% | 0.00% |
| 0.01 | 24.7× | 79.2× | 5.6% | 0.00% |
| 0.05 | 123.6× | 368.4× | 4.7% | 0.00% |
| 0.1 | 242.6× | 810.5× | 4.4% | 0.00% |
| 0.5 | 738× | 1,986× | 4.2% | 0.00% |

- **179/180** configurations show statistically significant speedup (Wilcoxon, p < 0.05)
- **0/706** found paths have non-zero optimality gap (178 synthetic + 79 fixed-real + 449 adaptive-real)

### Real-Data Validation — Fixed τ (300 rows)

| Dataset | Nodes | Edges | Best Speedup | Path-Found Rate | Max Gap |
|---------|-------|-------|-------------|-----------------|--------|
| RetailRocket (event-level) | 3 | 9 | 5× | 78% | 0.00% |
| RetailRocket (item-level) | 44,711 | 101,528 | 18,882× | 1% | 0.00% |
| RecSys 2015 | 12,935 | 70,442 | 2,309× | 0% | 0.00% |

### Real-Data Validation — Adaptive τ (540 rows)

τ set as a fraction (10%–110%) of each pair's baseline path probability:

| Dataset | Paths Found | Path-Found Rate | Max Speedup | Max Gap |
|---------|-------------|-----------------|-------------|--------|
| RetailRocket (event-level) | 147 / 180 | 82% | 5.8× | 0.00% |
| RetailRocket (item-level) | 152 / 180 | 84% | 3.4× | 0.00% |
| RecSys 2015 | 150 / 180 | 83% | 1.8× | 0.00% |

Adaptive τ resolves the near-zero path-found rates: RecSys goes from 0% to 83%, RR item-level from 1% to 84%. Optimality gap remains exactly 0.00% across all 449 adaptive found paths.

Massive speedups on large real graphs come primarily from early termination (pruning discards everything quickly). Low path-found rates under fixed τ confirm that real transition probabilities are very small.

### Verdict

**Hypothesis supported.** Pruning is admissible — it either preserves the optimal path exactly (0% gap) or prunes it entirely. The trade-off is reachability, not accuracy.

---

## 5. What Has Been Verified Against the Report

| Report Requirement | Status |
|--------------------|--------|
| Algorithm 1 pseudocode (baseline Dijkstra) | Implemented and matches |
| Algorithm 2 pseudocode (pruned Dijkstra with τ) | Implemented and matches |
| Stale-entry lazy deletion check | Implemented |
| Pruning condition: new_dist > T where T = -log(τ) | Implemented |
| Data structures: adjacency list, binary min-heap, hash maps | Implemented |
| time.perf_counter() for timing | Implemented (separate pass) |
| tracemalloc for peak memory | Implemented (separate pass) |
| All 7 evaluation metrics (Section 3.8.2) | Collected and recorded |
| Optimality gap formula (Section 3.8.2) | Implemented (cost-based) |
| Fixed random seeds per configuration | hashlib.md5 (deterministic) |
| ≥ 10 runs per configuration | 10 runs per config |
| Custom sparse graph generator (Table 3.4) | Erdős–Rényi + Layered |
| Layered stage-based graph generator | 5 stages, backward edges |
| Critical-τ finder with adaptive sweep | 110% probe, wall-clock speedup |
| Parameter matrix (Section 3.8.3) | Full matrix executed (2,160 rows) |
| Real-data validation | RetailRocket + RecSys 2015 (840 rows: 300 fixed + 540 adaptive) |
| Convergence verification (Section 4.4 item 3) | Tested (costs + edges_relaxed) |
| Probability consistency (Section 4.4 item 4) | Tested |
| Edge-case testing (Section 4.4 item 5) | Tested |

---

## 6. Project Stage

Based on the report's project timeline (Chapter 8, Figure 8.1):

- **Weeks 1-4 (Implementation): COMPLETE.**
- **Weeks 4-7 (Testing and Experimentation): COMPLETE.** Full synthetic (2,160 rows) and real-data (840 rows: 300 fixed + 540 adaptive) experiments executed and analysed.
- **Weeks 7-10 (Analysis, Writing, Presentation): IN PROGRESS.** Analysis notebook populated. Results written up. Final report and presentation remaining.

---

## 7. How to Run Everything

```bash
# Run unit tests
python -m pytest tests/ -v

# Run CLI with baseline only
python main.py

# Run CLI with baseline + pruned (tau=0.01)
python main.py --tau 0.01

# Run CLI with top-3 paths
python main.py --k 3

# Run full synthetic experiment matrix (2,160 rows)
python run_experiments.py

# Run quick subset for testing
python run_experiments.py --graph-types erdos_renyi --sizes 1000 --runs 2

# Run real-data experiments (300 rows)
python run_real_experiments.py

# Run analysis notebook
jupyter notebook analysis.ipynb
```

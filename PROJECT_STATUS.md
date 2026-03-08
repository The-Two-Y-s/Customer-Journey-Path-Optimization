# Project Status Report

**Project:** Customer Journey Path Optimization
**Course:** AT70.02 Algorithm Design and Analysis, Asian Institute of Technology
**Team:** The Two Y's -- Aye Khin Khin Hpone (Yolanda Lim) st125970, Yosakorn Sirisoot st126512
**Date:** March 8, 2026

---

## 1. What Has Been Done

The full implementation phase of the project is complete. Both algorithms described in the report (Baseline Dijkstra and Probability-Pruned Dijkstra) are implemented, tested, and runnable from the command line. The experiment infrastructure is built and ready to execute the full parameter matrix described in Chapter 3.8 of the report.

### Completed milestones:

- Core algorithm implementation (Algorithms 1 and 2 from the report)
- Log-probability weight transformation (w(u,v) = -log(p(u,v)))
- Stale-entry lazy deletion in both algorithms
- Pruning threshold tau with log-space comparison
- DijkstraMetrics dataclass collecting all 7 evaluation metrics per run
- CLI with --tau parameter, printing path probability and optimality gap
- Timing via time.perf_counter() and memory via tracemalloc (as specified in Table 3.4)
- Erdos-Renyi sparse graph generator scalable to |V| = 50,000
- Experiment runner script covering the full parameter matrix
- 16 unit tests passing, including convergence, probability consistency, and edge-case tests
- README aligned with current implementation

---

## 2. File Inventory

### Source Code

| File | Purpose |
|------|---------|
| `src/dijkstra.py` | Core algorithms. Contains `dijkstra()` (Algorithm 1: Baseline Dijkstra with stale-entry check) and `dijkstra_pruned()` (Algorithm 2: Probability-Pruned Dijkstra with threshold tau). Also contains `reconstruct_path()` for backtracking through the parent map. Both functions return a `DijkstraResult` dataclass containing `dist`, `parent`, and `DijkstraMetrics` (nodes_explored, edges_relaxed, max_pq_size). Uses only `heapq` and `math` from the standard library. |
| `src/preprocessing.py` | Data ingestion. `extract_transitions()` reads a CSV dataframe and extracts (source, target) transition pairs. Supports two input formats: explicit source/target columns, or session_id + state event streams ordered by step or timestamp. `compute_transition_statistics()` computes transition counts and MLE conditional probabilities P(target given source). |
| `src/graph_builder.py` | Graph construction. `build_weighted_graph()` takes a transition probability dictionary and builds a weighted adjacency list where each edge weight is -log(p(u,v)). Ensures sink nodes (nodes with no outgoing edges) are present in the adjacency map to prevent KeyError during traversal. |
| `main.py` | CLI entry point. Loads CSV data (or auto-generates synthetic data if the file is missing), builds the graph, and runs Dijkstra. Supports `--source`, `--target`, `--k` (top-k paths), `--tau` (pruning threshold), and `--output` (graph image). When tau > 0, runs both baseline and pruned algorithms and prints the optimality gap. Reports execution time, peak memory, nodes explored, edges relaxed, max PQ size, path cost, and path probability for each run. |

### Data Generation

| File | Purpose |
|------|---------|
| `data/synthetic_data_generator.py` | Markov-chain clickstream generator. `SyntheticJourneyGenerator` produces realistic customer journey data with states like Home, Search, Product_Trousers, Cart, Checkout, Exit. Generates a CSV with session_id, step, source, target, category, price, location, and timestamp columns. Used to produce the default `enhanced_synthetic_journey.csv` dataset. |
| `data/graph_generator.py` | Erdos-Renyi sparse directed graph generator for controlled experiments. `generate_erdos_renyi_graph()` creates random graphs with configurable |V|, average out-degree, probability distribution (uniform or power-law), and fixed random seed. Guarantees s-t connectivity via BFS check and bridge repair. Scales to |V| = 50,000 using per-node neighbor sampling (O(n * d_avg) instead of O(n^2)). |

### Experiment Infrastructure

| File | Purpose |
|------|---------|
| `run_experiments.py` | Experiment runner. Executes both algorithms across the full parameter matrix from Section 3.8.3 of the report: |V| in {1000, 5000, 10000, 50000}, d_avg in {2, 5, 10}, distribution in {uniform, power_law}, tau in {0, 0.001, 0.01, 0.05, 0.1, 0.5}, with 10 or more runs per configuration. Records all metrics to a CSV file. Supports CLI flags to run subsets (--sizes, --degrees, --distributions, --taus, --runs). |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_pipeline.py` | 16 unit tests covering the full pipeline. Organized into 6 test classes: TestPreprocessing (3 tests for transition extraction and probability computation), TestGraphAndDijkstra (5 tests for graph building, baseline Dijkstra, pruned Dijkstra, and missing-sink handling), TestConvergence (1 test verifying pruned algorithm converges to baseline as tau approaches 0), TestProbabilityConsistency (1 test verifying exp(-C*) equals the product of edge probabilities along the path), TestEdgeCases (3 tests for disconnected graphs, single-node graphs, and probability-1 edges), TestGraphGenerator (3 tests for ER graph size, connectivity guarantee, and power-law distribution). |

### Configuration and Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project documentation. Describes the team, algorithms, CLI usage, example output, and how to run tests and experiments. |
| `.gitignore` | Excludes __pycache__, .pyc files, generated CSV data, experiment results, output images, and the PDF report. |
| `analysis.ipynb` | Jupyter notebook (exists in repo, not yet populated with experiment analysis). |

---

## 3. Current Test Results

```
Ran 16 tests in 0.013s

OK
```

All 16 tests pass. The tests cover:
- Preprocessing: both CSV formats, probability computation
- Graph building: negative-log weight transform
- Baseline Dijkstra: optimal path, missing sink nodes, metrics collection
- Pruned Dijkstra: same-path guarantee at low tau, pruning at high tau
- Convergence: pruned approaches baseline as tau approaches 0 (Section 4.4 item 3)
- Probability consistency: exp(-C*) matches edge probability product (Section 4.4 item 4)
- Edge cases: disconnected graph, single node, probability-1 edges (Section 4.4 item 5)
- Graph generator: correct size, s-t connectivity, power-law support

---

## 4. What Has Been Verified Against the Report

| Report Requirement | Status |
|--------------------|--------|
| Algorithm 1 pseudocode (baseline Dijkstra) | Implemented and matches |
| Algorithm 2 pseudocode (pruned Dijkstra with tau) | Implemented and matches |
| Stale-entry lazy deletion check | Implemented |
| Pruning condition: new_dist > T where T = -log(tau) | Implemented |
| Data structures: adjacency list, binary min-heap (heapq), hash maps | Implemented |
| time.perf_counter() for timing | Implemented |
| tracemalloc for peak memory | Implemented |
| All 7 evaluation metrics (Section 3.8.2) | Collected and recorded |
| Optimality gap formula (Section 3.8.2) | Implemented |
| Fixed random seeds per configuration | Implemented |
| 10 or more runs per configuration | Configured (default = 10) |
| Custom sparse graph generator (Table 3.4) | Implemented (Erdos-Renyi) |
| Parameter matrix: |V|, d_avg, distribution, tau (Section 3.8.3) | Configured in run_experiments.py |
| Convergence verification (Section 4.4 item 3) | Tested |
| Probability consistency check (Section 4.4 item 4) | Tested |
| Edge-case testing (Section 4.4 item 5) | Tested |

---

## 5. Project Stage

Based on the report's project timeline (Chapter 8, Figure 8.1):

- **Weeks 1-4 (Implementation): COMPLETE.** Both algorithms are implemented, tested, and validated for correctness.
- **Weeks 4-7 (Testing and Experimentation): READY TO START.** The experiment runner is built and verified. The parameter matrix matches the report. Execution of the full experiment matrix has not yet been run.
- **Weeks 7-10 (Analysis, Writing, Presentation): NOT STARTED.** Depends on experiment results.

---

## 6. Next Steps

### Step 1: Run the full experiment matrix

```bash
python run_experiments.py
```

This will execute approximately 24 configurations (4 sizes x 3 degrees x 2 distributions) with 6 tau values each, repeated 10 times per configuration. Results are saved to `experiment_results.csv`.

For a quick partial run first:

```bash
python run_experiments.py --sizes 1000 5000 --runs 3
```

The 50,000-node experiments will take longer. Consider running smaller sizes first to verify the pipeline, then scaling up.

### Step 2: Analyze results in analysis.ipynb

Load `experiment_results.csv` into the Jupyter notebook and produce all figures and tables described in the report:

- Table 6.1: Mean execution time and peak memory per graph size (baseline vs pruned at tau=0.01), with standard deviation
- Figure 6.1: tau-sensitivity curves (runtime speedup and optimality gap vs tau)
- Scalability plot: log(execution_time) vs log(|V|) on log-log axes, verify slope matches O(|E| log |V|) theoretical bound
- Search-space reduction: nodes explored and edges relaxed, baseline vs pruned across sizes
- Max PQ size comparison
- Distribution effect: uniform vs power-law pruning effectiveness comparison
- Time-memory-optimality trade-off curve

### Step 3: Manual trace verification

Trace both algorithms on the five-node example graph from Figure 3.2 and Table 3.2 of the report (LP, SR, PP, CK, AB) to confirm the step-by-step dist[] values match:

- LP=0, SR=0.36, PP=0.87, CK=1.09, AB=2.48
- Optimal path: LP -> SR -> PP -> CK with probability 0.336

---

## 7. How to Run Everything

```bash
# Run unit tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run CLI with baseline only
python main.py

# Run CLI with baseline + pruned (tau=0.01)
python main.py --tau 0.01

# Run CLI with top-3 paths
python main.py --k 3

# Run full experiment matrix (10 runs per config)
python run_experiments.py

# Run quick subset for testing
python run_experiments.py --sizes 1000 --runs 2
```

# AT70.02  ·  Algorithm Design and Analysis

# Customer Journey Path Optimization

## Team The Two Y's
- Aye Khin Khin Hpone (Yolanda Lim) st125970
- Yosakorn Sirisoot st126512

---

## Table of Contents

- [AT70.02  ·  Algorithm Design and Analysis](#at7002----algorithm-design-and-analysis)
- [Customer Journey Path Optimization](#customer-journey-path-optimization)
  - [Team The Two Y's](#team-the-two-ys)
  - [Table of Contents](#table-of-contents)
  - [Project Overview](#project-overview)
    - [Hypothesis](#hypothesis)
  - [Project Structure](#project-structure)
  - [Real Datasets](#real-datasets)
  - [How It Works](#how-it-works)
  - [Installation](#installation)
  - [Usage](#usage)
    - [CLI Arguments](#cli-arguments)
  - [Algorithms](#algorithms)
  - [Graph Generators](#graph-generators)
    - [Probability Normalization](#probability-normalization)
  - [Critical-τ Finder](#critical-τ-finder)
  - [Experiment Runner](#experiment-runner)
    - [Real-Data Experiment Runner](#real-data-experiment-runner)
  - [Analysis Notebook](#analysis-notebook)
  - [Testing](#testing)
  - [Experimental Results](#experimental-results)
    - [Synthetic Data — Speedup by τ](#synthetic-data--speedup-by-τ)
    - [Real-Data Validation](#real-data-validation)
    - [Key Findings](#key-findings)

---

## Project Overview
This project finds the most probable customer conversion path in clickstream data.

Transition probabilities are converted to non-negative edge weights:

`w(u,v) = -log(p(u,v))`

This lets us run shortest-path search (Dijkstra) to recover the highest-probability path. A **Probability-Pruned Dijkstra** variant prunes partial paths whose cumulative probability falls below a threshold τ, trading reachability for speed.

### Hypothesis

> **Probability-Pruned Dijkstra provides meaningful speedup over baseline Dijkstra while preserving path optimality at conservative threshold τ values.**

Specifically, we expect that:
1. Pruning significantly reduces the number of edges explored, yielding large speedups.
2. When the pruned algorithm finds a path, it returns the **exact same optimal path** as the baseline (0% optimality gap).
3. The only cost of pruning is reduced reachability — at aggressive τ values, the optimal path may be pruned entirely, so no path is returned.

See [Experimental Results](#experimental-results) for the verdict.

> **Markov assumption:** Transition probabilities are memoryless — P(next page | current page) is independent of the pages visited earlier in the session. This is a standard simplifying assumption in clickstream analysis; real user behaviour may exhibit history-dependent patterns.

## Project Structure

<details>
<summary>Click to expand directory tree</summary>

```text
.
├── data/
│   ├── synthetic_data_generator.py   # Markov-chain clickstream generator
│   ├── graph_generator.py            # ER & Layered graph generators
│   ├── real_data_loader.py           # Loaders for real-world datasets
│   ├── enhanced_synthetic_journey.csv# Generated synthetic dataset
│   └── real_dataset/                 # Real-world datasets (not in repo)
│       ├── retailrocket/             # RetailRocket e-commerce dataset
│       │   ├── events.csv            # 2.7M events (view/addtocart/transaction)
│       │   ├── category_tree.csv
│       │   ├── item_properties_part1.csv
│       │   └── item_properties_part2.csv
│       └── recsys2015/               # YOOCHOOSE RecSys Challenge 2015
│           ├── yoochoose-clicks.dat  # 33M click events
│           ├── yoochoose-buys.dat    # Purchase events
│           └── yoochoose-test.dat    # Test split
├── src/
│   ├── critical_tau.py               # Critical-τ finder (adaptive sweep)
│   ├── dijkstra.py                   # Baseline & Pruned Dijkstra
│   ├── graph_builder.py              # Weighted graph construction
│   └── preprocessing.py              # Clickstream data ingestion
├── tests/
│   └── test_pipeline.py              # 40 unit tests
├── results/
│   ├── experiment_results.csv        # 2,160-row synthetic experiment output
│   ├── real_data_results.csv         # 300-row real-data experiment output
│   └── img/                          # Saved plot images from analysis
├── run_experiments.py                # Synthetic experiment matrix runner
├── run_real_experiments.py            # Real-data experiment runner
├── analysis.ipynb                    # Results analysis (5 plots + stats)
├── main.py                           # CLI entry point
├── requirements.txt
└── README.md
```

</details>

## Real Datasets

Two real-world e-commerce clickstream datasets are used for validation (not included in the repository due to size — download them manually into `data/real_dataset/`):

| Dataset | Folder | Key Files | Scale | Download |
|---------|--------|-----------|-------|----------|
| **RetailRocket** | `data/real_dataset/retailrocket/` | `events.csv`, `category_tree.csv`, `item_properties_part1.csv`, `item_properties_part2.csv` | 2.7M events, 235K items, 1.4M visitors | [Kaggle](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) |
| **RecSys 2015 (YOOCHOOSE)** | `data/real_dataset/recsys2015/` | `yoochoose-clicks.dat`, `yoochoose-buys.dat`, `yoochoose-test.dat` | 33M clicks, 9.2M sessions, ~52K items | [Kaggle](https://www.kaggle.com/datasets/chadgostopp/recsys-challenge-2015) |

<details>
<summary>Dataset details & loader usage</summary>

**RetailRocket** (`events.csv` — columns: `timestamp`, `visitorid`, `event`, `itemid`, `transactionid`)
supports two granularities:
- `event` — states are event types (`view`, `addtocart`, `transaction`) → 3-node funnel graph
- `item` — states are item IDs → large graph (~44K nodes from 50K sessions)

**RecSys 2015** (`yoochoose-clicks.dat` — columns: `SessionId`, `Timestamp`, `ItemId`, `Category`)
uses item-to-item click transitions within sessions → medium graph (~13K nodes from 50K sessions).

Load them programmatically:
```python
from data.real_data_loader import load_retailrocket, load_recsys2015

df_rr = load_retailrocket(granularity="event")              # 3-node funnel
df_rr = load_retailrocket(granularity="item", max_sessions=50000)
df_rc = load_recsys2015(max_sessions=50000)
```

</details>

## How It Works
1. Load clickstream data from CSV.
2. Extract transitions.
3. Estimate transition probabilities `P(target|source)`.
4. Build a weighted directed graph with `-log(probability)` edge weights.
5. Run **Baseline Dijkstra** (Algorithm 1) for the optimal path.
6. Optionally run **Probability-Pruned Dijkstra** (Algorithm 2) with threshold `τ`.
7. Report path, probability Π\* = exp(−C\*), and performance metrics.

<details>
<summary><h3>Probability Assignment</h3></summary>

Transition probabilities are assigned differently depending on the data source:

**Real / Clickstream Data** (`src/preprocessing.py`):  
For every source page `u`, count how many times each outgoing transition `u → v` appears in the session logs, then normalise:

$$P(v \mid u) = \frac{\text{count}(u \to v)}{\sum_{w} \text{count}(u \to w)}$$

This produces a valid conditional distribution where outgoing probabilities from each node sum to 1.

**Synthetic Graph Generators** (`data/graph_generator.py`):  
For each source node `u`, raw edge weights are drawn from the chosen distribution:
- **Uniform:** each raw weight ~ U(0.01, 1)
- **Power-law:** each raw weight via inverse-CDF Pareto (α = 2, x_min = 0.01)

The raw weights are then normalised per source node:

$$P(v \mid u) = \frac{\text{raw}(u \to v)}{\sum_{w} \text{raw}(u \to w)}$$

This ensures `Σ_v P(v|u) = 1` for every node, matching the real-data pipeline.

</details>

<details>
<summary><h3>Why -log(p) Works</h3></summary>

The probability of a complete path `s → v₁ → v₂ → … → t` is the product of its edge probabilities:

$$P(\text{path}) = \prod_{i} P(v_{i+1} \mid v_i)$$

Applying `-log` converts the product into a sum:

$$-\log P(\text{path}) = \sum_{i} \bigl(-\log P(v_{i+1} \mid v_i)\bigr)$$

Since all `P(v|u) ∈ (0, 1]`, each `-log(p)` is non-negative, so Dijkstra's non-negative-weight requirement is satisfied. **Minimising the sum of `-log(p)` weights is equivalent to maximising the path probability.**

</details>

<details>
<summary><h3>Pruning Cases</h3></summary>

The threshold `τ` defines the minimum acceptable path probability. It is converted to log-space as `T = -log(τ)`. During search, if a partial path's cumulative cost exceeds `T`, pruning kicks in and that path is abandoned. This produces three distinct outcomes:

| Case | Condition | Result |
|------|-----------|--------|
| **Optimal path preserved** | Optimal path probability ≥ τ | Pruned Dijkstra returns the exact same path as baseline (0% gap) with significant speedup |
| **Path pruned entirely** | Optimal path probability < τ | No path found — the threshold is too aggressive for this graph |
| **Suboptimal path** | (theoretically possible) | Never observed in practice — pruning either keeps the full optimal path or removes it entirely |

> **Why no suboptimal paths?** Dijkstra settles nodes in non-decreasing cost order. The pruning threshold `T` acts as a uniform upper bound: any node settled with cost ≤ T receives its true shortest-path distance, because all cheaper alternatives were already explored. Thus the pruned algorithm either finds the optimal path intact (when its cost ≤ T) or misses the target entirely (when the cheapest s-t path costs > T) — it can never return a worse path.

In our experiments, the pruning is **all-or-nothing**: across 1,800 pruned runs, every run that found a path returned the exact optimal path (0.00% gap). The only trade-off is reduced reachability — at aggressive τ values (e.g., τ = 0.5), only 3.3% of runs find a path because most optimal paths have probability well below 0.5.

</details>

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `matplotlib`, `scipy` (statistical testing), `pytest` (unit tests).

<details>
<summary><h3>Input Data Formats</h3></summary>

`src/preprocessing.py` supports two formats:

1. Direct transitions
- Required columns: `source`, `target`

2. Session event stream
- Required columns: `session_id`, `state`
- Also requires one ordering column: `step` or `timestamp`

The generated synthetic dataset uses direct transitions (`source`, `target`).

</details>

## Usage

1. Run with defaults (Baseline Dijkstra)
```bash
python main.py
```

Default behavior:
- Reads `data/enhanced_synthetic_journey.csv`.
- If the file does not exist, auto-generates synthetic data using `data/synthetic_data_generator.py`.
- Computes and prints the single optimal path from `Home` to `Checkout`.
- Reports path probability, execution time, peak memory, and exploration metrics.

2. Run with Pruned Dijkstra (threshold τ)
```bash
python main.py --tau 0.01
```

Runs both baseline and pruned Dijkstra side-by-side, printing the optimality gap Δ.

3. Specify dataset and nodes
```bash
python main.py --data data/enhanced_synthetic_journey.csv --source Home --target Checkout
```

4. Compute top-k paths
```bash
python main.py --source Home --target Checkout --k 3
```

5. Export graph visualization
```bash
python main.py --output output.png
```

Note:
- `--output` requires `networkx` and `matplotlib`.

### CLI Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--data` | `data/enhanced_synthetic_journey.csv` | CSV path |
| `--source` | `Home` | Start node |
| `--target` | `Checkout` | Target node |
| `--k` | `1` | Number of paths (k>1 uses best-first k-shortest) |
| `--tau` | `0.0` | Pruning threshold τ (0 = baseline only) |
| `--output` | — | Optional image file path |

<details>
<summary><h3>Example Output</h3></summary>

```text
==================================================
BASELINE DIJKSTRA
==================================================
Optimal Path:
Home -> Checkout

Total Cost (log-space): 2.9200
Path Probability:       0.053949

Metrics:
  Nodes explored:    5
  Edges relaxed:     12
  Max PQ size:       4
  Execution time:    0.123 ms
  Peak memory:       1.23 KB

==================================================
PRUNED DIJKSTRA (tau=0.01)
==================================================
Pruned Path:
Home -> Checkout

Total Cost (log-space): 2.9200
Path Probability:       0.053949

Metrics:
  Nodes explored:    3
  Edges relaxed:     8
  Max PQ size:       3
  Execution time:    0.098 ms
  Peak memory:       0.98 KB

  Optimality gap:    0.0000%
```

</details>

## Algorithms
- **Baseline Dijkstra** (Algorithm 1): Standard Dijkstra with lazy-deletion (stale-entry skip). Complexity: `O((V + E) log V)`. The `edges_relaxed` metric counts every outgoing edge examined from each settled node.
- **Probability-Pruned Dijkstra** (Algorithm 2): Converts threshold τ to log-space (`T = -log(τ)`) and discards any edge whose cumulative cost exceeds T before examining it. `edges_relaxed` counts only the edges that survive the τ threshold — the difference between baseline and pruned `edges_relaxed` is exactly the work saved by pruning. Same worst-case complexity but explores far fewer edges in practice (experiments show ~0.1% of baseline edges examined at τ = 0.1, with median speedups exceeding 200×).

## Graph Generators

Two generators in `data/graph_generator.py` produce controlled graphs for experiments.
Both use O(n·d) scalable edge sampling and guarantee source-target connectivity via BFS + bridge edge.

<details>
<summary>Erdős–Rényi Generator</summary>

Random directed graph for algorithm stress-testing:

```python
from data.graph_generator import generate_erdos_renyi_graph

graph = generate_erdos_renyi_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42
)
```

Parameters: `n` (vertices), `avg_degree`, `distribution` (`"uniform"` for U(0.01, 1) or `"power_law"` for inverse-CDF Pareto with α=2, x_min=0.01), `source`, `target`, `seed`.

</details>

<details>
<summary>Layered (Stage-Based) Generator</summary>

Funnel-shaped graph mimicking a real customer journey (Awareness → Interest → Consideration → Intent → Conversion):

```python
from data.graph_generator import generate_layered_graph

graph = generate_layered_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42,
    stages=["Awareness", "Interest", "Consideration", "Intent", "Conversion"],
    backward_prob=0.15
)
```

Nodes are distributed evenly across stages. Edges go primarily forward (up to +2 stages) with a configurable `backward_prob` for backward links modeling user loops.

</details>

### Probability Normalization

Both generators normalise outgoing edge probabilities per source node so that `Σ_v P(v|u) = 1`. See [Probability Assignment](#probability-assignment) for the full details and formulas.

## Critical-τ Finder

Finds the largest pruning threshold τ\* that preserves optimality (gap < tolerance) while maximizing speedup:

```python
from src.critical_tau import find_critical_tau

result = find_critical_tau(graph, source="s", target="t")
print(result.critical_tau)       # e.g. 0.00069
print(result.max_speedup_at_critical)  # e.g. 1.2x
```

Uses an adaptive tau sweep centered on the baseline path probability (including a 110% probe above the optimal to identify the cliff point where the path is lost), so it works correctly even on sparse/power-law graphs with very low path probabilities. Reports both node-count speedup and wall-clock speedup per τ value.

## Experiment Runner

Run the full parameter matrix described in the report:

```bash
python run_experiments.py
```

<details>
<summary>Customization & output format</summary>

```bash
python run_experiments.py --graph-types erdos_renyi layered \
    --sizes 1000 5000 10000 \
    --degrees 2 5 10 \
    --distributions uniform power_law \
    --taus 0 0.001 0.01 0.05 0.1 0.5 \
    --runs 10 --output results/experiment_results.csv
```

Each configuration generates one baseline row (τ = 0) and one row per non-zero τ. Timing and memory are measured in **separate passes** (tracemalloc is not active during timing) to avoid instrumentation overhead corrupting the stopwatch. Seeds are deterministic per `(run, n, d, graph_type, distribution)` using `hashlib.md5` for cross-process reproducibility.

Output CSV columns: `graph_type`, `graph_size`, `avg_degree`, `distribution`, `tau`, `run`, `seed`, `algorithm`, `execution_time_ms`, `peak_memory_bytes`, `nodes_explored`, `edges_relaxed`, `max_pq_size`, `path_cost`, `path_probability`, `path_length`, `path_found`, `optimality_gap_pct`.

The default matrix (2 graph types × 3 sizes × 3 degrees × 2 distributions × 6 τ values × 10 runs) produces **2,160 rows** saved to `results/experiment_results.csv`.

</details>

### Real-Data Experiment Runner

Run Dijkstra experiments on the real-world datasets:

```bash
python run_real_experiments.py
```

Customize:

```bash
python run_real_experiments.py --recsys-sessions 50000 --pairs 20 --seed 42
```

Tests three dataset configurations (RetailRocket event-level, RetailRocket item-level, RecSys 2015) with 20 random source-target pairs each across 5 τ values. Outputs **300 rows** to `results/real_data_results.csv`.

## Analysis Notebook

`analysis.ipynb` loads `results/experiment_results.csv` and produces:

1. **Speedup vs τ** — per graph type, size, and distribution
2. **Optimality gap vs τ** — shows accuracy trade-off
3. **Scalability** — execution time vs |V| (log-log scale), baseline vs pruned
4. **Critical τ\* heatmap** — largest τ preserving < 5% optimality gap
5. **Memory scaling** — peak memory vs |V|, baseline vs pruned
6. **Statistical testing** — Wilcoxon signed-rank test (paired by run) with significance counts

All plots are saved to `results/img/`. See [Experimental Results](#experimental-results) for the full findings.

## Testing

40 unit tests covering preprocessing, graph building, both Dijkstra variants, convergence (pruned → baseline as τ → 0 — including `edges_relaxed` convergence), probability consistency, edge cases, both generators, probability normalisation regression, k-shortest simple paths, synthetic-dataset end-to-end pipeline, real-data loaders (RetailRocket + RecSys 2015), and the critical-τ finder:

```bash
python -m pytest tests/ -v
```

## Experimental Results

**Verdict: Hypothesis supported.** Across all 1,800 pruned runs (synthetic) and 300 runs (real data), every run that found a path returned the **exact same optimal path** as the baseline (0.00% optimality gap). The pruning is admissible — it either preserves the full optimal path or prunes it entirely, never producing a suboptimal result. **The real trade-off is path-found rate, not accuracy:** aggressive τ values yield massive speedups but reduce the chance of finding any path at all.

### Synthetic Data — Speedup by τ

| τ | Median Speedup | Edges Examined (% of baseline) | Path-Found Rate | Gap (when found) |
|---|---------------|----------------|-----------------|------------------|
| 0.001 | 3.6× | 11.2% | 31.4% | 0.00% |
| 0.01 | 29.0× | 1.4% | 8.1% | 0.00% |
| 0.05 | 138.7× | 0.3% | 5.3% | 0.00% |
| 0.1 | 267.2× | 0.1% | 4.7% | 0.00% |
| 0.5 | 866.3× | ~0% | 3.3% | 0.00% |

### Real-Data Validation

Three dataset configurations were tested (20 random source-target pairs × 5 τ values = 300 rows):

| Dataset | Nodes | Edges | Best Speedup | Max Gap |
|---------|-------|-------|-------------|--------|
| RetailRocket (event-level funnel) | 3 | 9 | 1.8× | 0.00% |
| RetailRocket (item-level, 50K sessions) | 44,711 | 101,528 | 12,768× | 0.00% |
| RecSys 2015 (50K sessions) | 12,935 | 70,442 | 3,070× | 0.00% |

<details>
<summary>Detailed real-data analysis</summary>

The real-data results confirm the hypothesis generalizes beyond synthetic graphs:
- On **large real graphs** (RetailRocket-item, RecSys 2015), pruning delivers **3,000–12,000× speedups**
- The event-level funnel (3 nodes) is too small for meaningful speedup, but still shows 0% gap
- Path-found rates are low on real data because real transition probabilities are very small (most items are visited rarely), making even moderate τ values aggressive

</details>

### Key Findings

1. **180/180** synthetic configurations show statistically significant speedup (Wilcoxon signed-rank, p < 0.05)
2. **100% exact optimality** — every path found by the pruned variant is identical to the baseline optimal path (0.00% gap), on both synthetic and real data
3. With properly normalised transition probabilities (Σ P(v|u) = 1), individual edge probabilities are small, making pruning aggressive and yielding speedups up to 12,768× on real data
4. The trade-off is **reachability, not accuracy**: at τ = 0.5 only 3.3% of synthetic runs find a path, but those that do are guaranteed optimal
5. Both uniform and power-law distributions exhibit consistent behaviour — no distribution-specific asymmetry
6. **Real-data validation** on RetailRocket and RecSys 2015 confirms the hypothesis is not an artifact of synthetic generation
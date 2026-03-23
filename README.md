# Customer Journey Path Optimization

**AT70.02 · Algorithm Design and Analysis** — Asian Institute of Technology

**Team The Two Y's**
| Name | Student ID |
|------|-----------|
| Aye Khin Khin Hpone (Yolanda Lim) | st125970 |
| Yosakorn Sirisoot | st126512 |

---

## Table of Contents

- [Customer Journey Path Optimization](#customer-journey-path-optimization)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [Hypothesis](#hypothesis)
  - [Quick Start](#quick-start)
    - [Installation](#installation)
    - [Basic Usage](#basic-usage)
  - [Algorithms](#algorithms)
    - [Log-Probability Transform](#log-probability-transform)
    - [Baseline Dijkstra](#baseline-dijkstra)
    - [Probability-Pruned Dijkstra](#probability-pruned-dijkstra)
    - [Pruning Correctness](#pruning-correctness)
    - [Metric: `edges_relaxed` and `edges_examined`](#metric-edges_relaxed-and-edges_examined)
  - [Pipeline](#pipeline)
  - [Data](#data)
    - [Input Formats](#input-formats)
    - [Synthetic Graph Generators](#synthetic-graph-generators)
    - [Real-World Datasets](#real-world-datasets)
  - [Experiments](#experiments)
    - [Synthetic Experiment Runner](#synthetic-experiment-runner)
    - [Real-Data Experiment Runner](#real-data-experiment-runner)
    - [Critical-τ Finder](#critical-τ-finder)
    - [Analysis Notebook](#analysis-notebook)
  - [Results](#results)
    - [Synthetic Data — Speedup by τ](#synthetic-data--speedup-by-τ)
    - [Real-Data Validation](#real-data-validation)
    - [Key Findings](#key-findings)
  - [Testing](#testing)
  - [Project Structure](#project-structure)

---

## Overview

This project finds the **most probable customer conversion path** in clickstream data by modelling page transitions as a weighted directed graph and running shortest-path search.

Transition probabilities are converted to non-negative edge weights via `w(u,v) = -log(p(u,v))`, so minimising total weight is equivalent to maximising path probability. A **Probability-Pruned Dijkstra** variant discards partial paths whose cumulative probability falls below a threshold τ, trading reachability for speed.

### Hypothesis

> **Probability-Pruned Dijkstra provides meaningful speedup over baseline Dijkstra while preserving path optimality at conservative τ values.**

We expect:
1. Pruning reduces the number of edges examined, yielding large speedups.
2. When the pruned algorithm finds a path, it returns the **exact same optimal path** as the baseline (0% optimality gap).
3. The only cost is reduced **reachability** — at aggressive τ values, the optimal path may be pruned entirely, so no path is returned.

**Verdict:** Hypothesis supported — see [Results](#results).

> **Markov assumption.** Transition probabilities are memoryless — `P(next | current)` is independent of earlier pages. This is a standard simplifying assumption in clickstream analysis.

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

Dependencies: `pandas ≥ 1.5`, `numpy ≥ 1.23`, `matplotlib ≥ 3.6`, `scipy ≥ 1.10`, `pytest ≥ 7.0`.

### Basic Usage

```bash
# Baseline Dijkstra on synthetic data (auto-generates if missing)
python main.py

# Pruned Dijkstra with threshold τ = 0.01
python main.py --tau 0.01

# Custom dataset, source/target, top-3 paths
python main.py --data data/enhanced_synthetic_journey.csv --source Home --target Checkout --k 3

# Export graph visualisation (requires networkx)
python main.py --output output.png
```

| Flag | Default | Description |
|------|---------|-------------|
| `--data` | `data/enhanced_synthetic_journey.csv` | CSV path |
| `--source` | `Home` | Start node |
| `--target` | `Checkout` | Target node |
| `--k` | `1` | Number of paths (k > 1 uses best-first k-shortest) |
| `--tau` | `0.0` | Pruning threshold τ (0 = baseline only) |
| `--output` | — | Optional image file path |

<details>
<summary>Example output</summary>

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
  Edges examined:    12
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
  Edges examined:    8
  Edges relaxed:     6
  Max PQ size:       3
  Execution time:    0.098 ms
  Peak memory:       0.98 KB

  Optimality gap:    0.0000%
```

</details>

---

## Algorithms

### Log-Probability Transform

The probability of a path `s → v₁ → v₂ → … → t` is the product of edge probabilities:

$$P(\text{path}) = \prod_{i} P(v_{i+1} \mid v_i)$$

Applying `-log` converts the product into a sum:

$$-\log P(\text{path}) = \sum_{i} \bigl(-\log P(v_{i+1} \mid v_i)\bigr)$$

Since `P(v|u) ∈ (0, 1]`, every weight `-log(p)` is non-negative — Dijkstra's requirement is satisfied. **Minimising total weight = maximising path probability.**

### Baseline Dijkstra

Standard Dijkstra (Algorithm 1) with lazy-deletion via stale-entry skip. Uses a binary min-heap priority queue.

- **Complexity:** `O((V + E) log V)`
- **Implementation:** `src/dijkstra.py → dijkstra()`

### Probability-Pruned Dijkstra

Converts the threshold τ to log-space (`T = -log(τ)`) and discards any edge whose cumulative cost would exceed `T` before examining it.

- **Complexity:** Same worst-case `O((V + E) log V)`, but in practice examines far fewer edges.
- **Implementation:** `src/dijkstra.py → dijkstra_pruned()`

### Pruning Correctness

The threshold `T = -log(τ)` acts as a uniform upper bound on path cost. This produces three outcomes:

| Case | Condition | Result |
|------|-----------|--------|
| **Optimal path preserved** | Optimal path cost ≤ T | Same path as baseline with significant speedup |
| **Path pruned entirely** | Optimal path cost > T | No path found — τ is too aggressive |
| **Suboptimal path** | (theoretically possible) | **Never observed** — pruning is all-or-nothing |

> **Why no suboptimal paths?** Dijkstra settles nodes in non-decreasing cost order. Any node settled with cost ≤ T receives its true shortest-path distance, because all cheaper alternatives were already explored. The pruned algorithm either finds the optimal path intact or misses the target entirely — it can never return a worse path.

### Metric: `edges_relaxed` and `edges_examined`

Two edge counters provide complementary views of algorithmic work:

| Algorithm | `edges_examined` | `edges_relaxed` |
|-----------|-----------------|-----------------|
| **Baseline** | Every outgoing edge from a settled node | Same as `edges_examined` (no pruning) |
| **Pruned** | Every outgoing edge from a settled node (before threshold check) | Only edges that **survived** the τ threshold |

- The ratio `baseline_edges_examined / pruned_edges_examined` is an **apples-to-apples** comparison of total edge work.
- The ratio `baseline_edges_relaxed / pruned_edges_relaxed` measures **pruning aggressiveness** — how much work the threshold eliminates — but is not a strict like-for-like comparison since the pruned counter excludes threshold-rejected edges.
- The difference `pruned_edges_examined − pruned_edges_relaxed` isolates the **pruning overhead** (edges checked then discarded).

---

## Pipeline

1. **Load** clickstream data from CSV
2. **Extract** transitions (`src/preprocessing.py`)
3. **Estimate** transition probabilities `P(v|u)` via MLE counts
4. **Build** weighted directed graph with `-log(p)` edges (`src/graph_builder.py`)
5. **Run** Baseline Dijkstra for the optimal path (`src/dijkstra.py`)
6. **Optionally run** Pruned Dijkstra with threshold τ
7. **Report** path, probability Π\* = exp(−C\*), and performance metrics

<details>
<summary>Probability assignment details</summary>

**Real / clickstream data** — for every source page `u`, count outgoing transitions and normalise:

$$P(v \mid u) = \frac{\text{count}(u \to v)}{\sum_{w} \text{count}(u \to w)}$$

**Synthetic generators** — draw raw weights from the chosen distribution (uniform or power-law), then normalise per source node:

$$P(v \mid u) = \frac{\text{raw}(u \to v)}{\sum_{w} \text{raw}(u \to w)}$$

Both ensure `Σ_v P(v|u) = 1` for every node.

</details>

---

## Data

### Input Formats

`src/preprocessing.py` supports two CSV formats:

| Format | Required columns | Notes |
|--------|-----------------|-------|
| Direct transitions | `source`, `target` | One row per transition |
| Session event stream | `session_id`, `state` + (`step` or `timestamp`) | Consecutive events within a session form transitions |

### Synthetic Graph Generators

Two generators in `data/graph_generator.py` produce controlled graphs for experiments. Both use O(n·d) scalable edge sampling, guarantee s → t connectivity via BFS + bridge edge, and normalise outgoing probabilities to sum to 1.

<details>
<summary>Erdős–Rényi generator</summary>

Random sparse directed graph for algorithm stress-testing:

```python
from data.graph_generator import generate_erdos_renyi_graph

graph = generate_erdos_renyi_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42
)
```

Parameters: `n` (vertices), `avg_degree`, `distribution` (`"uniform"` or `"power_law"`), `source`, `target`, `seed`.

</details>

<details>
<summary>Layered (stage-based) generator</summary>

Funnel-shaped graph mimicking a customer journey (Awareness → Interest → Consideration → Intent → Conversion):

```python
from data.graph_generator import generate_layered_graph

graph = generate_layered_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42,
    backward_prob=0.15  # fraction of edges going backward (user loops)
)
```

Nodes are distributed evenly across stages. Edges go primarily forward (up to +2 stages); `backward_prob` controls backward links modelling user loops. Under the `"uniform"` distribution, forward edges draw transition probabilities from U(0.3, 0.8) while backward edges draw from U(0.05, 0.3), reflecting that forward progression is more likely than backtracking.

</details>

### Real-World Datasets

Two e-commerce clickstream datasets are used for validation (not included in the repo — download manually into `data/real_dataset/`):

| Dataset | Scale | Graph size (50K sessions) | Download |
|---------|-------|--------------------------|----------|
| **RetailRocket** | 2.7M events, 1.4M visitors | ~44K nodes, ~101K edges (item-level) | [Kaggle](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) |
| **RecSys 2015 (YOOCHOOSE)** | 33M clicks, 9.2M sessions | ~13K nodes, ~70K edges | [Kaggle](https://www.kaggle.com/datasets/chadgostopp/recsys-challenge-2015) |

<details>
<summary>Loader usage</summary>

```python
from data.real_data_loader import load_retailrocket, load_recsys2015

df_rr = load_retailrocket(granularity="event")              # 3-node funnel
df_rr = load_retailrocket(granularity="item", max_sessions=50000)  # large graph
df_rc = load_recsys2015(max_sessions=50000)
```

RetailRocket supports two granularities:
- `"event"` — states are event types (`view`/`addtocart`/`transaction`) → 3-node funnel
- `"item"` — states are item IDs → large graph

RecSys 2015 uses item-to-item click transitions within sessions.

</details>

---

## Experiments

### Synthetic Experiment Runner

```bash
python run_experiments.py
```

Runs both algorithms across the full parameter matrix:
- **Graph types:** Erdős–Rényi, Layered
- **|V|:** 1,000 / 5,000 / 10,000 (pass `--sizes 50000` for larger)
- **Avg degree:** 2 / 5 / 10
- **Distribution:** uniform / power-law
- **τ:** 0, 0.001, 0.01, 0.05, 0.1, 0.5
- **Runs:** 10 per configuration (deterministic `hashlib.md5` seeds)

Timing and memory are measured in **separate passes** so tracemalloc overhead does not corrupt the stopwatch. Default matrix produces **2,160 rows** → `results/experiment_results.csv`.

<details>
<summary>Customisation</summary>

```bash
python run_experiments.py --graph-types erdos_renyi \
    --sizes 1000 5000 --degrees 2 5 --runs 3
```

Output CSV columns: `graph_type`, `graph_size`, `avg_degree`, `distribution`, `tau`, `run`, `seed`, `algorithm`, `execution_time_ms`, `peak_memory_bytes`, `nodes_explored`, `edges_examined`, `edges_relaxed`, `max_pq_size`, `path_cost`, `path_probability`, `path_length`, `path_found`, `optimality_gap_pct`.

</details>

### Real-Data Experiment Runner

```bash
python run_real_experiments.py
```

Tests three dataset configurations (RetailRocket event-level, RetailRocket item-level, RecSys 2015) with 20 random reachable source-target pairs each across 5 τ values → **300 rows** → `results/real_data_results.csv`.

```bash
python run_real_experiments.py --recsys-sessions 50000 --pairs 20 --seed 42
```

### Critical-τ Finder

Finds the largest threshold τ\* that preserves optimality (gap < tolerance) while maximising speedup:

```python
from src.critical_tau import find_critical_tau

result = find_critical_tau(graph, source="s", target="t")
print(result.critical_tau)              # e.g. 0.00069
print(result.max_speedup_at_critical)   # e.g. 1.2×
```

Uses an adaptive sweep centered on the baseline path probability — including a 110% probe above the optimal to identify the cliff point where the path is lost. Reports both node-count speedup and wall-clock speedup per τ value.

### Analysis Notebook

`analysis.ipynb` loads the experiment CSV and produces five plots + statistical tests:

1. **Speedup vs τ** — per graph type, size, and distribution
2. **Optimality gap vs τ** — accuracy trade-off
3. **Scalability** — execution time vs |V| (log-log), baseline vs pruned
4. **Critical τ\* heatmap** — largest τ preserving < 5% gap
5. **Memory scaling** — peak memory vs |V|
6. **Statistical testing** — Wilcoxon signed-rank (paired by run)

Plots are saved to `results/img/`.

---

## Results

**Verdict: Hypothesis supported.** Across 1,800 pruned runs (synthetic) and 300 runs (real data), every run that found a path returned the **exact same optimal path** as the baseline (0.00% optimality gap). **The real trade-off is path-found rate, not accuracy:** aggressive τ values yield massive speedups but reduce the chance of finding any path.

### Synthetic Data — Speedup by τ

| τ | Median Speedup | Edges Examined (% of baseline) | Path-Found Rate | Gap (when found) |
|---|---------------|----------------|-----------------|------------------|
| 0.001 | 8.8× | 11.4% | 28.6% | 0.00% |
| 0.01 | 82.1× | 1.2% | 5.8% | 0.00% |
| 0.05 | 374.4× | 0.3% | 4.7% | 0.00% |
| 0.1 | 790.8× | 0.1% | 4.4% | 0.00% |
| 0.5 | 2,124× | ~0% | 3.9% | 0.00% |

### Real-Data Validation

Three dataset configurations (20 random source-target pairs × 5 τ values = 300 rows). "Best speedup" is the maximum wall-clock speedup across all runs, including runs where the pruned variant terminates quickly because it prunes all paths:

| Dataset | Nodes | Edges | Best Speedup | Path-Found Rate | Max Gap |
|---------|-------|-------|-------------|-----------------|--------|
| RetailRocket (event-level funnel) | 3 | 9 | 4.9× | 78% | 0.00% |
| RetailRocket (item-level, 50K sessions) | 44,711 | 101,528 | 27,693× | 1% | 0.00% |
| RecSys 2015 (50K sessions) | 12,935 | 70,442 | 4,191× | 0% | 0.00% |

> **Note on real-data path-found rates:** Real graphs have very low per-edge probabilities (items visited rarely), so even the smallest tested τ (0.0001) prunes most paths. The massive speedups on large real graphs come primarily from early termination. On the 3-node funnel (where probabilities are higher), pruning preserves most paths and still delivers measurable speedup.

### Key Findings

1. **180/180** synthetic configurations show statistically significant speedup (Wilcoxon signed-rank, p < 0.05)
2. **100% exact optimality** — every path found by the pruned variant matches the baseline (0.00% gap), on both synthetic and real data (0/171 synthetic, 0/79 real with non-zero gap)
3. Normalised transition probabilities (`Σ P(v|u) = 1`) make individual edge probabilities small, so pruning is aggressive — speedups up to **27,693×** on real data (wall-clock)
4. The trade-off is **reachability, not accuracy**: at τ = 0.5 only 3.9% of synthetic runs find a path, but those that do are guaranteed optimal
5. Both uniform and power-law distributions exhibit consistent behaviour
6. **Real-data validation** on RetailRocket and RecSys 2015 confirms the hypothesis generalises beyond synthetic graphs

---

## Testing

41 unit tests across 11 test classes:

```bash
python -m pytest tests/ -v
```

| Test class | Coverage |
|-----------|----------|
| `TestPreprocessing` | Transition extraction (both CSV formats), MLE probability computation |
| `TestGraphAndDijkstra` | Graph building, baseline & pruned Dijkstra, missing-sink handling |
| `TestConvergence` | Pruned → baseline as τ → 0 (costs, `edges_examined`, and `edges_relaxed`) |
| `TestProbabilityConsistency` | exp(−C\*) = Π edge probs along path |
| `TestEdgeCases` | Disconnected graph, single node, probability-1 edges |
| `TestGraphGenerator` | ER size, connectivity, power-law support |
| `TestLayeredGenerator` | Layered size, connectivity, stage labels, DAG mode |
| `TestProbabilityNormalization` | Outgoing probs sum to 1 (both generators × both distributions) |
| `TestKShortestSimplePaths` | k=1 matches Dijkstra, ascending cost, simple paths, disconnected |
| `TestRealDataLoaders` | RetailRocket + RecSys 2015 loading, Dijkstra on real graphs |
| `TestCriticalTau` | Critical-τ on ER/Layered graphs, unreachable target |

---

## Project Structure

```text
.
├── src/
│   ├── dijkstra.py                   # Baseline & Pruned Dijkstra
│   ├── graph_builder.py              # Weighted graph construction (-log transform)
│   ├── preprocessing.py              # Clickstream data → transitions → probabilities
│   └── critical_tau.py               # Critical-τ finder (adaptive sweep)
├── data/
│   ├── graph_generator.py            # ER & Layered graph generators
│   ├── synthetic_data_generator.py   # Markov-chain clickstream generator
│   ├── real_data_loader.py           # RetailRocket & RecSys 2015 loaders
│   ├── enhanced_synthetic_journey.csv
│   └── real_dataset/                 # (download manually — not in repo)
│       ├── retailrocket/
│       └── recsys2015/
├── tests/
│   └── test_pipeline.py              # 41 unit tests
├── results/
│   ├── experiment_results.csv        # 2,160-row synthetic experiment output
│   ├── real_data_results.csv         # 300-row real-data experiment output
│   └── img/                          # Saved plots from analysis notebook
├── run_experiments.py                # Synthetic experiment matrix runner
├── run_real_experiments.py           # Real-data experiment runner
├── analysis.ipynb                    # Results analysis & visualisation
├── main.py                           # CLI entry point
├── requirements.txt
└── README.md
```
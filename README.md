# AT70.02  ·  Algorithm Design and Analysis

# Customer Journey Path Optimization

## Team The Two Y's
- Aye Khin Khin Hpone (Yolanda Lim) st125970
- Yosakorn Sirisoot st126512

## Project Overview
This project finds the most probable customer conversion path in clickstream data.

Transition probabilities are converted to non-negative edge weights:

`w(u,v) = -log(p(u,v))`

This lets us run shortest-path search (Dijkstra) to recover the highest-probability path. A **Probability-Pruned Dijkstra** variant prunes partial paths whose cumulative probability falls below a threshold τ, trading optimality for speed.

> **Markov assumption:** Transition probabilities are memoryless — P(next page | current page) is independent of the pages visited earlier in the session. This is a standard simplifying assumption in clickstream analysis; real user behaviour may exhibit history-dependent patterns.

## Project Structure
```text
.
├── data/
│   ├── synthetic_data_generator.py   # Markov-chain clickstream generator
│   ├── graph_generator.py            # ER & Layered graph generators
│   └── enhanced_synthetic_journey.csv# Generated synthetic dataset
├── src/
│   ├── critical_tau.py               # Critical-τ finder (adaptive sweep)
│   ├── dijkstra.py                   # Baseline & Pruned Dijkstra
│   ├── graph_builder.py              # Weighted graph construction
│   └── preprocessing.py              # Clickstream data ingestion
├── tests/
│   └── test_pipeline.py              # 24 unit tests
├── results/
│   ├── experiment_results.csv        # 2,160-row experiment output
│   └── img/                          # Saved plot images from analysis
├── run_experiments.py                # Full experiment matrix runner
├── analysis.ipynb                    # Results analysis (5 plots + stats)
├── main.py                           # CLI entry point
├── requirements.txt
└── README.md
```

## How It Works
1. Load clickstream data from CSV.
2. Extract transitions.
3. Estimate transition probabilities `P(target|source)`.
4. Build a weighted directed graph with `-log(probability)` edge weights.
5. Run **Baseline Dijkstra** (Algorithm 1) for the optimal path.
6. Optionally run **Probability-Pruned Dijkstra** (Algorithm 2) with threshold `τ`.
7. Report path, probability Π\* = exp(−C\*), and performance metrics.

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `matplotlib`, `scipy` (statistical testing), `pytest` (unit tests).

## Input Data Formats
`src/preprocessing.py` supports two formats:

1. Direct transitions
- Required columns: `source`, `target`

2. Session event stream
- Required columns: `session_id`, `state`
- Also requires one ordering column: `step` or `timestamp`

The generated synthetic dataset uses direct transitions (`source`, `target`).

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

## CLI Arguments
| Flag | Default | Description |
|------|---------|-------------|
| `--data` | `data/enhanced_synthetic_journey.csv` | CSV path |
| `--source` | `Home` | Start node |
| `--target` | `Checkout` | Target node |
| `--k` | `1` | Number of paths (k>1 uses best-first k-shortest) |
| `--tau` | `0.0` | Pruning threshold τ (0 = baseline only) |
| `--output` | — | Optional image file path |

## Example Output
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

## Algorithms
- **Baseline Dijkstra** (Algorithm 1): Standard Dijkstra with lazy-deletion (stale-entry skip). Complexity: `O((V + E) log V)`.
- **Probability-Pruned Dijkstra** (Algorithm 2): Converts threshold τ to log-space (`T = -log(τ)`) and skips any edge relaxation where cumulative cost exceeds T. Same worst-case complexity but explores far fewer nodes/edges in practice (experiments show ~0.1% of baseline edges relaxed at τ = 0.1, with median speedups exceeding 200×).

## Graph Generators

Two generators in `data/graph_generator.py` produce controlled graphs for experiments.
Both use O(n·d) scalable edge sampling and guarantee source-target connectivity via BFS + bridge edge.

### Erdős–Rényi Generator
Random directed graph for algorithm stress-testing:

```python
from data.graph_generator import generate_erdos_renyi_graph

graph = generate_erdos_renyi_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42
)
```

Parameters: `n` (vertices), `avg_degree`, `distribution` (`"uniform"` for U(0.01, 1) or `"power_law"` for inverse-CDF Pareto with α=2, x_min=0.01), `source`, `target`, `seed`.

### Layered (Stage-Based) Generator
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

### Probability Normalization

Both generators **normalise outgoing edge probabilities per source node** so that `Σ_v P(v|u) = 1` for every node `u`. Raw values are drawn from the chosen distribution (uniform or power-law), then divided by their per-node sum to form a valid conditional distribution. This matches the real-data pipeline in `src/preprocessing.py` and ensures the `-log(p)` transformation produces meaningful shortest-path weights.

## Critical-τ Finder

Finds the largest pruning threshold τ\* that preserves optimality (gap < tolerance) while maximizing speedup:

```python
from src.critical_tau import find_critical_tau

result = find_critical_tau(graph, source="s", target="t")
print(result.critical_tau)       # e.g. 0.00069
print(result.max_speedup_at_critical)  # e.g. 1.2x
```

Uses an adaptive tau sweep centered on the baseline path probability, so it works correctly even on sparse/power-law graphs with very low path probabilities.

## Experiment Runner

Run the full parameter matrix described in the report:

```bash
python run_experiments.py
```

Customize with CLI flags:

```bash
python run_experiments.py --graph-types erdos_renyi layered \
    --sizes 1000 5000 10000 \
    --degrees 2 5 10 \
    --distributions uniform power_law \
    --taus 0 0.001 0.01 0.05 0.1 0.5 \
    --runs 10 --output results/experiment_results.csv
```

Each configuration generates one baseline row (τ = 0) and one row per non-zero τ. Timing and memory are measured in **separate passes** (tracemalloc is not active during timing) to avoid instrumentation overhead corrupting the stopwatch. Seeds are deterministic per `(run, n, d, graph_type, distribution)`.

Output CSV columns: `graph_type`, `graph_size`, `avg_degree`, `distribution`, `tau`, `run`, `seed`, `algorithm`, `execution_time_ms`, `peak_memory_bytes`, `nodes_explored`, `edges_relaxed`, `max_pq_size`, `path_cost`, `path_probability`, `path_length`, `path_found`, `optimality_gap_pct`.

The default matrix (2 graph types × 3 sizes × 3 degrees × 2 distributions × 6 τ values × 10 runs) produces **2,160 rows** saved to `results/experiment_results.csv`.

## Analysis Notebook

`analysis.ipynb` loads `results/experiment_results.csv` and produces:

1. **Speedup vs τ** — per graph type, size, and distribution
2. **Optimality gap vs τ** — shows accuracy trade-off
3. **Scalability** — execution time vs |V| (log-log scale), baseline vs pruned
4. **Critical τ\* heatmap** — largest τ preserving < 5% optimality gap
5. **Memory scaling** — peak memory vs |V|, baseline vs pruned
6. **Statistical testing** — Wilcoxon signed-rank test (paired by run) with significance counts

Key findings from the experiments:
- **180/180** configurations show statistically significant speedups (Wilcoxon signed-rank, p < 0.05)
- At τ = 0.01, pruned Dijkstra explores only ~1.4% of baseline edges (median 29× speedup)
- Both uniform and power-law distributions show consistent speedup behaviour (~10% path-found rate, ~90× median speedup)
- Pruning is admissible: 0.00% optimality gap across all runs that found a path

## Testing

24 unit tests covering preprocessing, graph building, both Dijkstra variants, convergence (pruned → baseline as τ → 0), probability consistency, edge cases, both generators, and the critical-τ finder:

```bash
python -m pytest tests/ -v
```

## Experimental Results

**Hypothesis:** Probability-Pruned Dijkstra provides meaningful speedup over the baseline while preserving path optimality at conservative τ values.

**Verdict: Supported.** The pruning is *admissible* — across all 1,800 pruned runs, every run that found a path returned the **exact same optimal path** as the baseline (0.00% optimality gap). The only cost is reduced reachability at aggressive τ values.

### Speedup by τ

| τ | Median Speedup | Edges Explored | Path-Found Rate | Gap (when found) |
|---|---------------|----------------|-----------------|------------------|
| 0.001 | 3.6× | 11.2% | 31.4% | 0.00% |
| 0.01 | 29.0× | 1.4% | 8.1% | 0.00% |
| 0.05 | 138.7× | 0.3% | 5.3% | 0.00% |
| 0.1 | 267.2× | 0.1% | 4.7% | 0.00% |
| 0.5 | 866.3× | ~0% | 3.3% | 0.00% |

### Key findings

- **180/180** configurations show statistically significant speedup (Wilcoxon signed-rank, p < 0.05)
- **100% exact optimality** — every path found by the pruned variant is identical to the baseline optimal path
- With properly normalised transition probabilities (Σ P(v|u) = 1), individual edge probabilities are smaller, making pruning more aggressive and yielding higher speedups
- The trade-off is **all-or-nothing**: the pruning either preserves the full optimal path or prunes it entirely — it never returns a suboptimal path
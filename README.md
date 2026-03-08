# AT70.02  ·  Algorithm Design and Analysis

# Customer Journey Path Optimization

## Team The Two Y's
- Aye Khin Khin Hpone (Yolanda Lim) st125970
- Yosakorn Sirisoot st126512

## Project Overview
This project finds the most probable customer conversion path in clickstream data.

Transition probabilities are converted to non-negative edge weights:

`w(u,v) = -log(p(u,v))`

This lets us run shortest-path search (Dijkstra) to recover the highest-probability path.

## Project Structure
```text
.
├── data/
│   ├── synthetic_data_generator.py   # Markov-chain clickstream generator
│   └── graph_generator.py            # ER & Layered graph generators
├── src/
│   ├── critical_tau.py               # Critical-τ finder
│   ├── dijkstra.py                   # Baseline & Pruned Dijkstra
│   ├── graph_builder.py
│   └── preprocessing.py
├── tests/
│   └── test_pipeline.py
├── run_experiments.py                # Full experiment matrix runner
├── analysis.ipynb
├── main.py
├── PROJECT_STATUS.md
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
- Reads `enhanced_synthetic_journey.csv`.
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
python main.py --data enhanced_synthetic_journey.csv --source Home --target Checkout
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
| `--data` | `enhanced_synthetic_journey.csv` | CSV path |
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
- **Baseline Dijkstra** (Algorithm 1): Standard Dijkstra with lazy-deletion stale-entry check. Complexity: `O((V + E) log V)`.
- **Probability-Pruned Dijkstra** (Algorithm 2): Prunes partial paths whose cumulative probability falls below threshold τ. Same worst-case complexity but explores fewer nodes in practice.

## Graph Generators

Two generators in `data/graph_generator.py` produce controlled graphs for experiments.
Both use O(n·d) scalable edge sampling and guarantee source-target connectivity.

### Erdős–Rényi Generator
Random directed graph for algorithm stress-testing:

```python
from data.graph_generator import generate_erdos_renyi_graph

graph = generate_erdos_renyi_graph(
    n=10000, avg_degree=5.0, distribution="uniform", seed=42
)
```

Parameters: `n` (vertices), `avg_degree`, `distribution` (`"uniform"` or `"power_law"`), `source`, `target`, `seed`.

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

Nodes are distributed evenly across stages. Edges go primarily forward (next stage) with a configurable `backward_prob` for same-stage or backward links.

## Critical-τ Finder

Finds the largest pruning threshold τ\* that preserves optimality (gap < tolerance) while maximizing speedup:

```python
from src.critical_tau import find_critical_tau

result = find_critical_tau(graph, source="0", target="99")
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
    --sizes 1000 5000 10000 50000 \
    --degrees 2 5 10 \
    --distributions uniform power_law \
    --taus 0 0.001 0.01 0.05 0.1 0.5 \
    --runs 10 --output experiment_results.csv
```

Results are saved to CSV with columns: `graph_type`, `n`, `avg_degree`, `distribution`, `seed`, `tau`, `baseline_time_s`, `pruned_time_s`, `baseline_mem_bytes`, `pruned_mem_bytes`, `baseline_nodes`, `pruned_nodes`, `baseline_edges`, `pruned_edges`, `baseline_maxpq`, `pruned_maxpq`, `gap_pct`.

## Testing

24 unit tests covering the full pipeline:

```bash
python -m unittest discover -s tests -p "test_*.py"
```
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
│   └── synthetic_data_generator.py
├── src/
│   ├── dijkstra.py
│   ├── graph_builder.py
│   └── preprocessing.py
├── analysis.ipynb
├── main.py
└── README.md
```

## How It Works
1. Load clickstream data from CSV.
2. Extract transitions.
3. Estimate transition probabilities `P(target|source)`.
4. Build a weighted directed graph with `-log(probability)` edge weights.
5. Run shortest-path search for optimal or top-k paths.

## Input Data Formats
`src/preprocessing.py` supports two formats:

1. Direct transitions
- Required columns: `source`, `target`

2. Session event stream
- Required columns: `session_id`, `state`
- Also requires one ordering column: `step` or `timestamp`

The generated synthetic dataset uses direct transitions (`source`, `target`).

## Usage

1. Run with defaults
```bash
python main.py
```

Default behavior:
- Reads `enhanced_synthetic_journey.csv`.
- If the file does not exist, auto-generates synthetic data using `data/synthetic_data_generator.py`.
- Computes and prints the single optimal path from `Home` to `Checkout`.

2. Specify dataset and nodes
```bash
python main.py --data enhanced_synthetic_journey.csv --source Home --target Checkout
```

3. Compute top-k paths
```bash
python main.py --data enhanced_synthetic_journey.csv --source Home --target Checkout --k 3
```

4. Export graph visualization
```bash
python main.py --data enhanced_synthetic_journey.csv --source Home --target Checkout --k 3 --output output.png
```

Note:
- `--output` requires `networkx` and `matplotlib`.

## CLI Arguments
- `--data`: CSV path (default: `enhanced_synthetic_journey.csv`)
- `--source`: start node (default: `Home`)
- `--target`: end node (default: `Checkout`)
- `--k`: number of paths (default: `1`)
- `--output`: optional image file path

## Example Output
```text
Optimal Path:
Home -> Checkout

Total Cost: 2.92
```

```text
Top 3 Paths:
1. Home -> Checkout (Cost: 2.92)
2. Home -> Cart -> Checkout (Cost: 3.33)
3. Home -> Search -> Cart -> Checkout (Cost: 3.78)
```

## Complexity
- Dijkstra with a priority queue: `O((V + E) log V)`

## Testing
Run the unit tests with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```
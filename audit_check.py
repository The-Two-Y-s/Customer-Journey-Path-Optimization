"""Temporary audit script to cross-check report claims against actual data."""
import csv, statistics, math
from collections import defaultdict

# ============ SYNTHETIC RESULTS ============
rows = list(csv.DictReader(open('results/experiment_results.csv')))
pruned = [r for r in rows if r['algorithm'] == 'pruned']
baseline = [r for r in rows if r['algorithm'] == 'baseline']

print(f"Total rows: {len(rows)}")
print(f"Baseline rows: {len(baseline)}, Pruned rows: {len(pruned)}")

# 1. Path-found rates by tau
tau_found = defaultdict(lambda: {'total': 0, 'found': 0})
for r in pruned:
    tau = r['tau']
    tau_found[tau]['total'] += 1
    if r['path_found'] == '1':
        tau_found[tau]['found'] += 1

print("\n=== PATH FOUND RATES BY TAU ===")
for tau in sorted(tau_found.keys(), key=float):
    d = tau_found[tau]
    pct = d['found'] / d['total'] * 100
    print(f"  tau={tau}: {d['found']}/{d['total']} = {pct:.1f}%")

# 2. Optimality gap
found_pruned = [r for r in pruned if r['path_found'] == '1' and float(r['optimality_gap_pct']) < 100]
gaps = [float(r['optimality_gap_pct']) for r in found_pruned]
print(f"\n=== OPTIMALITY GAP ===")
print(f"Path-found pruned rows (gap < 100): {len(found_pruned)}")
if gaps:
    print(f"Max gap: {max(gaps):.6f}%")
    print(f"Mean gap: {statistics.mean(gaps):.6f}%")

all_found = sum(1 for r in pruned if r['path_found'] == '1')
print(f"Total pruned rows with path_found=1: {all_found}")

bl_found = sum(1 for r in baseline if r['path_found'] == '1')
print(f"Baseline rows with path_found=1: {bl_found}/{len(baseline)}")

# Group baseline by config key
bl_map = {}
for r in baseline:
    key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
    bl_map[key] = r

# 3. Speedup by tau — ALL rows (not just path-found)
print("\n=== SPEEDUP BY TAU — ALL ROWS (MEDIAN) ===")
for tau_val in ['0.001', '0.01', '0.05', '0.1', '0.5']:
    tau_rows = [r for r in pruned if r['tau'] == tau_val]
    edge_speedups = []
    wall_speedups = []
    bl_times = []
    pr_times = []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e = int(bl['edges_relaxed'])
            pr_e = int(r['edges_relaxed'])
            if pr_e > 0:
                edge_speedups.append(bl_e / pr_e)
            elif bl_e > 0:
                edge_speedups.append(float('inf'))
            bl_t = float(bl['execution_time_ms'])
            pr_t = float(r['execution_time_ms'])
            bl_times.append(bl_t)
            pr_times.append(pr_t)
            if pr_t > 0:
                wall_speedups.append(bl_t / pr_t)

    # Filter out inf for median
    finite_edge = [x for x in edge_speedups if x != float('inf')]
    print(f"  tau={tau_val}:")
    if finite_edge:
        print(f"    edge speedup: median={statistics.median(finite_edge):.1f}x (n={len(finite_edge)} finite, {len(edge_speedups)-len(finite_edge)} inf)")
    if wall_speedups:
        print(f"    wall speedup: median={statistics.median(wall_speedups):.1f}x")
    print(f"    baseline_ms median={statistics.median(bl_times):.2f}")
    print(f"    pruned_ms  median={statistics.median(pr_times):.4f}")

# 3b. Speedup by tau — PATH-FOUND ONLY
print("\n=== SPEEDUP BY TAU — PATH-FOUND ONLY (MEDIAN) ===")
for tau_val in ['0.001', '0.01', '0.05', '0.1', '0.5']:
    tau_rows = [r for r in pruned if r['tau'] == tau_val and r['path_found'] == '1']
    edge_speedups = []
    wall_speedups = []
    bl_times = []
    pr_times = []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e = int(bl['edges_relaxed'])
            pr_e = int(r['edges_relaxed'])
            if pr_e > 0:
                edge_speedups.append(bl_e / pr_e)
            bl_t = float(bl['execution_time_ms'])
            pr_t = float(r['execution_time_ms'])
            bl_times.append(bl_t)
            pr_times.append(pr_t)
            if pr_t > 0:
                wall_speedups.append(bl_t / pr_t)

    print(f"  tau={tau_val} (n={len(tau_rows)}):")
    if edge_speedups:
        print(f"    edge speedup: median={statistics.median(edge_speedups):.1f}x")
    if wall_speedups:
        print(f"    wall speedup: median={statistics.median(wall_speedups):.1f}x")
    if bl_times:
        print(f"    baseline_ms median={statistics.median(bl_times):.2f}")
    if pr_times:
        print(f"    pruned_ms  median={statistics.median(pr_times):.4f}")

# 4. Speedup by size at tau=0.01 — ALL rows
print("\n=== SPEEDUP BY SIZE (tau=0.01, ALL ROWS, MEDIAN) ===")
for size in ['1000', '5000', '10000']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['graph_size'] == size]
    bl_rows_for_size = [r for r in baseline if r['graph_size'] == size]
    bl_times = [float(r['execution_time_ms']) for r in bl_rows_for_size]
    bl_mem = [int(r['peak_memory_bytes']) for r in bl_rows_for_size]
    pr_times = [float(r['execution_time_ms']) for r in tau_rows]
    pr_mem = [int(r['peak_memory_bytes']) for r in tau_rows]

    edge_sp = []
    wall_sp = []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e = int(bl['edges_relaxed'])
            pr_e = int(r['edges_relaxed'])
            if pr_e > 0:
                edge_sp.append(bl_e / pr_e)
            elif bl_e > 0:
                edge_sp.append(float('inf'))
            bl_t = float(bl['execution_time_ms'])
            pr_t = float(r['execution_time_ms'])
            if pr_t > 0:
                wall_sp.append(bl_t / pr_t)

    finite_edge = [x for x in edge_sp if x != float('inf')]
    n_inf = len(edge_sp) - len(finite_edge)
    print(f"  |V|={size}:")
    print(f"    baseline_ms median={statistics.median(bl_times):.2f}, pruned_ms median={statistics.median(pr_times):.4f}")
    print(f"    baseline_mem median={statistics.median(bl_mem)/1024:.1f}KB, pruned_mem median={statistics.median(pr_mem)/1024:.1f}KB")
    if finite_edge:
        print(f"    edge_speedup median={statistics.median(finite_edge):.1f}x ({n_inf} inf), wall_speedup median={statistics.median(wall_sp):.1f}x")

# 5. Speedup by graph type at tau=0.01 — ALL rows
print("\n=== SPEEDUP BY GRAPH TYPE (tau=0.01, ALL ROWS) ===")
for gtype in ['erdos_renyi', 'layered']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['graph_type'] == gtype]
    edge_sp = []
    wall_sp = []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e = int(bl['edges_relaxed'])
            pr_e = int(r['edges_relaxed'])
            if pr_e > 0:
                edge_sp.append(bl_e / pr_e)
            elif bl_e > 0:
                edge_sp.append(float('inf'))
            bl_t = float(bl['execution_time_ms'])
            pr_t = float(r['execution_time_ms'])
            if pr_t > 0:
                wall_sp.append(bl_t / pr_t)
    finite_edge = [x for x in edge_sp if x != float('inf')]
    n_inf = len(edge_sp) - len(finite_edge)
    if finite_edge:
        print(f"  {gtype}: edge={statistics.median(finite_edge):.1f}x ({n_inf} inf), wall={statistics.median(wall_sp):.1f}x")

# 6. Speedup by distribution at tau=0.01 — ALL rows
print("\n=== SPEEDUP BY DISTRIBUTION (tau=0.01, ALL ROWS) ===")
for dist in ['uniform', 'power_law']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['distribution'] == dist]
    edge_sp = []
    wall_sp = []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e = int(bl['edges_relaxed'])
            pr_e = int(r['edges_relaxed'])
            if pr_e > 0:
                edge_sp.append(bl_e / pr_e)
            elif bl_e > 0:
                edge_sp.append(float('inf'))
            bl_t = float(bl['execution_time_ms'])
            pr_t = float(r['execution_time_ms'])
            if pr_t > 0:
                wall_sp.append(bl_t / pr_t)
    finite_edge = [x for x in edge_sp if x != float('inf')]
    n_inf = len(edge_sp) - len(finite_edge)
    if finite_edge:
        print(f"  {dist}: edge={statistics.median(finite_edge):.1f}x ({n_inf} inf), wall={statistics.median(wall_sp):.1f}x")

# 7. Raw sample rows to debug
print("\n=== SAMPLE ROWS (tau=0.5, first 5 pruned) ===")
sample = [r for r in pruned if r['tau'] == '0.5'][:5]
for r in sample:
    key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
    bl = bl_map.get(key)
    print(f"  {r['graph_type']} n={r['graph_size']} d={r['avg_degree']} {r['distribution']}:")
    print(f"    bl: edges={bl['edges_relaxed']}, ms={bl['execution_time_ms']}")
    print(f"    pr: edges={r['edges_relaxed']}, ms={r['execution_time_ms']}, found={r['path_found']}")

# ============ REAL DATA RESULTS ============
print("\n\n========== REAL DATA RESULTS ==========")
real_rows = list(csv.DictReader(open('results/real_data_results.csv')))
print(f"Total real-data rows: {len(real_rows)}")

# Show column names
print(f"Columns: {list(real_rows[0].keys())}")

# By dataset
datasets = defaultdict(list)
for r in real_rows:
    datasets[r['dataset']].append(r)

for ds, ds_rows in datasets.items():
    found = sum(1 for r in ds_rows if r['path_found'] == '1' or r['path_found'] == 'True')
    speedups = []
    gaps = []
    for r in ds_rows:
        sp = r.get('speedup', '0')
        if sp and sp != '' and sp != 'inf' and sp != 'nan':
            try:
                speedups.append(float(sp))
            except:
                pass
        gap = r.get('optimality_gap_pct', '0')
        if gap and gap != '' and gap != 'nan':
            try:
                g = float(gap)
                if g < 100:
                    gaps.append(g)
            except:
                pass

    n_nodes = set(r['nodes'] for r in ds_rows)
    n_edges = set(r['edges'] for r in ds_rows)
    print(f"\n  {ds}:")
    print(f"    rows={len(ds_rows)}, path_found={found}/{len(ds_rows)}")
    print(f"    nodes={n_nodes}, edges={n_edges}")
    if speedups:
        print(f"    speedup: median={statistics.median(speedups):.1f}x, max={max(speedups):.1f}x")
    if gaps:
        print(f"    gap: max={max(gaps):.4f}%")

# Show a sample of real-data rows
print("\n=== SAMPLE REAL DATA ROWS ===")
for r in real_rows[:3]:
    print(f"  {r}")

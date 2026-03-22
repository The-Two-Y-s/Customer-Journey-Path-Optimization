"""Comprehensive audit: compute exact values for every table in the report."""
import csv, statistics, math
from collections import defaultdict

rows = list(csv.DictReader(open('results/experiment_results.csv')))
pruned = [r for r in rows if r['algorithm'] == 'pruned']
baseline = [r for r in rows if r['algorithm'] == 'baseline']

bl_map = {}
for r in baseline:
    key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
    bl_map[key] = r

print("="*70)
print("TABLE 5.1: SPEEDUP BY TAU (all rows)")
print("="*70)
for tau_val in ['0.001', '0.01', '0.05', '0.1', '0.5']:
    tau_rows = [r for r in pruned if r['tau'] == tau_val]
    edge_sp, wall_sp, bl_times, pr_times = [], [], [], []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map.get(key)
        if bl:
            bl_e, pr_e = int(bl['edges_relaxed']), int(r['edges_relaxed'])
            bl_t, pr_t = float(bl['execution_time_ms']), float(r['execution_time_ms'])
            bl_times.append(bl_t)
            pr_times.append(pr_t)
            if pr_e > 0: edge_sp.append(bl_e / pr_e)
            if pr_t > 0: wall_sp.append(bl_t / pr_t)
    finite_edge = [x for x in edge_sp if x < 1e15]
    found = sum(1 for r in tau_rows if r['path_found'] == '1')
    pct = found / len(tau_rows) * 100
    print(f"tau={tau_val}: edge_sp={statistics.median(finite_edge):.1f}x  wall_sp={statistics.median(wall_sp):.1f}x  "
          f"bl_ms={statistics.median(bl_times):.2f}  pr_ms={statistics.median(pr_times):.3f}  found={pct:.1f}%")

print("\n" + "="*70)
print("TABLE 5.2 / TABLE 4c: SPEEDUP BY SIZE (tau=0.01, all rows)")
print("="*70)
for size in ['1000', '5000', '10000']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['graph_size'] == size]
    bl_for = [bl_map[(r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])] for r in tau_rows]
    bl_times = [float(b['execution_time_ms']) for b in bl_for]
    pr_times = [float(r['execution_time_ms']) for r in tau_rows]
    bl_mems = [int(b['peak_memory_bytes'])/1024 for b in bl_for]
    pr_mems = [int(r['peak_memory_bytes'])/1024 for r in tau_rows]
    edge_sp, wall_sp = [], []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map[key]
        bl_e, pr_e = int(bl['edges_relaxed']), int(r['edges_relaxed'])
        bl_t, pr_t = float(bl['execution_time_ms']), float(r['execution_time_ms'])
        if pr_e > 0: edge_sp.append(bl_e / pr_e)
        if pr_t > 0: wall_sp.append(bl_t / pr_t)
    print(f"|V|={size}: bl_ms={statistics.median(bl_times):.2f}  pr_ms={statistics.median(pr_times):.3f}  "
          f"edge_sp={statistics.median(edge_sp):.1f}x  wall_sp={statistics.median(wall_sp):.1f}x")
    print(f"         bl_KB={statistics.median(bl_mems):.1f}  pr_KB={statistics.median(pr_mems):.1f}  "
          f"reduction={statistics.median(bl_mems)/statistics.median(pr_mems):.1f}x")

print("\n" + "="*70)
print("TABLE 5.3: SPEEDUP BY GRAPH TYPE (tau=0.01, all rows)")
print("="*70)
for gtype in ['erdos_renyi', 'layered']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['graph_type'] == gtype]
    edge_sp, wall_sp = [], []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map[key]
        bl_e, pr_e = int(bl['edges_relaxed']), int(r['edges_relaxed'])
        bl_t, pr_t = float(bl['execution_time_ms']), float(r['execution_time_ms'])
        if pr_e > 0: edge_sp.append(bl_e / pr_e)
        if pr_t > 0: wall_sp.append(bl_t / pr_t)
    print(f"{gtype}: edge={statistics.median(edge_sp):.1f}x  wall={statistics.median(wall_sp):.1f}x")

print("\n" + "="*70)
print("TABLE 5.4: SPEEDUP BY DISTRIBUTION (tau=0.01, all rows)")
print("="*70)
for dist in ['uniform', 'power_law']:
    tau_rows = [r for r in pruned if r['tau'] == '0.01' and r['distribution'] == dist]
    edge_sp, wall_sp = [], []
    for r in tau_rows:
        key = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['run'])
        bl = bl_map[key]
        bl_e, pr_e = int(bl['edges_relaxed']), int(r['edges_relaxed'])
        bl_t, pr_t = float(bl['execution_time_ms']), float(r['execution_time_ms'])
        if pr_e > 0: edge_sp.append(bl_e / pr_e)
        if pr_t > 0: wall_sp.append(bl_t / pr_t)
    print(f"{dist}: edge={statistics.median(edge_sp):.1f}x  wall={statistics.median(wall_sp):.1f}x")

# Real data
print("\n" + "="*70)
print("REAL DATA TABLES")
print("="*70)
real_rows = list(csv.DictReader(open('results/real_data_results.csv')))
datasets = defaultdict(list)
for r in real_rows:
    datasets[r['dataset']].append(r)

for ds, ds_rows in datasets.items():
    pruned_found = sum(1 for r in ds_rows if r['path_found'] in ('1', 'True'))
    # Check baseline found
    baseline_found = sum(1 for r in ds_rows if r['baseline_cost'] != 'inf' and float(r['baseline_cost']) < 1e10)
    speedups = []
    for r in ds_rows:
        sp = r.get('speedup', '')
        if sp and sp not in ('', 'inf', 'nan'):
            try: speedups.append(float(sp))
            except: pass
    max_sp = max(speedups) if speedups else 0
    med_sp = statistics.median(speedups) if speedups else 0
    gaps = []
    for r in ds_rows:
        g = r.get('optimality_gap_pct', '')
        if g and g not in ('', 'nan'):
            try:
                gv = float(g)
                if gv < 100: gaps.append(gv)
            except: pass
    print(f"\n{ds}:")
    print(f"  rows={len(ds_rows)}, baseline_found={baseline_found}/{len(ds_rows)}, pruned_found={pruned_found}/{len(ds_rows)}")
    print(f"  speedup: median={med_sp:.1f}x  max={max_sp:.1f}x")
    if gaps:
        print(f"  gap: max={max(gaps):.3f}%")

# Correctness chapter check
print("\n" + "="*70)
print("CORRECTNESS CHAPTER VERIFICATION")
print("="*70)
total_pruned = len(pruned)
total_found = sum(1 for r in pruned if r['path_found'] == '1')
print(f"Total pruned rows: {total_pruned}")
print(f"Path-found pruned rows: {total_found}")
print(f"Report says '171 of 180' -- should say '171 of {total_pruned}'")

# Check unique configs
configs_with_path = set()
configs_total = set()
for r in pruned:
    cfg = (r['graph_type'], r['graph_size'], r['avg_degree'], r['distribution'], r['tau'])
    configs_total.add(cfg)
    if r['path_found'] == '1':
        configs_with_path.add(cfg)
print(f"Unique (type,size,deg,dist,tau) combos: {len(configs_total)}")
print(f"Combos with >=1 path found: {len(configs_with_path)}")

# Summary text checks
print("\n" + "="*70)
print("PROSE VALUE CHECKS")
print("="*70)
# Complexity chapter: "0.64 → 3.60 → 7.25 ms"
for size in ['1000', '5000', '10000']:
    bl_rows = [r for r in baseline if r['graph_size'] == size]
    med = statistics.median([float(r['execution_time_ms']) for r in bl_rows])
    print(f"Baseline median for V={size}: {med:.2f} ms")

# Memory values
for size in ['1000', '5000', '10000']:
    bl_rows = [r for r in baseline if r['graph_size'] == size]
    med = statistics.median([int(r['peak_memory_bytes'])/1024 for r in bl_rows])
    print(f"Baseline mem median for V={size}: {med:.1f} KB")

# Pruned memory at tau=0.01
for size in ['1000', '5000', '10000']:
    pr_rows = [r for r in pruned if r['tau'] == '0.01' and r['graph_size'] == size]
    med = statistics.median([int(r['peak_memory_bytes'])/1024 for r in pr_rows])
    print(f"Pruned mem median for V={size}, tau=0.01: {med:.1f} KB")

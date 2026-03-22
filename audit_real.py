import csv
from collections import defaultdict

real = list(csv.DictReader(open('results/real_data_results.csv')))
ds = defaultdict(list)
for r in real:
    ds[r['dataset']].append(r)

for name, rows in ds.items():
    bl_inf = sum(1 for r in rows if r['baseline_cost'] == 'inf')
    bl_finite = sum(1 for r in rows if r['baseline_cost'] != 'inf')
    pr_found = sum(1 for r in rows if r['path_found'] in ('True', '1'))
    pairs = set((r['source'], r['target']) for r in rows)
    print(f"{name}: bl_inf={bl_inf} bl_finite={bl_finite} pr_found={pr_found} unique_pairs={len(pairs)}")
    # Show 3 sample rows
    for r in rows[:3]:
        src, tgt = r['source'], r['target']
        print(f"  s={src[:20]} t={tgt[:20]} tau={r['tau']} bl_cost={r['baseline_cost'][:10]} pr_cost={r['pruned_cost'][:10]} found={r['path_found']}")
    print()

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import heapq, math

# ── 1. Build a small customer journey graph ──────────────────────────
np.random.seed(42)

# Nodes: realistic customer journey stages
nodes = ['Landing', 'Search', 'Product A', 'Product B',
         'Reviews', 'Cart', 'Checkout', 'Dead End 1',
         'Dead End 2', 'Dead End 3', 'Browse', 'Wishlist']

# Edges: (from, to, probability)
edges = [
    ('Landing',   'Search',    0.45),
    ('Landing',   'Browse',    0.30),
    ('Landing',   'Dead End 1',0.25),
    ('Search',    'Product A', 0.40),
    ('Search',    'Product B', 0.35),
    ('Search',    'Dead End 2',0.25),
    ('Browse',    'Product A', 0.50),
    ('Browse',    'Wishlist',  0.30),
    ('Browse',    'Dead End 3',0.20),
    ('Product A', 'Reviews',   0.55),
    ('Product A', 'Cart',      0.30),
    ('Product A', 'Dead End 1',0.15),
    ('Product B', 'Cart',      0.60),
    ('Product B', 'Dead End 2',0.40),
    ('Reviews',   'Cart',      0.70),
    ('Reviews',   'Dead End 3',0.30),
    ('Cart',      'Checkout',  0.75),
    ('Cart',      'Dead End 1',0.25),
    ('Wishlist',  'Product B', 0.60),
    ('Wishlist',  'Dead End 3',0.40),
]

# Build graph dict
graph = {n: [] for n in nodes}
for u, v, p in edges:
    graph[u].append((v, -math.log(p)))

# ── 2. Run both algorithms, recording step-by-step snapshots ─────────
def dijkstra_steps(graph, start, goal, tau=0.0):
    T = -math.log(tau) if tau > 0 else math.inf
    pq = [(0, start)]
    dist = {start: 0}
    parent = {}
    settled = []
    pruned_edges = []

    while pq:
        cost, node = heapq.heappop(pq)
        if cost > dist.get(node, math.inf):
            continue
        settled.append(node)
        if node == goal:
            break
        for neighbor, weight in graph.get(node, []):
            new_cost = cost + weight
            if new_cost > T:
                pruned_edges.append((node, neighbor))
                continue
            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                parent[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))

    # Reconstruct path
    path = []
    if goal in dist:
        cur = goal
        while cur != start:
            path.append(cur)
            cur = parent[cur]
        path.append(start)
        path.reverse()

    return settled, pruned_edges, path, dist.get(goal, math.inf)

baseline_settled, _, baseline_path, baseline_cost = dijkstra_steps(graph, 'Landing', 'Checkout')
pruned_settled,  pruned_pruned, pruned_path, pruned_cost  = dijkstra_steps(graph, 'Landing', 'Checkout', tau=0.1)

# ── 3. Layout ────────────────────────────────────────────────────────
pos = {
    'Landing':   (0,   2.0),
    'Search':    (1.5, 3.2),
    'Browse':    (1.5, 0.8),
    'Product A': (3.0, 3.5),
    'Product B': (3.0, 1.8),
    'Wishlist':  (3.0, 0.2),
    'Reviews':   (4.5, 4.0),
    'Cart':      (4.5, 2.5),
    'Dead End 1':(2.0, 4.8),
    'Dead End 2':(4.5, 0.8),
    'Dead End 3':(5.5, 0.0),
    'Checkout':  (6.0, 2.5),
}

# ── 4. Animate ───────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.patch.set_facecolor('#1a1a2e')

COLORS = {
    'bg':       '#1a1a2e',
    'node':     '#2d3561',
    'settled_b':'#e07b54',   # baseline explored = orange
    'settled_p':'#4c9be8',   # pruned explored = blue
    'path':     '#4caf82',   # optimal path = green
    'pruned':   '#888888',   # pruned nodes = grey
    'edge':     '#444466',
    'text':     'white',
    'source':   '#f9c74f',
    'target':   '#f94144',
}

max_frames = max(len(baseline_settled), len(pruned_settled)) + 10

def draw_frame(ax, title, settled_so_far, path_nodes, pruned_set, color_settled, show_path):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])
    ax.set_title(title, color=COLORS['text'], fontsize=16, fontweight='bold', pad=12)
    ax.axis('off')

    # Draw edges
    for u, v, p in edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=COLORS['edge'],
                                    lw=1.2, connectionstyle='arc3,rad=0.1'))

    # Determine node colors
    path_set = set(path_nodes) if show_path else set()
    for node in nodes:
        x, y = pos[node]
        if node in path_set and show_path:
            color = COLORS['path']
            size  = 900
            zorder = 5
        elif node in pruned_set:
            color = COLORS['pruned']
            size  = 600
            zorder = 3
        elif node in settled_so_far:
            color = color_settled
            size  = 750
            zorder = 4
        elif node == 'Landing':
            color = COLORS['source']
            size  = 800
            zorder = 4
        elif node == 'Checkout':
            color = COLORS['target']
            size  = 800
            zorder = 4
        else:
            color = COLORS['node']
            size  = 600
            zorder = 3

        ax.scatter(x, y, s=size, c=color, zorder=zorder, edgecolors='white', linewidths=1.5)
        ax.text(x, y - 0.32, node, ha='center', va='top',
                fontsize=8.5, color=COLORS['text'], fontweight='bold')

    # Path edges
    if show_path and len(path_nodes) > 1:
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i+1]
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle='->', color=COLORS['path'],
                                        lw=3, connectionstyle='arc3,rad=0.1'))

    # Stats box
    n_explored = len(settled_so_far)
    info = f'Nodes explored: {n_explored}'
    ax.text(0.02, 0.05, info, transform=ax.transAxes,
            color=COLORS['text'], fontsize=12,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#2d3561', alpha=0.8))

def animate(frame):
    # How many nodes settled so far
    b_frame = min(frame, len(baseline_settled))
    p_frame = min(frame, len(pruned_settled))

    b_settled = set(baseline_settled[:b_frame])
    p_settled = set(pruned_settled[:p_frame])

    show_path = frame >= max_frames - 6

    draw_frame(axes[0], 'Baseline Dijkstra  (explores everything)',
               b_settled, baseline_path, set(), COLORS['settled_b'], show_path)
    draw_frame(axes[1], f'Pruned Dijkstra  \u03c4 = 0.1  (stops early)',
               p_settled, pruned_path, set(), COLORS['settled_p'], show_path)

    # Speedup label when done
    if show_path:
        speedup = baseline_cost / pruned_cost if pruned_cost > 0 else 0
        gap = abs(baseline_cost - pruned_cost) / baseline_cost * 100 if baseline_cost > 0 else 0
        fig.suptitle(
            f'Explored: {len(baseline_settled)} vs {len(pruned_settled)} nodes  |  '
            f'Gap: {gap:.1f}%  |  Same optimal path: {baseline_path == pruned_path}',
            color=COLORS['text'], fontsize=14, fontweight='bold', y=0.02)

anim = animation.FuncAnimation(fig, animate, frames=max_frames, interval=350, repeat=False)
plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.show()
fig.legend(handles=legend_elements, loc='upper center', ncol=5,
           facecolor='#2d3561', labelcolor='white', fontsize=11,
           framealpha=0.9, bbox_to_anchor=(0.5, 0.98))

anim = animation.FuncAnimation(fig, animate, frames=max_frames,
                                interval=500, repeat=True, repeat_delay=3000)

# Save as GIF (needs pillow: pip install pillow)
anim.save('results/img/demo_animation.gif', writer='pillow', fps=2,
           savefig_kwargs={'facecolor': '#1a1a2e'})
print("Saved: results/img/demo_animation.gif")
plt.show()

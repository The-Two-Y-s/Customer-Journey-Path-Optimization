import heapq


def dijkstra(graph, start, goal):
    pq = [(0, start)]
    dist = {start: 0}
    parent = {}

    while pq:
        cost, node = heapq.heappop(pq)

        if node == goal:
            break

        # Some graphs may omit sink nodes from the adjacency map.
        for neighbor, weight in graph.get(node, []):
            new_cost = cost + weight

            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                parent[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))

    return dist, parent


def reconstruct_path(parent, start, goal):
    if start == goal:
        return [start]
    if goal not in parent:
        return []

    path = [goal]
    cur = goal
    while cur != start:
        cur = parent[cur]
        path.append(cur)
    path.reverse()
    return path
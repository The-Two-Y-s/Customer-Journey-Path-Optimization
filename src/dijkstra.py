import heapq

def dijkstra(graph, start, goal):
    pq = [(0, start)]
    dist = {start: 0}
    parent = {}

    while pq:
        cost, node = heapq.heappop(pq)

        if node == goal:
            break

        for neighbor, weight in graph[node]:
            new_cost = cost + weight

            if neighbor not in dist or new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                parent[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))

    return dist, parent
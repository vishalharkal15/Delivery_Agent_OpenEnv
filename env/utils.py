import math
import heapq

# Distance
def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)


# Generate road graph (grid + diagonal)
def generate_graph(bounds, step=0.002):
    nodes = []
    edges = {}

    lat_min, lat_max, lon_min, lon_max = bounds

    lat = lat_min
    while lat < lat_max:
        lon = lon_min
        while lon < lon_max:
            node = (round(lat, 5), round(lon, 5))
            nodes.append(node)
            edges[node] = []

            # horizontal
            edges[node].append((lat, lon + step))
            # vertical
            edges[node].append((lat + step, lon))
            # diagonal (Broadway style)
            edges[node].append((lat + step, lon + step))

            lon += step
        lat += step

    return nodes, edges


# A* pathfinding
def astar(start, goal, graph):
    nodes, edges = graph

    open_set = []
    heapq.heappush(open_set, (0, start))

    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if distance(current, goal) < 0.001:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            return path[::-1]

        for neighbor in edges.get(current, []):
            tentative = g_score[current] + distance(current, neighbor)

            if neighbor not in g_score or tentative < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + distance(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))

    return []
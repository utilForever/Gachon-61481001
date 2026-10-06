from heapq import heappop, heappush
from itertools import count


def _reconstruct(parent, goal):
    path = []
    current = goal

    while current is not None:
        path.append(current)
        current = parent[current]

    path.reverse()
    return path


def _search(graph, start, goal, travel_times, use_heuristic):
    if start not in graph or goal not in graph:
        return {"path": None, "expanded": 0}

    minimum_time = min(travel_times[node] for node in graph)

    def heuristic(node):
        if not use_heuristic:
            return 0
        return (abs(node[0] - goal[0]) + abs(node[1] - goal[1])) * minimum_time

    distances = {start: 0}
    parent = {start: None}
    order = count()
    candidates = [(heuristic(start), next(order), 0, start)]
    expanded = 0

    while candidates:
        _, _, cost, current = heappop(candidates)
        # 더 작은 g를 등록한 뒤에도 힙에 남아 있는 오래된 후보는 건너뛴다.
        if cost != distances[current]:
            continue

        expanded += 1
        if current == goal:
            return {"path": _reconstruct(parent, goal), "expanded": expanded}

        for neighbor in graph[current]:
            new_cost = cost + travel_times[neighbor]
            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                parent[neighbor] = current
                priority = new_cost + heuristic(neighbor)
                heappush(candidates, (priority, next(order), new_cost, neighbor))

    return {"path": None, "expanded": expanded}


def search_result(graph, start, goal, travel_times, algorithm="dijkstra"):
    if algorithm not in ("dijkstra", "astar"):
        raise ValueError("algorithm은 dijkstra 또는 astar여야 합니다.")

    return _search(graph, start, goal, travel_times, algorithm == "astar")


def dijkstra_path(graph, start, goal, travel_times):
    return _search(graph, start, goal, travel_times, False)["path"]


def astar_path(graph, start, goal, travel_times):
    return _search(graph, start, goal, travel_times, True)["path"]


def dijkstra_all(graph, start, travel_times):
    if start not in graph:
        return {}

    distances = {start: 0}
    order = count()
    candidates = [(0, next(order), start)]

    while candidates:
        cost, _, current = heappop(candidates)
        if cost != distances[current]:
            continue

        for neighbor in graph[current]:
            new_cost = cost + travel_times[neighbor]
            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                heappush(candidates, (new_cost, next(order), neighbor))

    return distances

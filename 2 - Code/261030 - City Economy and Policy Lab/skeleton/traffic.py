"""도로망 연결성, BFS 경로, 대기열과 일자리 접근성 계산."""

from collections import deque

from model import neighbors4


def build_road_graph(city):
    """도로 셀을 노드로, 상하좌우 도로 연결을 인접 목록으로 반환한다."""
    graph = {}
    for y, row in enumerate(city["grid"]):
        for x, cell in enumerate(row):
            if cell["road"]:
                graph[(x, y)] = []
                for nx, ny in neighbors4(city, x, y):
                    if city["grid"][ny][nx]["road"]:
                        graph[(x, y)].append((nx, ny))

    return graph


def connected_components(graph):
    """도로 노드별 연결 요소 번호를 반환한다. 번호는 0부터 시작한다."""
    components = {}
    component_id = 0

    for start in graph:
        if start in components:
            continue

        queue = deque([start])
        components[start] = component_id
        while queue:
            current = queue.popleft()
            for neighbor in graph[current]:
                if neighbor not in components:
                    components[neighbor] = component_id
                    queue.append(neighbor)
        component_id += 1

    return components


def bfs_path(graph, start, goal):
    """통과 구간 수가 가장 적은 경로를 반환한다. 도달할 수 없으면 None이다."""
    if start not in graph or goal not in graph:
        return None

    queue = deque([start])
    parent = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            path = []
            while current is not None:
                path.append(current)
                current = parent[current]
            path.reverse()
            return path

        for neighbor in graph[current]:
            if neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)

    return None


def route_metrics(path, travel_times, cell_distance=100):
    """출발 셀을 제외한 경로의 거리(m)와 진입 시간(분)을 합산한다."""
    if not path:
        return None

    total_time = 0
    # 출발 셀은 이미 도착한 상태이므로, 다음 셀부터 진입 비용을 더한다.
    for node in path[1:]:
        total_time += travel_times[node]

    return {"distance_m": (len(path) - 1) * cell_distance, "time_min": total_time}


def advance_queue(queue, arrivals, capacity):
    """한 구간의 처리 차량 수와 남은 대기 차량 수를 반환한다."""
    waiting = queue + arrivals
    served = min(waiting, capacity)
    return {"served": served, "queue": waiting - served}


def count_accessible_jobs(jobs, travel_time_by_node, limit_minutes):
    """시간 기준 이내에 도달하는 건물의 일자리를 건물당 한 번씩 합산한다."""
    total = 0
    counted = set()

    for building in jobs:
        if building["id"] in counted:
            continue
        for entrance in building["entrances"]:
            if entrance in travel_time_by_node:
                if travel_time_by_node[entrance] <= limit_minutes:
                    total += building["jobs"]
                    counted.add(building["id"])
                    break

    return total

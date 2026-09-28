"""
도로 그래프, 연결 요소, 최소 구간 경로, 대기열과 일자리 접근성의 계산 규칙.

좌표는 (x, y), 셀 접근은 grid[y][x], 대기열의 1 tick은 1분이다.
도로의 이동거리는 m, 셀 진입 시간은 분, 대기열은 차량 수로 계산한다.
모든 함수는 입력을 읽기만 한다. 경로의 시간에는 출발 셀의 진입 비용을 더하지 않는다.
"""

from collections import deque

from model import neighbors4


def build_road_graph(city):
    """도로 좌표와 이웃 목록을 새 dict로 반환한다. 고립된 도로도 포함한다."""
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
    """각 노드의 연결 요소 번호를 반환한다. 그래프 순서대로 0번부터 붙인다."""
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
                    # 큐에 넣을 때 번호를 기록해 같은 노드를 중복해서 넣지 않는다.
                    components[neighbor] = component_id
                    queue.append(neighbor)

        component_id += 1

    return components


def bfs_path(graph, start, goal):
    """최소 구간 경로를 출발 / 도착 포함 리스트로 반환한다. 도달 불가이면 None이다."""
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

            # 도착지부터 모은 좌표를 출발지부터의 순서로 뒤집는다.
            path.reverse()
            return path

        for neighbor in graph[current]:
            if neighbor not in parent:
                # 처음 발견한 이전 노드만 기록해야 최소 구간 경로가 유지된다.
                parent[neighbor] = current
                queue.append(neighbor)

    return None


def route_metrics(path, travel_times, cell_distance=100):
    """경로의 거리(m)와 시간(분)을 반환한다. None이나 빈 경로이면 None이다."""
    if not path:
        return None

    total_time = 0
    # 출발 셀은 이미 도착한 상태이므로, 다음 셀부터 진입 비용을 더한다.
    for node in path[1:]:
        total_time += travel_times[node]

    return {"distance_m": (len(path) - 1) * cell_distance, "time_min": total_time}


def advance_queue(queue, arrivals, capacity):
    """1분간 처리한 차량 수와 다음 대기 차량 수를 반환한다. 입력은 음이 아닌 정수이다."""
    waiting = queue + arrivals
    served = min(waiting, capacity)
    return {"served": served, "queue": waiting - served}


def count_accessible_jobs(jobs, travel_time_by_node, limit_minutes):
    """시간 한도 이내의 일자리를 건물 ID마다 한 번만 합산한다. 입력은 보존한다."""
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
                    # 입구가 여러 개여도 같은 건물의 일자리는 한 번만 센다.
                    break

    return total

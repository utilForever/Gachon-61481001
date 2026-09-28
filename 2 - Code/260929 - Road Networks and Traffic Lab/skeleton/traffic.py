"""
좌표는 (x, y), 셀 접근은 grid[y][x], 대기열의 1 tick은 1분이다.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 화면에서는 여러 함수를 함께 사용합니다.
2. pass는 코드를 작성할 빈자리입니다. 해당 위치의 안내에 따라 코드를 작성하세요.
   주석만 있는 TODO는 주석 아래에 코드를 추가하면 됩니다.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
4. 파일을 저장하고 skeleton 폴더의 터미널에서 python checks.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미완성]은 아직 남은 NotImplementedError, [실패]는 기대한 결과와 다르다는 뜻입니다.

- 데이터를 읽을 때
graph는 도로 좌표를 키로, 상하좌우 이웃 도로의 좌표 리스트를 값으로 저장합니다.
travel_times는 도로 셀에 진입하는 시간이며, 출발 셀의 시간은 경로에 더하지 않습니다.
jobs의 각 항목은 건물 ID, 입구 도로 목록, 전체 일자리 수를 담은 dict입니다.
이 파일의 모든 함수는 입력을 읽기만 합니다. 결과는 새 dict나 list, 숫자 또는 None입니다.
"""

from collections import deque

from model import neighbors4


def build_road_graph(city):
    """도로 좌표와 이웃 목록을 새 dict로 반환한다. 고립된 도로도 포함한다."""
    raise NotImplementedError("TODO 1: 도로 그래프를 만드세요.")

    graph = {}

    for y, row in enumerate(city["grid"]):
        for x, cell in enumerate(row):
            # TODO 1: 도로 셀을 노드로 등록하고 이웃 도로를 연결하세요.
            # 1. cell["road"]가 True일 때만 graph[(x, y)]에 빈 리스트를 만드세요.
            # 2. neighbors4(city, x, y)로 지도 안의 이웃 좌표 (nx, ny)를 꺼내세요.
            # 3. city["grid"][ny][nx]["road"]가 True이면 이웃 리스트에 추가하세요.
            # 행 / 열의 순회 순서와 neighbors4의 왼쪽 / 오른쪽 / 위 / 아래 순서를 유지하세요.
            # 이웃이 없어도 빈 리스트를 남깁니다. 건물과 빈 땅은 노드에 넣지 않습니다.
            # 확인 예: 기본 도시의 graph[(2, 0)]은 [], graph[(0, 2)]는 [(1, 2), (0, 3)].
            pass

    return graph


def connected_components(graph):
    """각 노드의 연결 요소 번호를 반환한다. 그래프 순서대로 0번부터 붙인다."""
    raise NotImplementedError("TODO 2: 연결 요소를 구하세요.")

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
                # TODO 2: 처음 발견한 이웃에 현재 연결 요소 번호를 붙이세요.
                # 1. neighbor가 아직 components에 없는지 확인하세요.
                # 2. components[neighbor]에 component_id를 기록하세요.
                # 3. queue.append(...)로 이웃을 넣어 그 이웃의 주변도 탐색하게 하세요.
                # 큐에 넣을 때 번호를 기록해야 같은 노드를 중복해서 넣지 않습니다.
                # 시작 노드의 등록과 다음 번호로 넘어가는 코드는 이미 작성되어 있습니다.
                pass

        component_id += 1

    return components


def bfs_path(graph, start, goal):
    """최소 구간 경로를 출발 / 도착 포함 리스트로 반환한다. 도달 불가이면 None이다."""
    raise NotImplementedError("TODO 3: BFS로 이동 경로를 구하세요.")

    # TODO 3-A: start나 goal이 graph에 없으면 바로 None을 반환하세요.
    # 두 좌표가 같더라도 그래프에 없는 좌표라면 유효한 경로가 아닙니다.

    queue = deque([start])
    parent = {start: None}

    while queue:
        current = queue.popleft()

        if current == goal:
            # TODO 3-B: 이전 노드를 따라가며 경로를 복원하세요.
            # 1. 빈 path 리스트를 만들고 current가 None이 될 때까지 반복하세요.
            # 2. current를 path에 추가한 뒤 current를 parent[current]로 바꾸세요.
            # 3. 도착지부터 모았으므로 path.reverse()로 뒤집은 뒤 반환하세요.
            # start의 이전 노드는 None입니다. start == goal이면 [start]가 반환됩니다.
            pass

        for neighbor in graph[current]:
            # TODO 3-C: 아직 parent에 없는 이웃의 이전 노드를 기록하고 큐에 넣으세요.
            # parent[neighbor]에는 그 이웃을 발견한 current를 저장합니다.
            # parent는 방문 여부도 나타냅니다. 기록한 이웃을 다시 큐에 넣지 마세요.
            # graph[current]의 이웃 순서를 유지해야 같은 길이의 경로도 일정하게 나옵니다.
            pass

    # 큐를 모두 살펴봐도 도착하지 못하면 경로가 없다.
    return None


def route_metrics(path, travel_times, cell_distance=100):
    """경로의 거리(m)와 시간(분)을 반환한다. None이나 빈 경로이면 None이다."""
    raise NotImplementedError("TODO 4: 경로의 거리와 시간을 계산하세요.")

    # TODO 4: {"distance_m": 이동거리, "time_min": 총시간} 형태로 반환하세요.
    # 1. path가 None이거나 빈 리스트이면 바로 None을 반환하세요.
    # 2. 이동 구간 수는 len(path) - 1입니다. cell_distance를 곱해 거리를 구하세요.
    # 3. path[1:]의 각 node에 대해 travel_times[node]를 더해 총시간을 구하세요.
    # 출발 셀은 이미 도착한 상태이므로 비용을 더하지 않습니다. 입력 path는 보존하세요.
    # 확인 예: 노드가 4개이고 이후 세 셀의 시간이 1분씩이면 300 m / 3분입니다.
    # 노드가 하나뿐이면 시간 dict가 비어 있어도 거리 0, 시간 0을 반환해야 합니다.


def advance_queue(queue, arrivals, capacity):
    """1분간 처리한 차량 수와 다음 대기 차량 수를 반환한다. 입력은 음이 아닌 정수이다."""
    raise NotImplementedError("TODO 5: 대기열을 갱신하세요.")

    # TODO 5: {"served": 처리 차량 수, "queue": 다음 대기 차량 수}를 반환하세요.
    # 1. 기존 대기 queue에 이번 분의 유입 arrivals를 더하세요.
    # 2. 대기와 유입의 합, 처리 용량 capacity 중 작은 값만 처리할 수 있습니다.
    # 3. 합에서 실제 처리한 수를 빼 다음 대기를 구하세요.
    # 여기의 queue는 차량 수를 나타내는 정수입니다. BFS의 deque와 구분하세요.
    # 확인 예: (0, 8, 5)이면 처리 5대 / 대기 3대, (1, 2, 5)이면 처리 3대 / 대기 0대.


def count_accessible_jobs(jobs, travel_time_by_node, limit_minutes):
    """시간 한도 이내의 일자리를 건물 ID마다 한 번만 합산한다. 입력은 보존한다."""
    raise NotImplementedError("TODO 6: 도달 가능한 일자리 수를 계산하세요.")

    total = 0
    counted = set()

    for building in jobs:
        # TODO 6-A: building["id"]가 counted에 있으면 continue로 건너뛰세요.
        # 같은 건물이 여러 항목으로 전달되어도 일자리는 한 번만 더합니다.

        for entrance in building["entrances"]:
            # TODO 6-B: 도달 가능한 입구를 찾으면 이 건물의 일자리를 더하세요.
            # 1. entrance가 travel_time_by_node에 있는지 먼저 확인하세요.
            # 2. 그 입구까지의 시간이 limit_minutes 이하인지 확인하세요. 같은 값도 포함합니다.
            # 3. 조건을 만족하면 total에 building["jobs"]를 더하고 ID를 counted에 넣으세요.
            # 4. break로 이 건물의 나머지 입구 탐색을 끝내세요.
            # dict에 없는 입구는 도달 불가입니다. .get(entrance, 0)으로 처리하면 안 됩니다.
            # 확인 예: 일자리 12개인 건물의 입구 두 곳에 도달해도 합계는 12개입니다.
            pass

    return total

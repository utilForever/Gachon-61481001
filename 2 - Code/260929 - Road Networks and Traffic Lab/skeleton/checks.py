"""단계별 누적 검사: python checks.py --stage 3

제공 코드와 1~3단계를 검사한다. 전체 6단계에서는 통합 검사도 실행한다.
종료 코드: 0=통과, 1=실패 / 오류, 2=TODO 미완성.
"""

import argparse
import json
import tempfile
import traceback
from copy import deepcopy
from pathlib import Path

import traffic
from city_data import make_empty_city, validate_city
from routing import astar_path, dijkstra_all, dijkstra_path, search_result
from traffic_data import (
    cost_snapshot,
    job_destinations,
    load_scenario,
    make_scenario,
    save_scenario,
    step_selected_queue,
    sync_transport,
    validate_transport,
)


def same(actual, expected, description):
    if actual != expected:
        raise AssertionError(
            description + "\n  기대: " + repr(expected) + "\n  실제: " + repr(actual)
        )


def rejects_value_error(action, description):
    try:
        action()
    except ValueError:
        return

    raise AssertionError(description + ": ValueError가 발생해야 합니다.")


def sample_graph():
    return {
        (2, 0): [],
        (0, 2): [(1, 2), (0, 3)],
        (1, 2): [(0, 2), (2, 2), (1, 3)],
        (2, 2): [(1, 2), (3, 2), (2, 3)],
        (3, 2): [(2, 2), (3, 3)],
        (0, 3): [(1, 3), (0, 2)],
        (1, 3): [(0, 3), (2, 3), (1, 2)],
        (2, 3): [(1, 3), (3, 3), (2, 2)],
        (3, 3): [(2, 3), (3, 2)],
    }


def check_support():
    # Dijkstra / A*의 우회 경로와 확장 노드 수
    graph = sample_graph()
    times = {node: 1 for node in graph}
    times[(1, 2)] = 5
    for algorithm in ("dijkstra", "astar"):
        result = search_result(graph, (0, 2), (3, 2), times, algorithm)

        same(len(result["path"]), 6, "Dijkstra / A*의 우회 경로와 확장 노드 수")
        same(
            sum((times[node] for node in result["path"][1:])),
            5,
            "Dijkstra / A*의 우회 경로와 확장 노드 수",
        )
        same(result["expanded"] >= 1, True, "Dijkstra / A*의 우회 경로와 확장 노드 수")
    same(dijkstra_all(graph, (0, 2), times)[(3, 3)], 4, "Dijkstra / A*의 우회 경로와 확장 노드 수")

    # 최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가
    graph = sample_graph()
    times = {node: 1 for node in graph}
    for function in (dijkstra_path, astar_path):
        same(
            function(graph, (0, 2), (0, 2), times),
            [(0, 2)],
            "최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가",
        )
        same(
            function(graph, (0, 2), (2, 0), times),
            None,
            "최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가",
        )
        same(
            function(graph, (4, 0), (3, 2), times),
            None,
            "최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가",
        )
        same(
            function({}, (0, 0), (0, 0), {}),
            None,
            "최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가",
        )
    same(
        dijkstra_all(graph, (4, 0), times), {}, "최소 시간 탐색의 같은 좌표 / 없는 좌표 / 도달 불가"
    )

    # 세 시나리오의 도시 형식과 혼잡 시간
    for name in ("default", "congested", "disconnected"):
        city, state = make_scenario(name)
        validate_city(city)
        validate_transport(city, state)

        same(city["day"], 0, "세 시나리오의 도시 형식과 혼잡 시간")
    city, state = make_scenario("congested")

    same(cost_snapshot(state)[(1, 2)], 5, "세 시나리오의 도시 형식과 혼잡 시간")

    # 운영 중인 건물의 전체 일자리 수와 입구
    city, _ = make_scenario()

    same(
        job_destinations(city),
        [
            {"id": "J", "entrances": [(3, 2)], "jobs": 12},
            {"id": "F", "entrances": [(3, 3)], "jobs": 20},
        ],
        "운영 중인 건물의 전체 일자리 수와 입구",
    )
    city["buildings"]["J"]["status"] = "closed"

    same(
        [item["id"] for item in job_destinations(city)],
        ["F"],
        "운영 중인 건물의 전체 일자리 수와 입구",
    )

    # 교통 JSON 저장 / 불러오기와 중복 도로 거절
    city, state = make_scenario("congested")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "city.json"
        save_scenario(city, state, path)

        same(load_scenario(path), (city, state), "교통 JSON 저장 / 불러오기와 중복 도로 거절")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["traffic"]["roads"].append(raw["traffic"]["roads"][0])
        path.write_text(json.dumps(raw), encoding="utf-8")

        rejects_value_error(
            lambda: load_scenario(path), "교통 JSON 저장 / 불러오기와 중복 도로 거절"
        )

    # 잘못된 처리 용량 / 진입 시간 / 대기열 거절
    city, state = make_scenario()
    for key, value in [
        ("capacities", 0),
        ("base_times", 0.5),
        ("queues", -1),
        ("base_times", float("nan")),
        ("capacities", True),
    ]:
        bad = deepcopy(state)
        bad[key][(1, 2)] = value

        rejects_value_error(
            lambda: validate_transport(city, bad), "잘못된 처리 용량 / 진입 시간 / 대기열 거절"
        )

    # 도로 삭제 후 교통 상태 동기화와 원본 보존
    city, state = make_scenario()
    old = deepcopy(state)
    city["grid"][2][1]["road"] = False
    synced = sync_transport(city, state)

    same((1, 2) not in synced["queues"], True, "도로 삭제 후 교통 상태 동기화와 원본 보존")
    same(
        synced["selected_road"] in synced["queues"],
        True,
        "도로 삭제 후 교통 상태 동기화와 원본 보존",
    )
    same(state, old, "도로 삭제 후 교통 상태 동기화와 원본 보존")
    for row in city["grid"]:
        for cell in row:
            cell["road"] = False
    empty = sync_transport(city, state)

    same(empty["selected_road"], None, "도로 삭제 후 교통 상태 동기화와 원본 보존")
    same(empty["queues"], {}, "도로 삭제 후 교통 상태 동기화와 원본 보존")

    # 최소 시간 탐색은 그래프와 이동시간을 변경하지 않음
    graph = sample_graph()
    times = {node: 1 for node in graph}
    old = deepcopy((graph, times))
    astar_path(graph, (0, 2), (3, 2), times)
    dijkstra_all(graph, (0, 2), times)

    same((graph, times), old, "최소 시간 탐색은 그래프와 이동시간을 변경하지 않음")


def check_stage_1():
    # 기본 도시의 도로 연결과 노드 등록 순서
    city, _ = make_scenario()
    actual = traffic.build_road_graph(city)
    expected = sample_graph()

    same(actual, expected, "기본 도시의 도로 연결과 노드 등록 순서")
    same(list(actual), list(expected), "기본 도시의 도로 연결과 노드 등록 순서")

    # 경계 도로와 양방향 연결
    city = make_empty_city()
    for x, y in [(0, 0), (1, 0), (0, 1), (3, 3), (4, 3)]:
        city["grid"][y][x]["road"] = True
    graph = traffic.build_road_graph(city)

    same(graph[(0, 0)], [(1, 0), (0, 1)], "경계 도로와 양방향 연결")
    same(graph[(4, 3)], [(3, 3)], "경계 도로와 양방향 연결")
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            same(node in graph[neighbor], True, "경계 도로와 양방향 연결")

    # 빈 도시와 대각선 도로의 분리
    city = make_empty_city()

    same(traffic.build_road_graph(city), {}, "빈 도시와 대각선 도로의 분리")
    city["grid"][0][0]["road"] = True
    city["grid"][1][1]["road"] = True

    same(traffic.build_road_graph(city), {(0, 0): [], (1, 1): []}, "빈 도시와 대각선 도로의 분리")

    # 도로 그래프 생성은 도시를 변경하지 않음
    city, _ = make_scenario()
    old = deepcopy(city)
    traffic.build_road_graph(city)

    same(city, old, "도로 그래프 생성은 도시를 변경하지 않음")


def check_stage_2():
    # 기본 도시의 고립 도로와 연결 요소 번호
    components = traffic.connected_components(sample_graph())

    same(components[(2, 0)], 0, "기본 도시의 고립 도로와 연결 요소 번호")
    same(len(set(components.values())), 2, "기본 도시의 고립 도로와 연결 요소 번호")
    for node in sample_graph():
        if node != (2, 0):
            same(components[node], 1, "기본 도시의 고립 도로와 연결 요소 번호")

    # 빈 그래프와 고립된 노드
    same(traffic.connected_components({}), {}, "빈 그래프와 고립된 노드")
    graph = {(0, 0): [], (2, 0): [], (4, 0): []}

    same(
        traffic.connected_components(graph),
        {(0, 0): 0, (2, 0): 1, (4, 0): 2},
        "빈 그래프와 고립된 노드",
    )

    # 분리된 도로 구역의 연결 요소
    graph = {(0, 0): [(1, 0)], (1, 0): [(0, 0)], (3, 0): [(3, 1)], (3, 1): [(3, 0)], (4, 3): []}
    components = traffic.connected_components(graph)

    same(components[(0, 0)], components[(1, 0)], "분리된 도로 구역의 연결 요소")
    same(components[(3, 0)], components[(3, 1)], "분리된 도로 구역의 연결 요소")
    same(len(set(components.values())), 3, "분리된 도로 구역의 연결 요소")

    # 연결 요소 탐색은 그래프를 변경하지 않음
    graph = sample_graph()
    old = deepcopy(graph)
    traffic.connected_components(graph)

    same(graph, old, "연결 요소 탐색은 그래프를 변경하지 않음")


def check_stage_3():
    # BFS의 최소 구간 경로
    graph = sample_graph()
    path = traffic.bfs_path(graph, (0, 2), (3, 2))

    same(path, [(0, 2), (1, 2), (2, 2), (3, 2)], "BFS의 최소 구간 경로")
    same(len(path) - 1, 3, "BFS의 최소 구간 경로")

    # 같은 출발지와 도착지
    same(traffic.bfs_path(sample_graph(), (0, 2), (0, 2)), [(0, 2)], "같은 출발지와 도착지")

    # 없는 좌표와 도달할 수 없는 경로
    graph = sample_graph()
    for start, goal in [((4, 0), (3, 2)), ((0, 2), (4, 0)), ((0, 2), (2, 0))]:
        same(traffic.bfs_path(graph, start, goal), None, "없는 좌표와 도달할 수 없는 경로")
    same(traffic.bfs_path({}, (0, 0), (0, 0)), None, "없는 좌표와 도달할 수 없는 경로")

    # 순환 도로의 중복 없는 경로와 입력 보존
    graph = sample_graph()
    old = deepcopy(graph)
    path = traffic.bfs_path(graph, (3, 3), (0, 2))

    same(len(path), 5, "순환 도로의 중복 없는 경로와 입력 보존")
    same(len(set(path)), len(path), "순환 도로의 중복 없는 경로와 입력 보존")
    same(graph, old, "순환 도로의 중복 없는 경로와 입력 보존")


def check_stage_4():
    # 직진과 우회 경로의 거리 / 시간
    times = {node: 1 for node in sample_graph()}
    times[(1, 2)] = 5
    direct = [(0, 2), (1, 2), (2, 2), (3, 2)]
    detour = [(0, 2), (0, 3), (1, 3), (2, 3), (3, 3), (3, 2)]

    same(
        traffic.route_metrics(direct, times),
        {"distance_m": 300, "time_min": 7},
        "직진과 우회 경로의 거리 / 시간",
    )
    same(
        traffic.route_metrics(detour, times),
        {"distance_m": 500, "time_min": 5},
        "직진과 우회 경로의 거리 / 시간",
    )

    # 노드 하나인 경로와 경로 없음의 구분
    same(
        traffic.route_metrics([(0, 0)], {}),
        {"distance_m": 0, "time_min": 0},
        "노드 하나인 경로와 경로 없음의 구분",
    )
    same(traffic.route_metrics(None, {}), None, "노드 하나인 경로와 경로 없음의 구분")
    same(traffic.route_metrics([], {}), None, "노드 하나인 경로와 경로 없음의 구분")

    # 출발 셀 비용 제외와 구간 거리 매개변수
    times = {(0, 0): 100, (1, 0): 1.5, (2, 0): 2.5}

    same(
        traffic.route_metrics([(0, 0), (1, 0), (2, 0)], times, 80),
        {"distance_m": 160, "time_min": 4},
        "출발 셀 비용 제외와 구간 거리 매개변수",
    )

    # 경로 지표 계산은 경로와 이동시간을 변경하지 않음
    path = [(0, 0), (1, 0)]
    times = {(0, 0): 1, (1, 0): 2}
    old = deepcopy((path, times))
    traffic.route_metrics(path, times)

    same((path, times), old, "경로 지표 계산은 경로와 이동시간을 변경하지 않음")


def check_stage_5():
    # 4분 동안의 대기열 증가
    queue = 0
    for expected in [3, 6, 9, 12]:
        result = traffic.advance_queue(queue, 8, 5)

        same(result, {"served": 5, "queue": expected}, "4분 동안의 대기열 증가")
        queue = result["queue"]

    # 대기 없음과 남는 처리 용량
    same(traffic.advance_queue(0, 0, 5), {"served": 0, "queue": 0}, "대기 없음과 남는 처리 용량")
    same(traffic.advance_queue(1, 2, 5), {"served": 3, "queue": 0}, "대기 없음과 남는 처리 용량")

    # 유입이 없을 때 대기열 해소
    same(traffic.advance_queue(8, 0, 5), {"served": 5, "queue": 3}, "유입이 없을 때 대기열 해소")
    same(traffic.advance_queue(3, 0, 5), {"served": 3, "queue": 0}, "유입이 없을 때 대기열 해소")

    # 차량 수 보존과 처리 용량 제한
    for queue, arrivals, capacity in [(0, 8, 5), (20, 8, 5), (2, 1, 8), (1, 0, 1)]:
        result = traffic.advance_queue(queue, arrivals, capacity)

        same(result["served"] + result["queue"], queue + arrivals, "차량 수 보존과 처리 용량 제한")
        same(result["queue"] >= 0, True, "차량 수 보존과 처리 용량 제한")
        same(result["served"] <= capacity, True, "차량 수 보존과 처리 용량 제한")


def check_stage_6():
    # 일자리 접근성의 시간 한도 경계 포함
    jobs = [
        {"id": "J", "entrances": [(3, 2)], "jobs": 12},
        {"id": "F", "entrances": [(3, 3)], "jobs": 20},
    ]
    distances = {(3, 2): 3, (3, 3): 4}

    same(
        traffic.count_accessible_jobs(jobs, distances, 4), 32, "일자리 접근성의 시간 한도 경계 포함"
    )
    same(
        traffic.count_accessible_jobs(jobs, distances, 3), 12, "일자리 접근성의 시간 한도 경계 포함"
    )
    same(
        traffic.count_accessible_jobs(jobs, distances, 2), 0, "일자리 접근성의 시간 한도 경계 포함"
    )

    # 혼잡하거나 도달할 수 없는 일자리
    jobs = [
        {"id": "J", "entrances": [(3, 2)], "jobs": 12},
        {"id": "F", "entrances": [(3, 3)], "jobs": 20},
        {"id": "X", "entrances": [(2, 0)], "jobs": 50},
    ]

    same(
        traffic.count_accessible_jobs(jobs, {(3, 2): 5, (3, 3): 4}, 4),
        20,
        "혼잡하거나 도달할 수 없는 일자리",
    )
    same(traffic.count_accessible_jobs(jobs, {}, 4), 0, "혼잡하거나 도달할 수 없는 일자리")

    # 여러 입구와 중복 ID의 일자리는 한 번만 합산
    jobs = [
        {"id": "J", "entrances": [(1, 0), (2, 0)], "jobs": 12},
        {"id": "J", "entrances": [(2, 0)], "jobs": 12},
        {"id": "F", "entrances": [], "jobs": 20},
    ]

    same(
        traffic.count_accessible_jobs(jobs, {(1, 0): 3, (2, 0): 4}, 4),
        12,
        "여러 입구와 중복 ID의 일자리는 한 번만 합산",
    )

    # 빈 일자리 목록과 입력 보존
    same(traffic.count_accessible_jobs([], {}, 4), 0, "빈 일자리 목록과 입력 보존")
    jobs = [{"id": "J", "entrances": [(0, 0)], "jobs": 12}]
    distances = {(0, 0): 0}
    old = deepcopy((jobs, distances))

    same(traffic.count_accessible_jobs(jobs, distances, 0), 12, "빈 일자리 목록과 입력 보존")
    same((jobs, distances), old, "빈 일자리 목록과 입력 보존")


def check_integration():
    # 기본 / 혼잡 / 단절 도시의 연결 요소와 접근성
    for name, components, jobs in [
        ("default", 2, 32),
        ("congested", 2, 20),
        ("disconnected", 3, 0),
    ]:
        city, state = make_scenario(name)
        graph = traffic.build_road_graph(city)
        times = cost_snapshot(state)

        same(
            len(set(traffic.connected_components(graph).values())),
            components,
            "기본 / 혼잡 / 단절 도시의 연결 요소와 접근성",
        )
        distances = dijkstra_all(graph, state["start"], times)

        same(
            traffic.count_accessible_jobs(job_destinations(city), distances, 4),
            jobs,
            "기본 / 혼잡 / 단절 도시의 연결 요소와 접근성",
        )

    # 선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리
    city, state = make_scenario()
    old_city, old_state = (deepcopy(city), deepcopy(state))
    for _ in range(4):
        state = step_selected_queue(state)

    same(state["minute"], 4, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")
    same(state["queues"][(1, 2)], 12, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")
    same(state["last_served"], 5, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")
    same(city, old_city, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")
    same(old_state["minute"], 0, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")
    for node in state["queues"]:
        if node != (1, 2):
            same(state["queues"][node], 0, "선택한 도로만 대기열 갱신 / 도시와 교통 시간 분리")


STAGES = [
    ("TODO 1: 도로 그래프", check_stage_1),
    ("TODO 2: 연결 요소", check_stage_2),
    ("TODO 3: BFS 경로", check_stage_3),
    ("TODO 4: 경로 거리와 시간", check_stage_4),
    ("TODO 5: 대기열 갱신", check_stage_5),
    ("TODO 6: 일자리 접근성", check_stage_6),
]


def main():
    parser = argparse.ArgumentParser(description="Road Networks and Traffic Lab")
    parser.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1부터 이 단계까지 점검 (기본: 6)",
    )
    args = parser.parse_args()

    checks = [("제공 코드", check_support)] + STAGES[: args.stage]
    if args.stage == 6:
        checks.append(("통합 검사", check_integration))

    failed = False
    unfinished = False

    for name, check in checks:
        try:
            check()
        except NotImplementedError as error:
            unfinished = True
            print("[미완성] " + name + ": " + str(error))
        except AssertionError as error:
            failed = True
            print("[실패] " + name + ": " + str(error))
        except Exception:
            failed = True
            print("[오류] " + name)
            traceback.print_exc()
        else:
            print("[통과] " + name)

    if failed:
        return 1
    if unfinished:
        return 2

    print("요청한 모든 점검을 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

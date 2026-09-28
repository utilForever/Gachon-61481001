"""
교통 시나리오 생성, 이동시간 계산, 상태 검증, JSON 저장 / 불러오기.

도시의 day(일)와 교통의 minute(분)은 별개이다.
교통 상태는 도로 좌표별 진입 시간 / 처리 용량 / 대기 차량 수를 dict에 저장한다.
대기열 갱신은 선택한 도로 한 곳에만 적용하며, 계산 전 상태는 보존한다.
"""

import json
import math
from copy import deepcopy
from pathlib import Path

from city_data import make_empty_city, validate_city
from model import neighbors4

SCENARIOS = ("default", "congested", "disconnected")


def _road_nodes(city):
    nodes = []
    for y, row in enumerate(city["grid"]):
        for x, cell in enumerate(row):
            if cell["road"]:
                nodes.append((x, y))

    return nodes


def make_scenario(name="default"):
    """기본 / 혼잡 / 단절 시나리오의 도시와 교통 상태를 새로 만들어 반환한다."""
    if name not in SCENARIOS:
        raise ValueError("시나리오는 default / congested / disconnected 중 하나입니다.")

    city = make_empty_city()
    for y in (2, 3):
        for x in range(4):
            city["grid"][y][x]["road"] = True
    city["grid"][0][2]["road"] = True

    definitions = [
        ("H", "house", 0, 1, 6, 10, "R"),
        ("P", "park", 1, 1, 0, 0, None),
        ("J", "shop", 3, 1, 6, 12, "C"),
        ("F", "factory", 4, 3, 8, 20, "I"),
    ]
    for ident, kind, x, y, quantity, capacity, zone in definitions:
        building = {"id": ident, "kind": kind, "x": x, "y": y, "status": "operating"}
        if kind == "house":
            building.update(population=quantity, capacity=capacity)
        elif kind != "park":
            building.update(workers=quantity, capacity=capacity)
        city["buildings"][ident] = building
        city["grid"][y][x]["building_id"] = ident
        city["grid"][y][x]["zone"] = zone

    if name == "disconnected":
        city["grid"][2][2]["road"] = False
        city["grid"][3][2]["road"] = False

    nodes = _road_nodes(city)
    state = {
        "minute": 0,
        "start": (0, 2),
        "goal": (3, 2),
        "selected_road": (1, 2),
        "arrivals": 8,
        "last_served": 0,
        "base_times": {node: 1.0 for node in nodes},
        "capacities": {node: 5 for node in nodes},
        "queues": {node: 0 for node in nodes},
    }
    if name == "congested":
        state["queues"][(1, 2)] = 20

    validate_transport(city, state)
    return city, state


def _nonnegative_integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(label + "은(는) 0 이상의 정수여야 합니다.")


def validate_transport(city, state):
    """도시와 교통 상태의 도로 목록 / 값 / 좌표를 검사한다. 입력은 보존한다."""
    validate_city(city)
    names = {
        "minute",
        "start",
        "goal",
        "selected_road",
        "arrivals",
        "last_served",
        "base_times",
        "capacities",
        "queues",
    }
    if type(state) is not dict or set(state) != names:
        raise ValueError("교통 상태의 항목이 올바르지 않습니다.")

    nodes = set(_road_nodes(city))
    for key in ("minute", "arrivals", "last_served"):
        _nonnegative_integer(state[key], key)

    for key in ("start", "goal", "selected_road"):
        node = state[key]
        if node is None:
            if nodes:
                raise ValueError(key + "에 도로 셀을 선택하세요.")
        elif (
            type(node) is not tuple
            or len(node) != 2
            or any(type(value) is not int for value in node)
            or node not in nodes
        ):
            raise ValueError(key + "은(는) 지도에 있는 도로 좌표여야 합니다.")

    for key in ("base_times", "capacities", "queues"):
        if type(state[key]) is not dict or set(state[key]) != nodes:
            raise ValueError(key + "의 도로 목록이 지도와 일치하지 않습니다.")

    for node in nodes:
        base = state["base_times"][node]
        if type(base) not in (int, float) or not math.isfinite(base) or base < 1:
            raise ValueError("기본 진입 시간은 1분 이상의 유한한 수여야 합니다.")
        capacity = state["capacities"][node]
        if type(capacity) is not int or capacity < 1:
            raise ValueError("도로 처리 용량은 1대/분 이상의 정수여야 합니다.")
        _nonnegative_integer(state["queues"][node], "대기 차량 수")


def cost_snapshot(state):
    """기본 진입 시간에 대기 차량 수 / 처리 용량을 더한 새 dict를 반환한다."""
    times = {}
    for node in state["base_times"]:
        times[node] = state["base_times"][node] + state["queues"][node] / state["capacities"][node]

    return times


def job_destinations(city):
    """운영 중인 상점 / 공장의 ID, 입구 도로 목록, 전체 일자리 수를 모은다."""
    jobs = []
    for ident, building in city["buildings"].items():
        if building["kind"] not in ("shop", "factory"):
            continue
        if building["status"] != "operating":
            continue

        entrances = []
        for node in neighbors4(city, building["x"], building["y"]):
            x, y = node
            if city["grid"][y][x]["road"]:
                entrances.append(node)
        jobs.append({"id": ident, "entrances": entrances, "jobs": building["capacity"]})

    return jobs


def sync_transport(city, state):
    """편집한 도시의 도로 목록에 맞춘 새 교통 상태를 반환한다. 입력은 보존한다."""
    validate_city(city)
    new = deepcopy(state)
    nodes = _road_nodes(city)
    for key, default in (("base_times", 1.0), ("capacities", 5), ("queues", 0)):
        new[key] = {node: state[key].get(node, default) for node in nodes}
    for key in ("start", "goal", "selected_road"):
        if new[key] not in nodes:
            new[key] = nodes[0] if nodes else None

    validate_transport(city, new)
    return new


def step_selected_queue(state):
    """선택한 도로의 대기열만 1분 갱신한 독립적인 새 상태를 반환한다."""
    from traffic import advance_queue

    node = state["selected_road"]
    if node is None:
        raise ValueError("대기열을 갱신할 도로를 선택하세요.")

    result = advance_queue(state["queues"][node], state["arrivals"], state["capacities"][node])

    new = deepcopy(state)
    # 이번 실험은 선택한 도로 한 곳의 대기열만 1분 갱신한다.
    new["queues"][node] = result["queue"]
    new["last_served"] = result["served"]
    new["minute"] += 1

    return new


def save_scenario(city, state, path):
    """검증한 도시와 교통 상태를 하나의 UTF-8 JSON으로 저장한다."""
    validate_transport(city, state)
    transport = {
        key: state[key]
        for key in ("minute", "start", "goal", "selected_road", "arrivals", "last_served")
    }
    transport["roads"] = []
    for x, y in _road_nodes(city):
        node = (x, y)
        transport["roads"].append(
            {
                "x": x,
                "y": y,
                "base_time_min": state["base_times"][node],
                "capacity": state["capacities"][node],
                "queue": state["queues"][node],
            }
        )

    document = {"format": "virtual-city-traffic-v1", "city": city, "traffic": transport}
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    Path(path).write_text(text + "\n", encoding="utf-8")


def load_scenario(path):
    """JSON을 읽어 도로 좌표를 복원하고 검증한 도시 / 교통 상태를 반환한다."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("UTF-8 형식의 올바른 교통 시나리오 JSON 파일이 아닙니다.") from error

    if (
        type(document) is not dict
        or set(document) != {"format", "city", "traffic"}
        or document["format"] != "virtual-city-traffic-v1"
    ):
        raise ValueError("교통 시나리오 파일 형식이 올바르지 않습니다.")

    raw = document["traffic"]
    names = {"minute", "start", "goal", "selected_road", "arrivals", "last_served", "roads"}
    if type(raw) is not dict or set(raw) != names or type(raw["roads"]) is not list:
        raise ValueError("교통 시나리오의 상태 항목이 올바르지 않습니다.")

    state = {key: raw[key] for key in ("minute", "arrivals", "last_served")}
    for key in ("start", "goal", "selected_road"):
        node = raw[key]
        if node is None:
            state[key] = None
        elif type(node) is list and len(node) == 2 and all(type(value) is int for value in node):
            state[key] = tuple(node)
        else:
            raise ValueError(key + "의 좌표 형식이 올바르지 않습니다.")

    state.update(base_times={}, capacities={}, queues={})
    for road in raw["roads"]:
        if (
            type(road) is not dict
            or set(road) != {"x", "y", "base_time_min", "capacity", "queue"}
            or type(road["x"]) is not int
            or type(road["y"]) is not int
        ):
            raise ValueError("도로 설정의 형식이 올바르지 않습니다.")
        node = (road["x"], road["y"])
        if node in state["base_times"]:
            raise ValueError("도로 설정에 같은 좌표가 중복되어 있습니다.")
        state["base_times"][node] = road["base_time_min"]
        state["capacities"][node] = road["capacity"]
        state["queues"][node] = road["queue"]

    city = document["city"]
    validate_transport(city, state)
    return city, state

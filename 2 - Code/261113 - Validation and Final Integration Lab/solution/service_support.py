"""공공서비스 상태 초기화, 시간별 진행과 기존 도시 모형 연결."""

import ast
import csv
import json
import math
from copy import deepcopy
from pathlib import Path

import abm_support
import kpi_support
import service_rules as rules
from model import neighbors4
from routing import dijkstra_all
from traffic import build_road_graph

SCENARIOS = {
    "normal": "기본 조건",
    "outage": "정전",
    "flood": "침수",
    "hospital": "병원 확충",
    "water": "급수 확충",
    "both": "동시 확충",
}
RULE_NAMES = (
    "service_coverage",
    "advance_queue",
    "allocate_power",
    "update_water",
    "update_waste",
    "transport_pollution",
)
DEMANDS = {"hospital": 30, "pump": 20, "housing": 50, "industry": 20}
PRIORITY = ["hospital", "pump", "housing", "industry"]
POPULATIONS = {"A": 100, "B": 100, "C": 100, "D": 100}
REQUESTS = {"A": 4, "B": 3, "C": 3, "D": 2}
LOCAL_MINUTES = {"A": 2, "B": 2, "C": 8, "D": 12}


def pending_tasks():
    tree = ast.parse(Path(rules.__file__).read_text(encoding="utf-8"))
    pending = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in RULE_NAMES:
            for child in ast.walk(node):
                if isinstance(child, ast.Raise):
                    exception = child.exc.func if isinstance(child.exc, ast.Call) else child.exc
                    if isinstance(exception, ast.Name) and exception.id == "NotImplementedError":
                        pending.append(RULE_NAMES.index(node.name) + 1)
                        break

    return pending


def new_state(scenario="normal"):
    if scenario not in SCENARIOS:
        raise ValueError("알 수 없는 서비스 시나리오입니다.")

    return {
        "scenario": scenario,
        "hour": 0,
        "queue": 0,
        "water_stored": 10.0,
        "battery_kwh": 60.0,
        "waste_city": 0.0,
        "waste_plant": 0.0,
        "pollution": [100.0, 0.0, 0.0],
        "history": [],
        "fire_queue": 0,
        "fire_busy_until": [],
        "last": None,
    }


def ensure_state(session):
    if "services" not in session:
        session["services"] = new_state()

    return session["services"]


def conditions(state, hour=None):
    hour = state["hour"] if hour is None else hour
    flooded = state["scenario"] == "flood" and hour in (2, 3)
    road_depth = 0.4 if flooded else 0.0
    substation_depth = 0.6 if flooded else 0.0
    outage = (state["scenario"] == "outage" and hour in (2, 3)) or substation_depth > 0.5

    return {
        "supply_kw": 0 if outage else 100,
        "closed_roads": [(3, 1)] if road_depth > 0.3 else [],
        "road_depth": road_depth,
        "substation_depth": substation_depth,
        "inflow_rate": 8 if state["scenario"] in ("water", "both") else 6,
        "hospital_capacity": 10 if state["scenario"] in ("hospital", "both") else 8,
    }


def travel_times(session, closed_roads=()):
    graph = build_road_graph(session["city"])

    for closed in closed_roads:
        graph.pop(tuple(closed), None)

    for node in graph:
        graph[node] = [neighbor for neighbor in graph[node] if neighbor in graph]

    costs = {node: 2 for node in graph}
    destination = (0, 2)
    result = {}

    for area in POPULATIONS:
        building = session["city"]["buildings"][area]
        entrances = [
            node
            for node in neighbors4(session["city"], building["x"], building["y"])
            if node in graph
        ]
        candidates = []
        for entrance in entrances:
            distances = dijkstra_all(graph, entrance, costs)
            if destination in distances:
                candidates.append(distances[destination] + LOCAL_MINUTES[area])
        result[area] = min(candidates) if candidates else None

    return result


def current_coverage(session):
    state = ensure_state(session)
    config = conditions(state)
    times = travel_times(session, config["closed_roads"])

    return times, rules.service_coverage(times, POPULATIONS, 15)


def school_allocation():
    return [
        {
            "school": "S1",
            "areas": "A / B",
            "capacity": 70,
            "students": 50,
            "assigned": 50,
            "vacancy": 20,
            "unassigned": 0,
        },
        {
            "school": "S2",
            "areas": "C / D",
            "capacity": 30,
            "students": 50,
            "assigned": 30,
            "vacancy": 0,
            "unassigned": 20,
        },
    ]


def advance_fire(state, hour):
    busy = [return_hour for return_hour in state["fire_busy_until"] if return_hour > hour]
    requests = 3 if hour == 1 else 0
    waiting = state["fire_queue"] + requests
    dispatched = min(waiting, 2 - len(busy))
    busy.extend([hour + 2] * dispatched)
    state["fire_busy_until"] = busy
    state["fire_queue"] = waiting - dispatched

    return {
        "fire_requests": requests,
        "fire_dispatched": dispatched,
        "fire_waiting": state["fire_queue"],
        "fire_busy": len(busy),
    }


def runoff_volume(rain_m, area_m2, coefficient):
    return rain_m * area_m2 * coefficient


def noise_total(levels_db):
    return 10 * math.log10(sum(10 ** (level / 10) for level in levels_db)) if levels_db else None


def environmental_scores(session, amounts, closed_roads=()):
    graph = build_road_graph(session["city"])

    for closed in closed_roads:
        graph.pop(tuple(closed), None)

    for node in graph:
        graph[node] = [neighbor for neighbor in graph[node] if neighbor in graph]

    costs = {node: 2 for node in graph}
    parks = [
        building
        for building in session["city"]["buildings"].values()
        if building["kind"] == "park" and building["status"] == "operating"
    ]
    result = {}
    indices = {"A": 0, "B": 1, "C": 1, "D": 2}

    for area, index in indices.items():
        house = session["city"]["buildings"][area]
        entrances = [
            node for node in neighbors4(session["city"], house["x"], house["y"]) if node in graph
        ]
        park_access = False
        for start in entrances:
            distances = dijkstra_all(graph, start, costs)
            for park in parks:
                for node in neighbors4(session["city"], park["x"], park["y"]):
                    if node in distances and distances[node] <= 10:
                        park_access = True
        pollution_index = min(1, max(0, amounts[index] / 100))
        score = max(0, min(100, 100 - 40 * pollution_index - 20 * 0.5 + 15 * park_access))
        result[area] = score

    return result


def validate_state(state):
    for key in (
        "hour",
        "queue",
        "water_stored",
        "battery_kwh",
        "waste_city",
        "waste_plant",
        "fire_queue",
    ):
        if (
            not isinstance(state[key], (int, float))
            or not math.isfinite(state[key])
            or state[key] < 0
        ):
            raise ValueError(f"{key}: 유한한 음이 아닌 값이 필요합니다.")

    if state["water_stored"] > 20 + 1e-9 or state["battery_kwh"] > 60 + 1e-9:
        raise ValueError("저장 용량을 초과했습니다.")
    if len(state["pollution"]) != 3 or any(
        not math.isfinite(v) or v < 0 for v in state["pollution"]
    ):
        raise ValueError("오염량은 셀 3개의 음이 아닌 값이어야 합니다.")
    if state["scenario"] not in SCENARIOS or len(state["history"]) != state["hour"]:
        raise ValueError("시나리오 또는 시간 기록이 올바르지 않습니다.")


def advance_hour(session):
    missing = pending_tasks()
    if missing:
        raise NotImplementedError(
            "service_rules.py의 TODO " + ", ".join(map(str, missing)) + "을 완성하세요."
        )

    working = deepcopy(session)
    old = ensure_state(working)
    new = deepcopy(old)
    hour = old["hour"] + 1
    config = conditions(old, hour)
    times = travel_times(working, config["closed_roads"])
    coverage = rules.service_coverage(times, POPULATIONS.copy(), 15)
    arrivals = sum(REQUESTS[area] for area in coverage["covered"])
    unassigned = sum(REQUESTS.values()) - arrivals
    power = rules.allocate_power(config["supply_kw"], DEMANDS.copy(), PRIORITY.copy())
    backup_kw = min(30 - power["hospital"], 30, old["battery_kwh"])
    new["battery_kwh"] -= backup_kw  # 한 시간 동안 kW × 1시간만큼 kWh를 사용한다.
    hospital_kw = power["hospital"] + backup_kw
    inflow = config["inflow_rate"] * power["pump"] / DEMANDS["pump"]
    water = rules.update_water(old["water_stored"], inflow, 8, 20)
    new["water_stored"] = water["stored"]
    capacity = math.floor(
        config["hospital_capacity"] * min(hospital_kw / 30, water["supplied"] / 8)
    )
    queue = rules.advance_queue(old["queue"], arrivals, capacity)
    new["queue"] = queue["queue"]
    pollution = rules.transport_pollution(old["pollution"], 0.2, 0.1)
    new["pollution"] = pollution
    waste = {"city": old["waste_city"], "plant": old["waste_plant"], "collected": 0, "processed": 0}
    if hour % 24 == 0:
        waste = rules.update_waste(old["waste_city"], old["waste_plant"], 8, 6, 5)

    new["waste_city"], new["waste_plant"] = waste["city"], waste["plant"]
    fire = advance_fire(new, hour)
    row = {
        "hour": hour,
        "coverage_ratio": coverage["ratio"],
        "unreachable_population": coverage["unreachable_population"],
        "arrivals": arrivals,
        "unassigned": unassigned,
        "capacity": capacity,
        "served": queue["served"],
        "queue": new["queue"],
        "grid_kw": config["supply_kw"],
        "hospital_kw": hospital_kw,
        "pump_kw": power["pump"],
        "housing_kw": power["housing"],
        "industry_kw": power["industry"],
        "backup_kw": backup_kw,
        "battery_kwh": new["battery_kwh"],
        "water_inflow": inflow,
        "water_supplied": water["supplied"],
        "water_unmet": water["unmet"],
        "water_stored": water["stored"],
        "overflow": water["overflow"],
        "waste_city": waste["city"],
        "waste_plant": waste["plant"],
        "waste_collected": waste["collected"],
        "waste_processed": waste["processed"],
        "pollution_0": pollution[0],
        "pollution_1": pollution[1],
        "pollution_2": pollution[2],
        "road_depth": config["road_depth"],
        "substation_depth": config["substation_depth"],
        **fire,
    }
    new["hour"] = hour
    new["last"] = row
    new["history"].append(row)
    validate_state(new)

    # 모든 계산이 성공한 뒤에만 상태를 교체한다. 오류가 나면 기존 시각과 상태를 보존한다.
    scores = environmental_scores(working, pollution, config["closed_roads"])

    for area, score in scores.items():
        working["agents"]["houses"][area]["environment"] = score

    working["services"] = new
    session.clear()
    session.update(working)

    return row


def reset_services(session, scenario="normal"):
    session["services"] = new_state(scenario)

    for area, score in environmental_scores(session, session["services"]["pollution"]).items():
        session["agents"]["houses"][area]["environment"] = score


def save_session(session, path):
    abm_support.validate_agents(session)
    validate_state(ensure_state(session))

    base = {key: deepcopy(value) for key, value in session.items() if key != "services"}
    document = kpi_support._to_json_document({"format": "virtual-city-services-v1", **base})
    document["services"] = deepcopy(session["services"])
    Path(path).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_session(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("format") not in ("virtual-city-services-v1", "virtual-city-abm-v1"):
        raise ValueError("도시 / 행위자 또는 공공서비스 상태 파일을 선택하세요.")

    services = document.pop("services", new_state())
    agents = document.pop("agents")
    document["format"] = "virtual-city-kpi-v1"
    session = kpi_support.restore_session(kpi_support._from_json_document(document))
    session["agents"] = agents
    session["services"] = services
    abm_support.validate_agents(session)
    validate_state(services)

    return session


def export_history(session, path):
    rows = ensure_state(session)["history"]
    if not rows:
        raise ValueError("먼저 한 시간 이상 진행하세요.")

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

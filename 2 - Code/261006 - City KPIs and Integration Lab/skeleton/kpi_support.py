"""통근 자료 생성, 지표 계산 연결, 분 단위 관측, JSON 저장 / 복원, CSV 내보내기."""

import csv
import json
import math
from copy import deepcopy
from pathlib import Path
from statistics import median

import metrics
from model import neighbors4
from routing import dijkstra_all
from traffic import build_road_graph
from traffic_data import cost_snapshot, make_scenario, step_selected_queue, validate_transport

SCENARIOS = ("default", "congested", "disconnected")
KPI_KEYS = (
    "population",
    "building_count",
    "planned_trips",
    "reachable_trips",
    "unreachable_trips",
    "within_limit_trips",
    "accessibility_ratio",
    "mean_time_min",
    "median_time_min",
    "p90_time_min",
    "developable_count",
    "developable_cells",
    "observed_minutes",
    "congested_minutes",
    "peak_queue",
    "current_queue",
)


def make_lab_session(scenario="default"):
    """주택 H / A의 주민 10명으로 실험을 시작하고 가능한 경우 0분 지표를 기록한다."""
    city, transport = make_scenario(scenario)
    city["buildings"]["A"] = {
        "id": "A",
        "kind": "house",
        "x": 2,
        "y": 1,
        "population": 4,
        "capacity": 10,
        "status": "operating",
    }
    city["grid"][1][2]["building_id"] = "A"
    city["grid"][1][2]["zone"] = "R"

    session = {
        "city": city,
        "transport": transport,
        "history": [],
        "observations": [],
        "settings": {
            "scenario": scenario,
            "limit_minutes": 4.0,
            "queue_threshold": 5,
            "protected": [(1, 0)],
            "commute_target": "J",
        },
    }

    validate_transport(city, transport)
    record_current(session)
    return session


def _entrances(city, building):
    return [
        node
        for node in neighbors4(city, building["x"], building["y"])
        if city["grid"][node[1]][node[0]]["road"]
    ]


def build_commute_records(city, transport, destination_id="J"):
    """주민마다 예상 통근 한 건을 만든다. 도달 불가 시간은 None이며 입력은 보존한다."""
    graph = build_road_graph(city)
    costs = cost_snapshot(transport)
    destination = city["buildings"].get(destination_id)

    goals = []
    if (
        destination is not None
        and destination["kind"] in ("shop", "factory")
        and destination["status"] == "operating"
    ):
        goals = _entrances(city, destination)

    trips = []
    for ident, home in city["buildings"].items():
        if home["kind"] != "house":
            continue

        best_time = None
        for entrance in _entrances(city, home):
            distances = dijkstra_all(graph, entrance, costs)
            for goal in goals:
                if goal in distances:
                    time = distances[goal]
                    if best_time is None or time < best_time:
                        best_time = time

        # 주민 한 명마다 예정 통근 한 건을 만든다. 도달 불가도 목록에 남긴다.
        for index in range(home["population"]):
            trips.append(
                {
                    "home_id": ident,
                    "person_index": index + 1,
                    "destination_id": destination_id,
                    "time_min": best_time,
                }
            )

    return trips


def distribution_stats(trips):
    """도달 가능한 주민의 중앙값과 P90을 반환한다. 대상이 없으면 각각 None이다."""
    times = sorted(trip["time_min"] for trip in trips if trip["time_min"] is not None)
    if not times:
        return {"median_time_min": None, "p90_time_min": None}
    return {
        "median_time_min": median(times),
        "p90_time_min": times[math.ceil(0.9 * len(times)) - 1],
    }


def calculate_kpis(session):
    """현재 지표와 화면용 오류 안내를 반환한다. 시간과 기록은 바꾸지 않는다."""
    result = {key: None for key in KPI_KEYS}
    result["_errors"] = []
    result["_todo_status"] = {}

    city = session["city"]
    transport = session["transport"]

    settings = session["settings"]
    trips = build_commute_records(city, transport, settings["commute_target"])

    calls = [
        (1, metrics.summarize_city, (city,)),
        (2, metrics.summarize_trips, (trips, settings["limit_minutes"])),
        (3, metrics.find_developable_cells, (city, settings["protected"])),
        (4, metrics.summarize_congestion, (session["observations"], settings["queue_threshold"])),
    ]
    for task, function, args in calls:
        try:
            values = function(*args)
            if task == 3:
                result["developable_cells"] = values
                result["developable_count"] = len(values)
            else:
                result.update(values)
        except Exception as error:
            label = "TODO " + str(task) + ": "
            status = "미구현" if isinstance(error, NotImplementedError) else "오류"
            result["_todo_status"][task] = status
            result["_errors"].append(label + status + ": " + str(error).removeprefix(label))

    result.update(distribution_stats(trips))
    node = transport["selected_road"]
    result["current_queue"] = transport["queues"].get(node) if node is not None else None

    return result


def record_current(session):
    """현재 지표를 계산하고 오류가 없으면 기록한다. 같은 시각의 기록은 유지한다."""
    kpis = calculate_kpis(session)
    if not kpis["_errors"]:
        try:
            # 화면용 오류 안내는 기록에 넣지 않고 지표 값만 복사한다.
            row = {key: kpis[key] for key in KPI_KEYS}
            metrics.append_history(session["history"], session["transport"]["minute"], row)
        except Exception as error:
            status = "미구현" if isinstance(error, NotImplementedError) else "오류"
            kpis["_todo_status"][5] = status
            kpis["_errors"].append("TODO 5: " + status + ": " + str(error).removeprefix("TODO 5: "))

    return kpis


def advance_minutes(session, count=1):
    """선택 도로를 1분씩 관측 / 갱신하고 기록한다. 입력 session을 직접 수정한다."""
    if type(count) is not int or count < 1:
        raise ValueError("진행 시간은 1 이상의 정수여야 합니다.")
    if session["transport"]["selected_road"] is None:
        raise ValueError("관측할 도로를 선택하세요.")

    for _ in range(count):
        transport = session["transport"]
        node = transport["selected_road"]
        # [t, t+1) 구간은 시작 시점의 대기 차량 수로 관측한다.
        session["observations"].append(
            {
                "start_minute": transport["minute"],
                "duration_min": 1,
                "queue": transport["queues"][node],
                "road": node,
            }
        )
        session["transport"] = step_selected_queue(transport)
        result = record_current(session)

    return result


def reset_observation(session):
    """현재 도시와 대기열을 유지하고 시간 / 관측 / 기록을 초기화해 0분부터 시작한다."""
    session["transport"]["minute"] = 0
    session["transport"]["last_served"] = 0
    session["history"] = []
    session["observations"] = []

    return record_current(session)


def snapshot_session(session):
    """TODO 6으로 현재 실험 전체의 독립적인 스냅샷을 만든다."""
    return metrics.make_snapshot(
        session["city"],
        session["transport"],
        session["history"],
        session["settings"],
        session["observations"],
    )


def restore_session(snapshot):
    """저장 형식을 확인하고 독립적인 실험 상태를 복원한다. 잘못된 형식은 거절한다."""
    if type(snapshot) is not dict or snapshot.get("format") != "virtual-city-kpi-v1":
        raise ValueError("도시 지표 저장 파일 형식이 올바르지 않습니다.")

    names = {"city", "transport", "history", "settings", "observations"}
    if set(snapshot) != names | {"format"}:
        raise ValueError("저장된 도시 상태에 필요한 항목이 빠져 있습니다.")

    session = deepcopy({key: snapshot[key] for key in names})
    validate_session(session)
    return session


def _valid_number(value, label, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(label + " 값이 올바르지 않습니다.")


def validate_session(session):
    """도시, 교통, 설정, 기록의 시간 순서를 검증한다. 잘못된 상태는 ValueError이다."""
    validate_transport(session["city"], session["transport"])

    settings = session["settings"]
    if type(settings) is not dict or set(settings) != {
        "scenario",
        "limit_minutes",
        "queue_threshold",
        "protected",
        "commute_target",
    }:
        raise ValueError("지표 설정의 항목이 올바르지 않습니다.")
    if type(settings["scenario"]) is not str or type(settings["commute_target"]) is not str:
        raise ValueError("시나리오와 목적지 ID는 문자열이어야 합니다.")

    _valid_number(settings["limit_minutes"], "통근 시간 기준")
    _valid_number(settings["queue_threshold"], "혼잡 대기 차량 기준")

    if type(settings["protected"]) is not list:
        raise ValueError("보전 셀은 좌표 목록이어야 합니다.")
    for node in settings["protected"]:
        if (
            type(node) is not tuple
            or len(node) != 2
            or any(type(n) is not int for n in node)
            or not 0 <= node[0] < 5
            or not 0 <= node[1] < 4
        ):
            raise ValueError("보전 셀의 좌표가 올바르지 않습니다.")

    if type(session["history"]) is not list or type(session["observations"]) is not list:
        raise ValueError("기록과 관측값은 목록이어야 합니다.")

    minute = session["transport"]["minute"]
    previous = -1
    for row in session["history"]:
        if type(row) is not dict or set(row) != set(KPI_KEYS) | {"minute"}:
            raise ValueError("기록의 열이 올바르지 않습니다.")
        t = row["minute"]
        if type(t) is not int or not previous < t <= minute:
            raise ValueError("기록 시각은 중복 없이 시간 순서여야 합니다.")
        previous = t
        for key in KPI_KEYS:
            if key != "developable_cells" and row[key] is not None:
                _valid_number(row[key], key)
        if row["accessibility_ratio"] is not None and row["accessibility_ratio"] > 1:
            raise ValueError("접근성 비율은 0부터 1 사이여야 합니다.")

    end = 0
    selected = session["transport"]["selected_road"]
    for observation in session["observations"]:
        if type(observation) is not dict or set(observation) != {
            "start_minute",
            "duration_min",
            "queue",
            "road",
        }:
            raise ValueError("관측 기록의 항목이 올바르지 않습니다.")
        start = observation["start_minute"]
        duration = observation["duration_min"]
        _valid_number(start, "관측 시작")
        _valid_number(duration, "관측 간격")
        _valid_number(observation["queue"], "대기 차량 수")
        if (
            duration <= 0
            or start != end
            or start + duration > minute
            or observation["road"] != selected
        ):
            raise ValueError("관측 구간은 선택한 도로에서 시간 순서로 이어져야 합니다.")
        end = start + duration

    if end != minute:
        raise ValueError("관측 구간과 현재 시각이 일치하지 않습니다.")


def _to_json_document(snapshot):
    document = deepcopy(snapshot)
    transport = document["transport"]
    roads = []

    for node in transport["base_times"]:
        roads.append(
            {
                "position": list(node),
                "base_time": transport["base_times"][node],
                "capacity": transport["capacities"][node],
                "queue": transport["queues"][node],
            }
        )

    for key in ("base_times", "capacities", "queues"):
        del transport[key]

    transport["roads"] = roads
    return document


def _coordinate(value):
    if type(value) is not list or len(value) != 2 or any(type(n) is not int for n in value):
        raise ValueError("좌표는 정수 두 개로 된 목록이어야 합니다.")
    return tuple(value)


def _from_json_document(document):
    result = deepcopy(document)
    transport = result["transport"]
    roads = transport.pop("roads")
    for key in ("start", "goal", "selected_road"):
        if transport[key] is not None:
            transport[key] = _coordinate(transport[key])

    transport.update(base_times={}, capacities={}, queues={})
    for road in roads:
        if set(road) != {"position", "base_time", "capacity", "queue"}:
            raise ValueError("도로별 저장 정보가 올바르지 않습니다.")
        node = _coordinate(road["position"])
        if node in transport["base_times"]:
            raise ValueError("도로 좌표가 중복되어 있습니다.")
        transport["base_times"][node] = road["base_time"]
        transport["capacities"][node] = road["capacity"]
        transport["queues"][node] = road["queue"]

    result["settings"]["protected"] = [
        _coordinate(node) for node in result["settings"]["protected"]
    ]
    for observation in result["observations"]:
        observation["road"] = _coordinate(observation["road"])
    for row in result["history"]:
        if row["developable_cells"] is not None:
            row["developable_cells"] = [_coordinate(node) for node in row["developable_cells"]]

    return result


def save_session(session, path):
    """검증한 실험 상태와 기록을 UTF-8 JSON으로 저장한다."""
    validate_session(session)
    document = _to_json_document(snapshot_session(session))
    Path(path).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_session(path):
    """KPI JSON의 좌표와 기록을 복원하고 검증한 실험 상태를 반환한다."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        return restore_session(_from_json_document(document))
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("올바른 도시 지표 JSON 파일이 아닙니다.") from error


def export_history_csv(session, path):
    """시각별 지표와 실험 조건을 UTF-8 BOM이 있는 CSV로 내보낸다. 입력은 보존한다."""
    settings = session["settings"]
    selected = session["transport"]["selected_road"]
    context = {
        key: settings[key]
        for key in ("scenario", "limit_minutes", "queue_threshold", "commute_target")
    }
    context["selected_road_x"] = selected[0] if selected is not None else None
    context["selected_road_y"] = selected[1] if selected is not None else None
    context["protected"] = json.dumps(settings["protected"], ensure_ascii=False)

    columns = ["minute"] + list(context) + [key for key in KPI_KEYS if key != "developable_cells"]

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in session["history"]:
            writer.writerow({**context, **row})

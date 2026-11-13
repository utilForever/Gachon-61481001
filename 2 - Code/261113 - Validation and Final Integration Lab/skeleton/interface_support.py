"""도시 조회 정보, 시간별 기록, 지도 파일과 관측 자료 관리."""

import ast
import csv
import json
import math
from copy import deepcopy
from pathlib import Path

import abm_support
import economy_support
import interface_rules as rules
import kpi_support
import service_support

DATA_DIR = Path(__file__).resolve().parent / "data"
RULE_NAMES = (
    "build_selection_info",
    "layer_style",
    "build_time_series",
    "find_events",
    "point_to_cell",
    "apply_observation",
)
REASON_LABELS = {
    "applied": "반영",
    "target_mismatch": "대상 불일치",
    "unit_mismatch": "단위 불일치",
    "missing": "값 누락",
    "stale": "과거 관측",
    "duplicate": "같은 관측 시각",
}
GRID = {"origin_x": 0, "origin_y": 0, "cell_size": 20, "rows": 4, "cols": 5}


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


def new_state():
    return {
        "observation": {
            "target_id": "H",
            "unit": "명",
            "value": 8,
            "observed_at": 600,
            "received_at": 601,
        },
        "observation_index": 0,
        "observation_log": [],
        "selected_target": "H",
        "selected_hour": None,
    }


def ensure_state(session):
    if "interface" not in session:
        session["interface"] = new_state()

    return session["interface"]


def make_session(scenario="normal"):
    session = abm_support.make_session()
    service_support.reset_services(session, scenario)
    economy_support.ensure_state(session)
    ensure_state(session)

    return session


def advance_hour(session):
    row = service_support.advance_hour(session)
    ensure_state(session)["selected_hour"] = row["hour"]

    return deepcopy(row)


def service_history(session):
    # 서비스 초기 상태의 대기 인원은 0명이다.
    return [{"hour": 0, "queue": 0}] + deepcopy(service_support.ensure_state(session)["history"])


def travel_times(session):
    return service_support.current_coverage(session)[0]


def _record(session, hour=None):
    state = service_support.ensure_state(session)
    hour = state["hour"] if hour is None else hour
    if type(hour) is not int or not 0 <= hour <= state["hour"]:
        raise ValueError("기록된 시각을 선택하세요.")
    if hour == 0:
        _, coverage = service_support.current_coverage(session)
        return {
            "hour": 0,
            "queue": 0,
            "water_unmet": 0,
            "capacity": service_support.conditions(state, 0)["hospital_capacity"],
            "coverage_ratio": coverage["ratio"],
        }

    return next(row for row in state["history"] if row["hour"] == hour)


def selection_feature(session, target_id="H", hour=None):
    state = service_support.ensure_state(session)
    row = _record(session, hour)
    feature = {"id": target_id, "source": "simulation", "hour": row["hour"]}
    if target_id == "H":
        feature.update(name="병원 H", metric="진료 대기 인원", value=row["queue"], unit="명")
    elif target_id == "W":
        feature.update(
            name="급수 시설 W", metric="공급하지 못한 물의 양", value=row["water_unmet"], unit="m³"
        )
    elif target_id in service_support.POPULATIONS:
        if row["hour"] != state["hour"]:
            raise ValueError(
                "주거지 접근시간은 현재 도로망의 계산값입니다. 현재 시각을 선택하세요."
            )

        feature.update(
            name=f"주거지 {target_id}",
            metric="병원까지 접근시간",
            value=travel_times(session)[target_id],
            unit="분",
            missing_label="경로 없음",
        )
    else:
        raise ValueError("H, W 또는 주거지 A~D를 선택하세요.")

    return feature


def dashboard(session, hour=None):
    row = _record(session, hour)
    return {
        "hour": row["hour"],
        "queue": row["queue"],
        "water_unmet": row["water_unmet"],
        "capacity": row["capacity"],
        "coverage_percent": row["coverage_ratio"] * 100,
    }


def event_log(session):
    events = []
    previous_queue = 0
    state = service_support.ensure_state(session)

    for row in state["history"]:
        hour = row["hour"]
        if row["water_unmet"] > 0:
            events.append(
                {
                    "hour": hour,
                    "target_id": "W",
                    "severity": "warning",
                    "title": "급수 부족",
                    "message": f"급수 수요 중 {row['water_unmet']:g}m³를 공급하지 못했습니다.",
                }
            )
            normal_capacity = service_support.conditions(state, hour)["hospital_capacity"]
            message = (
                f"필요한 물 8m³ 중 {row['water_supplied']:g}m³를 공급했습니다. "
                f"전력과 급수 조건에 따라 시간당 진료 가능 인원이 {normal_capacity}명에서 {row['capacity']}명으로 줄었습니다."
            )
            events.append(
                {
                    "hour": hour,
                    "target_id": "H",
                    "severity": "warning",
                    "title": "진료 가능 인원 감소",
                    "message": message,
                }
            )

        if row["queue"] > previous_queue:
            events.append(
                {
                    "hour": hour,
                    "target_id": "H",
                    "severity": "warning",
                    "title": "대기 인원 증가",
                    "message": f"{row['arrivals']}명이 새로 도착하고 {row['served']}명이 진료를 마쳤습니다. 대기 인원은 {previous_queue}명에서 {row['queue']}명으로 늘었습니다.",
                }
            )

        if row["grid_kw"] == 0:
            events.append(
                {
                    "hour": hour,
                    "target_id": "H",
                    "severity": "warning",
                    "title": "외부 전력 공급 중단",
                    "message": f"외부 전력 공급이 끊겼습니다. 병원은 비상 전력 {row['backup_kw']:g}kW를 사용했습니다.",
                }
            )

        previous_queue = row["queue"]

    return events


def clock_label(minutes):
    if minutes is None:
        return "기록 없음"

    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _validate_observation(row):
    if not isinstance(row, dict) or any(
        key not in row for key in ("target_id", "unit", "value", "observed_at", "received_at")
    ):
        raise ValueError("관측 자료의 항목이 빠져 있습니다.")
    if (
        not isinstance(row["target_id"], str)
        or not row["target_id"]
        or not isinstance(row["unit"], str)
        or not row["unit"]
    ):
        raise ValueError("관측 대상과 단위를 입력하세요.")
    if row["value"] is not None and (
        type(row["value"]) not in (int, float)
        or not math.isfinite(row["value"])
        or row["value"] < 0
    ):
        raise ValueError("관측값은 0 이상의 숫자 또는 빈 값이어야 합니다.")

    for key in ("observed_at", "received_at"):
        if type(row[key]) is not int or not 0 <= row[key] < 1440:
            raise ValueError("관측·수신 시각은 당일 0시부터 경과한 분(0~1439)입니다.")

    if row["received_at"] < row["observed_at"]:
        raise ValueError("수신 시각이 관측 시각보다 빠릅니다.")


def load_observations(path=None):
    path = DATA_DIR / "observations.csv" if path is None else Path(path)
    records = []

    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                row["value"] = float(row["value"]) if row["value"].strip() else None
                row["observed_at"] = int(row["observed_at"])
                row["received_at"] = int(row["received_at"])
                _validate_observation(row)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"관측 자료 {len(records) + 2}행을 확인하세요: {error}") from error

            records.append(row)

    return records


def receive_next_observation(session):
    state = ensure_state(session)
    records = load_observations()
    index = state["observation_index"]
    if index >= len(records):
        return None

    incoming = deepcopy(records[index])
    result = rules.apply_observation(deepcopy(state["observation"]), incoming)
    _validate_observation(result["state"])
    state["observation"] = deepcopy(result["state"])
    state["observation_index"] += 1
    entry = {"incoming": incoming, "accepted": result["accepted"], "reason": result["reason"]}
    state["observation_log"].append(deepcopy(entry))

    return {**deepcopy(result), "incoming": incoming}


def reset_observations(session):
    state = ensure_state(session)
    fresh = new_state()

    for key in ("observation", "observation_index", "observation_log"):
        state[key] = fresh[key]


def load_map_document(path=None):
    path = DATA_DIR / "map_example.json" if path is None else Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != "fictional-osm-structure-v1":
        raise ValueError("제공된 가상 지도 자료 형식이 아닙니다.")

    return document


def load_map_features(path=None):
    document = load_map_document(path)
    nodes = {item["id"]: item for item in document["elements"] if item["type"] == "node"}
    features = []

    for element in document["elements"]:
        tags = element.get("tags", {})
        if element["type"] == "node" and "amenity" in tags:
            features.append(
                {
                    "id": f"node/{element['id']}",
                    "kind": "point",
                    "name": tags.get("name", "시설"),
                    "coordinates": [(element["x"], element["y"])],
                    "tags": tags.copy(),
                }
            )
        elif element["type"] == "way":
            coordinates = [(nodes[ident]["x"], nodes[ident]["y"]) for ident in element["nodes"]]
            if "highway" in tags:
                kind = "line"
            elif "building" in tags and coordinates[0] == coordinates[-1]:
                kind = "polygon"
            else:
                continue

            features.append(
                {
                    "id": f"way/{element['id']}",
                    "kind": kind,
                    "name": tags.get("name", "이름 없음"),
                    "coordinates": coordinates,
                    "tags": tags.copy(),
                }
            )

    return features


def _sample_line(coordinates, step):
    for start, end in zip(coordinates, coordinates[1:]):
        count = max(1, math.ceil(math.dist(start, end) / step))
        for index in range(count + 1):
            ratio = index / count
            yield (start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio)


def map_preview(features=None):
    features = load_map_features() if features is None else deepcopy(features)
    metadata = load_map_document()["grid"]
    roads, buildings, points, outside = set(), set(), [], []

    for feature in features:
        coordinates = feature["coordinates"]
        if feature["kind"] == "line":
            for x, y in _sample_line(coordinates, metadata["cell_size"] / 10):
                cell = rules.point_to_cell(x, y, **metadata)
                if cell is not None:
                    roads.add(cell)
        else:
            vertices = coordinates[:-1] if feature["kind"] == "polygon" else coordinates
            x = sum(point[0] for point in vertices) / len(vertices)
            y = sum(point[1] for point in vertices) / len(vertices)
            cell = rules.point_to_cell(x, y, **metadata)
            item = {"id": feature["id"], "name": feature["name"], "x": x, "y": y, "cell": cell}
            if cell is None:
                outside.append(item)
            elif feature["kind"] == "polygon":
                buildings.add(cell)
            else:
                points.append(item)

    return {
        "features": features,
        "metadata": metadata,
        "points": points,
        "road_cells": sorted(roads),
        "building_cells": sorted(buildings),
        "outside": outside,
    }


def validate_interface(state):
    _validate_observation(state["observation"])
    if type(state["observation_index"]) is not int or not 0 <= state["observation_index"] <= len(
        load_observations()
    ):
        raise ValueError("관측 수신 위치가 올바르지 않습니다.")
    if not isinstance(state["observation_log"], list):
        raise ValueError("관측 수신 기록은 목록이어야 합니다.")

    for entry in state["observation_log"]:
        _validate_observation(entry["incoming"])
        if entry["reason"] not in REASON_LABELS or type(entry["accepted"]) is not bool:
            raise ValueError("관측 처리 결과가 올바르지 않습니다.")


def save_session(session, path):
    abm_support.validate_agents(session)
    service_support.validate_state(service_support.ensure_state(session))
    economy_support.validate_state(economy_support.ensure_state(session))
    validate_interface(ensure_state(session))

    base = {
        key: deepcopy(value)
        for key, value in session.items()
        if key not in ("services", "finance", "interface")
    }
    document = kpi_support._to_json_document({"format": "virtual-city-interface-v1", **base})

    for key in ("services", "finance", "interface"):
        document[key] = deepcopy(session[key])

    Path(path).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_session(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("format") != "virtual-city-interface-v1":
        session = economy_support.load_session(path)
        ensure_state(session)

        return session

    extras = {key: document.pop(key) for key in ("agents", "services", "finance", "interface")}
    document["format"] = "virtual-city-kpi-v1"
    session = kpi_support.restore_session(kpi_support._from_json_document(document))
    session.update(extras)
    abm_support.validate_agents(session)
    service_support.validate_state(session["services"])
    economy_support.validate_state(session["finance"])
    validate_interface(session["interface"])

    return session

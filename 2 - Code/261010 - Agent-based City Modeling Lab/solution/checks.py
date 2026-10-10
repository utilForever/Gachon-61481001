"""
도시 지표 단계별 누적 검사: python checks.py --stage 3

--stage N은 TODO 1~N을 누적 검사한다. 생략하면 전체 6단계를 검사한다.
--integration은 완성 코드의 통합 동작을 확인한다. GUI 없이 실행할 수 있다.
종료 코드: 0=통과, 1=실패 / 오류, 2=TODO 미완성.
"""

import argparse
import csv
import math
import tempfile
import traceback
from copy import deepcopy
from pathlib import Path

import metrics
from kpi_support import (
    advance_minutes,
    calculate_kpis,
    export_history_csv,
    load_session,
    make_lab_session,
    record_current,
    reset_observation,
    restore_session,
    save_session,
    snapshot_session,
)
from traffic_data import make_scenario


def expect(actual, expected, label):
    if isinstance(expected, float):
        if actual is None or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
            raise AssertionError(label + ": 기대 " + repr(expected) + ", 실제 " + repr(actual))
    elif actual != expected:
        raise AssertionError(label + ": 기대 " + repr(expected) + ", 실제 " + repr(actual))


def check_stage_1():
    city, _ = make_scenario()
    city["grid"][0][0]["zone"] = "R"
    expect(
        metrics.summarize_city(city),
        {"population": 6, "building_count": 3},
        "공원과 빈 용도지역은 건물이 아님",
    )

    city["buildings"]["H"]["population"] = 0
    city["buildings"]["J"]["status"] = "closed"
    city["buildings"]["F"]["status"] = "construction"
    expect(
        metrics.summarize_city(city),
        {"population": 0, "building_count": 3},
        "일자리 수는 인구가 아님",
    )


def check_stage_2():
    trips = [{"time_min": t} for t in [0, 4, 8, None]]
    expect(
        metrics.summarize_trips(trips, 4),
        {
            "planned_trips": 4,
            "reachable_trips": 3,
            "unreachable_trips": 1,
            "within_limit_trips": 2,
            "accessibility_ratio": 0.5,
            "mean_time_min": 4.0,
        },
        "0분과 도달 불가를 구분",
    )

    result = metrics.summarize_trips([{"time_min": None}], 4)
    expect(result["accessibility_ratio"], 0.0, "도달 불가도 접근성 분모에 포함")
    expect(result["mean_time_min"], None, "도달 가능한 인원이 없음")

    empty = metrics.summarize_trips([], 4)
    expect(empty["accessibility_ratio"], None, "예정 인원이 없음")
    expect(empty["mean_time_min"], None, "빈 평균")

    weighted = metrics.summarize_trips([{"time_min": t} for t in [3] * 6 + [1] * 4], 4)
    expect(weighted["mean_time_min"], 2.2, "건물이 아닌 사람을 기준으로 평균")


def check_stage_3():
    city, _ = make_scenario()
    protected = [(1, 0)]
    expect(
        metrics.find_developable_cells(city, protected),
        [(3, 0), (2, 1), (4, 2)],
        "다섯 조건과 중복 방지",
    )
    city["grid"][0][3]["terrain"] = "water"
    expect(metrics.find_developable_cells(city, protected), [(2, 1), (4, 2)], "물은 제외")

    no_roads = deepcopy(city)
    for row in no_roads["grid"]:
        for cell in row:
            cell["road"] = False
    expect(metrics.find_developable_cells(no_roads, protected), [], "도로가 없는 도시")


def check_stage_4():
    observations = [
        {"start_minute": 0, "duration_min": 2, "queue": 4},
        {"start_minute": 2, "duration_min": 3, "queue": 5},
        {"start_minute": 5, "duration_min": 1, "queue": 9},
    ]
    expect(
        metrics.summarize_congestion(observations, 5),
        {
            "observed_minutes": 6,
            "congested_minutes": 4,
            "peak_queue": 9,
        },
        "행 수가 아닌 구간 길이를 합산",
    )
    expect(
        metrics.summarize_congestion([], 5),
        {
            "observed_minutes": 0,
            "congested_minutes": 0,
            "peak_queue": None,
        },
        "관측값이 없는 시작 상태",
    )


def check_stage_5():
    history = []
    source = {"population": 10, "developable_cells": [(3, 0)], "nested": {"values": [1]}}
    expect(metrics.append_history(history, 0, source), True, "첫 기록")
    saved = deepcopy(history)

    source["nested"]["values"].append(2)
    source["developable_cells"].clear()
    expect(history, saved, "과거 행의 중첩 자료도 독립")

    expect(metrics.append_history(history, 0, {"population": 999}), False, "중복 시각 거부")
    expect(history, saved, "중복 시각으로 과거 기록을 덮어쓰지 않음")
    expect(metrics.append_history(history, 1, {"population": 11}), True, "다음 시각 추가")
    expect(len(history), 2, "시각마다 한 행")


def check_stage_6():
    city, transport = make_scenario()
    history = [{"minute": 0, "nested": {"values": [1]}}]
    settings = {"protected": [(1, 0)], "limit_minutes": 4}
    observations = [{"start_minute": 0, "duration_min": 1, "queue": 6}]
    snapshot = metrics.make_snapshot(city, transport, history, settings, observations)
    expect(
        set(snapshot),
        {"format", "city", "transport", "history", "settings", "observations"},
        "저장 항목",
    )
    expect(snapshot["format"], "virtual-city-kpi-v1", "저장 형식")
    frozen = deepcopy(snapshot)

    city["buildings"]["H"]["population"] = 0
    transport["queues"][(1, 2)] = 99
    history[0]["nested"]["values"].append(2)
    settings["protected"].clear()
    observations[0]["queue"] = 99
    expect(snapshot, frozen, "다섯 항목의 중첩 자료를 모두 복사")

    snapshot["transport"]["queues"][(1, 2)] = 7
    expect(transport["queues"][(1, 2)], 99, "스냅샷 변경도 원본과 독립")


def integration():
    expected = {
        "default": (2.2, 1.0, 2, 0),
        "congested": (3.4, 0.4, 2, 20),
        "disconnected": (None, 0.0, 4, 0),
    }
    for scenario, values in expected.items():
        session = make_lab_session(scenario)
        kpis = calculate_kpis(session)
        expect(kpis["_errors"], [], scenario + " 계산 완료")
        for key, value in zip(
            ("mean_time_min", "accessibility_ratio", "developable_count", "current_queue"), values
        ):
            expect(kpis[key], value, scenario + " " + key)
        expect(kpis["population"], 10, "총인구")
        expect(kpis["building_count"], 4, "공원을 제외한 실제 건물 수")
        expect(kpis["peak_queue"], None, "0분에는 관측값 없음")
        expect(len(session["history"]), 1, "시작 시각 기록")
        for _ in range(3):
            record_current(session)
        expect(len(session["history"]), 1, "재계산은 중복 기록하지 않음")
    session = make_lab_session()
    kpis = advance_minutes(session, 5)
    expect(kpis["current_queue"], 15, "5분 현재 대기열")
    expect(kpis["peak_queue"], 12, "관측값의 최댓값")
    expect(kpis["observed_minutes"], 5, "관측 시간")
    expect(kpis["congested_minutes"], 3, "혼잡 지속 시간")
    expect(len(session["history"]), 6, "0분부터 5분까지 여섯 행")
    expect([row["minute"] for row in session["history"]], list(range(6)), "시각 순서")
    frozen = snapshot_session(session)
    restored = restore_session(frozen)
    advance_minutes(session, 2)
    advance_minutes(restored, 2)
    expect(restored, session, "상태 복원 후 같은 결과로 진행")
    expect(frozen["transport"]["minute"], 5, "스냅샷은 이후 진행과 독립")
    with tempfile.TemporaryDirectory() as temp:
        json_path = Path(temp) / "city.json"
        csv_path = Path(temp) / "history.csv"
        save_session(session, json_path)
        loaded = load_session(json_path)
        expect(loaded, session, "JSON 왕복 후 모든 도시 상태 일치")
        advance_minutes(loaded)
        advance_minutes(session)
        expect(loaded, session, "JSON 복원 후 이어서 실행")
        export_history_csv(loaded, csv_path)
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        expect(len(rows), 9, "CSV의 행 수")
        expect(rows[0]["peak_queue"], "", "관측 전 값은 빈 칸")
        expect(rows[0]["limit_minutes"], "4.0", "CSV의 접근성 기준")
        expect(rows[0]["queue_threshold"], "5", "CSV의 혼잡 기준")
        expect(rows[0]["protected"], "[[1, 0]]", "CSV의 개발 가능 토지 기준")

    reset_observation(session)
    expect(session["transport"]["minute"], 0, "새 실험 시작 시각")
    expect(len(session["history"]), 1, "새 실험 시작 행")
    expect(session["observations"], [], "새 실험 관측 초기화")

    empty = make_lab_session()
    for building in empty["city"]["buildings"].values():
        if building["kind"] == "house":
            building["population"] = 0
    values = calculate_kpis(empty)
    expect(values["accessibility_ratio"], None, "무인 도시 접근성")
    expect(values["mean_time_min"], None, "무인 도시 이동 시간")


STAGES = [
    ("TODO 1: 인구와 건물 수", check_stage_1),
    ("TODO 2: 접근성과 평균 이동 시간", check_stage_2),
    ("TODO 3: 개발 가능 토지", check_stage_3),
    ("TODO 4: 혼잡 지속 시간", check_stage_4),
    ("TODO 5: 시계열 기록", check_stage_5),
    ("TODO 6: 도시 상태 보관", check_stage_6),
]


def main():
    parser = argparse.ArgumentParser(description="도시 지표 실습 확인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1부터 이 단계까지 점검 (기본: 6)",
    )
    group.add_argument("--integration", action="store_true", help="완성 코드의 통합 동작 확인")
    args = parser.parse_args()

    checks = [("통합", integration)] if args.integration else STAGES[: args.stage]
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

"""선택 정보, 지도 좌표, 시계열과 관측 자료 반영을 확인하는 검사."""

import argparse
import math
import tempfile
from copy import deepcopy
from pathlib import Path

import interface_rules as rules
import interface_support as support


def expect(actual, expected, name="결과"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{name}: 딕셔너리가 필요합니다. 실제 {actual!r}"
        for key, value in expected.items():
            assert key in actual, f"{name}: {key} 키가 없습니다."
            expect(actual[key], value, f"{name}.{key}")
    elif isinstance(expected, bool):
        assert actual is expected, f"{name}: 예상 {expected!r}, 실제 {actual!r}"
    elif isinstance(expected, (int, float)):
        assert type(actual) in (int, float) and math.isclose(
            actual, expected, rel_tol=1e-9, abs_tol=1e-9
        ), f"{name}: 예상 {expected}, 실제 {actual!r}"
    else:
        assert actual == expected, f"{name}: 예상 {expected!r}, 실제 {actual!r}"


def check_1():
    feature = dict(
        id="H", name="중앙병원", metric="대기 인원", value=14, unit="명", source="simulation"
    )
    original = deepcopy(feature)
    expect(
        rules.build_selection_info(feature, 6),
        {
            "title": "중앙병원",
            "metric": "대기 인원",
            "time_label": "6시간째",
            "value_label": "14명",
            "source_label": "모형 계산값",
        },
        "병원 선택",
    )
    expect(
        rules.build_selection_info(dict(feature, value=0), 0),
        {"time_label": "0시간째", "value_label": "0명"},
        "0명도 유효한 값",
    )
    expect(
        rules.build_selection_info(dict(feature, value=None, source="observation"), 6),
        {"value_label": "자료 없음", "source_label": "예제 관측값"},
        "관측값 누락",
    )
    expect(
        rules.build_selection_info(dict(feature, value=0, source="observation"), 6),
        {"value_label": "0명", "source_label": "예제 관측값"},
        "관측된 0명",
    )
    expect(
        rules.build_selection_info(dict(feature, value=2, unit="m³"), 6),
        {"value_label": "2m³"},
        "급수량 단위",
    )
    expect(
        rules.build_selection_info(dict(feature, value=6, unit="명/시간"), 6),
        {"value_label": "6명/시간"},
        "시간당 인원 단위",
    )
    assert feature == original, "선택한 시설의 원본 자료를 바꾸지 마세요."


def check_2():
    cases = [
        (None, "#767676", "경로 없음"),
        (0, "#107C10", "5분 이하"),
        (5, "#107C10", "5분 이하"),
        (5.01, "#0078D4", "5분 초과~15분 이하"),
        (15, "#0078D4", "5분 초과~15분 이하"),
        (15.01, "#CA5010", "15분 초과"),
    ]

    for value, color, label in cases:
        expect(rules.layer_style(value), {"color": color, "label": label}, f"접근시간 {value}")


def check_3():
    history = [
        {"hour": 0, "queue": 0, "capacity": 8},
        {"hour": 2, "queue": None, "capacity": 8},
        {"hour": 5, "capacity": 6},
        {"hour": 9, "queue": 14, "capacity": 6},
    ]
    original = deepcopy(history)
    expect(
        rules.build_time_series(history, "queue"),
        [(0, 0), (2, None), (5, None), (9, 14)],
        "시각 간격과 누락 자료 유지",
    )
    expect(
        rules.build_time_series(history, "capacity"),
        [(0, 8), (2, 8), (5, 6), (9, 6)],
        "다른 지표 선택",
    )
    expect(rules.build_time_series([], "queue"), [], "빈 기록")
    assert history == original, "그래프를 만들 때 원본 시계열 자료를 바꾸지 마세요."


def check_4():
    events = [
        dict(hour=5, target_id="H", message="대기 10명", severity="info"),
        dict(hour=6, target_id="W", message="급수 부족", severity="warning"),
        dict(hour=6, target_id="H", message="처리 용량 감소", severity="warning"),
        dict(hour=6, target_id="H", message="대기 14명", severity="info"),
        dict(hour=7, target_id="H", message="대기 18명", severity="info"),
    ]
    original = deepcopy(events)
    expect(
        rules.find_events(events, 6, "H"), [events[2], events[3]], "같은 시각의 병원 기록만 선택"
    )
    expect(rules.find_events(events, 6, "W"), [events[1]], "대상이 다른 기록")
    expect(rules.find_events(events, 5, "W"), [], "해당 기록 없음")
    expect(rules.find_events([], 0, "H"), [], "빈 이벤트 목록")
    assert events == original, "기록을 찾아볼 때 원본 이벤트 목록을 바꾸지 마세요."


def check_5():
    cases = [
        ((45, 30), (2, 2)),
        ((0, 0), (3, 0)),
        ((99.99, 79.99), (0, 4)),
        ((20, 20), (2, 1)),
        ((-0.01, 30), None),
        ((45, -0.01), None),
        ((100, 30), None),
        ((45, 80), None),
    ]

    for (x, y), expected in cases:
        expect(rules.point_to_cell(x, y, 0, 0, 20, 4, 5), expected, f"좌표 ({x}, {y})")

    expect(rules.point_to_cell(-95, -55, -100, -60, 20, 4, 5), (3, 0), "음수 좌표의 원점")
    expect(rules.point_to_cell(-45, -10, -100, -60, 20, 4, 5), (1, 2), "원점 이동 후 행과 열")


def check_6():
    current = dict(target_id="H", unit="명", value=8, observed_at=600, received_at=602)
    fresh = dict(target_id="H", unit="명", value=14, observed_at=610, received_at=611)
    cases = [
        (current, fresh, True, "applied"),
        (current, dict(fresh, observed_at=590, received_at=630), False, "stale"),
        (current, dict(fresh, value=99, observed_at=600, received_at=640), False, "duplicate"),
        (current, dict(fresh, value=0), True, "applied"),
        (current, dict(fresh, value=None), False, "missing"),
        (current, dict(fresh, target_id="W", unit="m³", value=None), False, "target_mismatch"),
        (current, dict(fresh, unit="분", value=None), False, "unit_mismatch"),
        (dict(current, value=None, observed_at=None), fresh, True, "applied"),
        (dict(current, received_at=650), fresh, True, "applied"),
    ]

    for number, (before, incoming, accepted, reason) in enumerate(cases, 1):
        original = deepcopy((before, incoming))
        result = rules.apply_observation(before, incoming)
        expect(
            result,
            {"state": incoming if accepted else before, "accepted": accepted, "reason": reason},
            f"관측 사례 {number}",
        )
        assert (before, incoming) == original, "기존 상태와 수신 자료를 직접 바꾸지 마세요."
        assert (
            result["state"] is not before and result["state"] is not incoming
        ), "결과 상태는 복사본이어야 합니다."


def check_integration():
    session = support.make_session()
    finance = deepcopy(session["finance"])

    for _ in range(6):
        support.advance_hour(session)

    history = support.service_history(session)
    expect(
        rules.build_time_series(history, "queue"),
        [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8), (5, 10), (6, 14)],
        "기존 모델의 병원 대기",
    )
    expect(
        support.dashboard(session),
        {"hour": 6, "queue": 14, "capacity": 6, "water_unmet": 2, "coverage_percent": 75},
        "6시간째 KPI",
    )

    feature = support.selection_feature(session, "H", 6)
    expect(
        rules.build_selection_info(feature, 6),
        {"value_label": "14명", "time_label": "6시간째"},
        "패널과 그래프 값 일치",
    )

    events = rules.find_events(support.event_log(session), 6, "H")
    assert events, "6시간째 병원의 변화가 이벤트 기록에 없습니다."
    assert all(
        event["hour"] == 6 and event["target_id"] == "H" for event in events
    ), "다른 시간이나 다른 시설의 기록이 섞였습니다."
    assert any(
        "14" in event["message"] for event in events
    ), "병원 이벤트의 대기 인원과 시계열이 다릅니다."
    assert session["finance"] == finance, "서비스 시간 진행이 도시 재정을 바꿨습니다."

    original = deepcopy(session)
    expect(
        rules.build_selection_info(support.selection_feature(session, "H", 5), 5),
        {"value_label": "10명"},
        "5시간째 과거 기록",
    )
    expect(
        support.travel_times(session), {"A": 4, "B": 8, "C": 12, "D": 20}, "기존 도로망 접근시간"
    )

    for value in support.travel_times(session).values():
        rules.layer_style(value)

    rules.find_events(support.event_log(session), 5, "H")
    rules.build_time_series(support.service_history(session), "queue")
    support.dashboard(session, 5)
    assert session == original, "선택·레이어·과거 기록 조회가 도시 상태를 바꿨습니다."

    received = support.receive_next_observation(session)
    assert received is not None, "관측 자료를 읽지 못했습니다."
    expect(received, {"accepted": True, "reason": "applied"}, "첫 관측 자료 반영")

    for key in ("city", "services", "finance", "agents", "transport"):
        assert session[key] == original[key], f"관측 자료 반영이 {key}를 바꿨습니다."

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "interface_city.json"
        support.save_session(session, path)
        assert (
            support.load_session(path) == session
        ), "도시와 인터페이스 상태의 저장·복원 결과가 다릅니다."


def main():
    parser = argparse.ArgumentParser(description="인터페이스·시각화·디지털 트윈 규칙 확인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1단계부터 지정한 단계까지 누적 검사 (기본: 6)",
    )
    group.add_argument("--integration", action="store_true", help="기존 도시와의 통합 동작만 확인")
    args = parser.parse_args()
    stages = [check_1, check_2, check_3, check_4, check_5, check_6]
    selected = (
        [("통합", check_integration)]
        if args.integration
        else [
            (f"TODO {number}", function) for number, function in enumerate(stages[: args.stage], 1)
        ]
    )
    failed = unfinished = 0

    for name, function in selected:
        try:
            function()
            print(f"[통과] {name}")
        except NotImplementedError as error:
            unfinished += 1
            print(f"[미구현] {name}: {error} / interface_rules.py를 작성하세요.")
        except Exception as error:
            failed += 1
            print(f"[실패] {name}: {type(error).__name__}: {error}")

    if failed:
        print(f"{failed}개 항목을 다시 확인하세요.")
        return 1
    if unfinished:
        print(f"{unfinished}개 항목을 구현한 뒤 다시 확인하세요.")
        return 2

    print("선택한 검사를 모두 통과했습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

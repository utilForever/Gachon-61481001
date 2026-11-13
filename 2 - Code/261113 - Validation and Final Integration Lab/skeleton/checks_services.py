"""공공서비스 접근성, 대기열, 기반시설과 오염 계산을 확인하는 검사."""

import argparse
from copy import deepcopy
import tempfile
from pathlib import Path

import abm_support
import service_rules as rules
import service_support as support


def check_1():
    populations = {"A": 100, "B": 100, "C": 100, "D": 100}
    result = rules.service_coverage({"A": 4, "B": 8, "C": 12, "D": 20}, populations, 15)
    assert result == {
        "covered": ["A", "B", "C"],
        "population": 300,
        "ratio": 0.75,
        "unreachable_population": 0,
    }

    result = rules.service_coverage({"A": 0, "B": 15, "C": 16, "D": None}, populations, 15)
    assert result["covered"] == ["A", "B"] and result["unreachable_population"] == 100
    assert rules.service_coverage({}, {}, 15)["ratio"] == 0


def check_2():
    queue = 0

    for expected in (2, 4, 6):
        result = rules.advance_queue(queue, 10, 8)
        assert result == {"served": 8, "queue": expected}
        assert queue + 10 == result["served"] + result["queue"]

        queue = result["queue"]

    assert rules.advance_queue(0, 3, 8) == {"served": 3, "queue": 0}
    assert rules.advance_queue(2, 3, 0) == {"served": 0, "queue": 5}


def check_3():
    result = rules.allocate_power(100, support.DEMANDS, support.PRIORITY)
    assert result == {"hospital": 30, "pump": 20, "housing": 50, "industry": 0}
    assert sum(rules.allocate_power(0, support.DEMANDS, support.PRIORITY).values()) == 0
    assert rules.allocate_power(150, support.DEMANDS, support.PRIORITY) == support.DEMANDS

    reversed_result = rules.allocate_power(100, support.DEMANDS, list(reversed(support.PRIORITY)))
    assert reversed_result["industry"] == 20 and reversed_result["hospital"] == 10


def check_4():
    stored = 10

    for expected in (8, 6, 4, 2, 0, 0):
        result = rules.update_water(stored, 6, 8, 20)
        assert result["stored"] == expected
        assert stored + 6 == result["supplied"] + result["stored"] + result["overflow"]

        stored = result["stored"]

    assert result["supplied"] == 6 and result["unmet"] == 2
    assert rules.update_water(20, 10, 0, 20)["overflow"] == 10


def check_5():
    result = rules.update_waste(0, 0, 8, 6, 5)
    assert result == {"city": 2, "plant": 1, "collected": 6, "processed": 5}

    result = rules.update_waste(2, 1, 8, 6, 5)
    assert result["city"] == 4 and result["plant"] == 2
    assert 2 + 1 + 8 == result["city"] + result["plant"] + result["processed"]
    assert rules.update_waste(0, 0, 3, 6, 5) == {
        "city": 0,
        "plant": 0,
        "collected": 3,
        "processed": 3,
    }


def check_6():
    initial = [100, 0, 0]
    result = rules.transport_pollution(initial, 0.2, 0.1)
    assert result == [72, 18, 0]
    assert initial == [100, 0, 0]

    moved = rules.transport_pollution([100, 50, 0], 0.2, 0)
    assert moved == [80, 60, 10] and sum(moved) == 150
    assert rules.transport_pollution([0, 0, 100], 0.2, 0.1) == [0, 0, 90]


def check_integration():
    city = abm_support.make_session()
    support.reset_services(city, "normal")

    for _ in range(6):
        last = support.advance_hour(city)

    assert (last["queue"], last["water_supplied"], last["capacity"]) == (14, 6, 6)
    assert city["agents"]["month"] == 0 and city["transport"]["minute"] == 0

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "city.json"
        support.save_session(city, path)
        restored = support.load_session(path)

    assert restored == city
    support.reset_services(city, "flood")

    for hour in range(1, 5):
        row = support.advance_hour(city)
        assert row["unreachable_population"] == (100 if hour in (2, 3) else 0)

    assert city["city"]["grid"][1][3]["road"] is True


def main():
    parser = argparse.ArgumentParser(description="공공서비스 규칙 확인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1단계부터 지정한 단계까지 누적 검사 (기본: 6)",
    )
    group.add_argument("--integration", action="store_true", help="통합 동작만 확인")
    args = parser.parse_args()
    stages = [check_1, check_2, check_3, check_4, check_5, check_6]
    if args.integration:
        selected = [("통합", check_integration)]
    else:
        selected = [
            (f"TODO {number}", function)
            for number, function in enumerate(stages[: args.stage], start=1)
        ]

    failed = 0
    unfinished = 0

    for name, function in selected:
        try:
            function()
            print(f"[통과] {name}")
        except NotImplementedError as error:
            unfinished += 1
            print(f"[미구현] {name}: {error} / service_rules.py를 작성하세요.")
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

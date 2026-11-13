"""단계별 누적 검사: python skeleton/checks_validation.py --stage 3

명령은 실습 최상위 폴더에서 실행한다. 모범 답안 검사는 skeleton을 solution으로 바꾼다.
종료 코드: 0=통과, 1=실패 / 오류, 2=TODO 미구현."""

import argparse
from copy import deepcopy
import csv
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import validation_rules as rules
import validation_support as support


def expect(actual, expected, label):
    assert actual == expected, f"{label}: 기대값 {expected!r}, 실제값 {actual!r}"


def near(actual, expected, label):
    assert abs(actual - expected) < 1e-9, f"{label}: 기대값 {expected}, 실제값 {actual}"


def raises_value_error(function, *args):
    try:
        function(*args)
    except ValueError:
        return

    raise AssertionError("잘못된 입력은 ValueError로 알려야 합니다.")


def check_1():
    cases = [
        (10, 10, 6, {"served": 6, "queue": 14}, True),
        (0, 3, 8, {"served": 3, "queue": 0}, True),
        (4, 3, 0, {"served": 0, "queue": 7}, True),
        (0, 0, 0, {"served": 0, "queue": 0}, True),
        (2, 6, 6, {"served": 2, "queue": 6}, False),
        (2, 6, 6, {"served": 7, "queue": 1}, False),
        (0, 3, 8, {"served": 8, "queue": -5}, False),
        (0, 3, 8, {"served": 3, "queue": 3}, False),
        (0, 3, 8, {"served": True, "queue": 2}, False),
        (-1, 3, 8, {"served": 2, "queue": 0}, False),
        (0, 3, 8, {"served": 3}, False),
    ]

    for queue, arrivals, capacity, result, valid in cases:
        expect(
            rules.is_valid_step(queue, arrivals, capacity, result),
            valid,
            f"대기열 {queue, arrivals, capacity, result}",
        )


def check_2():
    old = random.getstate()
    expect(rules.make_arrivals(101), [9, 14, 11, 13, 6, 14], "시드 101")
    expect(rules.make_arrivals(102), [8, 11, 8, 14, 8, 12], "시드 102")
    expect(rules.make_arrivals(101), [9, 14, 11, 13, 6, 14], "같은 시드 재현")
    expect(random.getstate(), old, "다른 도시 기능의 난수 상태 유지")
    expect(rules.make_arrivals(0, 3, 0, 0), [0, 0, 0], "방문 인원 0명")
    raises_value_error(rules.make_arrivals, 1, 6, 14, 6)


def check_3():
    arrivals = [9, 14, 11, 13, 6, 14]
    before = arrivals.copy()
    result = rules.run_scenario(arrivals, 8)
    expect(result["final_queue"], 19, "기준 최종 대기")
    expect([row["queue"] for row in result["history"]], [1, 7, 10, 15, 13, 19], "시간별 대기")
    expect([row["served"] for row in result["history"]], [8] * 6, "시간별 진료")
    expect([row["hour"] for row in result["history"]], list(range(1, 7)), "기록 시각")
    expect(arrivals, before, "입력 목록 유지")
    expect(rules.run_scenario(arrivals, 8), result, "호출마다 초기화")
    expect(rules.run_scenario([3, 0, 5], 0)["final_queue"], 8, "용량 0명/시간")
    expect(rules.run_scenario([3, 0, 5], 100)["final_queue"], 0, "충분한 용량")
    expect(rules.run_scenario([], 8), {"history": [], "final_queue": 0}, "빈 실행")
    raises_value_error(rules.run_scenario, [1, -1], 8)


def check_4():
    empty = {"count": 0, "mean": None, "stddev": None, "minimum": None, "maximum": None}
    expect(rules.summarize([]), empty, "자료 없음")
    expect(
        rules.summarize([7]),
        {"count": 1, "mean": 7, "stddev": None, "minimum": 7, "maximum": 7},
        "결과 1개",
    )
    near(rules.summarize([8, 10, 12])["stddev"], 2, "표본 표준편차 A")
    near(rules.summarize([2, 10, 18])["stddev"], 8, "표본 표준편차 B")
    near(rules.summarize([1, 2, 2])["mean"], 5 / 3, "표시 전 반올림 금지")
    expect(rules.summarize([0, 0])["stddev"], 0, "실제 변동 0")
    raises_value_error(rules.summarize, [float("nan")])


def check_5():
    rows = rules.compare_scenarios(range(101, 131))
    expect(len(rows), 30, "반복 횟수")
    expect([row["seed"] for row in rows], list(range(101, 131)), "전체 시드 유지")
    expect([row["reduction"] for row in rows[:5]], [11, 9, 8, 7, 6], "앞 5회 감소 인원")
    near(
        rules.summarize([row["baseline"]["final_queue"] for row in rows])["mean"], 12.6, "기준 평균"
    )
    near(
        rules.summarize([row["policy"]["final_queue"] for row in rows])["mean"],
        118 / 30,
        "비교 평균",
    )
    near(rules.summarize([row["reduction"] for row in rows])["mean"], 26 / 3, "평균 감소")

    for row in rows:
        for key in ("baseline", "policy"):
            expect(
                [step["arrivals"] for step in row[key]["history"]],
                row["arrivals"],
                "동일 입력 비교",
            )

    equal = rules.compare_scenarios([101, 102], 8, 8)
    expect([row["reduction"] for row in equal], [0, 0], "같은 용량 비교")
    raises_value_error(rules.compare_scenarios, [101, 101])


def check_6():
    rows = rules.sensitivity_analysis(range(101, 131), [6, 8, 10, 12, 14])
    expect([row["capacity"] for row in rows], [6, 8, 10, 12, 14], "비교할 용량")

    for row, expected in zip(rows, [721 / 30, 12.6, 118 / 30, 0.4, 0]):
        near(row["summary"]["mean"], expected, "용량별 평균")
        expect(len(row["values"]), 30, "회차별 원자료 유지")

    values = rules.sensitivity_analysis([101], [0, 100])
    expect([row["values"] for row in values], [[67], [0]], "극단 용량")
    expect(rules.sensitivity_analysis([101], []), [], "비교할 용량 없음")


def check_integration():
    import interface_support
    import service_support
    import service_rules

    session = interface_support.make_session()
    service_support.ensure_state(session)
    before = deepcopy(session)
    bundle = support.run_comparison(support.DEFAULT_SETTINGS)
    expect(session, before, "반복 실험이 현재 도시를 변경하지 않음")
    expect(rules.advance_queue, service_rules.advance_queue, "기존 서비스 함수 재사용")

    for _ in range(6):
        service_support.advance_hour(session)

    expect(session["services"]["queue"], 14, "기존 기본 도시 6시간 대기")
    interface_support.ensure_state(session)
    expect(support.replay_record(bundle, 0)["matches"], True, "저장 입력 재현")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "experiment.json"
        support.save_experiment(bundle, path)
        restored = support.load_experiment(path)
        expect(restored, bundle, "실험 저장·복원")
        expect(support.replay_record(restored, 29)["matches"], True, "마지막 회차 재현")

        csv_path = Path(directory) / "experiment.csv"
        support.export_csv(bundle, csv_path)

        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            records = list(csv.DictReader(stream))

        expect(len(records), 30 * 2 * 6, "CSV 전체 시간별 기록")
        expect(records[0]["arrivals"], "9", "CSV 원입력")

        broken = deepcopy(bundle)
        broken["records"][0]["baseline"]["history"][0]["queue"] += 1
        raises_value_error(support.validate_bundle, broken)


def check_previous():
    folder = Path(__file__).resolve().parent

    for filename in (
        "checks.py",
        "checks_abm.py",
        "checks_services.py",
        "checks_economy.py",
        "checks_interface.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(folder / filename)],
            cwd=folder,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode:
            raise AssertionError(f"{filename}\n{completed.stdout}\n{completed.stderr}")


def main():
    parser = argparse.ArgumentParser(description="반복 실험·검증·통합 동작 확인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1단계부터 지정한 단계까지 누적 검사 (기본: 6)",
    )
    group.add_argument("--integration", action="store_true", help="도시 연계, 저장·복원·재현 검사")
    group.add_argument(
        "--release", action="store_true", help="6단계, 통합, 이전 주차 검사 모두 실행"
    )
    args = parser.parse_args()
    stages = [check_1, check_2, check_3, check_4, check_5, check_6]
    selected = [(f"{number}단계", test) for number, test in enumerate(stages[: args.stage], 1)]
    if args.integration:
        selected = [("통합", check_integration)]
    elif args.release:
        selected += [("통합", check_integration), ("이전 주차 회귀", check_previous)]

    for name, test in selected:
        try:
            test()
            print(f"[통과] {name}")
        except NotImplementedError as error:
            print(f"[미구현] {error}")
            print("validation_rules.py를 작성하고 같은 명령을 다시 실행하세요.")

            return 2
        except Exception as error:
            print(f"[실패] {name}: {type(error).__name__}: {error}")
            return 1

    print("선택한 검사를 모두 통과했습니다.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

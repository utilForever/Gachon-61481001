import argparse
import math
import tempfile
from copy import deepcopy
from pathlib import Path

import abm_support
import economy_rules as rules
import economy_support as support
import service_support


def expect(actual, expected, name="결과"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{name}: 딕셔너리가 필요합니다. 실제 {actual!r}"
        for key, value in expected.items():
            assert key in actual, f"{name}: {key} 키가 없습니다."
            expect(actual[key], value, f"{name}.{key}")
    elif isinstance(expected, (int, float)):
        assert isinstance(actual, (int, float)) and math.isclose(
            actual, expected, rel_tol=1e-9, abs_tol=1e-9
        ), f"{name}: 예상 {expected}, 실제 {actual!r}"
    else:
        assert actual == expected, f"{name}: 예상 {expected!r}, 실제 {actual!r}"


def check_1():
    expect(
        rules.tax_revenue(200, 5, 200, 0.1, 0.1),
        {"income": 1000, "household_tax": 100, "firm_tax": 20, "revenue": 120},
    )

    expect(
        rules.tax_revenue(200, 5, 200, 0.09, 0.1),
        {"household_tax": 90, "revenue": 110},
        "가구 세율 9%",
    )

    expect(
        rules.tax_revenue(0, 5, -30, 0.1, 0.1),
        {"income": 0, "household_tax": 0, "firm_tax": 0, "revenue": 0},
        "고용 없음 / 기업 손실",
    )


def check_2():
    budgets = {"hospital": 24, "water": 6, "other": 20}
    original = budgets.copy()

    expect(
        rules.monthly_costs(8, 2, 14, budgets), {"maintenance": 30, "services": 50, "recurring": 80}
    )

    expect(
        rules.monthly_costs(9, 2, 14, budgets),
        {"maintenance": 32, "recurring": 82},
        "도로 1칸 추가",
    )

    expect(
        rules.monthly_costs(0, 2, 0, {}),
        {"maintenance": 0, "services": 0, "recurring": 0},
        "빈 도시",
    )

    assert budgets == original, "입력 예산 딕셔너리를 바꾸지 마세요."


def check_3():
    quantities = {"road": 0, "hospital": 1, "water": 1}
    prices = {"road": 20, "hospital": 20, "water": 12}
    original = deepcopy((quantities, prices))

    expect(rules.construction_cost(quantities, prices), 32, "동시 확충")
    expect(
        rules.construction_cost({"road": 2, "hospital": 0, "water": 0}, prices), 40, "도로 2칸 신설"
    )
    expect(
        rules.construction_cost({"road": 0, "hospital": 0, "water": 0}, prices), 0, "추가 공사 없음"
    )

    assert (quantities, prices) == original, "수량과 단가 입력을 바꾸지 마세요."


def check_4():
    expect(rules.monthly_balance(120, 30, 50, 200, 0.01, 0), {"interest": 2, "balance": 38})

    expect(
        rules.monthly_balance(120, 30, 58, 200, 0.01, 32),
        {"interest": 2, "balance": -2},
        "동시 확충 첫 달",
    )

    expect(
        rules.monthly_balance(0, 0, 0, 0, 0.01, 0),
        {"interest": 0, "balance": 0},
        "부채와 수지 없음",
    )


def check_5():
    expect(
        rules.settle_finances(20, 200, 38, 20),
        {"borrowing": 0, "repayment": 38, "cash": 20, "debt": 162},
        "흑자 상환",
    )

    expect(
        rules.settle_finances(20, 200, -2, 20),
        {"borrowing": 2, "repayment": 0, "cash": 20, "debt": 202},
        "적자 차입",
    )

    expect(
        rules.settle_finances(20, 5, 10, 20),
        {"borrowing": 0, "repayment": 5, "cash": 25, "debt": 0},
        "부채 전액 상환",
    )

    expect(
        rules.settle_finances(25, 0, -2, 20),
        {"borrowing": 0, "repayment": 0, "cash": 23, "debt": 0},
        "보유 현금 사용",
    )

    expect(
        rules.settle_finances(20, 200, 0, 20),
        {"borrowing": 0, "repayment": 0, "cash": 20, "debt": 200},
        "수지 0",
    )


def check_6():
    baseline = {"queue6": 14, "queue24": 86, "debt": 84.8562, "cash": 20, "coverage": 0.75}
    alternative = {"queue6": 12, "queue24": 48, "debt": 103.1576, "cash": 20, "coverage": 0.75}
    original = deepcopy((baseline, alternative))

    expect(
        rules.compare_policy(baseline, alternative),
        {"queue6": -2, "queue24": -38, "debt": 18.3014, "cash": 0, "coverage": 0},
    )
    expect(
        rules.compare_policy(baseline, baseline), {key: 0 for key in baseline}, "기준과 기준 비교"
    )

    changed_coverage = dict(alternative, coverage=1.0)
    expect(rules.compare_policy(baseline, changed_coverage), {"coverage": 0.25}, "25%포인트 개선")

    assert (baseline, alternative) == original, "비교할 원본 결과를 바꾸지 마세요."


def check_integration():
    session = abm_support.make_session()
    service_support.reset_services(session)
    support.reset_finance(session)
    original = deepcopy(session)

    report = support.run_comparison(session)
    assert session == original, "정책 비교가 원본 도시 상태를 바꿨습니다."

    expected = {
        "normal": (14, 86, 84.8562),
        "hospital": (3, 57, 123.4388),
        "water": (12, 48, 103.1576),
        "both": (0, 0, 141.7402),
    }
    for row in report["results"]:
        queue6, queue24, debt = expected[row["policy"]]
        expect(
            row,
            {"queue6": queue6, "queue24": queue24, "debt": debt, "cash": 20, "coverage": 0.75},
            row["name"],
        )

    support.reset_finance(session, "both")
    month1 = support.advance_month(session)
    month2 = support.advance_month(session)
    expect(
        month1, {"construction": 32, "balance": -2, "borrowing": 2, "debt": 202}, "동시 확충 1개월"
    )
    expect(
        month2,
        {"construction": 0, "interest": 2.02, "balance": 29.98, "debt": 172.02},
        "동시 확충 2개월",
    )
    assert (
        session["services"] == original["services"]
    ), "재정 결산은 서비스 시간을 진행하지 않습니다."
    assert session["agents"] == original["agents"], "재정 결산은 행위자 상태를 바꾸지 않습니다."
    assert (
        session["transport"] == original["transport"]
    ), "재정 결산은 교통 시간을 진행하지 않습니다."

    session["finance"]["comparison"] = report
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "city.json"
        support.save_session(session, path)
        assert support.load_session(path) == session, "저장 / 복원 결과가 다릅니다."
        old_path = Path(directory) / "previous.json"
        old_session = deepcopy(original)
        old_session.pop("finance")
        service_support.save_session(old_session, old_path)
        restored = support.load_session(old_path)
        assert restored["finance"]["month"] == 0 and restored["services"] == old_session["services"]

    support.reset_finance(session, income_tax_rate=0.09)
    for _ in range(3):
        row = support.advance_month(session)
    expect(row, {"revenue": 110, "debt": 115.1572}, "세율 9% / 3개월")

    session["city"]["grid"][3][4]["road"] = True
    expect(support.preview(session), {"road_cells": 9, "maintenance": 32}, "현재 지도 연결")


def main():
    parser = argparse.ArgumentParser(description="도시 경제 / 재정 규칙 확인")
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
            print(f"[미구현] {name}: {error} / economy_rules.py를 작성하세요.")
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

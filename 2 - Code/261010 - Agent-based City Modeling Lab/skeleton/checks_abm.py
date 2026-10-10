"""
행위자 단계별 누적 검사: python checks_abm.py --stage 3

--stage N은 TODO 1~N을 누적 검사한다. 생략하면 전체 7단계를 검사한다.
--integration은 월별 진행 / 저장 복원 / 이웃 모델을 확인한다. GUI 없이 실행할 수 있다.
종료 코드: 0=통과, 1=실패 / 오류, 2=TODO 미완성.
"""

import argparse
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import traceback
from unittest.mock import patch

import abm_support as support
import agent_rules as rules
from neighborhood import Neighborhood


def expect(actual, expected, label):
    if isinstance(expected, float):
        matched = (
            actual is not None
            and isinstance(actual, (int, float))
            and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
        )
    else:
        matched = actual == expected
    if not matched:
        raise AssertionError(f"{label}: 기대 {expected!r}, 실제 {actual!r}")


def check_stage_1():
    expect(rules.satisfaction(45, 80, 200, 50), 40.5, "주택 A")
    expect(rules.satisfaction(20, 100, 200, 70), 62 + 1 / 3, "주택 B")
    expect(rules.satisfaction(0, 0, 200, 100), 100.0, "최대 점수")
    expect(rules.satisfaction(60, 200, 200, 0), 0.0, "점수가 0이 되는 경계")
    expect(rules.satisfaction(90, 300, 200, 50), 10.0, "통근과 주거비 점수 하한")
    expect(rules.satisfaction(None, 80, 200, 50), 28.0, "도달 불가의 통근 점수")
    expect(rules.satisfaction(0, 0, 0, 0), 50.0, "소득 0의 주거비 점수")


def check_stage_2():
    household = dict(dissatisfied_months=2, cooldown=0, savings=30, move_cost=30)
    expect(rules.should_move(household), True, "2개월 / 비용과 같은 저축")
    for key, value, label in (
        ("dissatisfied_months", 1, "불만족 1개월"),
        ("cooldown", 1, "대기 기간이 남음"),
        ("savings", 29, "이사 비용 부족"),
    ):
        expect(rules.should_move({**household, key: value}), False, label)
    expect(rules.should_move({**household, "dissatisfied_months": 3}), True, "2개월 이상")
    expect(
        household,
        dict(dissatisfied_months=2, cooldown=0, savings=30, move_cost=30),
        "판단 함수는 가구 상태를 바꾸지 않음",
    )


def check_stage_3():
    def home(ident, score, feasible=True):
        return dict(home_id=ident, score=score, feasible=feasible)

    candidates = [home("B", 50), home("C", 90), home("D", 95)]
    frozen = deepcopy(candidates)
    expect(rules.choose_home({}, candidates, 40), candidates[0], "10점 개선한 첫 후보 선택")
    expect(candidates, frozen, "후보 순서를 바꾸지 않음")

    candidates = [home("B", 100, False), home("C", 49.9), home("D", 50)]
    expect(rules.choose_home({}, candidates, 40), candidates[2], "입주 제약과 개선 폭 확인")

    candidates = [home("B", 100, False), home("C", 49), home("D", 45), home("E", 100)]
    expect(rules.choose_home({}, candidates, 40), None, "네 번째 후보는 조사하지 않음")
    expect(rules.choose_home({}, [], 40), None, "후보 없음")


def check_stage_4():
    session = support.make_session()
    state = session["agents"]
    citizens = deepcopy(state["citizens"])
    firms = deepcopy(state["firms"])
    other = deepcopy(state["households"]["H2"])

    rules.move_household(state, "H1", "B")
    household = state["households"]["H1"]
    expect(
        (household["home_id"], state["houses"]["A"]["occupant"], state["houses"]["B"]["occupant"]),
        ("B", None, "H1"),
        "양방향 거주 관계",
    )
    expect(household["savings"], 120, "이사 비용을 한 번 차감")
    expect((household["dissatisfied_months"], household["cooldown"]), (0, 3), "이주 뒤 대기 상태")
    expect(state["citizens"], citizens, "가구 이동은 시민의 소속 / 고용을 유지")
    expect(state["firms"], firms, "기업 상태 유지")
    expect(state["households"]["H2"], other, "다른 가구 유지")

    support.synchronize_buildings(session)
    support.validate_agents(session)
    expect(session["city"]["buildings"]["A"]["population"], 0, "옛 주택의 인구")
    expect(session["city"]["buildings"]["B"]["population"], 2, "새 주택의 인구")


def check_stage_5():
    firm = dict(profit=150, move_cost=500, cash=700)
    expect(rules.should_move_firm(firm, 260), True, "6개월 순편익 160만원")
    expect(rules.should_move_firm({**firm, "cash": 499}, 260), False, "선불 이전 자금 부족")
    expect(rules.should_move_firm({**firm, "cash": 500}, 260), True, "이전 비용과 같은 자금")

    firm = dict(profit=150, move_cost=300, cash=300)
    expect(rules.should_move_firm(firm, 200), False, "순편익 0은 이전하지 않음")
    expect(rules.should_move_firm(firm, 200.5), True, "순편익이 양수")
    expect(rules.should_move_firm(firm, 140), False, "월 이익 감소")


def check_stage_6():
    session = support.make_session()
    state = session["agents"]
    citizens = deepcopy(state["citizens"])
    households = deepcopy(state["households"])

    rules.move_firm(state, "F1", "Y")
    firm = state["firms"]["F1"]
    expect(
        (firm["site_id"], state["sites"]["X"]["occupant"], state["sites"]["Y"]["occupant"]),
        ("Y", None, "F1"),
        "양방향 사업장 관계",
    )
    expect((firm["cash"], firm["profit"]), (200, 260), "이전 비용과 새 월 이익")
    expect(firm["employees"], ["P1", "P3"], "고용 시민 유지")
    expect(state["citizens"], citizens, "시민의 고용 관계 유지")
    expect(state["households"], households, "기업 이전은 가구를 이주시키지 않음")

    support.synchronize_buildings(session)
    support.validate_agents(session)
    expect(session["city"]["buildings"]["X"]["workers"], 0, "옛 사업장의 고용 인원")
    expect(session["city"]["buildings"]["Y"]["workers"], 2, "새 사업장의 고용 인원")


def check_stage_7():
    grid = [["A", "B", None], ["B", "A", "A"], [None, "A", "B"]]
    frozen = deepcopy(grid)
    expect(rules.same_type_ratio(grid, 1, 1), 0.5, "자신과 빈칸을 제외한 3 / 6")
    expect(grid, frozen, "비율 계산은 격자를 바꾸지 않음")
    expect(
        rules.same_type_ratio([["A", "B"], ["A", "B"]], 0, 0),
        1 / 3,
        "모서리에서 대각선을 포함하고 경계를 연결하지 않음",
    )
    expect(rules.same_type_ratio([["A", None, "B"]], 0, 0), None, "이웃이 없으면 None")
    expect(rules.same_type_ratio([["A"]], 0, 0), None, "한 칸 격자")
    expect(rules.same_type_ratio([["A", "B"]], 0, 0), 0.0, "다른 유형의 이웃만 있음")
    expect(rules.same_type_ratio([[None, "A"], ["A", "A"]], 1, 1), 1.0, "같은 유형의 이웃만 있음")


def _competition_session():
    session = support.make_session()
    state = session["agents"]
    state["houses"]["D"]["rent"] = 180
    state["houses"]["D"]["environment"] = 0
    state["firms"]["F1"]["employees"] = ["P1"]
    state["firms"]["F2"] = dict(site_id="Y", employees=["P3"], profit=260, cash=0, move_cost=500)
    state["sites"]["Y"]["occupant"] = "F2"
    state["citizens"]["P3"]["employer_id"] = "F2"
    for household in state["households"].values():
        household["dissatisfied_months"] = 1

    support.synchronize_buildings(session)
    support.validate_agents(session)
    return session


def _check_candidates():
    session = support.make_session()
    candidates = support.home_candidates(session, "H1")
    expect([row["home_id"] for row in candidates], ["B", "C", "D"], "현재 주택 제외 / 조사 순서")
    expect(
        [row["feasible"] for row in candidates],
        [True, False, False],
        "예산 경계의 빈집 허용 / 예산 초과와 입주한 주택 제외",
    )
    session["city"]["buildings"]["B"]["capacity"] = 2
    expect(support.home_candidates(session, "H1")[0]["feasible"], True, "정원과 같은 가구원 수")
    session["city"]["buildings"]["B"]["capacity"] = 1
    expect(support.home_candidates(session, "H1")[0]["feasible"], False, "거주 정원 부족")
    session["city"]["buildings"]["B"].update(capacity=4, status="closed")
    expect(support.home_candidates(session, "H1")[0]["feasible"], False, "폐쇄된 주택 제외")

    disconnected = support.make_session("disconnected")
    expect(
        any(row["feasible"] for row in support.home_candidates(disconnected, "H1")),
        False,
        "직장까지 경로가 없는 주택 제외",
    )


def _check_competition():
    session = _competition_session()
    reversed_session = deepcopy(session)
    reversed_session["agents"]["households"] = dict(
        reversed(list(session["agents"]["households"].items()))
    )
    before = deepcopy(session["agents"]["households"])
    support.advance_month(session)
    support.advance_month(reversed_session)
    expect(session, reversed_session, "가구 dict의 순서와 무관한 같은 시드의 추첨")
    state = session["agents"]
    winners = [
        ident for ident, household in state["households"].items() if household["home_id"] == "B"
    ]
    expect(len(winners), 1, "빈집 한 호에 한 가구만 입주")
    expect(len(state["events"]), 1, "같은 달에 생긴 빈집을 새 후보로 재사용하지 않음")
    loser = next(ident for ident in before if ident not in winners)
    expect(
        state["households"][loser]["home_id"],
        before[loser]["home_id"],
        "미승인 가구는 현재 집 유지",
    )
    expect(
        state["households"][loser]["savings"],
        before[loser]["savings"],
        "미승인 가구의 비용은 차감하지 않음",
    )
    support.validate_agents(session)


def _check_cooldown():
    session = support.make_session()
    for _ in range(2):
        support.advance_month(session)
    state = session["agents"]
    state["houses"]["B"].update(rent=200, environment=0)
    state["houses"]["A"].update(rent=0, environment=100)
    state["firms"]["F1"]["cash"] = 0
    for month, cooldown in ((3, 2), (4, 1), (5, 0)):
        support.advance_month(session)
        household = session["agents"]["households"]["H1"]
        expect(session["agents"]["month"], month, "월 진행")
        expect(
            (household["home_id"], household["cooldown"]),
            ("B", cooldown),
            "이주 다음 세 달 동안 재이주 금지",
        )
    support.advance_month(session)
    household = session["agents"]["households"]["H1"]
    expect((household["home_id"], household["savings"]), ("A", 90), "네 번째 달에는 재이주 가능")


def _check_atomic_update():
    session = support.make_session()
    support.advance_month(session)
    original = deepcopy(session)

    def unfinished(state, household_id, home_id):
        state["households"][household_id]["savings"] = -1
        raise NotImplementedError("중간에 멈춘 TODO")

    with patch.object(rules, "move_household", unfinished):
        try:
            support.advance_month(session)
        except NotImplementedError:
            pass
        else:
            raise AssertionError("미완성 함수의 예외가 전달되어야 합니다.")
    expect(session, original, "계산 중 오류가 발생하면 월 / 자금 / 참조를 모두 유지")


def integration():
    import checks as previous_checks

    for task in (
        previous_checks.check_stage_1,
        previous_checks.check_stage_2,
        previous_checks.check_stage_3,
        previous_checks.check_stage_4,
        previous_checks.check_stage_5,
        previous_checks.check_stage_6,
        previous_checks.integration,
    ):
        task()
    session = support.make_session()
    citizens = deepcopy(session["agents"]["citizens"])
    first = support.monthly_snapshot(session)
    expect(first["H1_score"], 40.5, "초기 H1 만족도")
    expect(first["mean_commute"], 30.0, "초기 취업 시민 평균")
    expect(len(support.commute_records(session)), 2, "비취업 시민은 통근 분모에서 제외")
    for month in range(1, 7):
        support.advance_month(session)
        row = session["agents"]["history"][-1]
        expect(row["month"], month, "월별 기록")
        expect(row["H1_home"], "A" if month == 1 else "B", "H1의 이주 시점")
        expect(row["F1_site"], "X" if month < 3 else "Y", "분기마다 기업 이전 검토")
        expect(
            row["mean_commute"],
            30.0 if month == 1 else 17.5 if month == 2 else 32.5,
            "현재 사업장을 반영한 평균 통근 시간",
        )
        expect(session["transport"]["minute"], 0, "월 진행으로 교통의 분은 바뀌지 않음")
        expect(session["agents"]["citizens"], citizens, "이주와 이전 뒤에도 시민 소속 / 고용 유지")
        support.validate_agents(session)
    expect(len(session["agents"]["history"]), 7, "0개월부터 6개월까지 기록")
    expect(session["agents"]["firms"]["F1"]["cash"], 200, "기업 이전 비용을 한 번 차감")
    expect(support.calculate_kpis(session)["population"], 3, "시민 수 보존")

    _check_candidates()
    _check_competition()
    _check_cooldown()
    _check_atomic_update()

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "agents.json"
        support.save_session(session, path)
        restored = support.load_session(path)
        expect(restored, session, "도시 / 행위자 / 월별 기록 JSON 왕복")
        support.advance_month(session)
        support.advance_month(restored)
        expect(restored, session, "저장 복원 후 다음 달 결과")
        competition = _competition_session()
        competition["agents"]["seed"] = 17
        support.save_session(competition, path)
        restored = support.load_session(path)
        support.advance_month(competition)
        support.advance_month(restored)
        expect(restored, competition, "시드를 복원한 뒤 같은 경합 결과")

    model = Neighborhood(seed=42)
    expect(model.snapshot()["dissatisfied"], 21, "초기 불만족 인원")
    for round_number in range(1, 11):
        model.advance()
        counts = Counter(cell for row in model.labels() for cell in row)
        expect(counts, Counter({"A": 25, "B": 25, None: 14}), "유형별 인구와 빈칸 수 보존")
        expect(len(set(model.positions.values())), 50, "행위자 위치 중복 없음")
        if round_number == 1:
            expect(model.history[-1]["dissatisfied"], 2, "1회차 불만족 인원")
            expect(model.history[-1]["moves"], 15, "1회차 이동 수")
        if round_number == 9:
            expect(model.history[-1]["dissatisfied"], 0, "9회차 불만족 인원")
            expect(model.moves_total, 28, "9회차까지 누적 이동 수")
    expect(model.history[-1]["moves"], 0, "안정된 배치에서는 이동 없음")


STAGES = [
    ("TODO 1: 만족도", check_stage_1),
    ("TODO 2: 이주 검토", check_stage_2),
    ("TODO 3: 주택 선택", check_stage_3),
    ("TODO 4: 가구 이주", check_stage_4),
    ("TODO 5: 기업 이전 판단", check_stage_5),
    ("TODO 6: 기업 이전", check_stage_6),
    ("TODO 7: 이웃 비율", check_stage_7),
]


def main():
    parser = argparse.ArgumentParser(description="행위자 기반 도시 모델 실습 확인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 8),
        default=7,
        help="1부터 이 단계까지 점검 (기본: 7)",
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

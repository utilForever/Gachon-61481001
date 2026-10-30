"""월별 재정 갱신, 운영안 비교, 상태 저장 / 불러오기와 CSV 기록."""

import ast
import csv
import json
import math
from copy import deepcopy
from pathlib import Path

import abm_support
import economy_rules as rules
import kpi_support
import service_support

POLICIES = {
    "normal": "기준",
    "hospital": "병원 확충",
    "water": "급수 확충",
    "both": "동시 확충",
}
RULE_NAMES = (
    "tax_revenue",
    "monthly_costs",
    "construction_cost",
    "monthly_balance",
    "settle_finances",
    "compare_policy",
)
UNIT_COSTS = {"road": 20, "hospital": 20, "water": 12}
POLICY_QUANTITIES = {
    "normal": {"road": 0, "hospital": 0, "water": 0},
    "hospital": {"road": 0, "hospital": 1, "water": 0},
    "water": {"road": 0, "hospital": 0, "water": 1},
    "both": {"road": 0, "hospital": 1, "water": 1},
}


def pending_tasks():
    """NotImplementedError가 남아 있는 규칙의 TODO 번호를 반환한다."""
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


def new_state(policy="normal", income_tax_rate=0.1, profit_tax_rate=0.1):
    """0개월 재정을 현금 20 / 부채 200으로 만든다. 세율은 0~1 비율이다."""
    if policy not in POLICIES:
        raise ValueError("비교할 정책을 선택하세요.")
    if not (0 <= income_tax_rate <= 1 and 0 <= profit_tax_rate <= 1):
        raise ValueError("세율은 0~100%로 입력하세요.")

    return {
        "policy": policy,
        "month": 0,
        "cash": 20.0,
        "debt": 200.0,
        "reserve": 20.0,
        "interest_rate": 0.01,
        "employed": 200,
        "wage": 5.0,
        "firm_profit": 200.0,
        "income_tax_rate": income_tax_rate,
        "profit_tax_rate": profit_tax_rate,
        "capital_paid": False,
        "history": [],
        "comparison": None,
    }


def ensure_state(session):
    """입력 session에 재정이 없으면 초기화하고, 재정 상태를 반환한다."""
    if "finance" not in session:
        session["finance"] = new_state()
    return session["finance"]


def reset_finance(session, policy="normal", income_tax_rate=0.1, profit_tax_rate=0.1):
    """입력 session의 재정 상태와 기록만 초기화한다. 도시와 다른 시계는 유지한다."""
    session["finance"] = new_state(policy, income_tax_rate, profit_tax_rate)


def road_count(session):
    return sum(1 for row in session["city"]["grid"] for cell in row if cell["road"])


def service_budgets(policy):
    """운영안별 서비스 월 예산을 예산 단위로 반환한다."""
    return {
        "hospital": 30 if policy in ("hospital", "both") else 24,
        "water": 8 if policy in ("water", "both") else 6,
        "other": 20,
    }


def preview(session):
    """다음 결산의 세금, 비용과 현재 도로 수를 반환한다.

    재정이 없으면 초기화하지만, 월을 진행하거나 건설비를 지불하지는 않는다.
    """
    state = ensure_state(session)
    taxes = rules.tax_revenue(
        state["employed"],
        state["wage"],
        state["firm_profit"],
        state["income_tax_rate"],
        state["profit_tax_rate"],
    )

    roads = road_count(session)
    costs = rules.monthly_costs(roads, 2, 14, service_budgets(state["policy"]))

    # 첫 결산 이후에는 수량을 0으로 두어 건설비를 중복 청구하지 않는다.
    quantities = (
        {key: 0 for key in UNIT_COSTS}
        if state["capital_paid"]
        else POLICY_QUANTITIES[state["policy"]]
    )
    construction = rules.construction_cost(quantities, UNIT_COSTS)

    return {**taxes, **costs, "construction": construction, "road_cells": roads}


def validate_state(state):
    """재정 수치의 범위와 기록 수를 검증한다. 값이 잘못되면 ValueError를 발생시킨다."""
    if state["policy"] not in POLICIES:
        raise ValueError("저장된 정책을 확인하세요.")
    if type(state["month"]) is not int or state["month"] < 0:
        raise ValueError("재정의 월은 0 이상의 정수여야 합니다.")

    for key in (
        "cash",
        "debt",
        "reserve",
        "interest_rate",
        "employed",
        "wage",
        "firm_profit",
        "income_tax_rate",
        "profit_tax_rate",
    ):
        value = state[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(key + " 값은 유한한 숫자여야 합니다.")

    if (
        min(
            state["cash"],
            state["debt"],
            state["reserve"],
            state["interest_rate"],
            state["employed"],
            state["wage"],
        )
        < 0
    ):
        raise ValueError("현금, 부채, 인원과 비용을 음수로 만들 수 없습니다.")
    if not (0 <= state["income_tax_rate"] <= 1 and 0 <= state["profit_tax_rate"] <= 1):
        raise ValueError("세율은 0~1 범위여야 합니다.")

    if len(state["history"]) != state["month"]:
        raise ValueError("재정의 월과 기록 수가 일치하지 않습니다.")
    for row in state["history"]:
        for value in row.values():
            if isinstance(value, (int, float)) and not math.isfinite(value):
                raise ValueError("월별 기록에 유한하지 않은 숫자가 있습니다.")


def advance_month(session):
    """한 달을 결산해 재정 상태를 갱신하고, 해당 월의 기록을 반환한다."""
    # 모든 계산을 마친 뒤 재정 상태만 교체한다. 서비스와 행위자 시계는 진행하지 않는다.
    working = deepcopy(session)
    old = ensure_state(working)
    values = preview(working)
    balance = rules.monthly_balance(
        values["revenue"],
        values["maintenance"],
        values["services"],
        old["debt"],
        old["interest_rate"],
        values["construction"],
    )
    settled = rules.settle_finances(old["cash"], old["debt"], balance["balance"], old["reserve"])

    row = {
        "month": old["month"] + 1,
        "policy": old["policy"],
        "opening_cash": old["cash"],
        "opening_debt": old["debt"],
        **values,
        **balance,
        **settled,
    }

    expected_cash = old["cash"] + balance["balance"] + settled["borrowing"] - settled["repayment"]
    expected_debt = old["debt"] + settled["borrowing"] - settled["repayment"]
    if not math.isclose(settled["cash"], expected_cash, abs_tol=1e-9) or not math.isclose(
        settled["debt"], expected_debt, abs_tol=1e-9
    ):
        raise ValueError("현금과 부채의 보존식을 다시 확인하세요.")

    new = deepcopy(old)
    new.update(
        month=row["month"],
        cash=settled["cash"],
        debt=settled["debt"],
        capital_paid=True,
    )
    new["history"].append(row)
    validate_state(new)

    session["finance"] = new
    return row


def run_comparison(session, months=3):
    """네 운영안의 결과, 기준 대비 변화량과 월별 기록을 반환한다.

    각 복사본에서 재정 months개월과 서비스 24시간을 따로 진행하며 원본은 유지한다.
    """
    if type(months) is not int or months < 1:
        raise ValueError("비교 기간은 1개월 이상이어야 합니다.")

    # 각 대안은 같은 지도를 복사하고 대기, 물, 현금과 부채를 같은 초기값으로 되돌린다.
    source = deepcopy(session)
    settings = ensure_state(source)
    results, series = [], {}

    for policy, name in POLICIES.items():
        trial = deepcopy(source)
        reset_finance(trial, policy, settings["income_tax_rate"], settings["profit_tax_rate"])
        trial["finance"].update(
            employed=settings["employed"],
            wage=settings["wage"],
            firm_profit=settings["firm_profit"],
            interest_rate=settings["interest_rate"],
        )

        series[policy] = [{"month": 0, "debt": 200.0}]
        for _ in range(months):
            series[policy].append(advance_month(trial))

        # 재정 개월 수와 서비스 시간은 서로 다른 관찰 기간이다.
        service_support.reset_services(trial, policy)
        queue6 = None
        for hour in range(1, 25):
            service_row = service_support.advance_hour(trial)
            if hour == 6:
                queue6 = service_row["queue"]

        results.append(
            {
                "policy": policy,
                "name": name,
                "queue6": queue6,
                "queue24": service_row["queue"],
                "debt": trial["finance"]["debt"],
                "cash": trial["finance"]["cash"],
                "coverage": service_row["coverage_ratio"],
            }
        )

    baseline = results[0]
    deltas = [
        {
            "policy": row["policy"],
            "name": row["name"],
            **rules.compare_policy(baseline, row),
        }
        for row in results
    ]

    return {
        "results": results,
        "deltas": deltas,
        "series": series,
        "months": months,
        "hours": 24,
        "road_cells": road_count(source),
        "income_tax_rate": settings["income_tax_rate"],
        "profit_tax_rate": settings["profit_tax_rate"],
    }


def behavior_examples(session):
    """가구 소득·소비와 F1의 세후 이전 순편익을 반환한다.

    가구 집계는 예산 단위, F1은 만원이며 실제 이동이나 고용은 갱신하지 않는다.
    """
    state = ensure_state(session)
    taxes = rules.tax_revenue(
        state["employed"],
        state["wage"],
        state["firm_profit"],
        state["income_tax_rate"],
        state["profit_tax_rate"],
    )
    disposable = taxes["income"] - taxes["household_tax"]

    sites = session["agents"]["sites"]
    before, after = sites["X"]["profit"], sites["Y"]["profit"]
    move_cost = session["agents"]["firms"]["F1"]["move_cost"]
    gain = 6 * (after - before) * (1 - state["profit_tax_rate"]) - move_cost

    return {
        "income": taxes["income"],
        "tax": taxes["household_tax"],
        "disposable": disposable,
        "local_consumption": disposable * 5 / 9,
        "outside_spending": disposable * 2 / 9,
        "saving": disposable * 2 / 9,
        "firm_before": before,
        "firm_after": after,
        "move_cost": move_cost,
        "gain6": gain,
        "profit_tax_rate": state["profit_tax_rate"],
    }


def save_session(session, path):
    """도시와 각 시계, 재정 이력·비교 결과를 검증해 UTF-8 JSON으로 저장한다."""
    abm_support.validate_agents(session)
    service_support.validate_state(service_support.ensure_state(session))
    validate_state(ensure_state(session))

    base = {
        key: deepcopy(value) for key, value in session.items() if key not in ("services", "finance")
    }
    document = kpi_support._to_json_document({"format": "virtual-city-economy-v1", **base})
    document["services"] = deepcopy(session["services"])
    document["finance"] = deepcopy(session["finance"])
    Path(path).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_session(path):
    """저장 상태를 복원·검증한다. 이전 행위자 / 서비스 파일에는 0개월 재정을 추가한다."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("format") != "virtual-city-economy-v1":
        session = service_support.load_session(path)
        ensure_state(session)
        return session

    finance = document.pop("finance")
    services = document.pop("services")
    agents = document.pop("agents")
    document["format"] = "virtual-city-kpi-v1"
    session = kpi_support.restore_session(kpi_support._from_json_document(document))
    session.update(agents=agents, services=services, finance=finance)

    abm_support.validate_agents(session)
    service_support.validate_state(services)
    validate_state(finance)
    return session


def export_history(session, path):
    """현재 재정의 월별 기록을 UTF-8 BOM CSV로 저장한다. 기록이 없으면 ValueError이다."""
    rows = ensure_state(session)["history"]
    if not rows:
        raise ValueError("먼저 한 달 이상 결산하세요.")

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

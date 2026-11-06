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

POLICIES = {"normal": "기준", "hospital": "병원 확충", "water": "급수 확충", "both": "동시 확충"}
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
    if "finance" not in session:
        session["finance"] = new_state()
    return session["finance"]


def reset_finance(session, policy="normal", income_tax_rate=0.1, profit_tax_rate=0.1):
    session["finance"] = new_state(policy, income_tax_rate, profit_tax_rate)


def road_count(session):
    return sum(1 for row in session["city"]["grid"] for cell in row if cell["road"])


def service_budgets(policy):
    return {
        "hospital": 30 if policy in ("hospital", "both") else 24,
        "water": 8 if policy in ("water", "both") else 6,
        "other": 20,
    }


def preview(session):
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

    quantities = (
        {key: 0 for key in UNIT_COSTS}
        if state["capital_paid"]
        else POLICY_QUANTITIES[state["policy"]]
    )
    construction = rules.construction_cost(quantities, UNIT_COSTS)

    return {**taxes, **costs, "construction": construction, "road_cells": roads}


def validate_state(state):
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
    new.update(month=row["month"], cash=settled["cash"], debt=settled["debt"], capital_paid=True)
    new["history"].append(row)
    validate_state(new)

    session["finance"] = new
    return row


def run_comparison(session, months=3):
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
        {"policy": row["policy"], "name": row["name"], **rules.compare_policy(baseline, row)}
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
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_session(path):
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
    rows = ensure_state(session)["history"]
    if not rows:
        raise ValueError("먼저 한 달 이상 결산하세요.")

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

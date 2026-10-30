"""
세금 수입, 월별 비용과 수지, 현금과 부채의 결산, 정책별 변화량을 계산하는 규칙.

재정의 1 tick은 1개월이고, 금액은 예산 단위다. 이자는 월초 부채를 기준으로 계산한다.
모든 함수는 입력을 읽기만 하며, 계산값은 반올림하지 않고 새 결과로 반환한다.
건설비가 발생하는 월과 도시 상태의 갱신은 제공 코드가 관리한다.
"""


def tax_revenue(employed, wage, firm_profit, income_tax_rate, profit_tax_rate):
    """가구 소득과 두 세금, 총 세금 수입을 새 딕셔너리로 반환한다. 기업 손실의 세금은 0이다."""
    income = employed * wage
    household_tax = income * income_tax_rate
    # 기업 이익이 양수일 때만 과세하며 손실 환급은 모델링하지 않는다.
    firm_tax = max(0, firm_profit) * profit_tax_rate

    return {
        "income": income,
        "household_tax": household_tax,
        "firm_tax": firm_tax,
        "revenue": household_tax + firm_tax,
    }


def monthly_costs(road_cells, road_unit_cost, facility_maintenance, service_budgets):
    """월 유지관리비와 서비스 운영비, 두 비용의 합계를 새 딕셔너리로 반환한다."""
    maintenance = road_cells * road_unit_cost + facility_maintenance
    services = sum(service_budgets.values())

    return {
        "maintenance": maintenance,
        "services": services,
        "recurring": maintenance + services,
    }


def construction_cost(quantities, unit_costs):
    """공사 수량과 단가의 곱을 합산해 반환한다. 수량의 모든 키는 단가에도 있다."""
    total = 0

    for item, quantity in quantities.items():
        total += quantity * unit_costs[item]

    return total


def monthly_balance(revenue, maintenance, services, debt, interest_rate, construction):
    """월초 부채의 이자와 차입·원금 상환 전 월 수지를 새 딕셔너리로 반환한다."""
    # 이번 달 신규 차입은 다음 달 이자에 반영한다.
    interest = debt * interest_rate
    balance = revenue - maintenance - services - interest - construction
    return {"interest": interest, "balance": balance}


def settle_finances(cash, debt, balance, reserve):
    """최소 보유 현금을 지키는 차입·상환액과 월말 현금·부채를 새 딕셔너리로 반환한다."""
    # 최소 보유액을 뺀 부족분은 빌리고, 여유분은 남은 부채 한도에서 상환한다.
    available = cash + balance - reserve
    borrowing = max(0, -available)
    repayment = min(debt, max(0, available))

    return {
        "borrowing": borrowing,
        "repayment": repayment,
        "cash": cash + balance + borrowing - repayment,
        "debt": debt + borrowing - repayment,
    }


def compare_policy(baseline, alternative):
    """다섯 정책 지표의 비교안에서 기준을 뺀 변화량을 새 딕셔너리로 반환한다."""
    differences = {}

    # 감소는 음수, 증가는 양수로 남기며 지표별 단위는 그대로 유지한다.
    for key in ("queue6", "queue24", "debt", "cash", "coverage"):
        differences[key] = alternative[key] - baseline[key]

    return differences

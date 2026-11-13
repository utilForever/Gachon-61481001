"""세입 / 세출, 건설비, 차입 / 상환과 정책 차이를 계산하는 규칙."""


def tax_revenue(employed, wage, firm_profit, income_tax_rate, profit_tax_rate):
    income = employed * wage
    household_tax = income * income_tax_rate
    firm_tax = max(0, firm_profit) * profit_tax_rate

    return {
        "income": income,
        "household_tax": household_tax,
        "firm_tax": firm_tax,
        "revenue": household_tax + firm_tax,
    }


def monthly_costs(road_cells, road_unit_cost, facility_maintenance, service_budgets):
    maintenance = road_cells * road_unit_cost + facility_maintenance
    services = sum(service_budgets.values())

    return {"maintenance": maintenance, "services": services, "recurring": maintenance + services}


def construction_cost(quantities, unit_costs):
    total = 0

    for item, quantity in quantities.items():
        total += quantity * unit_costs[item]

    return total


def monthly_balance(revenue, maintenance, services, debt, interest_rate, construction):
    interest = debt * interest_rate
    balance = revenue - maintenance - services - interest - construction

    return {"interest": interest, "balance": balance}


def settle_finances(cash, debt, balance, reserve):
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
    differences = {}

    for key in ("queue6", "queue24", "debt", "cash", "coverage"):
        differences[key] = alternative[key] - baseline[key]

    return differences

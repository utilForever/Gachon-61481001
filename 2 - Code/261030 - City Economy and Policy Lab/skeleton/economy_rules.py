"""
세금 수입, 월별 비용과 수지, 현금과 부채의 결산, 정책별 변화량을 계산하는 규칙.

재정의 1 tick은 1개월이고, 금액은 예산 단위다. 이자는 월초 부채를 기준으로 계산한다.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 각 함수의 안내 주석 아래에 코드를 추가하세요.
2. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
3. 파일을 저장하고 skeleton 폴더의 터미널에서 python checks_economy.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
4. 여섯 함수를 완성하면 python checks_economy.py와
   python checks_economy.py --integration을 각각 실행하세요.

- 데이터를 읽을 때
모든 함수는 입력을 읽기만 합니다. 입력 딕셔너리를 수정하지 않고 새 결과를 반환하세요.
반환 키는 제공 코드가 사용하므로 이름을 그대로 쓰세요. 내부 계산값은 반올림하지 않습니다.
수량과 단가는 음이 아닌 수, 세율은 0~1입니다. 기업 이익과 월 수지는 음수일 수 있습니다.
건설비가 발생하는 월과 도시 상태의 갱신은 제공 코드가 관리합니다.
"""


def tax_revenue(employed, wage, firm_profit, income_tax_rate, profit_tax_rate):
    """가구 소득과 두 세금, 총 세금 수입을 새 딕셔너리로 반환한다. 기업 손실의 세금은 0이다."""
    raise NotImplementedError("tax_revenue")

    # TODO 1: income / household_tax / firm_tax / revenue를 계산해 반환하세요.
    # 1. 취업자 수 employed에 1인당 월 임금 wage를 곱해 가구 소득 income을 구하세요.
    # 2. 가구 소득에 income_tax_rate를 곱해 household_tax를 구하세요.
    # 3. firm_profit이 양수인 부분에만 profit_tax_rate를 적용해 firm_tax를 구하세요.
    #    기업이 손실을 보아도 세금 환급은 없습니다. 이때 firm_tax는 0입니다.
    # 4. 두 세금을 합친 revenue와 앞의 세 값을 같은 이름의 키로 반환하세요.
    # 확인 예: (200, 5, 200, 0.1, 0.1)이면 소득 1000, 가구세 100, 기업세 20, 수입 120입니다.
    # 소득이나 기업 이익 전체를 세금 수입에 더하지 마세요.


def monthly_costs(road_cells, road_unit_cost, facility_maintenance, service_budgets):
    """월 유지관리비와 서비스 운영비, 두 비용의 합계를 새 딕셔너리로 반환한다."""
    raise NotImplementedError("monthly_costs")

    # TODO 2: maintenance / services / recurring을 계산해 반환하세요.
    # 1. 도로 셀 수 road_cells와 셀당 월 단가 road_unit_cost를 곱하세요.
    #    여기에 시설 수선비 facility_maintenance를 더한 값이 maintenance입니다.
    # 2. service_budgets는 서비스 이름을 키로, 월 예산을 값으로 가진 딕셔너리입니다.
    #    .values()로 예산을 꺼내 합산한 값을 services로 사용하세요.
    # 3. maintenance와 services의 합계를 recurring에 담아 세 값을 반환하세요.
    # 확인 예: 도로 8칸, 단가 2, 수선비 14, 서비스 예산 24 / 6 / 20이면 30 / 50 / 80입니다.
    # 서비스 예산 딕셔너리가 비어 있으면 운영비는 0입니다. 입력 예산은 바꾸지 마세요.


def construction_cost(quantities, unit_costs):
    """공사 수량과 단가의 곱을 합산해 반환한다. 수량의 모든 키는 단가에도 있다."""
    raise NotImplementedError("construction_cost")

    # TODO 3: 공사별 수량과 단가를 곱해 건설비 합계를 숫자 하나로 반환하세요.
    # 1. 합계를 0으로 시작하고 quantities.items()에서 공사 이름과 수량을 꺼내세요.
    # 2. 같은 공사 이름으로 unit_costs에서 단가를 찾아 수량과 곱하세요.
    # 3. 공사별 금액을 누적하고 반복이 끝나면 합계를 반환하세요.
    # 확인 예: 병원 1개와 급수 시설 1개를 짓고 단가가 각각 20과 12이면 합계는 32입니다.
    # 수량이 모두 0이거나 공사가 없으면 0입니다. 단가만 있고 수량에 없는 공사는 제외합니다.
    # 첫 달 이후의 공사 수량은 제공 코드가 정합니다. 여기서 월이나 도시 상태를 바꾸지 마세요.


def monthly_balance(revenue, maintenance, services, debt, interest_rate, construction):
    """월초 부채의 이자와 차입·원금 상환 전 월 수지를 새 딕셔너리로 반환한다."""
    raise NotImplementedError("monthly_balance")

    # TODO 4: interest / balance를 계산해 반환하세요.
    # 1. 월초 부채 debt에 월 이자율 interest_rate를 곱해 interest를 구하세요.
    # 2. 세금 수입 revenue에서 maintenance, services, interest, construction을 빼세요.
    #    이 값이 월 수지 balance이며, 적자이면 음수로 그대로 반환합니다.
    # 3. 이자와 월 수지를 각각 interest와 balance 키에 담아 반환하세요.
    # 확인 예: (120, 30, 50, 200, 0.01, 0)이면 이자는 2, 월 수지는 38입니다.
    # 신규 차입과 원금 상환은 TODO 5에서 처리합니다. 여기서 다시 더하거나 빼지 마세요.


def settle_finances(cash, debt, balance, reserve):
    """최소 보유 현금을 지키는 차입·상환액과 월말 현금·부채를 새 딕셔너리로 반환한다."""
    raise NotImplementedError("settle_finances")

    # TODO 5: borrowing / repayment / cash / debt를 계산해 반환하세요.
    # 1. 월초 현금 cash에 월 수지 balance를 더하고 최소 보유 현금 reserve를 빼세요.
    # 2. 결과가 음수이면 부족분만큼 borrowing으로 빌리고, repayment는 0으로 두세요.
    # 3. 결과가 양수이면 남은 부채 debt 한도에서 repayment로 갚고, borrowing은 0입니다.
    #    결과가 0이면 borrowing과 repayment를 모두 0으로 두세요.
    # 4. 월말 현금에는 월 수지와 차입을 더하고 상환을 빼세요.
    #    월말 부채에는 차입을 더하고 상환을 빼서 네 값을 새 딕셔너리로 반환하세요.
    # 확인 예: (20, 200, 38, 20)이면 차입 0, 상환 38, 월말 현금 20, 부채 162입니다.
    # (20, 5, 10, 20)이면 부채 5만 갚고 현금 25를 남깁니다. 남은 현금을 버리지 마세요.
    # 최소 보유액보다 많은 현금은 적자에 먼저 쓸 수 있습니다. 계산값은 반올림하지 마세요.


def compare_policy(baseline, alternative):
    """다섯 정책 지표의 비교안에서 기준을 뺀 변화량을 새 딕셔너리로 반환한다."""
    raise NotImplementedError("compare_policy")

    # TODO 6: 지표마다 비교안에서 기준을 뺀 변화량을 반환하세요.
    # 1. queue6, queue24, debt, cash, coverage 다섯 키를 차례로 확인하세요.
    # 2. 같은 키의 alternative 값에서 baseline 값을 빼세요. 빼는 순서를 지키세요.
    # 3. 원래 키와 계산한 차이를 새 딕셔너리에 담아 반환하세요. 입력은 바꾸지 않습니다.
    # 확인 예: queue24가 기준 86, 비교안 48이면 변화량은 -38입니다.
    # coverage가 0.75에서 1.0이 되면 차이는 0.25입니다. 25%포인트 표시는 GUI가 담당합니다.
    # 대기 감소와 부채 증가의 의미는 다릅니다. 단위가 다른 지표를 하나로 합산하지 마세요.

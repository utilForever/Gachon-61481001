"""
가구의 만족도와 이주, 기업의 이전, 이웃 비율을 계산하는 행동 규칙.

- 실습 진행 방법
1. TODO 1부터 7까지 순서대로 작성하세요. 자세한 힌트는 각 함수의 주석에 있습니다.
2. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈춥니다.
3. 파일을 저장하고 이 폴더의 터미널에서 python checks_abm.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 번호를 1~7로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
4. 모든 함수를 작성한 뒤 python checks_abm.py와
   python checks_abm.py --integration을 각각 실행하세요.
   화면에 변경 내용을 반영하려면 프로그램을 닫고 다시 실행하세요.

- 데이터를 읽을 때
state는 session["agents"]이며, 시민 / 가구 / 주택 / 기업 / 사업장을 ID로 연결합니다.
시간은 편도 분, 금액은 만원, 환경은 0~100점입니다. 행위자는 월 단위로 행동합니다.
조회 / 판단 함수는 입력을 읽기만 합니다.
move_household와 move_firm은 승인된 이동을 입력 상태에 직접 반영합니다.
이웃 격자의 좌표는 (x, y), 셀 접근은 grid[y][x]이며 빈칸은 None입니다.
"""


def satisfaction(commute_min, rent, income, environment):
    """통근 / 주거비 / 환경의 가중합을 반환한다. 결과를 반올림하지 않는다."""
    raise NotImplementedError("TODO 1: 가구의 만족도 점수를 계산하세요.")

    # TODO 1: 세 점수를 구한 뒤 가중치를 곱해 더하세요.
    # 1. 통근 점수는 100 * max(0, 1 - commute_min / 60)입니다.
    #    commute_min이 None이면 경로가 없으므로 통근 점수를 0으로 처리하세요.
    # 2. 주거비 점수는 100 * max(0, 1 - rent / income)입니다.
    #    income이 0이면 주거비 점수를 0으로 처리해 0으로 나누지 않도록 하세요.
    # 3. 통근 0.5 / 주거비 0.3 / 환경 0.2의 가중합을 반환하세요.
    # environment는 이미 0~100점입니다. 표시용 반올림은 화면에서 처리합니다.
    # 확인 예: (45, 80, 200, 50)이면 40.5, (None, 80, 200, 50)이면 28.0입니다.


def should_move(household):
    """가구의 이주 검토 조건을 bool로 반환한다. 입력 가구는 변경하지 않는다."""
    raise NotImplementedError("TODO 2: 가구가 이주를 검토할 수 있는지 판단하세요.")

    # TODO 2: 다음 세 조건을 모두 만족하는지 and로 연결해 반환하세요.
    # 1. household["dissatisfied_months"]가 2 이상입니다.
    # 2. household["cooldown"]이 0입니다.
    # 3. household["savings"]가 household["move_cost"] 이상입니다.
    # 불만족 기간과 대기 기간은 제공 코드가 갱신합니다. 여기서는 읽기만 하세요.
    # 확인 예: 불만족 2개월 / 대기 0개월 / 저축 30 / 비용 30이면 True입니다.
    # True는 이주 검토가 가능하다는 뜻입니다. 실제 입주 승인은 따로 처리합니다.


def choose_home(household, candidates, current_score):
    """앞의 세 후보 중 조건에 맞는 첫 후보 dict를 반환한다. 없으면 None이다."""
    raise NotImplementedError("TODO 3: 조건을 만족하는 첫 주택 후보를 선택하세요.")

    # TODO 3: candidates의 앞 세 항목을 주어진 순서로 조사하세요.
    # 각 후보는 home_id / feasible / score를 가진 dict입니다.
    # 1. candidates[:3]으로 조사 범위를 제한하세요. 후보가 적어도 사용할 수 있습니다.
    # 2. feasible이 True이고 score가 current_score + 10 이상인지 확인하세요.
    # 3. 조건을 만족하면 그 후보 dict 자체를 즉시 반환하세요. 없으면 None을 반환하세요.
    # 후보를 정렬하거나 가장 높은 점수를 찾지 않습니다. 점수와 입주 조건은 계산되어 있습니다.
    # household는 공통 호출 형식에 포함된 인수입니다. 후보 판단에 직접 쓰지 않아도 됩니다.
    # 확인 예: 현재 40점이고 입주 가능한 후보가 50점 / 90점이면 첫 50점 후보를 선택합니다.


def move_household(state, household_id, new_home_id):
    """승인된 가구 이주를 입력 상태에 반영한다. 시민의 소속 / 고용은 유지한다."""
    raise NotImplementedError("TODO 4: 승인된 가구 이주를 상태에 반영하세요.")

    # TODO 4: 가구와 주택의 참조를 함께 바꾸고 비용과 대기 기간을 갱신하세요.
    # 1. state["households"][household_id]에서 가구를 읽고 기존 home_id를 보관하세요.
    # 2. state["houses"]에서 옛 주택의 occupant는 None으로 바꾸세요.
    #    새 주택의 occupant에는 household_id를 기록하세요. 가구 dict 전체를 넣지 않습니다.
    # 3. 가구의 home_id를 new_home_id로 바꾸고 savings에서 move_cost를 한 번 빼세요.
    # 4. dissatisfied_months는 0, cooldown은 3으로 바꾸세요.
    # 입주 승인과 다른 가구와의 경합은 제공 코드가 처리했습니다. 이동만 반영하세요.
    # 시민 목록과 다른 가구는 바꾸지 않습니다. 건물 인구는 제공 코드가 나중에 동기화합니다.
    # 확인 예: H1이 A에서 B로 이사하면 A는 빈집, B의 occupant는 "H1", 저축은 120입니다.


def should_move_firm(firm, candidate_profit):
    """6개월 순편익과 이전 자금으로 판단한다. 입력 기업은 변경하지 않는다."""
    raise NotImplementedError("TODO 5: 기업의 이전 여부를 판단하세요.")

    # TODO 5: 순편익이 양수이고 이전 비용을 낼 수 있는지 반환하세요.
    # 1. 월 이익 증가분은 candidate_profit - firm["profit"]입니다.
    # 2. 6개월 증가분에서 firm["move_cost"]를 빼 순편익을 구하세요.
    # 3. 순편익이 0보다 크고 firm["cash"]가 firm["move_cost"] 이상이어야 합니다.
    # 순편익이 정확히 0이면 False입니다. 판단 단계에서는 현금을 차감하지 않습니다.
    # 확인 예: 현재 이익 150 / 후보 이익 260 / 비용 500이면 순편익은 160입니다.
    # 현금이 500이면 이전 가능하고, 499이면 비용을 낼 수 없습니다.


def move_firm(state, firm_id, new_site_id):
    """승인된 기업 이전을 입력 상태에 반영한다. 직원과 고용 관계는 유지한다."""
    raise NotImplementedError("TODO 6: 승인된 기업 이전을 상태에 반영하세요.")

    # TODO 6: 기업과 사업장의 참조를 함께 바꾸고 비용과 이익을 갱신하세요.
    # 1. state["firms"][firm_id]에서 기업을 읽고 기존 site_id를 확인하세요.
    # 2. state["sites"]에서 옛 사업장의 occupant는 None으로 바꾸세요.
    #    새 사업장의 occupant에는 firm_id를 기록하세요.
    # 3. 기업의 site_id를 new_site_id로 바꾸고 cash에서 move_cost를 한 번 빼세요.
    # 4. 새 사업장의 profit을 읽어 기업의 profit에 저장하세요.
    # employees와 시민의 employer_id는 유지합니다. 가구의 주택도 바꾸지 않습니다.
    # 확인 예: F1이 X에서 Y로 이전하면 자금은 700 - 500 = 200, 월 이익은 260입니다.


def same_type_ratio(grid, x, y):
    """거주 이웃 중 같은 유형의 비율을 반환한다. 거주 이웃이 없으면 None이다."""
    raise NotImplementedError("TODO 7: 거주 이웃 중 같은 유형의 비율을 계산하세요.")

    # TODO 7: 자신을 제외한 주변 8칸에서 같은 유형의 비율을 계산하세요.
    # grid[y][x]는 현재 행위자의 유형이고, None인 칸은 빈칸입니다.
    # 1. dx, dy에 -1 / 0 / 1을 조합하되 (0, 0)은 자신이므로 제외하세요.
    # 2. nx = x + dx, ny = y + dy로 이웃 좌표를 구하고 격자 범위를 확인하세요.
    #    범위는 0 <= nx < len(grid[0]), 0 <= ny < len(grid)입니다.
    # 3. 이웃이 None이 아니면 거주 이웃 수를 늘리고, 같은 유형이면 같은 유형 수도 늘리세요.
    # 4. 거주 이웃이 있으면 같은 유형 수 / 거주 이웃 수를, 없으면 None을 반환하세요.
    # 입력 격자는 바꾸지 않습니다. 음수 인덱스로 반대편 셀을 읽지 않도록 주의하세요.
    # 확인 예: 거주 이웃 6명 중 같은 유형이 3명이면 0.5, 한 칸 격자이면 None입니다.

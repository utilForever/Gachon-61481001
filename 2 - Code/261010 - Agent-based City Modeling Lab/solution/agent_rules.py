"""
가구의 만족도와 이주, 기업의 이전, 이웃 비율을 계산하는 행동 규칙.

시간은 편도 분, 금액은 만원, 환경은 0~100점이며 행위자는 월 단위로 행동한다.
조회 / 판단 함수는 입력을 읽기만 한다. 결과의 반올림은 화면에서 처리한다.
move_household와 move_firm은 승인된 이동을 입력 상태에 직접 반영한다.
이웃 격자의 좌표는 (x, y), 셀 접근은 grid[y][x]이며 빈칸은 None이다.
"""


def satisfaction(commute_min, rent, income, environment):
    """통근 / 주거비 / 환경의 가중합을 반환한다. 결과를 반올림하지 않는다."""
    commute_score = 0 if commute_min is None else 100 * max(0, 1 - commute_min / 60)
    rent_score = 0 if income == 0 else 100 * max(0, 1 - rent / income)

    return 0.5 * commute_score + 0.3 * rent_score + 0.2 * environment


def should_move(household):
    """가구의 이주 검토 조건을 bool로 반환한다. 입력 가구는 변경하지 않는다."""
    return (
        household["dissatisfied_months"] >= 2
        and household["cooldown"] == 0
        and household["savings"] >= household["move_cost"]
    )


def choose_home(household, candidates, current_score):
    """앞의 세 후보 중 조건에 맞는 첫 후보 dict를 반환한다. 없으면 None이다."""
    for candidate in candidates[:3]:
        if candidate["feasible"] and candidate["score"] >= current_score + 10:
            return candidate

    return None


def move_household(state, household_id, new_home_id):
    """승인된 가구 이주를 입력 상태에 반영한다. 시민의 소속 / 고용은 유지한다."""
    household = state["households"][household_id]
    old_home_id = household["home_id"]

    # 승인된 이주는 주택과 가구의 참조를 함께 갱신한다.
    state["houses"][old_home_id]["occupant"] = None
    state["houses"][new_home_id]["occupant"] = household_id

    household["home_id"] = new_home_id
    household["savings"] -= household["move_cost"]
    household["dissatisfied_months"] = 0
    household["cooldown"] = 3


def should_move_firm(firm, candidate_profit):
    """6개월 순편익과 이전 자금으로 판단한다. 입력 기업은 변경하지 않는다."""
    benefit = 6 * (candidate_profit - firm["profit"]) - firm["move_cost"]
    return benefit > 0 and firm["cash"] >= firm["move_cost"]


def move_firm(state, firm_id, new_site_id):
    """승인된 기업 이전을 입력 상태에 반영한다. 직원과 고용 관계는 유지한다."""
    firm = state["firms"][firm_id]
    state["sites"][firm["site_id"]]["occupant"] = None
    state["sites"][new_site_id]["occupant"] = firm_id

    firm["site_id"] = new_site_id
    firm["cash"] -= firm["move_cost"]
    firm["profit"] = state["sites"][new_site_id]["profit"]


def same_type_ratio(grid, x, y):
    """거주 이웃 중 같은 유형의 비율을 반환한다. 거주 이웃이 없으면 None이다."""
    same = 0
    occupied = 0

    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if (dx == 0 and dy == 0) or not (0 <= ny < len(grid) and 0 <= nx < len(grid[0])):
                continue

            neighbor = grid[ny][nx]
            if neighbor is not None:
                occupied += 1
                if neighbor == grid[y][x]:
                    same += 1

    return same / occupied if occupied else None

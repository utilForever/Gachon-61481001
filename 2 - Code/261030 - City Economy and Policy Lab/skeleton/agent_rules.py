# 가구와 기업의 이동 판단 / 상태 갱신, 같은 유형의 이웃 비율 계산.


def satisfaction(commute_min, rent, income, environment):
    """통근 시간(분), 주거비 부담과 환경 점수를 가중합한 만족도를 반환한다."""
    commute_score = 0 if commute_min is None else 100 * max(0, 1 - commute_min / 60)
    rent_score = 0 if income == 0 else 100 * max(0, 1 - rent / income)
    return 0.5 * commute_score + 0.3 * rent_score + 0.2 * environment


def should_move(household):
    """연속 불만족 기간, 재이주 대기 기간과 이사 자금으로 이주 검토 여부를 판단한다."""
    return (
        household["dissatisfied_months"] >= 2
        and household["cooldown"] == 0
        and household["savings"] >= household["move_cost"]
    )


def choose_home(household, candidates, current_score):
    """앞의 세 후보 중 입주 가능하고 만족도가 10점 이상 개선되는 첫 후보를 반환한다."""
    for candidate in candidates[:3]:
        if candidate["feasible"] and candidate["score"] >= current_score + 10:
            return candidate

    return None


def move_household(state, household_id, new_home_id):
    """승인된 가구 이주를 반영한다. 주택 참조, 저축과 대기 기간을 직접 갱신한다."""
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
    """향후 6개월 순편익이 양수이고 이전 자금이 충분한지 판단한다."""
    benefit = 6 * (candidate_profit - firm["profit"]) - firm["move_cost"]
    return benefit > 0 and firm["cash"] >= firm["move_cost"]


def move_firm(state, firm_id, new_site_id):
    """승인된 기업 이전을 반영한다. 사업장 참조, 자금과 월 이익을 직접 갱신한다."""
    firm = state["firms"][firm_id]
    state["sites"][firm["site_id"]]["occupant"] = None
    state["sites"][new_site_id]["occupant"] = firm_id
    firm["site_id"] = new_site_id
    firm["cash"] -= firm["move_cost"]
    firm["profit"] = state["sites"][new_site_id]["profit"]


def same_type_ratio(grid, x, y):
    """주변 8칸의 거주자 중 같은 유형의 비율을 반환한다. 이웃이 없으면 None이다."""
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

"""만족도, 가구 / 기업 이주와 이웃 구성 비율을 계산하는 규칙."""


def satisfaction(commute_min, rent, income, environment):
    commute_score = 0 if commute_min is None else 100 * max(0, 1 - commute_min / 60)
    rent_score = 0 if income == 0 else 100 * max(0, 1 - rent / income)

    return 0.5 * commute_score + 0.3 * rent_score + 0.2 * environment


def should_move(household):
    return (
        household["dissatisfied_months"] >= 2
        and household["cooldown"] == 0
        and household["savings"] >= household["move_cost"]
    )


def choose_home(household, candidates, current_score):
    for candidate in candidates[:3]:
        if candidate["feasible"] and candidate["score"] >= current_score + 10:
            return candidate

    return None


def move_household(state, household_id, new_home_id):
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
    benefit = 6 * (candidate_profit - firm["profit"]) - firm["move_cost"]
    return benefit > 0 and firm["cash"] >= firm["move_cost"]


def move_firm(state, firm_id, new_site_id):
    firm = state["firms"][firm_id]
    state["sites"][firm["site_id"]]["occupant"] = None
    state["sites"][new_site_id]["occupant"] = firm_id
    firm["site_id"] = new_site_id
    firm["cash"] -= firm["move_cost"]
    firm["profit"] = state["sites"][new_site_id]["profit"]


def same_type_ratio(grid, x, y):
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

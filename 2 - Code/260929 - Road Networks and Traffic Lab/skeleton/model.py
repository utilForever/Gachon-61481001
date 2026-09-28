"""
용도지역과 건물 배치, 주변 환경과 수요에 따른 입주, 인구와 예산의 갱신 규칙.

좌표는 (x, y), 셀 접근은 grid[y][x], 도시의 1 tick은 1일이다.
조회 / 계산 함수는 입력을 읽기만 한다. 세금은 하루 시작 인구를 기준으로 계산한다.
place_building은 0일에 입력 도시를 직접 수정하고, step은 원본을 보존한 새 도시를 반환한다.
이번 도로망 실습에서는 이 파일의 함수를 제공 코드로 사용한다.
"""

from copy import deepcopy

from city_data import validate_city


def neighbors4(city, x, y):
    """지도 안의 왼쪽 / 오른쪽 / 위 / 아래 좌표 목록을 반환한다. 입력 좌표는 지도 안이다."""
    height = len(city["grid"])
    width = len(city["grid"][0])
    result = []

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx = x + dx
        ny = y + dy
        if 0 <= nx < width and 0 <= ny < height:
            result.append((nx, ny))

    return result


def total_population(city):
    """운영 상태와 관계없이 모든 주택의 인구를 합산한다. 빈 도시이면 0이다."""
    population = 0
    for building in city["buildings"].values():
        if building["kind"] == "house":
            population += building["population"]

    return population


def can_build(city, x, y, kind):
    """건물 종류와 용도지역이 맞는 비어 있는 땅인지 판단한다. 입력은 보존한다."""
    if type(x) is not int or type(y) is not int:
        return False
    if not (0 <= y < len(city["grid"]) and 0 <= x < len(city["grid"][0])):
        return False

    cell = city["grid"][y][x]
    if cell["terrain"] != "land" or cell["road"] or cell["building_id"] is not None:
        return False

    allowed_zone = {"house": "R", "shop": "C", "factory": "I", "park": None}
    return kind in allowed_zone and cell["zone"] == allowed_zone[kind]


def occupancy(building):
    """주택 / 상점 / 공장의 점유율을 반환한다. 공원이거나 수용량이 0이면 None이다."""
    if building["kind"] == "park" or building["capacity"] == 0:
        return None

    if building["kind"] == "house":
        quantity = building["population"]
    else:
        quantity = building["workers"]

    return quantity / building["capacity"]


def road_access(city, building):
    """건물의 상하좌우에 도로가 하나 이상 있는지 판단한다. 대각선은 제외한다."""
    for nx, ny in neighbors4(city, building["x"], building["y"]):
        if city["grid"][ny][nx]["road"]:
            return True

    return False


def environment_score(city, building):
    """운영 중인 상하좌우 공원마다 +2, 공장마다 -3을 합산한다."""
    score = 0
    for nx, ny in neighbors4(city, building["x"], building["y"]):
        ident = city["grid"][ny][nx]["building_id"]
        if ident is None:
            continue

        neighbor = city["buildings"][ident]
        if neighbor["status"] != "operating":
            continue

        if neighbor["kind"] == "park":
            score += 2
        elif neighbor["kind"] == "factory":
            score -= 3

    return score


def growth_request(city, house):
    """주택의 입주 요청량과 전출량을 튜플로 반환한다. 실제 수요 배정은 별도이다."""
    if house["kind"] != "house" or house["status"] != "operating":
        return (0, 0)

    score = environment_score(city, house)
    if not road_access(city, house) or score <= -1:
        return (0, min(1, house["population"]))
    if score == 0:
        return (0, 0)

    vacancy = house["capacity"] - house["population"]
    return (min(city["rules"]["growth_per_day"], vacancy), 0)


def allocate_arrivals(requests, demand):
    """건물 ID 순서로 남은 수요를 배정한 새 dict를 반환한다. 입력은 보존한다."""
    allocated = {}
    remaining = demand

    for ident in sorted(requests):
        count = min(requests[ident], remaining)
        allocated[ident] = count
        remaining -= count

    return allocated


def step(old):
    """시작 상태를 보존하고 하루 뒤의 독립적인 새 상태를 반환한다."""
    validate_city(old)
    new = deepcopy(old)
    start_population = total_population(old)
    requests = {}
    departures = {}

    # 각 주택의 변화량은 같은 시작 상태에서 계산한다.
    for ident, house in old["buildings"].items():
        if house["kind"] == "house":
            requests[ident], departures[ident] = growth_request(old, house)

    allocated = allocate_arrivals(requests, old["demand"])
    for ident in requests:
        new["buildings"][ident]["population"] = (
            old["buildings"][ident]["population"] + allocated[ident] - departures[ident]
        )

    new["demand"] = old["demand"] - sum(allocated.values())
    new["departed"] = old["departed"] + sum(departures.values())

    rules = old["rules"]
    # 세금은 지난주와 같이 하루 시작 인구를 기준으로 계산한다.
    new["budget"] = (
        old["budget"]
        + start_population * rules["tax_per_person_day"]
        - rules["maintenance_per_day"]
    )
    new["day"] = old["day"] + 1

    validate_city(new)
    return new


def place_building(city, x, y, kind):
    """0일에 건물을 배치하고 새 ID를 반환한다. 배치 조건을 먼저 확인한다."""
    validate_city(city)
    if city["day"] != 0:
        raise ValueError("건물 배치는 0일에만 가능합니다. 시작 상태로 돌아가세요.")
    if not can_build(city, x, y, kind):
        raise ValueError(
            "건물은 비어 있는 땅에, 맞는 용도지역에 배치하세요. 공원은 용도 미지정 셀에 놓습니다."
        )

    prefix = {"house": "H", "park": "P", "shop": "C", "factory": "I"}[kind]
    number = 1
    while prefix + str(number) in city["buildings"]:
        number += 1
    ident = prefix + str(number)

    building = {"id": ident, "kind": kind, "x": x, "y": y, "status": "operating"}
    if kind == "house":
        building["population"] = 0
        building["capacity"] = 10
    elif kind in ("shop", "factory"):
        building["workers"] = 0
        building["capacity"] = 10

    # 모든 설치 조건을 확인한 뒤 셀과 건물 참조를 함께 기록한다.
    city["buildings"][ident] = building
    city["grid"][y][x]["building_id"] = ident
    validate_city(city)
    return ident

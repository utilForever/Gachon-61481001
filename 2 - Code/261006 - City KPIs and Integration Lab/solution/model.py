from copy import deepcopy
from city_data import validate_city


def neighbors4(city, x, y):
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
    population = 0

    for building in city["buildings"].values():
        if building["kind"] == "house":
            population += building["population"]

    return population


def can_build(city, x, y, kind):
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
    if building["kind"] == "park" or building["capacity"] == 0:
        return None

    if building["kind"] == "house":
        quantity = building["population"]
    else:
        quantity = building["workers"]

    return quantity / building["capacity"]


def road_access(city, building):
    for nx, ny in neighbors4(city, building["x"], building["y"]):
        if city["grid"][ny][nx]["road"]:
            return True

    return False


def environment_score(city, building):
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
    allocated = {}
    remaining = demand

    for ident in sorted(requests):
        count = min(requests[ident], remaining)
        allocated[ident] = count
        remaining -= count

    return allocated


def step(old):
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

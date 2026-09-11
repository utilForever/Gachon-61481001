"""
주택과 공원 배치, 외부 전력과 도로 / 공원 접근성에 따른 입주, 인구와 예산의 갱신 규칙.

좌표는 (x, y), 셀 접근은 grid[y][x], 1 tick은 1일이다.
조회 / 계산 함수는 입력을 읽기만 한다. 세금은 하루 시작 인구를 기준으로 계산한다.
place_building은 0일에 입력 도시를 직접 수정하고, step은 원본을 보존한 새 도시를 반환한다.
"""

from copy import deepcopy

from city_data import validate_city


def neighbors4(city, x, y):
    """지도 안의 상하좌우 좌표 목록을 반환한다. 입력 좌표는 지도 안이다."""
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


def place_building(city, x, y, kind):
    """0일에 건물을 배치하고 새 ID를 반환한다. 실패하면 입력을 보존한다."""
    validate_city(city)

    if city["day"] != 0:
        raise ValueError("건물 배치는 0일에만 가능합니다. 시나리오를 다시 선택하세요.")
    if kind not in ("house", "park"):
        raise ValueError("건물 종류는 house 또는 park여야 합니다.")

    height = len(city["grid"])
    width = len(city["grid"][0])

    if type(x) is not int or type(y) is not int:
        raise ValueError("좌표 x, y는 정수여야 합니다.")
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("지도 밖에는 건물을 배치할 수 없습니다.")

    cell = city["grid"][y][x]

    if cell["terrain"] != "land":
        raise ValueError("건물은 땅에만 놓을 수 있습니다.")
    if cell["road"]:
        raise ValueError("도로가 있는 셀에는 건물을 놓을 수 없습니다.")
    if cell["building_id"] is not None:
        raise ValueError("이미 건물이 있는 셀입니다.")

    # H/P 접두사 뒤에 가장 작은 사용 가능한 번호를 붙인다.
    prefix = "H" if kind == "house" else "P"
    number = 1

    while prefix + str(number) in city["buildings"]:
        number += 1

    ident = prefix + str(number)
    building = {"id": ident, "kind": kind, "x": x, "y": y, "status": "operating"}

    if kind == "house":
        building["population"] = 0
        building["capacity"] = 10

    # 모든 설치 조건을 확인한 뒤 두 참조를 함께 기록한다.
    city["buildings"][ident] = building
    cell["building_id"] = ident

    validate_city(city)
    return ident


def eligible(city, house):
    """건물 dict를 받아 입주 조건을 판단한다. 수용량 제한은 arrivals에서 처리한다."""
    if house["kind"] != "house" or house["status"] != "operating":
        return False
    if not city["external_power"]:
        return False

    x = house["x"]
    y = house["y"]
    road_access = False

    for nx, ny in neighbors4(city, x, y):
        if city["grid"][ny][nx]["road"]:
            road_access = True
            break

    park_access = False

    for building in city["buildings"].values():
        if building["kind"] == "park" and building["status"] == "operating":
            distance = abs(x - building["x"]) + abs(y - building["y"])
            if distance <= city["rules"]["park_radius"]:
                park_access = True
                break

    return road_access and park_access


def arrivals(city, house):
    """입력 상태를 보존하고 하루 입주량을 반환한다. 주택 인구는 수용량 이하다."""
    if not eligible(city, house):
        return 0

    remaining = house["capacity"] - house["population"]
    return min(city["rules"]["growth_per_day"], remaining)


def step(old):
    """시작 상태를 보존하고 하루 뒤의 독립적인 새 상태를 반환한다."""
    raise NotImplementedError("TODO 6: 하루를 갱신하세요.")

    # old는 하루 시작 상태입니다. deepcopy(old)로 복사한 new에 하루 뒤 상태를 기록합니다.
    # 모든 계산은 old를 기준으로 하고, 변경한 값은 new에만 기록하세요.
    # 이 역할을 섞으면 건물을 계산하는 순서에 따라 결과가 달라질 수 있습니다.
    validate_city(old)

    new = deepcopy(old)
    start_population = total_population(old)

    for ident, house in old["buildings"].items():
        if house["kind"] == "house":
            # TODO 6-A: 이 주택의 하루 뒤 인구를 new에 기록하세요.
            # .items()에서 ident는 건물 ID, house는 old에 들어 있는 건물 dict입니다.
            # TODO 5의 arrivals(old, house)로 입주량을 구하세요.
            # 그 주택의 시작 인구 house["population"]에 입주량을 더하세요.
            # 결과를 new["buildings"][ident]["population"]에 저장하세요.
            # house["population"]을 직접 바꾸면 old도 바뀌므로 주의하세요.
            pass

    rules = old["rules"]

    # TODO 6-B: 하루 뒤 예산을 계산해 new["budget"]에 저장하세요.
    # 시작 예산 old["budget"]에 세금을 더하고 하루 유지비를 한 번 빼세요.
    # 세금은 start_population * rules["tax_per_person_day"]로 계산합니다.
    # 하루 유지비는 rules["maintenance_per_day"]입니다. 규칙 값을 읽어 사용하세요.
    # 오늘 입주한 사람은 오늘 세금에 포함하지 않습니다. 시작 인구를 사용하세요.
    # 확인 예: 시작 예산 100, 시작 인구 14, 세금 3, 유지비 10이면 100 + 14 * 3 - 10 = 132.

    # TODO 6-C: old["day"]보다 1 큰 값을 new["day"]에 저장하세요.
    # 아래의 검증과 return은 이미 작성되어 있습니다. old는 그대로 두세요.

    validate_city(new)
    return new

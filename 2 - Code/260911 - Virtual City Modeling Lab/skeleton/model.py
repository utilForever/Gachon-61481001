"""
좌표는 (x, y), 셀 접근은 grid[y][x], 1 tick은 1일이다.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 뒤 단계에서 앞 단계 함수를 사용합니다.
2. pass는 코드를 작성할 빈자리입니다. 해당 위치의 안내에 따라 코드를 작성하세요.
   주석만 있는 TODO는 주석 아래에 코드를 추가하면 됩니다.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
4. 파일을 저장하고 skeleton 폴더의 터미널에서 python checks.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미완성]은 아직 남은 NotImplementedError, [실패]는 기대한 결과와 다르다는 뜻입니다.

- 데이터를 읽을 때
(x, y)는 (가로, 세로) 좌표이고, 셀은 city["grid"][y][x]로 찾습니다.
city["buildings"]는 건물 ID를 키로, 건물 정보 dict를 값으로 저장합니다.
neighbors4, total_population, eligible, arrivals는 입력을 읽기만 합니다.
place_building은 입력 도시를 직접 수정하고, step은 원본을 보존한 새 도시를 반환합니다.
"""

from copy import deepcopy

from city_data import validate_city


def neighbors4(city, x, y):
    """지도 안의 상하좌우 좌표 목록을 반환한다. 입력 좌표는 지도 안이다."""
    raise NotImplementedError("TODO 1: 이웃 셀을 구하세요.")

    height = len(city["grid"])
    width = len(city["grid"][0])
    result = []

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        # TODO 1: 현재 위치에서 한 칸 이동한 이웃 좌표를 모으세요.
        # 1. dx, dy는 이동량입니다. x에 dx를, y에 dy를 더해 nx, ny를 구하세요.
        # 2. 0 <= nx < width와 0 <= ny < height를 모두 만족하는지 확인하세요.
        # 3. 지도 안이면 result.append(...)로 좌표 튜플 (nx, ny)를 추가하세요.
        # 지도 밖 좌표는 건너뜁니다. width와 height 자체는 유효한 인덱스가 아닙니다.
        # 확인 예: (0, 0)의 이웃은 (1, 0), (0, 1) 두 개이며 순서는 상관없습니다.
        pass

    return result


def total_population(city):
    """운영 상태와 관계없이 모든 주택의 인구를 합산한다. 빈 도시이면 0이다."""
    raise NotImplementedError("TODO 2: 총인구를 계산하세요.")

    population = 0

    for building in city["buildings"].values():
        # TODO 2: 주택에 사는 사람 수를 population에 누적하세요.
        # .values()로 꺼낸 building은 ID 문자열이 아니라 건물 정보 dict입니다.
        # building["kind"]가 "house"일 때만 building["population"]을 더하세요.
        # 건물 수를 세는 것이 아닙니다. 공원은 제외하고 운영이 중지된 주택은 포함합니다.
        # 확인 예: 주택 인구가 6명, 8명이면 14, 주택이 없으면 초기값 0이 반환됩니다.
        pass

    return population


def place_building(city, x, y, kind):
    """0일에 건물을 배치하고 새 ID를 반환한다. 실패하면 입력을 보존한다."""
    raise NotImplementedError("TODO 3: 건물을 배치하세요.")

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

    # TODO 3-A: 선택한 cell에 건물을 놓아도 되는지 다음 세 조건을 검사하세요.
    # 1. cell["terrain"]이 "land"가 아니면 설치할 수 없습니다.
    # 2. cell["road"]가 True이면 이미 도로가 있으므로 설치할 수 없습니다.
    # 3. cell["building_id"]가 None이 아니면 이미 건물이 있으므로 설치할 수 없습니다.
    # 각 경우에 raise ValueError("설치할 수 없는 이유")로 함수를 중단하세요.
    # 실패한 설치는 도시를 바꾸면 안 됩니다. 이 검사에서는 데이터를 읽기만 하세요.

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

    # TODO 3-B: 위에서 만든 building과 ident를 두 곳에 연결해 저장하세요.
    # 1. city["buildings"]에 ident를 키로, building을 값으로 등록하세요.
    # 2. 선택한 cell의 "building_id"에는 같은 ident를 저장하세요.
    # 셀에 넣는 값은 건물 dict 전체가 아니라 "H1" 같은 ID 문자열입니다.
    # 두 곳을 모두 기록해야 아래 validate_city(city)를 통과할 수 있습니다.
    # ID 만들기, 주택 초기값 설정, 마지막 return은 이미 작성되어 있습니다.

    validate_city(city)
    return ident


def eligible(city, house):
    """건물 dict를 받아 입주 조건을 판단한다. 수용량 제한은 arrivals에서 처리한다."""
    raise NotImplementedError("TODO 4: 입주 조건을 판단하세요.")

    # TODO 4-A: 입주 대상이 될 수 없는 경우를 먼저 제외하세요.
    # house는 건물 정보 dict입니다. 주택이 아닌 건물이 전달될 수도 있습니다.
    # house["kind"]가 "house"가 아니거나 house["status"]가 "operating"이 아니면
    # False를 반환하세요. city["external_power"]가 False일 때도 False를 반환하세요.
    # 이 조건들을 통과하면 아래에서 도로와 공원도 확인해야 하므로 계속 진행합니다.

    x = house["x"]
    y = house["y"]
    road_access = False

    for nx, ny in neighbors4(city, x, y):
        # TODO 4-B: 상하좌우 이웃 중 도로가 하나라도 있는지 확인하세요.
        # TODO 1의 neighbors4가 돌려준 (nx, ny)로 city["grid"][ny][nx]를 읽으세요.
        # 그 셀의 "road"가 True이면 road_access를 True로 바꾸세요.
        # 하나를 찾으면 break로 반복을 끝내도 됩니다. 대각선 도로는 세지 않습니다.
        # 도로가 없는 다른 셀을 만났다고 road_access를 다시 False로 바꾸지 마세요.
        pass

    park_access = False

    for building in city["buildings"].values():
        # TODO 4-C: 허용 거리 안에 운영 중인 공원이 하나라도 있는지 확인하세요.
        # 1. building["kind"]가 "park"이고 "status"가 "operating"인 건물만 살펴보세요.
        # 2. 주택 (x, y)와 공원 (building["x"], building["y"])의 거리를 구하세요.
        #    가로 차이의 절댓값 + 세로 차이의 절댓값이며 abs(...)를 사용합니다.
        #    예: (1, 1)에서 (2, 2)까지는 가로 1칸 + 세로 1칸 = 2칸입니다.
        # 3. 거리가 city["rules"]["park_radius"] 이하이면 park_access를 True로 바꾸세요.
        # 반경과 같은 거리도 포함합니다. 하나를 찾으면 break로 끝내도 됩니다.
        # 마지막 return은 도로와 공원 조건이 모두 True일 때만 True를 반환합니다.
        pass

    return road_access and park_access


def arrivals(city, house):
    """입력 상태를 보존하고 하루 입주량을 반환한다. 주택 인구는 수용량 이하다."""
    raise NotImplementedError("TODO 5: 입주량을 계산하세요.")

    # TODO 5: 오늘 들어올 수 있는 사람 수를 정수로 반환하세요.
    # 1. TODO 4의 eligible(city, house)가 False이면 바로 0을 반환하세요.
    # 2. 입주 가능하면 house["capacity"]에서 house["population"]을 빼 빈자리를 구하세요.
    # 3. 빈자리와 city["rules"]["growth_per_day"] 중 작은 값을 min(...)으로 반환하세요.
    # 확인 예: 하루 최대 2명일 때 빈자리가 4명이면 2, 1명이면 1, 0명이면 0입니다.
    # 여기서는 입주량만 계산합니다. house의 인구는 바꾸지 말고 TODO 6에서 반영하세요.


def step(old):
    """시작 상태를 보존하고 하루 뒤의 독립적인 새 상태를 반환한다."""
    validate_city(old)

    new = deepcopy(old)
    start_population = total_population(old)

    for ident, house in old["buildings"].items():
        if house["kind"] == "house":
            incoming = arrivals(old, house)
            new["buildings"][ident]["population"] = house["population"] + incoming

    rules = old["rules"]

    # 세금은 하루 시작 인구를 기준으로 계산한다.
    new["budget"] = (
        old["budget"]
        + start_population * rules["tax_per_person_day"]
        - rules["maintenance_per_day"]
    )
    new["day"] = old["day"] + 1

    validate_city(new)
    return new

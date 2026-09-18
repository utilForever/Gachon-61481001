"""
좌표는 (x, y), 셀 접근은 grid[y][x], 1 tick은 1일이다.

- 실습 진행 방법
1. TODO 1부터 7까지 순서대로 작성하세요. 뒤 단계에서 앞 단계 함수를 사용합니다.
2. TODO 주석 아래에 코드를 작성하세요. TODO 7-A~D는 임시 값을 계산 결과로 바꿉니다.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
4. 파일을 저장하고 README.md가 있는 폴더의 터미널에서
   python skeleton/checks.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~7로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미완성]은 아직 남은 NotImplementedError, [실패]는 기대한 결과와 다르다는 뜻입니다.

- 데이터를 읽을 때
(x, y)는 (가로, 세로) 좌표이고, 셀은 city["grid"][y][x]로 찾습니다.
city["buildings"]는 건물 ID를 키로, 건물 정보 dict를 값으로 저장합니다.
조회 / 계산 함수는 입력을 읽기만 합니다. 입주 요청과 실제 입주 배정은 구분합니다.
place_building은 입력 도시를 직접 수정하고, step은 원본을 보존한 새 도시를 반환합니다.
neighbors4, total_population, place_building은 제공된 함수를 그대로 사용하세요.
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


def can_build(city, x, y, kind):
    """셀과 용도지역을 확인해 건설 가능 여부를 반환한다. 입력은 수정하지 않는다."""
    raise NotImplementedError("TODO 1: 용도지역과 건물 종류의 대응을 확인하세요.")

    if type(x) is not int or type(y) is not int:
        return False
    if not (0 <= y < len(city["grid"]) and 0 <= x < len(city["grid"][0])):
        return False

    cell = city["grid"][y][x]
    if cell["terrain"] != "land" or cell["road"] or cell["building_id"] is not None:
        return False

    # TODO 1: 이 셀의 용도지역에 요청한 종류의 건물을 놓을 수 있는지 판단하세요.
    # 입력: kind는 건물 종류이고, cell["zone"]은 위에서 찾은 셀의 용도지역입니다.
    # 위 코드는 이미 좌표, 땅 여부, 도로, 기존 건물을 검사했습니다.
    # 1. 다음 대응을 확인하세요: house → "R", shop → "C", factory → "I".
    #    park는 용도를 지정하지 않은 셀(None)에만 놓을 수 있습니다.
    # 2. 대응이 맞으면 True, 맞지 않거나 모르는 건물 종류이면 False를 반환하세요.
    # 확인 예: "R"인 셀에 house는 True, factory는 False입니다.
    # 여기서는 가능 여부만 판단합니다. 셀을 바꾸거나 실제 건물을 만들지 마세요.
    # 주변 도로와 입주 수요는 이후 단계에서 사용하므로 여기서는 검사하지 않습니다.


def occupancy(building):
    """건물의 점유율을 반환한다. 공원이거나 수용량이 0이면 None이다."""
    raise NotImplementedError("TODO 2: 점유율을 계산하세요.")

    # TODO 2: 건물 하나의 점유율(사용 중인 인원 / 수용 인원)을 반환하세요.
    # 입력: building은 건물 하나의 dict입니다. 종류는 building["kind"]로 확인합니다.
    # 1. 공원(park)이면 None을 반환하세요. 공원에는 capacity 항목이 없으므로
    #    수용량을 읽기 전에 종류부터 확인해야 합니다.
    # 2. 나머지 건물도 capacity가 0이면 나눗셈을 하지 말고 None을 반환하세요.
    # 3. 주택(house)은 population, 상점(shop)과 공장(factory)은 workers를
    #    capacity로 나누세요. /를 사용하며, 건물의 값은 수정하지 않습니다.
    # 확인 예: 10명 중 6명이 거주하면 0.6, 수용량 10인 공실이면 0입니다.
    # None은 "점유율을 정의할 수 없음"입니다. 60이나 "60%"로 바꾸지는 마세요.
    # 화면에 퍼센트로 표시하는 일은 GUI가 담당합니다.


def road_access(city, building):
    """건물의 상하좌우에 도로가 하나라도 있는지 판단한다. 대각선은 제외한다."""
    raise NotImplementedError("TODO 3: 도로 접근성을 확인하세요.")

    # TODO 3: 건물의 상하좌우 중 한 곳이라도 도로가 있으면 True를 반환하세요.
    # 1. neighbors4(city, building["x"], building["y"])로 이웃 좌표를 구하세요.
    #    neighbors4는 지도 안에 있는 (x, y) 좌표만 돌려줍니다.
    # 2. 각 (nx, ny)에 대해 city["grid"][ny][nx]["road"]를 확인하세요.
    # 3. 도로를 찾으면 True, 모든 이웃을 확인해도 없으면 False를 반환하세요.
    # 주의: 첫 이웃에 도로가 없다고 바로 False를 반환하면 나머지를 놓칩니다.
    # 대각선과 건물 자신의 셀은 검사하지 않습니다. 지도 끝도 neighbors4가 처리합니다.


def environment_score(city, building):
    """운영 중인 상하좌우 공원마다 +2, 공장마다 -3을 합산한 점수를 반환한다."""
    raise NotImplementedError("TODO 4: 주변 환경 점수를 계산하세요.")

    # TODO 4: 건물 주변의 환경 점수 E를 정수로 반환하세요.
    # 1. 점수를 0에서 시작하고, TODO 3처럼 neighbors4로 상하좌우를 순회하세요.
    # 2. 이웃 셀의 building_id를 읽으세요. None이면 건물이 없으므로 건너뜁니다.
    # 3. ID가 있으면 city["buildings"][ID]에서 이웃 건물의 정보를 찾으세요.
    #    status가 "operating"인 건물만 계산합니다. 건설 중이거나 닫혔으면 건너뜁니다.
    # 4. park마다 2를 더하고, factory마다 3을 빼세요. 다른 종류는 점수를 바꾸지 않습니다.
    # 모든 이웃을 확인한 뒤 합계를 반환하세요. 셀이나 건물의 값은 수정하지 않습니다.
    # 확인 예: 운영 중인 공원 1개와 공장 1개가 인접하면 E는 2 - 3 = -1입니다.


def growth_request(city, house):
    """입주 요청량과 전출량을 반환한다. 실제 수요 배정은 allocate_arrivals에서 한다."""
    raise NotImplementedError("TODO 5: 입주 요청량과 전출량을 계산하세요.")

    # TODO 5: 주택 하나의 (입주 요청량, 전출량)을 정수 2개의 튜플로 반환하세요.
    # 아직 인구를 바꾸는 단계가 아닙니다. "몇 명이 들어오거나 나가려는지"만 계산합니다.
    # 1. house의 kind가 "house"가 아니거나 status가 "operating"이 아니면 (0, 0).
    # 2. TODO 3의 road_access와 TODO 4의 environment_score로 도로 여부와 E를 구하세요.
    # 3. 다음 조건을 위에서부터 판단하세요. 도로가 없으면 좋은 환경이어도 전출합니다.
    #    - 도로 없음 또는 E <= -1: 입주 요청은 0, 전출은 최대 1명입니다.
    #      현재 population이 0이면 전출도 0이어야 합니다.
    #    - 도로 있음, E == 0: 변화가 없으므로 (0, 0)입니다.
    #    - 도로 있음, E >= 1: 전출은 0, 입주 요청은 하루 한도와 빈자리 중 작은 값입니다.
    #      하루 한도는 city["rules"]["growth_per_day"] (현재 2명),
    #      빈자리는 house["capacity"]에서 house["population"]을 뺀 값입니다.
    # 확인 예: 도로가 있고 E=2, 인구 9명 / 수용량 10명이면 (1, 0)입니다.
    # city["demand"]가 0이어도 이 요청은 1입니다. 실제 입주 인원은 TODO 6에서 정합니다.


def allocate_arrivals(requests, demand):
    """ID 순서로 대기 인구를 배정한 새 dict를 반환한다. 입력 요청량은 보존한다."""
    raise NotImplementedError("TODO 6: 입주 대기 인구를 배정하세요.")

    # TODO 6: 한정된 입주 대기 인구를 주택들에 나누어 배정하세요.
    # 입력: requests는 {건물 ID: 입주 요청 인원}, demand는 도시 전체의 대기 인원입니다.
    # 반환: {건물 ID: 실제 입주 인원} 형태의 새 dict입니다. requests는 수정하지 마세요.
    # 1. 결과를 담을 빈 dict와, demand에서 시작하는 "남은 대기 인원"을 준비하세요.
    # 2. sorted(requests)로 ID를 오름차순 정렬한 뒤 하나씩 처리하세요.
    # 3. 해당 주택의 요청 인원과 남은 대기 인원 중 작은 값을 배정하세요.
    # 4. 결과 dict에 배정량을 기록하고, 남은 대기 인원에서 그만큼 빼세요.
    # 확인 예: requests={"B": 2, "A": 2}, demand=3이면 {"A": 2, "B": 1}입니다.
    # 대기 인원이 다 떨어져도 나머지 ID에 0을 기록하세요. 모든 요청 ID가 필요합니다.
    # 요청이 없는 빈 dict를 받았다면 결과도 빈 dict입니다.


def step(old):
    """시작 상태를 보존하고 하루 뒤의 독립적인 새 상태를 반환한다."""
    raise NotImplementedError("TODO 7: 하루를 갱신하세요.")

    # TODO 7: TODO 5~6을 연결해 하루 뒤의 새 도시를 완성하세요.
    # old는 하루 시작 상태, new는 deepcopy로 만드는 독립적인 복사본입니다.
    # 모든 주택은 같은 시작 상태를 기준으로 판단해야 합니다. old는 수정하지 마세요.
    # 아래 TODO 7-A~D의 임시 값 (0, 0), {}, 0을 실제 계산 결과로 바꾸세요.
    # 네 부분을 완성하면 함수 맨 위의 raise 문을 삭제하세요. 마지막 return은 제공됩니다.
    # 세금 계산, 날짜 증가, 검증 코드는 이미 준비되어 있으므로 그대로 두세요.
    # 확인 예: 기본 도시의 첫날 결과는 A=8명, B=9명, 대기=0명, 예산=132입니다.
    validate_city(old)

    new = deepcopy(old)
    start_population = total_population(old)
    requests = {}
    departures = {}

    for ident, house in old["buildings"].items():
        if house["kind"] == "house":
            # TODO 7-A: growth_request에 old와 현재 house를 전달하세요.
            # 반환된 (입주 요청량, 전출량)을 아래 두 dict의 같은 ident에 나눠 담으세요.
            # 여기서는 요청과 전출량만 모읍니다. 실제 입주 배정은 모든 요청을 모은 뒤 합니다.
            requests[ident], departures[ident] = (0, 0)

    # TODO 7-B: allocate_arrivals에 모아 둔 requests와 old["demand"]를 전달하세요.
    # 반환된 dict를 allocated에 담으세요. 요청 인원과 실제 입주 인원은 다를 수 있습니다.
    allocated = {}

    for ident in requests:
        # TODO 7-C: 이 주택의 시작 인구는 old["buildings"][ident]["population"]입니다.
        # 여기에 allocated[ident]를 더하고 departures[ident]를 빼서 new에 기록하세요.
        # requests는 희망 인원입니다. 인구에는 실제 배정된 allocated를 사용해야 합니다.
        new["buildings"][ident]["population"] = 0

    # TODO 7-D: 도시 전체의 대기 인원과 누적 전출 인원을 갱신하세요.
    # new의 demand는 old의 demand에서 실제 입주 인원의 합계를 뺀 값입니다.
    # new의 departed는 old의 departed에 이번 전출 인원의 합계를 더한 값입니다.
    # 힌트: dict.values()로 인원들을 꺼내고 sum으로 합칠 수 있습니다.
    # 전출자는 도시를 떠납니다. 대기 인원으로 되돌리지 마세요.
    new["demand"] = 0
    new["departed"] = 0

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
    """0일에 용도지역에 맞는 건물을 배치하고 새 ID를 반환한다. 실패하면 입력을 보존한다."""
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

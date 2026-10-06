"""
좌표는 (x, y), 셀 접근은 grid[y][x], 교통 관측의 1 tick은 1분이다.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 지표 계산, 기록, 상태 보관을 차례로 완성합니다.
2. pass는 코드를 작성할 빈자리입니다. 해당 위치의 안내에 따라 코드를 작성하세요.
   주석만 있는 TODO는 주석 아래에 코드를 추가하면 됩니다.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
4. 파일을 저장하고 skeleton 폴더의 터미널에서 python checks.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미완성]은 아직 남은 NotImplementedError, [실패]는 기대한 결과와 다르다는 뜻입니다.
5. 6단계까지 완성하면 python checks.py --integration으로 저장과 복원까지 확인하세요.

- 데이터를 읽을 때
city["buildings"]의 값은 건물 정보 dict이며, 주택의 population은 거주 인구입니다.
trips는 주민 한 명마다 한 건씩 준비됩니다. time_min=None은 도달 불가, 0은 유효한 시간입니다.
observations의 duration_min은 구간 길이이고, queue는 그 구간 시작 시점의 대기 차량 수입니다.
TODO 1~4는 입력을 읽기만 합니다. TODO 5는 history에 새 행을 추가하고 kpis는 보존합니다.
TODO 6은 원본을 보존한 독립적인 스냅샷을 반환합니다. 중첩 자료도 복사해야 합니다.
"""

from copy import deepcopy

from model import neighbors4


def summarize_city(city):
    """주택 인구와 공원을 제외한 건물 수를 반환한다. 운영 상태와 관계없이 센다."""
    raise NotImplementedError("TODO 1: 인구와 건물 수를 계산하세요.")

    population = 0
    building_count = 0

    for building in city["buildings"].values():
        # TODO 1: 인구와 건물 수를 각각 누적하세요.
        # .values()로 꺼낸 building은 ID 문자열이 아니라 건물 정보 dict입니다.
        # 1. kind가 "house"이면 population에 그 주택의 population을 더하세요.
        # 2. kind가 "park"가 아니면 building_count를 1 늘리세요.
        # 주택은 두 집계에 모두 포함합니다. 두 번째 조건을 elif로 연결하지 마세요.
        # 일자리 수는 인구에 더하지 않습니다. 폐쇄 / 건설 중인 건물도 집계합니다.
        # 확인 예: 인구 6명의 주택, 상점, 공장, 공원이 있으면 인구 6명, 건물 3동입니다.
        pass

    return {"population": population, "building_count": building_count}


def summarize_trips(trips, limit):
    """주민별 접근성과 평균 시간을 반환한다. 각 계산의 분모가 0이면 None이다."""
    raise NotImplementedError("TODO 2: 접근성과 평균 이동 시간을 계산하세요.")

    reachable = 0
    within_limit = 0
    total_time = 0

    for trip in trips:
        # TODO 2: 도달 가능한 인원과 그들의 이동시간을 누적하세요.
        # trip["time_min"]을 time에 담고 다음 조건을 확인하세요.
        # 1. time이 None이 아닐 때만 reachable을 1 늘리고 total_time에 time을 더하세요.
        # 2. 그중 time이 limit 이하이면 within_limit도 1 늘리세요.
        # if time처럼 참 / 거짓으로만 판단하면 유효한 시간 0을 놓치게 됩니다.
        # 기준과 같은 시간도 포함합니다. 도달 불가인 None은 시간 합에 더하지 않습니다.
        # 확인 예: [0, 4, 8, None], 기준 4분이면 도달 3명, 기준 이내 2명, 시간 합 12분입니다.
        pass

    planned = len(trips)

    # 접근성은 전체 예정 인원, 평균은 도달 가능한 인원으로 나눈다.
    # 반환 형식과 빈 분모 처리는 제공한다. 위의 세 누적값을 계산해 연결하세요.
    return {
        "planned_trips": planned,
        "reachable_trips": reachable,
        "unreachable_trips": planned - reachable,
        "within_limit_trips": within_limit,
        "accessibility_ratio": within_limit / planned if planned else None,
        "mean_time_min": total_time / reachable if reachable else None,
    }


def find_developable_cells(city, protected):
    """도로에 인접한 개발 가능 셀을 행 / 열 순서로 한 번씩 반환한다. 입력은 보존한다."""
    raise NotImplementedError("TODO 3: 개발 가능한 셀을 구하세요.")

    result = []

    for y, row in enumerate(city["grid"]):
        for x, cell in enumerate(row):
            # TODO 3-A: 개발할 수 없는 셀을 먼저 건너뛰세요.
            # terrain이 "land"가 아니거나, road가 True이거나,
            # building_id가 None이 아니거나, (x, y)가 protected에 있으면 제외합니다.
            # 네 조건 중 하나라도 해당하면 continue로 다음 셀을 확인하세요.
            # 여기서는 셀의 정보를 읽기만 합니다. 용도지역 zone은 추가 조건이 아닙니다.

            for nx, ny in neighbors4(city, x, y):
                # TODO 3-B: 상하좌우에 도로가 하나라도 있으면 현재 셀을 추가하세요.
                # 이웃은 city["grid"][ny][nx]로 읽고 그 셀의 road를 확인합니다.
                # 도로가 있으면 result에 이웃이 아닌 현재 좌표 (x, y)를 추가하세요.
                # break로 이웃 탐색을 끝내야 도로가 여러 개여도 한 번만 추가됩니다.
                # 대각선 도로는 포함하지 않습니다. 지도 경계는 neighbors4가 처리합니다.
                pass

    return result


def summarize_congestion(observations, threshold):
    """관측 시간, 혼잡 시간, 최대 대기열을 반환한다. 관측이 없으면 0 / 0 / None이다."""
    raise NotImplementedError("TODO 4: 혼잡 지속 시간을 계산하세요.")

    observed = 0
    congested = 0
    peak = None

    for observation in observations:
        # TODO 4: 이 구간의 길이와 대기 차량 수를 세 집계에 반영하세요.
        # observation["duration_min"]을 duration, observation["queue"]를 queue에 담으세요.
        # 1. observed에 duration을 더하세요. 구간마다 1을 더하는 것이 아닙니다.
        # 2. queue가 threshold 이상이면 congested에도 duration을 더하세요.
        # 3. peak가 None이거나 queue가 기존 peak보다 크면 peak를 queue로 바꾸세요.
        # None과 숫자를 바로 비교하지 않도록 첫 관측인지 먼저 확인하세요.
        # 확인 예: 길이 [2, 3, 1], 대기 [4, 5, 9], 기준 5이면 관측 6분 / 혼잡 4분 / 최대 9대.
        pass

    return {
        "observed_minutes": observed,
        "congested_minutes": congested,
        "peak_queue": peak,
    }


def append_history(history, minute, kpis):
    """새 시각의 독립적인 기록을 추가하면 True, 같은 시각이 이미 있으면 False이다."""
    raise NotImplementedError("TODO 5: 시계열 기록을 추가하세요.")

    for row in history:
        # TODO 5-A: row의 minute이 입력 minute과 같으면 바로 False를 반환하세요.
        # 이전 행을 덮어쓰거나 삭제하지 않습니다. 전체 기록에서 중복 시각을 확인하세요.
        # 확인 예: 0분을 기록한 뒤 0분으로 다시 호출해도 기록은 한 행이어야 합니다.
        pass

    # TODO 5-B: 새 행을 만든 뒤 history에 추가하세요.
    # 1. deepcopy(kpis)로 원본과 독립적인 row를 만드세요.
    # 2. 새 row의 "minute"에 입력 minute을 저장하세요.
    # 3. history.append(...)로 그 행을 추가하세요. 마지막 True 반환은 제공되어 있습니다.
    # kpis 자체에 minute을 넣거나 그대로 추가하면 원본과 기록이 같은 자료를 공유합니다.
    # 확인 예: 나중에 원본의 developable_cells를 비워도 과거 기록의 좌표는 남아야 합니다.

    return True


def make_snapshot(city, transport, history, settings, observations):
    """도시, 교통, 기록, 설정, 관측값을 원본과 독립적인 스냅샷으로 반환한다."""
    raise NotImplementedError("TODO 6: 도시 상태를 보관하세요.")

    snapshot = {}

    # TODO 6: snapshot에 저장할 형식과 다섯 항목을 담으세요.
    # 1. "format"에는 문자열 "virtual-city-kpi-v1"을 저장하세요.
    # 2. "city", "transport", "history", "settings", "observations"에는
    #    각각 같은 이름의 인자로 받은 값을 저장하세요.
    # 아래 deepcopy가 딕셔너리 전체를 복사합니다. 파일에 쓰는 일은 제공 코드가 담당합니다.
    # 확인 예: 원본의 대기열이나 기록을 바꿔도 스냅샷에는 저장 당시의 값이 남아야 합니다.
    # 반대로 스냅샷의 중첩 자료를 바꿔도 원본은 그대로여야 합니다.

    return deepcopy(snapshot)

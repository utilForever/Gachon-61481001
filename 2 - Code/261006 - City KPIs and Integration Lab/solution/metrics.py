"""
인구와 건물 수, 통근 접근성과 이동시간, 개발 가능 토지, 혼잡 시간의 집계 규칙.

좌표는 (x, y), 셀 접근은 grid[y][x], 교통 관측의 1 tick은 1분이다.
조회 / 계산 함수는 입력을 읽기만 한다. time_min=None은 도달 불가, 0은 유효한 시간이다.
append_history는 history에 독립적인 행을 추가하고, make_snapshot은 원본을 보존한다.
"""

from copy import deepcopy

from model import neighbors4


def summarize_city(city):
    """주택 인구와 공원을 제외한 건물 수를 반환한다. 운영 상태와 관계없이 센다."""
    population = 0
    building_count = 0

    for building in city["buildings"].values():
        if building["kind"] == "house":
            population += building["population"]
        if building["kind"] != "park":
            building_count += 1

    return {"population": population, "building_count": building_count}


def summarize_trips(trips, limit):
    """주민별 접근성과 평균 시간을 반환한다. 각 계산의 분모가 0이면 None이다."""
    reachable = 0
    within_limit = 0
    total_time = 0

    for trip in trips:
        time = trip["time_min"]
        if time is not None:
            reachable += 1
            total_time += time
            if time <= limit:
                within_limit += 1

    planned = len(trips)

    # 접근성은 전체 예정 인원, 평균 시간은 도달 가능한 인원을 기준으로 한다.
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
    result = []

    for y, row in enumerate(city["grid"]):
        for x, cell in enumerate(row):
            if (
                cell["terrain"] != "land"
                or cell["road"]
                or cell["building_id"] is not None
                or (x, y) in protected
            ):
                continue

            for nx, ny in neighbors4(city, x, y):
                if city["grid"][ny][nx]["road"]:
                    result.append((x, y))
                    break

    return result


def summarize_congestion(observations, threshold):
    """관측 시간, 혼잡 시간, 최대 대기열을 반환한다. 관측이 없으면 0 / 0 / None이다."""
    observed = 0
    congested = 0
    peak = None

    for observation in observations:
        duration = observation["duration_min"]
        queue = observation["queue"]
        observed += duration
        if queue >= threshold:
            congested += duration
        if peak is None or queue > peak:
            peak = queue

    return {
        "observed_minutes": observed,
        "congested_minutes": congested,
        "peak_queue": peak,
    }


def append_history(history, minute, kpis):
    """새 시각의 독립적인 기록을 추가하면 True, 같은 시각이 이미 있으면 False이다."""
    for row in history:
        if row["minute"] == minute:
            return False

    row = deepcopy(kpis)
    row["minute"] = minute
    history.append(row)
    return True


def make_snapshot(city, transport, history, settings, observations):
    """도시, 교통, 기록, 설정, 관측값을 원본과 독립적인 스냅샷으로 반환한다."""
    # 중첩된 자료도 복사해야 저장 시점의 상태가 이후 변화와 분리된다.
    return deepcopy(
        {
            "format": "virtual-city-kpi-v1",
            "city": city,
            "transport": transport,
            "history": history,
            "settings": settings,
            "observations": observations,
        }
    )

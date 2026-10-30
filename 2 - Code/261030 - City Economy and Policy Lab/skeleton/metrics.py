"""도시 / 통근 / 혼잡 지표 계산과 독립적인 기록·스냅샷 생성."""

from copy import deepcopy

from model import neighbors4


def summarize_city(city):
    """전체 주택 인구와 공원을 제외한 건물 수를 합산한다."""
    population = 0
    building_count = 0

    for building in city["buildings"].values():
        if building["kind"] == "house":
            population += building["population"]
        if building["kind"] != "park":
            building_count += 1

    return {"population": population, "building_count": building_count}


def summarize_trips(trips, limit):
    """통근 접근성 비율과 도달 가능한 사람들의 평균 시간(분)을 반환한다."""
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
    """보전 대상이 아니며 도로에 인접한 비어 있는 땅의 좌표 목록을 반환한다."""
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
    """관측 구간 길이로 총 관측 시간과 혼잡 시간(분), 최대 대기열을 집계한다."""
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
    """중복 시각은 건너뛰고 독립 복사한 지표를 추가한다. 추가 여부를 반환한다."""
    for row in history:
        if row["minute"] == minute:
            return False

    row = deepcopy(kpis)
    row["minute"] = minute
    history.append(row)
    return True


def make_snapshot(city, transport, history, settings, observations):
    """도시, 교통, 기록과 설정의 중첩 자료까지 복사한 스냅샷을 반환한다."""
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

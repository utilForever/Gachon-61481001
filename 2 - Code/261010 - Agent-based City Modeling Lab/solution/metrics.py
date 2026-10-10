"""인구 / 통근 / 개발 가능 토지 / 혼잡 지표 계산과 독립적인 기록 생성."""

from copy import deepcopy

from model import neighbors4


def summarize_city(city):
    population = 0
    building_count = 0

    for building in city["buildings"].values():
        if building["kind"] == "house":
            population += building["population"]
        if building["kind"] != "park":
            building_count += 1

    return {"population": population, "building_count": building_count}


def summarize_trips(trips, limit):
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
    for row in history:
        if row["minute"] == minute:
            return False

    row = deepcopy(kpis)
    row["minute"] = minute
    history.append(row)

    return True


def make_snapshot(city, transport, history, settings, observations):
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

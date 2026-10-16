"""
서비스 권역, 병원 대기열, 전력 / 물 / 폐기물, 오염물질 이동 규칙.

서비스의 1 tick은 1시간이고, 병원까지의 이동 시간은 분으로 전달된다.
여섯 함수는 입력을 읽기만 하고 새 결과를 반환한다. 입력 목록과 딕셔너리는 보존한다.
전력은 kW, 에너지는 kWh, 물은 m³, 폐기물은 t 단위를 사용한다.
오염물질 이동량은 모두 같은 시작 상태에서 계산한다.
"""


def service_coverage(travel_minutes, populations, limit_minutes):
    """이동 시간이 기준 이하인 지역과 인구를 요약한다. 전체 인구가 0이면 비율은 0이다."""
    covered = []
    covered_population = 0
    unreachable_population = 0

    for area, population in populations.items():
        minutes = travel_minutes[area]
        if minutes is None:
            unreachable_population += population
        elif minutes <= limit_minutes:
            covered.append(area)
            covered_population += population

    total_population = sum(populations.values())
    ratio = covered_population / total_population if total_population else 0
    return {
        "covered": covered,
        "population": covered_population,
        "ratio": ratio,
        "unreachable_population": unreachable_population,
    }


def advance_queue(queue, arrivals, capacity):
    """기존 대기와 새 요청에서 실제 진료 인원과 다음 시간의 대기 인원을 계산한다."""
    served = min(queue + arrivals, capacity)
    return {"served": served, "queue": queue + arrivals - served}


def allocate_power(supply_kw, demands_kw, priority):
    """우선순위대로 시설별 전력을 배분한다. 수요와 남은 공급량을 초과하지 않는다."""
    allocated = {}
    remaining = supply_kw
    for facility in priority:
        allocated[facility] = min(demands_kw[facility], remaining)
        remaining -= allocated[facility]

    return allocated


def update_water(stored_m3, inflow_m3, demand_m3, capacity_m3):
    """유입 후 급수하고 다음 저장량, 공급량, 미충족 수요, 넘침을 m³ 단위로 반환한다."""
    available = stored_m3 + inflow_m3
    supplied = min(demand_m3, available)
    remaining = available - supplied
    overflow = max(0, remaining - capacity_m3)

    return {
        "stored": min(remaining, capacity_m3),
        "supplied": supplied,
        "unmet": demand_m3 - supplied,
        "overflow": overflow,
    }


def update_waste(city_t, plant_t, generated_t, collection_t, treatment_t):
    """도시의 폐기물을 수거한 뒤 시설에서 처리하고 남은 양을 t 단위로 반환한다."""
    collected = min(city_t + generated_t, collection_t)
    processed = min(plant_t + collected, treatment_t)

    return {
        "city": city_t + generated_t - collected,
        "plant": plant_t + collected - processed,
        "collected": collected,
        "processed": processed,
    }


def transport_pollution(amounts, move_ratio, removal_ratio):
    """동쪽 이동과 제거를 반영한 새 목록을 반환한다. 이동량은 원본에서 계산한다."""
    # 이동량은 모두 갱신 전 상태에서 계산한다. 마지막 셀에서는 경계 밖으로 이동시키지 않는다.
    moved = amounts.copy()
    for index in range(len(amounts) - 1):
        transfer = amounts[index] * move_ratio
        moved[index] -= transfer
        moved[index + 1] += transfer

    return [amount * (1 - removal_ratio) for amount in moved]

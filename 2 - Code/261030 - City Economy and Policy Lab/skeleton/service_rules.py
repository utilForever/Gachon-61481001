"""서비스 권역, 대기열, 전력 / 물 / 폐기물과 오염물질의 갱신 규칙.

입력을 직접 수정하지 않고 계산 결과를 반환한다.
전력은 kW, 물은 m³, 폐기물은 t이며, 오염량은 학습용 단위이다.
"""


def service_coverage(travel_minutes, populations, limit_minutes):
    """시간 기준 이내의 지역과 인구 비율, 도로로 도달할 수 없는 인구를 반환한다."""
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
    """기존 대기와 신규 요청을 합쳐 처리량과 남은 대기 인원을 반환한다."""
    served = min(queue + arrivals, capacity)
    return {"served": served, "queue": queue + arrivals - served}


def allocate_power(supply_kw, demands_kw, priority):
    """우선순위에 따라 시설별 수요 한도 안에서 전력(kW)을 배분한다."""
    allocated = {}
    remaining = supply_kw
    for facility in priority:
        allocated[facility] = min(demands_kw[facility], remaining)
        remaining -= allocated[facility]

    return allocated


def update_water(stored_m3, inflow_m3, demand_m3, capacity_m3):
    """급수 후 저장량, 공급량, 부족량과 넘친 물의 양(m³)을 반환한다."""
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
    """발생 / 수거 / 처리 순서로 도시와 처리시설의 폐기물 잔량(t)을 계산한다."""
    collected = min(city_t + generated_t, collection_t)
    processed = min(plant_t + collected, treatment_t)
    return {
        "city": city_t + generated_t - collected,
        "plant": plant_t + collected - processed,
        "collected": collected,
        "processed": processed,
    }


def transport_pollution(amounts, move_ratio, removal_ratio):
    """동쪽 셀로 동시에 이동한 뒤 제거율을 적용한 새 오염량 목록을 반환한다."""
    # 이동량은 모두 갱신 전 상태에서 계산한다. 마지막 셀에서는 경계 밖으로 이동시키지 않는다.
    moved = amounts.copy()
    for index in range(len(amounts) - 1):
        transfer = amounts[index] * move_ratio
        moved[index] -= transfer
        moved[index + 1] += transfer

    return [amount * (1 - removal_ratio) for amount in moved]

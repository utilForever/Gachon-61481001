"""서비스 권역, 대기열, 전력 / 급수 / 폐기물과 오염 이동을 계산하는 규칙."""


def service_coverage(travel_minutes, populations, limit_minutes):
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
    served = min(queue + arrivals, capacity)
    return {"served": served, "queue": queue + arrivals - served}


def allocate_power(supply_kw, demands_kw, priority):
    allocated = {}
    remaining = supply_kw

    for facility in priority:
        allocated[facility] = min(demands_kw[facility], remaining)
        remaining -= allocated[facility]

    return allocated


def update_water(stored_m3, inflow_m3, demand_m3, capacity_m3):
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
    collected = min(city_t + generated_t, collection_t)
    processed = min(plant_t + collected, treatment_t)

    return {
        "city": city_t + generated_t - collected,
        "plant": plant_t + collected - processed,
        "collected": collected,
        "processed": processed,
    }


def transport_pollution(amounts, move_ratio, removal_ratio):
    # 이동량은 모두 갱신 전 상태에서 계산한다. 마지막 셀에서는 경계 밖으로 이동시키지 않는다.
    moved = amounts.copy()

    for index in range(len(amounts) - 1):
        transfer = amounts[index] * move_ratio
        moved[index] -= transfer
        moved[index + 1] += transfer

    return [amount * (1 - removal_ratio) for amount in moved]

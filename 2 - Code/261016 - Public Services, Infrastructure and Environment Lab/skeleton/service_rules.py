"""
서비스 권역, 병원 대기열, 전력 / 물 / 폐기물, 오염물질 이동 규칙.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 각 함수의 설명과 확인 예를 읽으세요.
2. pass는 코드를 작성할 빈자리입니다. 번호를 붙인 주석에 따라 코드를 작성하세요.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   return 아래에 남아 있어도 화면의 미구현 검사에서 감지됩니다.
4. 파일을 저장하고 skeleton 폴더의 터미널에서 python checks_services.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미구현]은 남은 NotImplementedError, [실패]는 기대값 불일치나 실행 오류입니다.
5. 모두 완성하면 python checks_services.py --integration으로 통합 동작을 확인하세요.

- 데이터를 읽을 때
서비스의 1 tick은 1시간이다. 병원까지의 이동 시간은 분으로 전달된다.
지역 / 시설 이름은 딕셔너리의 키이다. 이동 시간 None은 경로가 없다는 뜻이다.
여섯 함수는 입력을 읽기만 하고 새 결과를 반환한다. 입력 목록과 딕셔너리는 보존한다.
전력은 kW, 에너지는 kWh, 물은 m³, 폐기물은 t 단위를 사용한다.
"""


def service_coverage(travel_minutes, populations, limit_minutes):
    """이동 시간이 기준 이하인 지역과 인구를 요약한다. 전체 인구가 0이면 비율은 0이다."""
    raise NotImplementedError("TODO 1: 서비스 권역에 포함된 지역과 인구를 계산하세요.")

    # TODO 1: 권역 지역 목록, 권역 인구, 인구 비율, 경로가 없는 인구를 반환하세요.
    # 1. 빈 지역 목록과 인구 합계 두 개를 준비하고 populations.items()를 순회하세요.
    #    area는 지역 ID, population은 그 지역 인구입니다. 이동 시간은 travel_minutes[area]입니다.
    # 2. 시간이 None이면 경로가 없는 인구에 더하세요. 시간 0과 None을 구분하세요.
    # 3. 시간이 limit_minutes 이하이면 지역 ID를 목록에 넣고 권역 인구에 더하세요.
    # 4. 권역 인구를 전체 인구의 합으로 나누세요. 전체 인구가 0이면 비율은 0입니다.
    # 5. covered / population / ratio / unreachable_population 키를 가진 dict를 반환하세요.
    # 지역 목록은 populations의 순서를 유지합니다. 기준을 넘은 지역은 경로가 없는 지역과 다릅니다.
    # 확인 예: 각 100명, 시간 A=4 / B=8 / C=12 / D=20, 기준 15분이면 A·B·C, 300명, 0.75입니다.
    pass


def advance_queue(queue, arrivals, capacity):
    """기존 대기와 새 요청에서 실제 진료 인원과 다음 시간의 대기 인원을 계산한다."""
    raise NotImplementedError("TODO 2: 진료 인원과 다음 시간의 대기 인원을 계산하세요.")

    # TODO 2: 이번에 진료한 인원과 다음 시간에 기다릴 인원을 반환하세요.
    # 1. 기존 대기 queue에 새 요청 arrivals를 더해 전체 대기 인원을 구하세요.
    # 2. 전체 대기 인원과 capacity 중 작은 값을 min(...)으로 구하세요.
    # 3. 전체 대기 인원에서 실제 진료 인원을 빼 다음 대기 인원을 구하세요.
    # 4. served / queue 키를 가진 dict를 반환하세요. print로 출력하는 것이 아닙니다.
    # 확인 예: 대기 0명, 요청 10명, 용량 8명이면 {"served": 8, "queue": 2}입니다.
    pass


def allocate_power(supply_kw, demands_kw, priority):
    """우선순위대로 시설별 전력을 배분한다. 수요와 남은 공급량을 초과하지 않는다."""
    raise NotImplementedError("TODO 3: 우선순위에 따라 시설별 전력을 배분하세요.")

    # TODO 3: 시설 이름을 키로, 배분한 전력을 값으로 갖는 dict를 반환하세요.
    # 1. 빈 결과 dict와 남은 공급량을 준비하세요. 남은 공급량의 초기값은 supply_kw입니다.
    # 2. priority를 순회하세요. 각 항목은 "hospital" 같은 시설 이름입니다.
    # 3. demands_kw[facility]와 남은 공급량 중 작은 값을 해당 시설에 배분하세요.
    # 4. 배분한 만큼 남은 공급량에서 빼고 다음 시설을 처리하세요.
    # 공급이 소진되어도 모든 시설을 결과에 넣습니다. 뒤 시설의 배분량은 0입니다.
    # 확인 예: 공급 100, 병원 / 펌프 / 주거 / 산업 수요 30 / 20 / 50 / 20이면 30 / 20 / 50 / 0입니다.
    pass


def update_water(stored_m3, inflow_m3, demand_m3, capacity_m3):
    """유입 후 급수하고 다음 저장량, 공급량, 미충족 수요, 넘침을 m³ 단위로 반환한다."""
    raise NotImplementedError("TODO 4: 물의 공급량과 저장량, 미충족 수요와 넘침을 계산하세요.")

    # TODO 4: stored / supplied / unmet / overflow 키를 가진 dict를 반환하세요.
    # 1. 기존 저장량과 유입량을 더해 이번에 사용할 수 있는 물의 양을 구하세요.
    # 2. 사용 가능한 양과 demand_m3 중 작은 값만 공급하세요.
    # 3. 공급 후 남은 물에서 capacity_m3을 넘는 양은 overflow, 보관하는 양은 stored입니다.
    # 4. 수요에서 실제 공급량을 뺀 값이 unmet입니다. 물이 충분하면 0입니다.
    # 저장 용량은 급수한 뒤 적용합니다. 처음부터 유입량을 잘라 버리면 공급량이 달라집니다.
    # 확인 예: 저장 10, 유입 6, 수요 8, 용량 20이면 저장 8 / 공급 8 / 부족 0 / 넘침 0입니다.
    pass


def update_waste(city_t, plant_t, generated_t, collection_t, treatment_t):
    """도시의 폐기물을 수거한 뒤 시설에서 처리하고 남은 양을 t 단위로 반환한다."""
    raise NotImplementedError("TODO 5: 폐기물의 수거량과 처리량, 남은 양을 계산하세요.")

    # TODO 5: city / plant / collected / processed 키를 가진 dict를 반환하세요.
    # 1. 도시의 기존 양 city_t와 발생량 generated_t를 합친 뒤 collection_t 이내로 수거하세요.
    # 2. 시설의 기존 양 plant_t에 이번 수거량을 더한 뒤 treatment_t 이내로 처리하세요.
    # 3. 도시에는 수거하지 못한 양, 시설에는 처리하지 못한 양이 남습니다.
    # 이번에 수거한 양도 같은 단계에서 처리할 수 있습니다. 수거는 이동이고 처리는 제거입니다.
    # 확인 예: 도시 0, 시설 0, 발생 8, 수거 능력 6, 처리 능력 5이면 도시 2 / 시설 1입니다.
    # 이때 collected는 6, processed는 5입니다. 공급된 인자를 사용하고 예시 숫자를 고정하지 마세요.
    pass


def transport_pollution(amounts, move_ratio, removal_ratio):
    """동쪽 이동과 제거를 반영한 새 목록을 반환한다. 이동량은 원본에서 계산한다."""
    raise NotImplementedError("TODO 6: 오염물질의 이동과 제거를 반영한 새 목록을 반환하세요.")

    # TODO 6: 모든 셀의 이동을 반영한 뒤 제거를 적용해 새 목록을 반환하세요.
    # 1. amounts.copy()로 별도 목록을 만드세요. 원본 amounts에 결과를 기록하면 안 됩니다.
    # 2. 마지막 셀을 제외한 각 인덱스에서 amounts[index] * move_ratio로 이동량을 구하세요.
    # 3. 복사한 목록의 현재 셀에서 이동량을 빼고 바로 다음 셀에 더하세요.
    # 4. 모든 이동이 끝나면 각 셀에 (1 - removal_ratio)를 곱해 제거를 반영하세요.
    # 이동량은 원본에서 읽습니다. 이번에 받은 양을 같은 단계에서 다시 보내지 마세요.
    # 마지막 셀은 경계 밖으로 보내지 않지만, 앞 셀에서 받은 양과 제거는 반영합니다.
    # 확인 예: [100, 0, 0], 이동 0.2, 제거 0.1이면 [72, 18, 0]이며 원본은 그대로입니다.
    pass

"""
병원 대기열의 결과 검사, 방문 인원 생성, 반복 비교와 용량별 비교를 구현한다.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 뒤 단계에서 앞 단계 함수를 사용합니다.
2. pass는 코드를 작성할 빈자리입니다. 주석만 있는 TODO는 그 아래에 코드를 추가하세요.
3. 한 함수를 작성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 아래 코드는 실행되지 않습니다. 제공된 입력 검사는 유지하세요.
4. 실습 최상위 폴더에서 python skeleton/checks_validation.py --stage 1로 확인하세요.
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미구현]은 아직 남은 NotImplementedError, [실패]는 검사 중 발견한 문제입니다.

- 데이터를 읽을 때
arrivals는 시간별 방문 인원 목록이고, capacity는 한 시간에 진료할 수 있는 인원입니다.
history에는 1시간째부터의 기록을 담으며, final_queue는 실행 종료 시점의 대기 인원입니다.
각 실행은 대기 0명부터 시작합니다. 입력 목록과 기존 도시 상태는 변경하지 않습니다.
비교할 두 용량에는 같은 방문 목록을 사용합니다. 대기 인원과 대기시간을 구분하세요.
"""

import random
import statistics

from service_rules import advance_queue
from validation_inputs import (
    nonnegative_integer,
    require_arrivals,
    require_integer,
    require_numbers,
    require_seeds,
    require_settings,
)


def is_valid_step(queue, arrivals, capacity, result):
    """한 시간의 결과가 대기열 규칙에 맞으면 True를 반환한다. 입력은 변경하지 않는다."""
    if not all(nonnegative_integer(value) for value in (queue, arrivals, capacity)):
        return False
    if not isinstance(result, dict) or "served" not in result or "queue" not in result:
        return False

    served, remaining = result["served"], result["queue"]

    raise NotImplementedError("1단계: is_valid_step")

    # TODO 1: 제공된 입력 검사에 이어 결과의 인원과 계산 규칙을 확인하세요.
    # 1. served와 remaining에 nonnegative_integer(...)를 적용하세요.
    #    둘 중 하나라도 검사 결과가 False이면 False를 반환하세요. bool도 제외합니다.
    # 2. served가 min(queue + arrivals, capacity)와 같은지 확인하세요.
    # 3. served + remaining이 queue + arrivals와 같은지 확인하세요.
    # 위 조건을 모두 만족할 때만 True를 반환합니다. 인원의 합만 맞으면 충분하지 않습니다.
    # 확인 예: 대기 2명, 방문 3명, 용량 10명에서 진료 4명 / 남은 대기 1명은 False입니다.
    pass


def make_arrivals(seed, hours=6, low=6, high=14):
    """지역 난수 생성기로 시간별 방문 목록을 만든다. low와 high는 모두 포함한다."""
    require_settings(seed, hours, low, high)

    raise NotImplementedError("2단계: make_arrivals")

    # TODO 2-A: random.Random(seed)로 지역 난수 생성기 generator를 만드세요.
    # 다른 도시 기능의 난수 상태가 바뀌지 않도록 전역 random.seed(...)는 사용하지 않습니다.
    # 생성기는 아래 시간 반복문 밖에서 한 번만 만듭니다.

    arrivals = []

    for _ in range(hours):
        # TODO 2-B: generator.randint(low, high)로 뽑은 인원을 arrivals에 추가하세요.
        # randint는 양 끝값을 포함합니다. 시간마다 생성기를 새로 만들면 안 됩니다.
        # 확인 예: 시드 101 / 6시간 / 6~14명이면 [9, 14, 11, 13, 6, 14]입니다.
        pass

    return arrivals


def run_scenario(arrivals, capacity):
    """대기 0명부터 한 회차를 실행해 history와 final_queue를 반환한다. 입력은 보존한다."""
    arrivals = require_arrivals(arrivals)
    require_integer(capacity, "진료 용량")

    raise NotImplementedError("3단계: run_scenario")

    queue = 0
    history = []

    for hour, visitors in enumerate(arrivals, 1):
        # TODO 3: 이번 시간의 진료 결과를 검사하고, 다음 시간으로 넘길 대기를 갱신하세요.
        # 1. 제공된 advance_queue(queue, visitors, capacity)의 결과를 result에 저장하세요.
        # 2. TODO 1의 is_valid_step(queue, visitors, capacity, result)로 검사하세요.
        #    검사에 실패하면 raise ValueError("계산 결과가 규칙과 다릅니다.")로 중단하세요.
        # 3. 검사가 끝난 뒤 queue에 result["queue"]를 저장하세요. 검사 전에 바꾸면 안 됩니다.
        # 4. hour / arrivals / served / queue 키를 가진 새 dict를 history에 추가하세요.
        #    값은 각각 hour / visitors / result["served"] / 갱신한 queue입니다.
        # 시간마다 새 dict를 만들어야 이전 기록이 나중 시간의 값으로 바뀌지 않습니다.
        # 확인 예: 시드 101의 입력 / 용량 8이면 대기는 [1, 7, 10, 15, 13, 19]입니다.
        pass

    return {"history": history, "final_queue": queue}


def summarize(values):
    """개수 / 평균 / 표본 표준편차 / 범위를 반환한다. 계산할 수 없는 통계값은 None이다."""
    values = require_numbers(values)

    raise NotImplementedError("4단계: summarize")

    count = len(values)

    if count == 0:
        # TODO 4-A: 빈 자료의 결과 dict를 반환하세요.
        # count는 0, mean / stddev / minimum / maximum은 모두 None입니다.
        # 평균을 구하기 전에 반환해야 0으로 나누는 오류를 피할 수 있습니다.
        pass

    # TODO 4-B: 자료가 있을 때 평균 / 표본 표준편차 / 최솟값 / 최댓값을 구해 반환하세요.
    # 평균은 sum(values) / count입니다. statistics.stdev(values)는 자료가 2개 이상일 때만
    # 호출하고, 자료가 하나이면 stddev는 None으로 둡니다. min(...)과 max(...)도 사용하세요.
    # 반환 키는 count / mean / stddev / minimum / maximum입니다. 함수 안에서 반올림하지 마세요.
    # 확인 예: [8, 10, 12]이면 개수 3 / 평균 10 / 표본 표준편차 2 / 최솟값 8 / 최댓값 12입니다.
    # [7]의 표본 표준편차는 None, [0, 0]의 표본 표준편차는 0입니다. 두 상태를 구분하세요.


def compare_scenarios(seeds, baseline_capacity=8, policy_capacity=10, hours=6, low=6, high=14):
    """시드별 같은 방문 목록으로 두 용량을 실행한다. 감소 인원은 기준 대기에서 비교 대기를 뺀다."""
    seeds = require_seeds(seeds)
    require_integer(baseline_capacity, "기준 용량")
    require_integer(policy_capacity, "비교 용량")

    raise NotImplementedError("5단계: compare_scenarios")

    results = []

    for seed in seeds:
        # TODO 5: 같은 입력으로 두 용량을 실행하고 회차별 결과를 results에 추가하세요.
        # 1. TODO 2의 make_arrivals(seed, hours, low, high)를 한 번 호출하세요.
        # 2. 만든 방문 목록을 TODO 3의 run_scenario에 전달해 기준 / 비교 용량으로 실행하세요.
        # 3. seed / arrivals / baseline / policy / reduction 키를 가진 새 dict를 추가하세요.
        #    baseline과 policy에는 각 실행의 전체 결과 dict를 넣습니다.
        #    reduction은 baseline["final_queue"]에서 policy["final_queue"]를 뺀 값입니다.
        # 확인 예: 시드 101 / 용량 8과 10이면 기준 19명 / 비교 8명 / 감소 11명입니다.
        # 두 용량에 다른 방문 목록을 주거나, 기준 실행의 대기를 비교 실행으로 넘기지 마세요.
        pass

    return results


def sensitivity_analysis(seeds, capacities, hours=6, low=6, high=14):
    """같은 입력 묶음으로 용량별 최종 대기와 요약 통계를 구한다. 입력한 용량 순서를 유지한다."""
    seeds = require_seeds(seeds)

    raise NotImplementedError("6단계: sensitivity_analysis")

    inputs = []

    for seed in seeds:
        # TODO 6-A: make_arrivals(seed, hours, low, high)의 결과를 inputs에 추가하세요.
        # inputs는 회차별 방문 목록을 모은 리스트입니다. 용량 반복문보다 먼저 만듭니다.
        pass

    results = []

    for capacity in capacities:
        require_integer(capacity, "진료 용량")

        values = []
        for arrivals in inputs:
            # TODO 6-B: 이 방문 목록을 현재 capacity로 실행하고 final_queue를 values에 추가하세요.
            # 시간별 대기를 모두 더하는 것이 아닙니다. 한 회차당 마지막 대기 한 개를 모읍니다.
            pass

        # TODO 6-C: capacity / values / summary 키를 가진 새 dict를 results에 추가하세요.
        # summary에는 TODO 4의 summarize(values) 결과를 넣습니다.
        # 확인 예: 시드 101만 사용할 때 용량 0의 values는 [67], 용량 100은 [0]입니다.
        # 모든 용량에 같은 inputs를 사용하고, results는 capacities의 순서대로 만듭니다.

    return results

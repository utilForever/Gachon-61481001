"""병원 대기열의 결과 검사, 방문 인원 생성, 반복 비교와 용량별 비교의 모범 답안.

1회 실행은 대기 0명부터 시작한다. 입력 목록과 기존 도시 상태는 변경하지 않는다.
비교할 두 용량에는 같은 방문 목록을 사용하고, 시드별 입력은 모든 용량에 공통으로 사용한다.
통계값은 반올림하지 않는다. 자료가 없거나 표본 표준편차를 구할 수 없으면 None으로 구분한다."""

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
    if not all(nonnegative_integer(value) for value in (served, remaining)):
        return False

    return served == min(queue + arrivals, capacity) and served + remaining == queue + arrivals


def make_arrivals(seed, hours=6, low=6, high=14):
    """지역 난수 생성기로 시간별 방문 목록을 만든다. low와 high는 모두 포함한다."""
    require_settings(seed, hours, low, high)

    generator = random.Random(seed)
    arrivals = []

    for _ in range(hours):
        arrivals.append(generator.randint(low, high))

    return arrivals


def run_scenario(arrivals, capacity):
    """대기 0명부터 한 회차를 실행해 history와 final_queue를 반환한다. 입력은 보존한다."""
    arrivals = require_arrivals(arrivals)
    require_integer(capacity, "진료 용량")

    queue = 0
    history = []

    for hour, visitors in enumerate(arrivals, 1):
        result = advance_queue(queue, visitors, capacity)
        if not is_valid_step(queue, visitors, capacity, result):
            raise ValueError(f"{hour}시간째 대기열 계산이 규칙과 맞지 않습니다.")

        queue = result["queue"]
        history.append(
            {"hour": hour, "arrivals": visitors, "served": result["served"], "queue": queue}
        )

    return {"history": history, "final_queue": queue}


def summarize(values):
    """개수 / 평균 / 표본 표준편차 / 범위를 반환한다. 계산할 수 없는 통계값은 None이다."""
    values = require_numbers(values)

    count = len(values)

    if count == 0:
        return {"count": 0, "mean": None, "stddev": None, "minimum": None, "maximum": None}

    mean = sum(values) / count
    # 표본 표준편차는 두 개 이상의 결과가 있어야 계산할 수 있다.
    stddev = statistics.stdev(values) if count >= 2 else None

    return {
        "count": count,
        "mean": mean,
        "stddev": stddev,
        "minimum": min(values),
        "maximum": max(values),
    }


def compare_scenarios(seeds, baseline_capacity=8, policy_capacity=10, hours=6, low=6, high=14):
    """시드별 같은 방문 목록으로 두 용량을 실행한다. 감소 인원은 기준 대기에서 비교 대기를 뺀다."""
    seeds = require_seeds(seeds)
    require_integer(baseline_capacity, "기준 용량")
    require_integer(policy_capacity, "비교 용량")

    results = []

    for seed in seeds:
        arrivals = make_arrivals(seed, hours, low, high)
        # 한 번 만든 방문 인원 목록을 두 조건에 공통으로 사용한다.
        baseline = run_scenario(arrivals, baseline_capacity)
        policy = run_scenario(arrivals, policy_capacity)
        results.append(
            {
                "seed": seed,
                "arrivals": arrivals,
                "baseline": baseline,
                "policy": policy,
                "reduction": baseline["final_queue"] - policy["final_queue"],
            }
        )

    return results


def sensitivity_analysis(seeds, capacities, hours=6, low=6, high=14):
    """같은 입력 묶음으로 용량별 최종 대기와 요약 통계를 구한다. 입력한 용량 순서를 유지한다."""
    seeds = require_seeds(seeds)

    inputs = []

    for seed in seeds:
        inputs.append(make_arrivals(seed, hours, low, high))

    results = []

    for capacity in capacities:
        require_integer(capacity, "진료 용량")

        values = []
        for arrivals in inputs:
            values.append(run_scenario(arrivals, capacity)["final_queue"])
        results.append({"capacity": capacity, "values": values, "summary": summarize(values)})

    return results

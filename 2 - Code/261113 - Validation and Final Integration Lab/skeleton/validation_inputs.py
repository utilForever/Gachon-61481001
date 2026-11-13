"""반복 실험의 정수, 방문 목록, 통계 자료와 시드 조건을 검사하는 제공 코드."""

import math


def nonnegative_integer(value):
    """bool을 제외한 0 이상의 정수이면 True를 반환한다."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def require_integer(value, name, minimum=0):
    """최솟값 이상의 정수를 반환한다. 조건에 맞지 않으면 ValueError를 발생시킨다."""
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name}은(는) {minimum} 이상의 정수여야 합니다.")

    return value


def require_arrivals(values):
    """방문 인원을 새 리스트로 만들고, 각 값이 0 이상의 정수인지 검사한다."""
    values = list(values)
    if not all(nonnegative_integer(value) for value in values):
        raise ValueError("방문 인원은 0 이상의 정수여야 합니다.")

    return values


def require_numbers(values):
    """통계 자료를 새 리스트로 만든다. bool, 무한대와 NaN은 허용하지 않는다."""
    values = list(values)
    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        for value in values
    ):
        raise ValueError("집계할 값은 유한한 숫자여야 합니다.")

    return values


def require_settings(seed, hours, low, high):
    """시드 / 기간 / 방문 범위를 검사한다. low와 high는 같은 값이어도 된다."""
    require_integer(seed, "시드")
    require_integer(hours, "기간", 1)
    require_integer(low, "최소 방문 인원")
    require_integer(high, "최대 방문 인원")

    if low > high:
        raise ValueError("최소 방문 인원은 최대 방문 인원보다 클 수 없습니다.")


def require_seeds(seeds):
    """중복 없는 시드 목록을 새 리스트로 반환한다. 빈 목록은 허용하지 않는다."""
    seeds = list(seeds)
    if not seeds:
        raise ValueError("시드가 하나 이상 필요합니다.")

    for seed in seeds:
        require_integer(seed, "시드")

    if len(set(seeds)) != len(seeds):
        raise ValueError("반복 실험에는 서로 다른 시드를 사용하세요.")

    return seeds

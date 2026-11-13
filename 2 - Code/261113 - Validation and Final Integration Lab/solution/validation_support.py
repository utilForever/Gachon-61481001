"""반복 실험 실행, 설정 / 기록 검증과 JSON / CSV 저장을 연결하는 제공 코드."""

from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter

import validation_rules as rules
from validation_inputs import require_integer, require_settings

CODE_VERSION = "2026.11.13.1"
DEFAULT_SETTINGS = {
    "first_seed": 101,
    "count": 30,
    "hours": 6,
    "low": 6,
    "high": 14,
    "baseline_capacity": 8,
    "policy_capacity": 10,
}
CAPACITIES = [6, 8, 10, 12, 14]
ASSUMPTIONS = {
    "target": "병원 H의 대기열",
    "initial_queue": 0,
    "time_step": "1시간",
    "metric": "실행 종료 시점의 대기 인원(명)",
    "arrivals": "시간별 독립 이산 균등분포",
    "fixed": "도로와 서비스 대상 고정, 전력·급수 충분",
    "excluded": "확충 비용, 추가 수요, 대기 포기, 환자 우선순위",
    "city_state": "현재 도시 상태를 변경하지 않는 별도 실험",
}


def checked_settings(settings):
    """필수 설정과 화면의 실행 한도를 검사하고, 필요한 항목만 담은 새 dict를 반환한다."""
    if not isinstance(settings, dict) or any(key not in settings for key in DEFAULT_SETTINGS):
        raise ValueError("실험 설정 항목이 빠졌습니다.")

    result = {key: settings[key] for key in DEFAULT_SETTINGS}
    require_settings(result["first_seed"], result["hours"], result["low"], result["high"])

    for key in ("baseline_capacity", "policy_capacity", "count"):
        require_integer(result[key], key, 1 if key == "count" else 0)

    limits = {
        "first_seed": 2147483000,
        "count": 500,
        "hours": 168,
        "low": 10000,
        "high": 10000,
        "baseline_capacity": 10000,
        "policy_capacity": 10000,
    }
    if any(result[key] > maximum for key, maximum in limits.items()):
        raise ValueError("화면에서는 최대 500회, 168시간, 인원·용량 10,000까지 사용할 수 있습니다.")

    return result


def seeds_for(settings):
    """시작 시드부터 반복 횟수만큼 연속된 시드 목록을 만든다."""
    return list(range(settings["first_seed"], settings["first_seed"] + settings["count"]))


def code_hashes():
    """계산에 사용하는 세 소스 파일의 SHA-256 해시를 구한다. 서식 변경도 반영된다."""
    directory = Path(__file__).resolve().parent
    return {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in ("validation_rules.py", "service_rules.py", "validation_support.py")
    }


ACTIVE_CODE_HASHES = code_hashes()


def make_bundle(settings, records, elapsed_ms=0.0):
    """설정과 결과를 복사해 실행 환경 / 코드 정보와 함께 저장할 실험 dict를 만든다."""
    return {
        "schema_version": 1,
        "code_version": CODE_VERSION,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_sha256": deepcopy(ACTIVE_CODE_HASHES),
        "settings": checked_settings(settings),
        "assumptions": deepcopy(ASSUMPTIONS),
        "records": deepcopy(records),
        "sensitivity": [],
        "elapsed_ms": elapsed_ms,
    }


def run_comparison(settings):
    """설정에 따라 두 용량을 반복 비교하고, 계산 시간과 결과를 실험 dict로 반환한다."""
    settings = checked_settings(settings)
    started = perf_counter()
    records = rules.compare_scenarios(
        seeds_for(settings),
        settings["baseline_capacity"],
        settings["policy_capacity"],
        settings["hours"],
        settings["low"],
        settings["high"],
    )

    return make_bundle(settings, records, (perf_counter() - started) * 1000)


def run_sensitivity(settings):
    """지정된 용량별로 같은 입력 묶음을 실행하고, 결과와 계산 시간을 반환한다."""
    settings = checked_settings(settings)
    started = perf_counter()
    result = rules.sensitivity_analysis(
        seeds_for(settings), CAPACITIES, settings["hours"], settings["low"], settings["high"]
    )

    return result, (perf_counter() - started) * 1000


def _check_run(run, arrivals, capacity):
    """저장된 시간별 기록과 최종 대기가 원래 입력 / 용량의 계산 결과와 같은지 검사한다."""
    if not isinstance(run, dict) or not isinstance(run.get("history"), list):
        raise ValueError("시간별 기록이 없습니다.")
    if len(run["history"]) != len(arrivals):
        raise ValueError("방문 인원과 시간별 기록의 길이가 다릅니다.")

    queue = 0

    for hour, (visitors, row) in enumerate(zip(arrivals, run["history"]), 1):
        if not isinstance(row, dict) or any(
            type(row.get(key)) is not int for key in ("hour", "arrivals", "served", "queue")
        ):
            raise ValueError("시간별 기록의 시각과 인원은 정수여야 합니다.")

        served = min(queue + visitors, capacity)
        queue += visitors - served
        expected = {"hour": hour, "arrivals": visitors, "served": served, "queue": queue}
        if row != expected:
            raise ValueError(f"{hour}시간째 저장된 기록이 대기열 규칙과 맞지 않습니다.")

    if type(run.get("final_queue")) is not int or run.get("final_queue") != queue:
        raise ValueError("마지막 대기 인원이 시간별 기록과 다릅니다.")


def validate_bundle(bundle):
    """설정 / 입력 / 기록 / 통계의 일관성을 검사하고 전달받은 실험 dict를 반환한다."""
    if (
        not isinstance(bundle, dict)
        or type(bundle.get("schema_version")) is not int
        or bundle.get("schema_version") != 1
    ):
        raise ValueError("지원하지 않는 실험 파일입니다.")

    settings = checked_settings(bundle.get("settings"))
    records = bundle.get("records")
    if not isinstance(records, list) or len(records) != settings["count"]:
        raise ValueError("반복 횟수와 저장된 기록 수가 다릅니다.")

    for expected_seed, row in zip(seeds_for(settings), records):
        if (
            not isinstance(row, dict)
            or type(row.get("seed")) is not int
            or row.get("seed") != expected_seed
        ):
            raise ValueError("시드 순서가 설정과 다릅니다.")

        arrivals = row.get("arrivals")
        if not isinstance(arrivals, list) or len(arrivals) != settings["hours"]:
            raise ValueError("시간별 방문 인원 목록이 잘못되었습니다.")
        for value in arrivals:
            require_integer(value, "방문 인원")

            if not settings["low"] <= value <= settings["high"]:
                raise ValueError("방문 인원이 설정 범위를 벗어났습니다.")
        _check_run(row.get("baseline"), arrivals, settings["baseline_capacity"])
        _check_run(row.get("policy"), arrivals, settings["policy_capacity"])
        if (
            type(row.get("reduction")) is not int
            or row.get("reduction") != row["baseline"]["final_queue"] - row["policy"]["final_queue"]
        ):
            raise ValueError("감소 인원이 두 결과의 차이와 다릅니다.")

    sensitivity = bundle.get("sensitivity", [])
    if not isinstance(sensitivity, list):
        raise ValueError("용량별 비교는 목록이어야 합니다.")

    for row in sensitivity:
        if not isinstance(row, dict):
            raise ValueError("용량별 비교 항목이 잘못되었습니다.")

        capacity = require_integer(row.get("capacity"), "진료 용량")

        values = []
        for record in records:
            queue = 0
            for visitors in record["arrivals"]:
                queue = max(0, queue + visitors - capacity)
            values.append(queue)
        expected = {
            "count": len(values),
            "mean": sum(values) / len(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else None,
            "minimum": min(values),
            "maximum": max(values),
        }
        if (
            not isinstance(row.get("values"), list)
            or not all(type(value) is int for value in row["values"])
            or row["values"] != values
            or not isinstance(row.get("summary"), dict)
        ):
            raise ValueError("용량별 원자료가 방문 인원과 맞지 않습니다.")
        for key, value in expected.items():
            actual = row["summary"].get(key)
            if value is None:
                valid = actual is None
            else:
                valid = type(actual) in (int, float) and abs(actual - value) < 1e-9

            if not valid:
                raise ValueError("용량별 요약값이 원자료와 맞지 않습니다.")

    return bundle


def replay_record(bundle, index):
    """선택한 회차의 저장된 방문 목록으로 다시 계산하고, 기존 결과와 일치하는지 반환한다."""
    validate_bundle(bundle)

    settings = bundle["settings"]
    row = bundle["records"][index]
    # 저장된 원입력을 재사용하므로 난수 생성 순서의 변화와 구분할 수 있다.
    baseline = rules.run_scenario(row["arrivals"], settings["baseline_capacity"])
    policy = rules.run_scenario(row["arrivals"], settings["policy_capacity"])

    return {
        "baseline": baseline,
        "policy": policy,
        "matches": baseline == row["baseline"] and policy == row["policy"],
    }


def save_experiment(bundle, path):
    """검증한 실험을 UTF-8 JSON으로 저장한다."""
    validate_bundle(bundle)

    Path(path).write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")


def load_experiment(path):
    """40MB 이하의 JSON을 읽고 검증한 실험 dict를 반환한다."""
    path = Path(path)
    if path.stat().st_size > 40 * 1024 * 1024:
        raise ValueError("실험 파일은 40MB 이하만 열 수 있습니다.")

    return validate_bundle(json.loads(path.read_text(encoding="utf-8")))


def export_csv(bundle, path):
    """검증한 실험의 기준 / 비교 시간별 기록을 UTF-8 BOM이 있는 CSV로 저장한다."""
    validate_bundle(bundle)

    settings = bundle["settings"]
    fields = [
        "seed",
        "scenario",
        "hour",
        "arrivals",
        "served",
        "queue",
        "capacity",
        "final_queue",
        "reduction",
        "first_seed",
        "count",
        "hours",
        "low",
        "high",
        "python_version",
        "code_version",
        "validation_rules_sha256",
        "created_at",
    ]

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in bundle["records"]:
            for key, capacity_key in (
                ("baseline", "baseline_capacity"),
                ("policy", "policy_capacity"),
            ):
                for row in record[key]["history"]:
                    writer.writerow(
                        {
                            **row,
                            "seed": record["seed"],
                            "scenario": key,
                            "capacity": settings[capacity_key],
                            "final_queue": record[key]["final_queue"],
                            "reduction": record["reduction"],
                            **{
                                name: settings[name]
                                for name in ("first_seed", "count", "hours", "low", "high")
                            },
                            "python_version": bundle.get("python_version", ""),
                            "code_version": bundle.get("code_version", ""),
                            "validation_rules_sha256": bundle.get("code_sha256", {}).get(
                                "validation_rules.py", ""
                            ),
                            "created_at": bundle.get("created_at", ""),
                        }
                    )

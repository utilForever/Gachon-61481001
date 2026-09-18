"""단계별 누적 검사: python checks.py --stage 3

종료 코드: 0=통과, 1=오류, 2=TODO 미완성.
"""

import argparse
from copy import deepcopy
import traceback

import city_data
import model


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_stage_1():
    city = city_data.make_empty_city()
    require(
        not model.can_build(city, 0, 0, "house"),
        "용도 미지정 셀에는 주택을 놓을 수 없습니다.",
    )

    city_data.edit_zone(city, 0, 0, "R")
    require(
        city["grid"][0][0]["building_id"] is None,
        "용도지역 지정만으로 건물을 만들면 안 됩니다.",
    )
    require(model.can_build(city, 0, 0, "house"), "R에는 주택을 놓을 수 있어야 합니다.")
    require(
        not model.can_build(city, 0, 0, "factory"),
        "R에는 산업 건물을 놓을 수 없습니다.",
    )

    before = deepcopy(city)
    try:
        model.place_building(city, 0, 0, "factory")
    except ValueError:
        pass
    else:
        raise AssertionError("용도와 맞지 않는 배치를 거부해야 합니다.")
    require(city == before, "배치 실패 시 원래 도시를 보존해야 합니다.")

    ident = model.place_building(city, 0, 0, "house")
    require(
        city["grid"][0][0]["building_id"] == ident,
        "셀과 건물 참조를 함께 기록해야 합니다.",
    )
    require(city["buildings"][ident]["population"] == 0, "새 주택은 공실로 시작합니다.")

    before = deepcopy(city)
    try:
        city_data.edit_zone(city, 0, 0, "C")
    except ValueError:
        pass
    else:
        raise AssertionError("건물이 있는 셀의 용도 변경은 거부해야 합니다.")
    require(city == before, "용도 변경 거부 시 건물과 셀을 그대로 보존해야 합니다.")
    require(
        not model.can_build(city, 0, 0, "house"),
        "건물이 있는 셀에는 중복 배치할 수 없습니다.",
    )
    require(not model.can_build(city, 4, 0, "park"), "물 위에는 공원을 놓을 수 없습니다.")
    require(not model.can_build(city, -1, 0, "house"), "지도 밖은 건설할 수 없습니다.")

    for x, zone, kind in [(1, "C", "shop"), (2, "I", "factory")]:
        city_data.edit_zone(city, x, 0, zone)
        require(
            model.can_build(city, x, 0, kind),
            "C/상업 건물, I/산업 건물의 대응을 확인하세요.",
        )
        model.place_building(city, x, 0, kind)
    require(model.total_population(city) == 0, "종사자 수를 주택 인구에 더하면 안 됩니다.")
    city_data.validate_city(city)


def check_stage_2():
    city = city_data.make_city()
    require(model.occupancy(city["buildings"]["A"]) == 0.6, "6명 / 10명은 0.6입니다.")

    empty = deepcopy(city["buildings"]["A"])
    empty["population"] = 0
    require(model.occupancy(empty) == 0, "수용량이 양수인 공실 주택의 점유율은 0입니다.")

    empty["capacity"] = 0
    require(model.occupancy(empty) is None, "수용량 0이면 점유율을 정의하지 않습니다.")
    require(
        model.occupancy(city["buildings"]["P"]) is None,
        "공원에는 점유율을 적용하지 않습니다.",
    )

    factory = {"kind": "factory", "workers": 4, "capacity": 10}
    require(model.occupancy(factory) == 0.4, "상업 / 산업 건물은 workers를 사용합니다.")


def check_stage_3():
    city = city_data.make_city()
    require(model.road_access(city, city["buildings"]["A"]), "A의 아래쪽 도로를 확인하세요.")

    city["grid"][2][1]["road"] = False
    require(
        not model.road_access(city, city["buildings"]["A"]),
        "대각선 도로는 접근 조건에 포함하지 않습니다.",
    )

    corner = {"x": 0, "y": 0}
    city["grid"][0][4]["road"] = True
    require(
        not model.road_access(city, corner),
        "지도 경계에서 반대편 셀로 순환하면 안 됩니다.",
    )


def check_stage_4():
    city = city_data.make_city("industry")
    require(
        model.environment_score(city, city["buildings"]["A"]) == 2,
        "A는 공원 1개와 인접하므로 E=2입니다.",
    )
    require(
        model.environment_score(city, city["buildings"]["B"]) == -1,
        "B는 공원 1개 / 산업 건물 1개와 인접하므로 E=-1입니다.",
    )

    city["buildings"]["I"]["status"] = "closed"
    require(
        model.environment_score(city, city["buildings"]["B"]) == 2,
        "운영 중인 주변 건물만 셉니다.",
    )

    city["buildings"]["P"]["status"] = "construction"
    require(
        model.environment_score(city, city["buildings"]["A"]) == 0,
        "건설 중인 공원은 아직 영향을 주지 않습니다.",
    )


def check_stage_5():
    city = city_data.make_city("industry")
    require(
        model.growth_request(city, city["buildings"]["A"]) == (2, 0),
        "좋은 환경에서는 빈자리 범위에서 최대 2명이 입주를 요청합니다.",
    )
    require(
        model.growth_request(city, city["buildings"]["B"]) == (0, 1),
        "E=-1이면 입주보다 전출 규칙을 우선합니다.",
    )

    city["buildings"]["A"]["population"] = 9
    city["demand"] = 0
    require(
        model.growth_request(city, city["buildings"]["A"]) == (1, 0),
        "요청량은 빈자리로 제한하며 수요 배정은 다음 단계입니다.",
    )

    city["buildings"]["B"]["population"] = 0
    require(
        model.growth_request(city, city["buildings"]["B"]) == (0, 0),
        "인구가 0인 주택에서는 더 전출할 수 없습니다.",
    )

    city["buildings"]["A"]["status"] = "closed"
    require(
        model.growth_request(city, city["buildings"]["A"]) == (0, 0),
        "운영 중인 주택에만 규칙을 적용합니다.",
    )

    city = city_data.make_city()
    city["buildings"]["P"]["status"] = "closed"
    require(
        model.growth_request(city, city["buildings"]["A"]) == (0, 0),
        "도로가 있고 E=0이면 현 상태를 유지합니다.",
    )

    city["grid"][2][1]["road"] = False
    require(
        model.growth_request(city, city["buildings"]["A"]) == (0, 1),
        "도로가 없으면 환경과 관계없이 최대 1명이 전출합니다.",
    )


def check_stage_6():
    requests = {"B": 2, "A": 2}
    before = deepcopy(requests)
    result = model.allocate_arrivals(requests, 3)
    require(
        result == {"A": 2, "B": 1},
        "입력 순서와 관계없이 ID 오름차순으로 A=2, B=1을 배정하세요.",
    )
    require(requests == before, "요청량 dict를 수정하면 안 됩니다.")
    require(
        model.allocate_arrivals(requests, 0) == {"A": 0, "B": 0},
        "대기 수요가 없으면 입주도 없습니다.",
    )
    require(
        model.allocate_arrivals({"A": 0, "B": 1}, 9) == {"A": 0, "B": 1},
        "요청량보다 많이 배정하면 안 됩니다.",
    )
    require(model.allocate_arrivals({}, 3) == {}, "주택이 없는 도시도 처리해야 합니다.")


def check_stage_7():
    old = city_data.make_city()
    original = deepcopy(old)
    new = model.step(old)
    require(old == original, "step은 시작 상태를 수정하면 안 됩니다.")
    require(
        (
            new["buildings"]["A"]["population"],
            new["buildings"]["B"]["population"],
            new["demand"],
        )
        == (8, 9, 0),
        "기본 도시 1일: A=8, B=9, 대기 수요=0입니다.",
    )
    require(
        new["budget"] == 132 and new["day"] == 1,
        "지난주 세금 규칙은 시작 인구 14명을 사용합니다.",
    )

    new["grid"][0][0]["zone"] = "R"
    require(
        old["grid"][0][0]["zone"] is None,
        "다음 상태의 셀도 독립적으로 복사해야 합니다.",
    )

    city = city_data.make_city("industry")
    expected = [(8, 7, 3, 1, 132), (10, 6, 1, 2, 167), (10, 5, 1, 3, 205)]
    for day, (a, b, demand, departed, budget) in enumerate(expected, 1):
        city = model.step(city)
        actual = (
            city["buildings"]["A"]["population"],
            city["buildings"]["B"]["population"],
            city["demand"],
            city["departed"],
            city["budget"],
        )
        require(
            actual == (a, b, demand, departed, budget),
            f"산업 건물 있는 도시 {day}일 결과가 다릅니다: {actual}",
        )
        require(
            model.total_population(city) + city["demand"] + city["departed"] == 19,
            "인구 + 대기 수요 + 누적 전출은 19명으로 보존됩니다.",
        )

    for _ in range(20):
        city = model.step(city)
    require(
        city["buildings"]["B"]["population"] == 0,
        "쇠퇴가 계속되어도 인구는 음수가 되면 안 됩니다.",
    )
    require("B" in city["buildings"], "공실 주택을 자동으로 철거하면 안 됩니다.")

    reverse = city_data.make_city()
    reverse["buildings"] = dict(reversed(list(reverse["buildings"].items())))
    require(
        model.step(reverse)["buildings"] == model.step(city_data.make_city())["buildings"],
        "건물 저장 순서가 달라도 같은 결과가 나와야 합니다.",
    )
    city_data.validate_city(city)


STAGES = [
    ("TODO 1: 용도지역과 건물", check_stage_1),
    ("TODO 2: 점유율", check_stage_2),
    ("TODO 3: 도로 접근성", check_stage_3),
    ("TODO 4: 주변 환경", check_stage_4),
    ("TODO 5: 성장 / 쇠퇴 규칙", check_stage_5),
    ("TODO 6: 수요 배정", check_stage_6),
    ("TODO 7: 도시 동시 갱신", check_stage_7),
]


def main():
    parser = argparse.ArgumentParser(description="Land Use and Building Growth Lab")
    parser.add_argument(
        "--stage",
        type=int,
        choices=range(1, 8),
        default=7,
        help="1부터 이 단계까지 점검 (기본: 7)",
    )
    args = parser.parse_args()

    failed = False
    unfinished = False

    for name, check in STAGES[: args.stage]:
        try:
            check()
        except NotImplementedError as error:
            unfinished = True
            print("[미완성] " + name + ": " + str(error))
        except AssertionError as error:
            failed = True
            print("[실패] " + name + ": " + str(error))
        except Exception:
            failed = True
            print("[오류] " + name)
            traceback.print_exc()
        else:
            print("[통과] " + name)

    if failed:
        return 1
    if unfinished:
        return 2

    print("요청한 모든 점검을 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

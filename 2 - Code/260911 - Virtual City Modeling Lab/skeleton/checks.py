"""단계별 누적 검사: python checks.py --stage 3

종료 코드: 0=통과, 1=오류, 2=TODO 미완성.
"""

import argparse
from copy import deepcopy
from pathlib import Path
import tempfile
import traceback

import city_data
import model


def same(actual, expected, description):
    if actual != expected:
        raise AssertionError(
            description + "\n  기대: " + repr(expected) + "\n  실제: " + repr(actual)
        )


def rejects_value_error(action, description):
    try:
        action()
    except ValueError:
        return

    raise AssertionError(description + ": ValueError가 발생해야 합니다.")


def check_support():
    city = city_data.make_city()
    city_data.validate_city(city)
    same(city["buildings"]["A"]["population"], 6, "A의 초기 인구")
    same(city["buildings"]["B"]["population"], 8, "B의 초기 인구")
    same(city["grid"][1][2]["building_id"], "P", "공원 셀의 참조")
    same(city["grid"][0][4]["terrain"], "water", "물 셀 좌표")

    without = city_data.make_city(False)
    same(without["grid"][1][2]["building_id"], None, "공원 없는 시나리오")
    same("P" in without["buildings"], False, "공원 없는 객체 목록")

    empty = city_data.make_empty_city()
    same(empty["buildings"], {}, "빈 도시의 객체 목록")
    empty["grid"][0][0]["road"] = True
    same(empty["grid"][0][1]["road"], False, "셀끼리 같은 dict를 공유하지 않음")
    same(empty["grid"][1][0]["road"], False, "행끼리 같은 셀을 공유하지 않음")
    same(city["grid"][0][0]["road"], False, "도시끼리 상태를 공유하지 않음")

    bad = deepcopy(city)
    bad["grid"][1][1]["building_id"] = None
    rejects_value_error(lambda: city_data.validate_city(bad), "객체의 셀 참조 누락")

    bad = deepcopy(city)
    bad["grid"][0][0]["building_id"] = "MISSING"
    rejects_value_error(lambda: city_data.validate_city(bad), "존재하지 않는 객체 참조")

    bad = deepcopy(city)
    bad["grid"][0][0] = bad["grid"][0][1]
    rejects_value_error(lambda: city_data.validate_city(bad), "셀 dict 공유")

    bad = deepcopy(city)
    bad["buildings"]["A"]["population"] = 11
    rejects_value_error(lambda: city_data.validate_city(bad), "수용량 초과")

    bad = deepcopy(city)
    bad["external_power"] = 1
    rejects_value_error(lambda: city_data.validate_city(bad), "전력은 bool이어야 함")

    bad = deepcopy(city)
    bad["rules"]["growth_per_day"] = -1
    rejects_value_error(lambda: city_data.validate_city(bad), "음수 입주량")

    bad = deepcopy(city)
    bad["grid"][0][4]["road"] = True
    rejects_value_error(lambda: city_data.validate_city(bad), "물 위 도로")

    for bad in [None, [], {}, {"grid": []}]:
        rejects_value_error(lambda: city_data.validate_city(bad), "잘못된 도시 형식")

    edit = city_data.make_empty_city()
    city_data.edit_road(edit, 0, 0)
    same(edit["grid"][0][0]["road"], True, "도로 설치")
    city_data.edit_road(edit, 0, 0)
    same(edit["grid"][0][0]["road"], False, "도로 토글 삭제")
    city_data.edit_road(edit, 0, 0)
    city_data.erase_at(edit, 0, 0)
    same(edit["grid"][0][0]["road"], False, "지우개로 도로 삭제")

    city_data.erase_at(city, 2, 1)
    same("P" in city["buildings"], False, "지우개로 객체 삭제")
    same(city["grid"][1][2]["building_id"], None, "삭제 시 셀 참조도 정리")
    city_data.validate_city(city)
    before = deepcopy(city)
    rejects_value_error(lambda: city_data.edit_road(city, 4, 0), "물 위 도로 편집")
    rejects_value_error(lambda: city_data.edit_road(city, 1, 1), "건물 위 도로 편집")
    rejects_value_error(lambda: city_data.erase_at(city, -1, 0), "범위 밖 삭제")
    same(city, before, "거절한 편집은 상태를 바꾸지 않음")

    city["day"] = 1
    before = deepcopy(city)
    rejects_value_error(lambda: city_data.edit_road(city, 0, 0), "실행 후 도로 편집")
    rejects_value_error(lambda: city_data.erase_at(city, 1, 1), "실행 후 객체 삭제")
    same(city, before, "실행 후 편집 거절은 상태를 바꾸지 않음")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "도시.json"
        city_data.save_city(city, path)
        loaded = city_data.load_city(path)
        same(loaded, city, "UTF-8 JSON 저장/불러오기 왕복")

        loaded["budget"] = 999
        same(city["budget"], 100, "불러온 상태의 독립성")

        path.write_text('{"grid": []}', encoding="utf-8")
        rejects_value_error(lambda: city_data.load_city(path), "손상된 도시 JSON")


def check_stage_1():
    city = city_data.make_city()
    before = deepcopy(city)
    result = model.neighbors4(city, 2, 1)
    same(isinstance(result, list), True, "이웃 좌표는 list로 반환")
    same(set(result), {(1, 1), (3, 1), (2, 0), (2, 2)}, "중앙 셀의 4방향 이웃")
    same(len(result), 4, "중앙 이웃 중복 없음")
    same(set(model.neighbors4(city, 0, 0)), {(1, 0), (0, 1)}, "왼쪽 위 경계")
    same(set(model.neighbors4(city, 4, 3)), {(3, 3), (4, 2)}, "오른쪽 아래 경계")
    same(set(model.neighbors4(city, 0, 2)), {(0, 1), (0, 3), (1, 2)}, "왼쪽 변 경계")
    same(city, before, "이웃 조회는 상태를 바꾸지 않음")


def check_stage_2():
    city = city_data.make_city()
    same(model.total_population(city), 14, "초기 총인구 6+8")
    same(model.total_population(city_data.make_empty_city()), 0, "빈 도시의 총인구")

    city["buildings"]["A"]["population"] = 9
    same(model.total_population(city), 17, "셀 개수가 아니라 주택의 인구 합산")

    city["buildings"]["B"]["status"] = "closed"
    same(model.total_population(city), 17, "총인구는 운영 상태와 관계없이 거주자 합산")

    city["buildings"]["P"]["population"] = 100
    same(model.total_population(city), 17, "공원은 인구 합산 대상에서 제외")


def check_stage_3():
    city = city_data.make_empty_city()
    ident = model.place_building(city, 1, 0, "house")
    same(ident, "H1", "첫 신규 주택 ID")
    same(city["grid"][0][1]["building_id"], ident, "셀 좌표는 grid[y][x]")
    same(city["buildings"][ident]["x"], 1, "객체 x 좌표")
    same(city["buildings"][ident]["y"], 0, "객체 y 좌표")
    same(city["buildings"][ident]["population"], 0, "새 주택의 초기 인구")
    same(city["buildings"][ident]["capacity"], 10, "새 주택 수용량")
    same(city["buildings"][ident]["status"], "operating", "새 건물 운영 상태")

    same(model.place_building(city, 2, 0, "house"), "H2", "주택 ID 중복 방지")
    same(model.place_building(city, 3, 0, "park"), "P1", "공원 ID")
    city_data.validate_city(city)

    city_data.erase_at(city, 1, 0)
    same(model.place_building(city, 1, 0, "house"), "H1", "가장 작은 사용 가능한 ID")

    city_data.edit_road(city, 0, 0)
    before = deepcopy(city)
    for x, y, kind in [
        (1, 0, "park"),
        (0, 0, "house"),
        (4, 0, "park"),
        (-1, 0, "house"),
        (5, 0, "park"),
        (0, 4, "house"),
        (1, 3, "factory"),
    ]:
        rejects_value_error(
            lambda: model.place_building(city, x, y, kind),
            "설치 불가: " + repr((x, y, kind)),
        )
        same(city, before, "실패한 설치는 객체와 셀 모두 변경하지 않음")

    city["day"] = 1
    before = deepcopy(city)
    rejects_value_error(lambda: model.place_building(city, 0, 3, "house"), "실행 후 건물 설치")
    same(city, before, "실행 후 건물 설치 거절은 상태를 바꾸지 않음")


def check_stage_4():
    city = city_data.make_city()
    same(model.eligible(city, city["buildings"]["A"]), True, "A는 입주 조건 충족")
    same(model.eligible(city, city["buildings"]["B"]), True, "B는 입주 조건 충족")
    same(
        model.eligible(city, city["buildings"]["P"]),
        False,
        "공원은 입주 대상 주택 아님",
    )
    before = deepcopy(city)
    model.eligible(city, city["buildings"]["A"])
    same(city, before, "조건 조회는 상태를 바꾸지 않음")

    no_park = city_data.make_city(False)
    same(model.eligible(no_park, no_park["buildings"]["A"]), False, "공원 없음")

    city["external_power"] = False
    same(model.eligible(city, city["buildings"]["A"]), False, "전력 없음")

    city["external_power"] = True
    city["buildings"]["A"]["status"] = "construction"
    same(model.eligible(city, city["buildings"]["A"]), False, "주택 공사 중")

    city["buildings"]["A"]["status"] = "operating"
    city["buildings"]["P"]["status"] = "construction"
    same(model.eligible(city, city["buildings"]["A"]), False, "공원 공사 중")

    city["buildings"]["P"]["status"] = "operating"
    city["grid"][2][1]["road"] = False
    same(
        model.eligible(city, city["buildings"]["A"]),
        False,
        "대각선 도로만 있으면 접근 불가",
    )

    city["grid"][2][1]["road"] = True
    city["rules"]["park_radius"] = 0
    same(model.eligible(city, city["buildings"]["A"]), False, "공원 거리 제한 적용")

    city["rules"]["park_radius"] = 1
    same(model.eligible(city, city["buildings"]["A"]), True, "공원 반경의 경계는 포함")

    distant = city_data.make_empty_city()
    house_id = model.place_building(distant, 0, 0, "house")
    model.place_building(distant, 2, 2, "park")
    city_data.edit_road(distant, 1, 0)
    distant["rules"]["park_radius"] = 3
    same(
        model.eligible(distant, distant["buildings"][house_id]),
        False,
        "대각선 공원 (2,2)까지 맨해튼 거리 4: 반경 3 밖",
    )

    distant["rules"]["park_radius"] = 4
    same(
        model.eligible(distant, distant["buildings"][house_id]),
        True,
        "맨해튼 거리 4: 반경 4의 경계는 포함",
    )


def check_stage_5():
    city = city_data.make_city()
    house = city["buildings"]["A"]
    same(model.arrivals(city, house), 2, "하루 최대 2명 입주")

    house["population"] = 9
    before = deepcopy(city)
    same(model.arrivals(city, house), 1, "빈자리 1명만 남았을 때")
    same(city, before, "입주량 계산은 아직 인구를 변경하지 않음")

    house["population"] = 10
    same(model.arrivals(city, house), 0, "수용량에 도달했을 때")

    house["population"] = 6
    city["rules"]["growth_per_day"] = 3
    same(model.arrivals(city, house), 3, "규칙 값을 사용하며 2를 하드코딩하지 않음")

    city["external_power"] = False
    same(model.arrivals(city, house), 0, "조건을 충족하지 않으면 입주 0명")


def check_stage_6():
    old = city_data.make_city()
    before = deepcopy(old)
    day1 = model.step(old)
    same(old, before, "step은 입력 상태를 변경하지 않음")
    same(day1["day"], 1, "하루 경과")
    same(day1["buildings"]["A"]["population"], 8, "1일 후 A 인구")
    same(day1["buildings"]["B"]["population"], 10, "1일 후 B 인구")
    same(model.total_population(day1), 18, "1일 후 총인구")
    same(day1["budget"], 132, "세금은 하루 시작 인구 14명 기준: 100+42-10")

    day2 = model.step(day1)
    same(day2["day"], 2, "이틀 경과")
    same(model.total_population(day2), 20, "2일 후 총인구")
    same(day2["budget"], 176, "두 번째 날 예산: 132+54-10")
    same(day1["budget"], 132, "두 번째 실행도 이전 상태 보존")

    day2["grid"][0][0]["road"] = True
    day2["rules"]["growth_per_day"] = 9
    day2["buildings"]["A"]["population"] = 0
    same(day1["grid"][0][0]["road"], False, "격자도 독립 복사")
    same(day1["rules"]["growth_per_day"], 2, "규칙도 독립 복사")
    same(day1["buildings"]["A"]["population"], 8, "객체도 독립 복사")

    without = model.step(model.step(city_data.make_city(False)))
    same(
        (model.total_population(without), without["budget"]),
        (14, 164),
        "공원 없는 비교 실험",
    )

    reordered = city_data.make_city()
    reordered["buildings"] = dict(reversed(list(reordered["buildings"].items())))
    same(
        model.step(reordered),
        model.step(city_data.make_city()),
        "객체 순회 순서에 독립적인 결과",
    )

    changed_rules = city_data.make_city()
    changed_rules["rules"]["tax_per_person_day"] = 1
    changed_rules["rules"]["maintenance_per_day"] = 5
    same(model.step(changed_rules)["budget"], 109, "재정 규칙 값을 사용")

    invalid = city_data.make_city()
    invalid["buildings"]["A"]["population"] = 11
    before = deepcopy(invalid)
    rejects_value_error(lambda: model.step(invalid), "잘못된 상태의 실행 거절")
    same(invalid, before, "거절한 실행은 입력을 변경하지 않음")


STAGES = [
    ("TODO 1: 이웃 셀", check_stage_1),
    ("TODO 2: 총인구", check_stage_2),
    ("TODO 3: 건물 배치", check_stage_3),
    ("TODO 4: 입주 조건", check_stage_4),
    ("TODO 5: 입주량", check_stage_5),
    ("TODO 6: 하루 갱신", check_stage_6),
]


def main():
    parser = argparse.ArgumentParser(description="Virtual City Modeling Lab")
    parser.add_argument(
        "--stage",
        type=int,
        choices=range(1, 7),
        default=6,
        help="1부터 이 단계까지 점검 (기본: 6)",
    )
    args = parser.parse_args()

    checks = [("제공 코드", check_support)] + STAGES[: args.stage]
    failed = False
    unfinished = False

    for name, check in checks:
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

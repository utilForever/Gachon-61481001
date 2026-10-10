"""
행위자 초기화, 통근 계산, 월별 실행, 상태 검증, JSON 저장 / 불러오기.

session["agents"]의 시민 / 가구 / 주택 / 기업 / 사업장은 ID로 연결한다.
한 달의 신청은 같은 시작 상태에서 모으고, 승인된 이동을 복사본에 반영한다.
검증을 마친 복사본만 입력 session에 반영하므로 계산 실패 시 기존 상태를 보존한다.
행위자의 월별 기록과 교통의 분 단위 기록은 따로 관리한다.
"""

import csv
import json
import random
from copy import deepcopy
from pathlib import Path

import agent_rules as rules
import kpi_support
import metrics
from model import neighbors4
from routing import dijkstra_all
from traffic import build_road_graph
from traffic_data import cost_snapshot, sync_transport


def make_session(scenario="default"):
    """시민 3명 / 가구 2개 / 기업 1개로 시작하는 독립적인 실험 상태를 만든다."""
    session = kpi_support.make_lab_session("default")
    city = session["city"]
    for row in city["grid"]:
        for cell in row:
            cell.update(road=False, zone=None, building_id=None)
    city["buildings"] = {}

    for y in (1, 2):
        for x in range(4):
            city["grid"][y][x]["road"] = True

    for ident, x in (("A", 0), ("B", 2), ("C", 1), ("D", 3)):
        city["buildings"][ident] = dict(
            id=ident, kind="house", x=x, y=0, population=0, capacity=4, status="operating"
        )
        city["grid"][0][x].update(zone="R", building_id=ident)

    for ident, x in (("X", 3), ("Y", 0)):
        city["buildings"][ident] = dict(
            id=ident, kind="shop", x=x, y=3, workers=0, capacity=8, status="operating"
        )
        city["grid"][3][x].update(zone="C", building_id=ident)

    city["buildings"]["P"] = dict(id="P", kind="park", x=2, y=3, status="operating")
    city["grid"][3][2]["building_id"] = "P"

    session["transport"] = sync_transport(city, session["transport"])
    transport = session["transport"]
    transport["base_times"].update(
        {
            (0, 1): 10,
            (1, 1): 10,
            (2, 1): 15,
            (3, 1): 5,
            (0, 2): 5,
            (1, 2): 100,
            (2, 2): 100,
            (3, 2): 15,
        }
    )
    transport["selected_road"] = (1, 1)
    if scenario == "congested":
        transport["queues"][(1, 1)] = 100
    elif scenario == "disconnected":
        for x in range(4):
            city["grid"][2][x]["road"] = False
        session["transport"] = sync_transport(city, transport)

    state = {
        "month": 0,
        "seed": 42,
        "history": [],
        "events": [],
        "citizens": {
            "P1": {"household_id": "H1", "employer_id": "F1"},
            "P2": {"household_id": "H1", "employer_id": None},
            "P3": {"household_id": "H2", "employer_id": "F1"},
        },
        "households": {
            "H1": dict(
                home_id="A",
                members=["P1", "P2"],
                income=200,
                rent_budget=100,
                savings=150,
                move_cost=30,
                dissatisfied_months=0,
                cooldown=0,
            ),
            "H2": dict(
                home_id="D",
                members=["P3"],
                income=240,
                rent_budget=120,
                savings=100,
                move_cost=30,
                dissatisfied_months=0,
                cooldown=0,
            ),
        },
        "houses": {
            "A": dict(rent=80, environment=50, occupant="H1"),
            "B": dict(rent=100, environment=70, occupant=None),
            "C": dict(rent=130, environment=60, occupant=None),
            "D": dict(rent=90, environment=80, occupant="H2"),
        },
        "firms": {
            "F1": dict(site_id="X", employees=["P1", "P3"], profit=150, cash=700, move_cost=500)
        },
        "sites": {"X": dict(occupant="F1", profit=150), "Y": dict(occupant=None, profit=260)},
    }

    session["agents"] = state
    session["settings"].update(
        scenario=scenario, commute_target="X", limit_minutes=30, protected=[(4, 3)]
    )
    session["history"] = []
    session["observations"] = []

    synchronize_buildings(session)
    return session


def synchronize_buildings(session):
    """가구원과 직원 목록을 기준으로 입력 도시의 건물 인구 / 고용 인원을 갱신한다."""
    city, state = session["city"], session["agents"]
    for building in city["buildings"].values():
        if building["kind"] == "house":
            building["population"] = 0
        elif building["kind"] in ("shop", "factory"):
            building["workers"] = 0

    for household in state["households"].values():
        city["buildings"][household["home_id"]]["population"] += len(household["members"])

    for firm in state["firms"].values():
        city["buildings"][firm["site_id"]]["workers"] += len(firm["employees"])


def travel_time(session, home_id, site_id):
    """주택과 사업장 사이의 최소 통근 시간을 반환한다. 경로가 없으면 None이다."""
    city = session["city"]
    graph = build_road_graph(city)
    costs = cost_snapshot(session["transport"])

    def entrances(ident):
        building = city["buildings"][ident]
        return [node for node in neighbors4(city, building["x"], building["y"]) if node in graph]

    times = []
    for start in entrances(home_id):
        distances = dijkstra_all(graph, start, costs)
        times.extend(distances[goal] for goal in entrances(site_id) if goal in distances)

    return min(times) if times else None


def commute_records(session):
    """취업 시민마다 현재 주택과 사업장 사이의 통근 기록을 만든다."""
    state = session["agents"]
    result = []
    for ident, citizen in state["citizens"].items():
        employer = citizen["employer_id"]
        if employer is not None:
            home = state["households"][citizen["household_id"]]["home_id"]
            site = state["firms"][employer]["site_id"]
            result.append(
                dict(
                    citizen_id=ident,
                    home_id=home,
                    destination_id=site,
                    time_min=travel_time(session, home, site),
                )
            )

    return result


def household_commute(session, household_id, home_id):
    """취업 가구원의 평균 통근을 반환한다. 취업자가 없거나 도달 불가이면 None이다."""
    state = session["agents"]
    workers = [
        state["citizens"][ident]
        for ident in state["households"][household_id]["members"]
        if state["citizens"][ident]["employer_id"] is not None
    ]
    times = [
        travel_time(session, home_id, state["firms"][worker["employer_id"]]["site_id"])
        for worker in workers
    ]

    return sum(times) / len(times) if times and all(t is not None for t in times) else None


def score_home(session, household_id, home_id):
    """가구가 지정한 주택에 거주한다고 가정한 만족도를 반환한다. 상태는 유지한다."""
    state = session["agents"]
    household, home = state["households"][household_id], state["houses"][home_id]

    return rules.satisfaction(
        household_commute(session, household_id, home_id),
        home["rent"],
        household["income"],
        home["environment"],
    )


def home_candidates(session, household_id):
    """현재 주택을 제외하고 정해진 조사 순서로 후보의 입주 가능 여부와 점수를 만든다."""
    state = session["agents"]
    household = state["households"][household_id]
    candidates = []

    # 정해진 조사 순서를 유지한다. 선택 규칙에서 최대 세 후보만 검토한다.
    for ident in ("B", "C", "D", "A"):
        if ident == household["home_id"]:
            continue

        home, building = state["houses"][ident], session["city"]["buildings"][ident]
        feasible = (
            home["occupant"] is None
            and home["rent"] <= household["rent_budget"]
            and len(household["members"]) <= building["capacity"]
            and building["status"] == "operating"
            and household_commute(session, household_id, ident) is not None
        )
        candidates.append(
            dict(home_id=ident, feasible=feasible, score=score_home(session, household_id, ident))
        )

    return candidates


def validate_agents(session):
    """도시 / 교통 상태와 소속 / 입주 / 고용 참조, 인원과 자금의 일관성을 검증한다."""
    from traffic_data import validate_transport

    validate_transport(session["city"], session["transport"])
    state = session["agents"]
    seen = set()
    for ident, household in state["households"].items():
        assert state["houses"][household["home_id"]]["occupant"] == ident, "가구 / 주택 참조 불일치"
        assert household["savings"] >= 0 and household["cooldown"] >= 0
        for person in household["members"]:
            assert person not in seen, "시민의 가구 중복"
            seen.add(person)
            assert state["citizens"][person]["household_id"] == ident
    assert seen == set(state["citizens"])

    for home_id, home in state["houses"].items():
        occupant = home["occupant"]
        expected = 0 if occupant is None else len(state["households"][occupant]["members"])
        assert session["city"]["buildings"][home_id]["population"] == expected

    employed = set()
    for ident, firm in state["firms"].items():
        assert state["sites"][firm["site_id"]]["occupant"] == ident
        assert firm["cash"] >= 0
        for person in firm["employees"]:
            assert person not in employed
            employed.add(person)
            assert state["citizens"][person]["employer_id"] == ident
    assert employed == {p for p, c in state["citizens"].items() if c["employer_id"] is not None}

    for site_id, site in state["sites"].items():
        occupant = site["occupant"]
        if occupant is None:
            expected = 0
        else:
            assert state["firms"][occupant]["site_id"] == site_id, "기업 / 사업장 참조 불일치"
            expected = len(state["firms"][occupant]["employees"])
        assert session["city"]["buildings"][site_id]["workers"] == expected


def monthly_snapshot(session):
    """현재 월의 가구 / 기업 상태와 통근 지표를 기록용 dict로 반환한다."""
    state = session["agents"]
    scores = {
        ident: score_home(session, ident, h["home_id"]) for ident, h in state["households"].items()
    }
    times = [trip["time_min"] for trip in commute_records(session) if trip["time_min"] is not None]

    return dict(
        month=state["month"],
        H1_home=state["households"]["H1"]["home_id"],
        H1_score=scores["H1"],
        H1_savings=state["households"]["H1"]["savings"],
        F1_site=state["firms"]["F1"]["site_id"],
        F1_cash=state["firms"]["F1"]["cash"],
        mean_commute=sum(times) / len(times) if times else None,
        dissatisfied=sum(s < 50 for s in scores.values()),
    )


def advance_month(session):
    """한 달의 계산과 검증을 마친 뒤 입력 상태를 갱신한다. 실패하면 원본을 보존한다."""
    # 복사본에서 계산을 끝낸 후 반영하므로 미완성 함수가 원본을 바꾸지 않는다.
    candidate = deepcopy(session)
    state = candidate["agents"]
    state["month"] += 1
    if not state["history"]:
        state["history"].append(monthly_snapshot(session))

    blocked = set()
    for ident, household in state["households"].items():
        current = score_home(candidate, ident, household["home_id"])
        if household["cooldown"] > 0:
            blocked.add(ident)
            household["cooldown"] -= 1
        household["dissatisfied_months"] = (
            household["dissatisfied_months"] + 1 if current < 50 else 0
        )

    proposals = {}
    for ident, household in state["households"].items():
        current = score_home(candidate, ident, household["home_id"])
        if ident not in blocked and rules.should_move(household):
            home = rules.choose_home(household, home_candidates(candidate, ident), current)
            if home is not None:
                proposals.setdefault(home["home_id"], []).append(ident)

    # 같은 월초 상태에서 신청을 모으고, 한 주택에 한 가구만 승인한다.
    rng = random.Random(state["seed"] + state["month"])
    for destination in sorted(proposals):
        applicants = sorted(proposals[destination])
        ident = rng.choice(applicants)
        origin = state["households"][ident]["home_id"]
        rules.move_household(state, ident, destination)
        state["events"].append(f"{state['month']}개월: {ident} {origin} → {destination}")

    # 분기마다 검토하되, 순편익은 앞으로의 6개월을 기준으로 계산한다.
    if state["month"] % 3 == 0:
        for ident, firm in state["firms"].items():
            candidates = [
                (site["profit"], name)
                for name, site in state["sites"].items()
                if site["occupant"] is None
                and candidate["city"]["buildings"][name]["status"] == "operating"
                and len(firm["employees"]) <= candidate["city"]["buildings"][name]["capacity"]
            ]
            if candidates:
                profit, destination = max(candidates)
                if rules.should_move_firm(firm, profit):
                    origin = firm["site_id"]
                    rules.move_firm(state, ident, destination)
                    state["events"].append(
                        f"{state['month']}개월: {ident} {origin} → {destination}"
                    )

    synchronize_buildings(candidate)
    validate_agents(candidate)
    state["history"].append(monthly_snapshot(candidate))

    # 월별 기록과 분 단위 교통 실험의 기록은 섞지 않는다.
    candidate["history"] = []
    session.clear()
    session.update(candidate)


def calculate_kpis(session):
    """현재 시민의 통근과 도시 / 교통 상태에서 지표를 계산한다. 입력은 유지한다."""
    result = {key: None for key in kpi_support.KPI_KEYS}
    trips = commute_records(session)
    result.update(metrics.summarize_city(session["city"]))
    result.update(metrics.summarize_trips(trips, session["settings"]["limit_minutes"]))
    result.update(kpi_support.distribution_stats(trips))
    cells = metrics.find_developable_cells(session["city"], session["settings"]["protected"])
    result.update(developable_cells=cells, developable_count=len(cells))
    result.update(
        metrics.summarize_congestion(
            session["observations"], session["settings"]["queue_threshold"]
        )
    )

    selected = session["transport"]["selected_road"]
    result.update(current_queue=session["transport"]["queues"].get(selected), _errors=[])

    return result


def record_current(session):
    """현재 분의 지표를 계산하고 입력 상태의 기록에 추가한다. 중복 시각은 유지한다."""
    values = calculate_kpis(session)
    metrics.append_history(
        session["history"],
        session["transport"]["minute"],
        {key: value for key, value in values.items() if key != "_errors"},
    )
    return values


def save_session(session, path):
    """검증한 도시 / 교통 / 행위자 상태를 UTF-8 JSON으로 저장한다."""
    validate_agents(session)
    base = {key: value for key, value in session.items() if key != "agents"}
    document = kpi_support._to_json_document({"format": "virtual-city-abm-v1", **deepcopy(base)})
    document["agents"] = deepcopy(session["agents"])
    Path(path).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_session(path):
    """JSON의 도시 / 교통 / 행위자 상태를 복원하고 검증한 뒤 반환한다."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("format") != "virtual-city-abm-v1":
        raise ValueError("행위자 도시 상태 파일이 아닙니다.")

    agents = document.pop("agents")
    document["format"] = "virtual-city-kpi-v1"
    session = kpi_support.restore_session(kpi_support._from_json_document(document))
    session["agents"] = agents
    validate_agents(session)
    return session


def export_months(session, path):
    """월별 기록을 CSV로 저장한다. 아직 기록이 없으면 ValueError를 발생시킨다."""
    rows = session["agents"]["history"]
    if not rows:
        raise ValueError("내보낼 월별 기록이 없습니다. 먼저 1개월 진행하세요.")

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

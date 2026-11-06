"""
도시 상태 표시, 지도 색상, 시계열 / 이벤트 조회, 좌표 변환, 관측값 갱신 규칙.

- 실습 진행 방법
1. TODO 1부터 6까지 순서대로 작성하세요. 자세한 힌트는 각 함수의 주석에 있습니다.
2. pass는 코드를 작성할 빈자리입니다. 주석만 있는 TODO는 그 아래에 코드를 추가하세요.
3. 한 함수를 완성했다면 그 함수의 raise NotImplementedError(...) 한 줄을 삭제하세요.
   이 줄이 남아 있으면 함수 실행이 그 자리에서 멈추므로 아래 코드는 실행되지 않습니다.
4. 파일을 저장하고 README.md가 있는 폴더에서 다음 명령으로 확인하세요.
   python skeleton/checks_interface.py --stage 1
   끝낸 단계에 맞춰 숫자를 2~6으로 바꾸면 1단계부터 그 단계까지 함께 검사합니다.
   [미구현]은 아직 남은 NotImplementedError, [실패]는 결과 불일치나 실행 오류입니다.

- 데이터를 읽을 때
hour는 모형의 서비스 경과 시간이고, observed_at은 당일 0시부터 지난 분입니다.
0은 유효한 값이며 None은 결측 또는 경로 없음을 나타냅니다.
공간 좌표는 (x, y)이지만 화면의 셀은 (행, 열)로 반환하며, 0행은 맨 위입니다.
여섯 함수 모두 입력을 보존합니다. 관측값은 모형 계산값과 별도로 관리합니다.
"""


def build_selection_info(feature, hour):
    """시설 정보와 경과 시간을 받아 표시 문구를 담은 새 dict를 반환한다."""
    raise NotImplementedError("TODO 1: build_selection_info")

    # TODO 1-A: feature["value"]를 읽어 값과 단위를 표시할 문구를 만드세요.
    # 1. 값이 None이면 feature의 missing_label을 사용하고, 없으면 "자료 없음"으로 표시하세요.
    # 2. 숫자이면 feature["unit"]을 바로 붙이세요. 14와 "명"이면 "14명"입니다.
    #    f-string의 :g 형식을 쓰면 14.0의 불필요한 소수점을 생략할 수 있습니다.
    # if value로 판단하면 0도 빠집니다. None인지 직접 확인하세요.

    # TODO 1-B: 다음 다섯 항목을 담은 새 dict를 반환하세요.
    # title은 feature["name"], metric은 feature["metric"]을 그대로 사용하세요.
    # time_label은 "6시간째"처럼 hour를 표시하고, value_label은 1-A의 문구입니다.
    # source_label은 source가 "simulation"이면 "모형 계산값",
    # "observation"이면 "예제 관측값"입니다. 원본 feature는 수정하지 마세요.
    pass


def layer_style(value):
    """접근시간에 맞는 color / label을 반환한다. None은 경로 없음이다."""
    raise NotImplementedError("TODO 2: layer_style")

    # TODO 2: 고정된 구간에 따라 색상과 문구를 담은 dict를 반환하세요.
    # None:       color="#767676", label="경로 없음"
    # 5분 이하:   color="#107C10", label="5분 이하"
    # 15분 이하:  color="#0078D4", label="5분 초과~15분 이하"
    # 15분 초과:  color="#CA5010", label="15분 초과"
    # None을 숫자와 비교하지 않도록 먼저 처리하고, 작은 시간 구간부터 확인하세요.
    # 확인 예: 0과 5는 초록, 5.01과 15는 파랑입니다. 색상과 문구를 함께 반환하세요.
    pass


def build_time_series(history, key):
    """입력 순서대로 (hour, 값) 목록을 반환한다. 없는 키의 값은 None이다."""
    raise NotImplementedError("TODO 3: build_time_series")

    points = []

    for row in history:
        # TODO 3: 이 기록의 시각과 값을 하나의 튜플로 묶어 points에 추가하세요.
        # row["hour"]는 실제 기록 시각입니다. 반복문의 순번으로 바꾸지 마세요.
        # row.get(key)를 사용하면 해당 키가 없을 때 None을 얻을 수 있습니다.
        # 확인 예: 시각이 0, 2, 5이면 그대로 유지하고, 값 0과 None도 바꾸지 않습니다.
        # 입력은 이미 시간순입니다. 정렬하거나 빠진 시각의 자료를 만들지 마세요.
        pass

    return points


def find_events(events, hour, target_id):
    """같은 시각 / 대상의 이벤트를 입력 순서대로 반환한다. 없으면 빈 목록이다."""
    raise NotImplementedError("TODO 4: find_events")

    selected = []

    for event in events:
        # TODO 4: 시각과 대상이 모두 일치하는 event만 selected에 추가하세요.
        # event["hour"]와 hour, event["target_id"]와 target_id를 각각 비교하세요.
        # 두 조건은 and로 연결합니다. 같은 시각이라도 다른 시설의 기록은 제외합니다.
        # message만 꺼내지 말고 이벤트 dict 전체를 추가하세요. 원본 목록은 수정하지 마세요.
        pass

    return selected


def point_to_cell(x, y, origin_x, origin_y, cell_size, rows, cols):
    """왼쪽 아래 원점의 좌표를 화면의 (행, 열)로 바꾼다. 지도 밖이면 None이다."""
    raise NotImplementedError("TODO 5: point_to_cell")

    # TODO 5: 원점 이동, 지도 범위 확인, 행 / 열 계산 순서로 작성하세요.
    # 1. x에서 origin_x를, y에서 origin_y를 빼 local_x, local_y를 구하세요.
    # 2. 가로 범위는 0 <= local_x < cols * cell_size,
    #    세로 범위는 0 <= local_y < rows * cell_size입니다. 밖이면 None을 반환하세요.
    # 3. local_x를 cell_size로 나눈 몫이 열입니다. //와 int(...)를 사용할 수 있습니다.
    # 4. 세로도 몫을 구하되, 화면의 0행이 위쪽이므로 rows - 1에서 그 몫을 빼세요.
    # 5. 정수 (행, 열) 튜플을 반환하세요. (x, y) 순서와 혼동하지 마세요.
    # 확인 예: 원점 (0, 0), 20m 셀, 4행 / 5열이면 (45, 30)은 (2, 2)입니다.
    # 오른쪽 / 위쪽 경계는 제외합니다. (100, 20)은 None이며 가장자리로 옮기지 않습니다.
    pass


def apply_observation(current, incoming):
    """반영 여부 / 이유와 독립적인 상태 dict를 반환한다. 두 입력은 보존한다."""
    raise NotImplementedError("TODO 6: apply_observation")

    state = current.copy()
    reason = "applied"

    # TODO 6-A: 다음 순서로 거절 조건을 확인하고 reason을 바꾸세요.
    # 1. target_id가 다르면 "target_mismatch", unit이 다르면 "unit_mismatch"입니다.
    # 2. incoming["value"]가 None이면 "missing"입니다. 0은 정상 관측값입니다.
    # 3. 현재 observed_at이 None이 아닐 때만 새 관측 시각과 비교하세요.
    #    새 시각이 더 작으면 "stale", 같으면 "duplicate"입니다.
    # if / elif로 연결해 먼저 발견한 이유를 유지하세요. received_at으로 비교하지 마세요.
    # 현재 관측 시각이 None이면 앞의 조건을 만족한 첫 관측을 반영합니다.
    pass

    # TODO 6-B: reason이 "applied"일 때만 incoming의 복사본을 state에 넣으세요.
    # 반영하지 않으면 위에서 만든 current의 복사본을 그대로 사용합니다.
    # state = incoming으로 연결하면 같은 dict를 공유합니다. .copy()를 사용하세요.
    # 아래 반환 형식은 제공되어 있습니다. current와 incoming은 직접 바꾸지 마세요.
    pass

    return {"state": state, "accepted": reason == "applied", "reason": reason}

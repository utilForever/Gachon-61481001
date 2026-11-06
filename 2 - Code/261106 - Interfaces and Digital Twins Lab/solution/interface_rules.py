"""
도시 상태 표시, 지도 색상, 시계열 / 이벤트 조회, 좌표 변환, 관측값 갱신 규칙.

여섯 함수 모두 입력을 보존한다. 0은 유효한 값이고 None은 결측 또는 경로 없음이다.
공간 좌표는 (x, y), 화면의 셀은 (행, 열)이며 0행은 맨 위이다.
hour는 모형의 경과 시간, observed_at은 당일 0시부터 지난 분으로 서로 구분한다.
"""


def build_selection_info(feature, hour):
    """시설 정보와 경과 시간을 받아 표시 문구를 담은 새 dict를 반환한다."""
    value = feature["value"]
    # 0명도 유효한 값이므로 None만 결측으로 처리한다.
    if value is None:
        value_label = feature.get("missing_label", "자료 없음")
    else:
        value_label = f"{value:g}{feature['unit']}"

    sources = {"simulation": "모형 계산값", "observation": "예제 관측값"}
    return {
        "title": feature["name"],
        "metric": feature["metric"],
        "time_label": f"{hour}시간째",
        "value_label": value_label,
        "source_label": sources[feature["source"]],
    }


def layer_style(value):
    """접근시간에 맞는 color / label을 반환한다. None은 경로 없음이다."""
    if value is None:
        return {"color": "#767676", "label": "경로 없음"}
    if value <= 5:
        return {"color": "#107C10", "label": "5분 이하"}
    if value <= 15:
        return {"color": "#0078D4", "label": "5분 초과~15분 이하"}

    return {"color": "#CA5010", "label": "15분 초과"}


def build_time_series(history, key):
    """입력 순서대로 (hour, 값) 목록을 반환한다. 없는 키의 값은 None이다."""
    points = []
    for row in history:
        points.append((row["hour"], row.get(key)))

    return points


def find_events(events, hour, target_id):
    """같은 시각 / 대상의 이벤트를 입력 순서대로 반환한다. 없으면 빈 목록이다."""
    selected = []
    for event in events:
        if event["hour"] == hour and event["target_id"] == target_id:
            selected.append(event)

    return selected


def point_to_cell(x, y, origin_x, origin_y, cell_size, rows, cols):
    """왼쪽 아래 원점의 좌표를 화면의 (행, 열)로 바꾼다. 지도 밖이면 None이다."""
    local_x = x - origin_x
    local_y = y - origin_y
    if not (0 <= local_x < cols * cell_size):
        return None
    if not (0 <= local_y < rows * cell_size):
        return None

    col = int(local_x // cell_size)
    # 공간 좌표의 y는 위로 증가하지만 화면의 행은 아래로 증가한다.
    row = rows - 1 - int(local_y // cell_size)
    return (row, col)


def apply_observation(current, incoming):
    """반영 여부 / 이유와 독립적인 상태 dict를 반환한다. 두 입력은 보존한다."""
    state = current.copy()
    reason = "applied"

    if incoming["target_id"] != current["target_id"]:
        reason = "target_mismatch"
    elif incoming["unit"] != current["unit"]:
        reason = "unit_mismatch"
    elif incoming["value"] is None:
        reason = "missing"
    elif current["observed_at"] is not None:
        # 늦게 도착한 과거 자료가 최신 상태를 덮지 않도록 관측 시각을 비교한다.
        if incoming["observed_at"] < current["observed_at"]:
            reason = "stale"
        elif incoming["observed_at"] == current["observed_at"]:
            reason = "duplicate"

    if reason == "applied":
        # 호출자가 반환 상태를 바꿔도 입력 관측은 바뀌지 않아야 한다.
        state = incoming.copy()

    return {"state": state, "accepted": reason == "applied", "reason": reason}

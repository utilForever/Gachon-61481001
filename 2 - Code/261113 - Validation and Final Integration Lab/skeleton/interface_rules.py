"""선택 정보, 지도 좌표, 시계열과 관측 자료 적용 여부를 계산하는 규칙."""


def build_selection_info(feature, hour):
    value = feature["value"]
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
    if value is None:
        return {"color": "#767676", "label": "경로 없음"}
    if value <= 5:
        return {"color": "#107C10", "label": "5분 이하"}
    if value <= 15:
        return {"color": "#0078D4", "label": "5분 초과~15분 이하"}

    return {"color": "#CA5010", "label": "15분 초과"}


def build_time_series(history, key):
    points = []

    for row in history:
        points.append((row["hour"], row.get(key)))

    return points


def find_events(events, hour, target_id):
    selected = []

    for event in events:
        if event["hour"] == hour and event["target_id"] == target_id:
            selected.append(event)

    return selected


def point_to_cell(x, y, origin_x, origin_y, cell_size, rows, cols):
    local_x = x - origin_x
    local_y = y - origin_y
    if not (0 <= local_x < cols * cell_size):
        return None
    if not (0 <= local_y < rows * cell_size):
        return None

    col = int(local_x // cell_size)
    row = rows - 1 - int(local_y // cell_size)

    return (row, col)


def apply_observation(current, incoming):
    state = current.copy()
    reason = "applied"
    if incoming["target_id"] != current["target_id"]:
        reason = "target_mismatch"
    elif incoming["unit"] != current["unit"]:
        reason = "unit_mismatch"
    elif incoming["value"] is None:
        reason = "missing"
    elif current["observed_at"] is not None:
        if incoming["observed_at"] < current["observed_at"]:
            reason = "stale"
        elif incoming["observed_at"] == current["observed_at"]:
            reason = "duplicate"

    if reason == "applied":
        state = incoming.copy()

    return {"state": state, "accepted": reason == "applied", "reason": reason}

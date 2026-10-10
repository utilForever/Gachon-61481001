"""도시 편집기와 도로망 분석 화면."""

from copy import deepcopy
import tkinter as tk
from tkinter import filedialog, ttk
import traceback

import city_data
from gui import CityApp
import routing
import traffic
import traffic_data


class TrafficApp:
    CELL = 84
    LEFT = 38
    TOP = 30

    def __init__(self, root):
        self.root = root
        root.title("가상 도시 / 도로망과 교통")
        root.geometry("1200x800")
        root.minsize(1160, 780)
        CityApp._set_fonts(self)

        self.city, self.transport = traffic_data.make_scenario()
        self.baseline = deepcopy(self.transport)
        self.selected = self.transport["selected_road"]
        self.graph = None
        self.components = None
        self.results = {}
        self.path = None
        self.active_algorithm = ""
        self.history = []

        self.mode = tk.StringVar(value="queue")
        self.summary = tk.StringVar(
            value="도로망을 분석하면 연결 요소와 경로를 확인할 수 있습니다."
        )
        self.status = tk.StringVar(value="기본 도시를 불러왔습니다. ‘도로망 분석’부터 시작하세요.")
        self.route_text = tk.StringVar(value="계산한 경로를 선택하면 지도에 표시합니다.")
        self.queue_text = tk.StringVar()
        self.inspector = tk.StringVar()
        self.access_text = tk.StringVar(
            value="출발 도로에서 4분 이내에 갈 수 있는 일자리를 계산합니다."
        )
        self.arrivals_input = tk.StringVar(value="8")
        self.capacity_input = tk.StringVar(value="5")
        self.queue_input = tk.StringVar(value="0")
        self.time_limit = tk.StringVar(value="4")

        self._make_widgets()
        self.refresh()

    def _make_widgets(self):
        outer = ttk.Frame(self.root, padding=(12, 8))
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x", pady=(0, 8))
        ttk.Label(heading, text="도로망과 교통", style="Title.TLabel").pack(side="left")
        ttk.Label(heading, text="도시 지도 / 경로 / 선택 도로의 대기열").pack(side="right")

        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x")
        ttk.Separator(footer).pack(fill="x", pady=(7, 4))
        ttk.Label(footer, textvariable=self.status, foreground="#15517a", wraplength=1140).pack(
            anchor="w"
        )

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        for label, preset in (
            ("기본 도시", "default"),
            ("혼잡 도시", "congested"),
            ("단절 도시", "disconnected"),
        ):
            ttk.Button(toolbar, text=label, command=lambda name=preset: self.use_preset(name)).pack(
                side="left", padx=(0, 6)
            )
        ttk.Button(toolbar, text="도시 편집", command=self.open_city_editor).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(toolbar, text="불러오기", command=self.load_file).pack(side="right")
        ttk.Button(toolbar, text="저장", command=self.save_file).pack(side="right", padx=(0, 6))

        modes = ttk.Frame(outer)
        modes.pack(fill="x", pady=(0, 7))
        ttk.Label(modes, text="지도에서 선택  ").pack(side="left")
        for label, value in (
            ("대기열 도로", "queue"),
            ("출발 도로 S", "start"),
            ("도착 도로 T", "goal"),
            ("셀 조회", "inspect"),
        ):
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode).pack(
                side="left", padx=(0, 14)
            )
        ttk.Label(modes, text="이동: 상하좌우 / 도로 한 구간: 100 m").pack(side="right")

        body = ttk.Frame(outer)
        body.pack(fill="x")
        map_side = ttk.Frame(body)
        map_side.pack(side="left", anchor="n")
        self.canvas = tk.Canvas(
            map_side,
            width=470,
            height=375,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8bec4",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.click_map)
        ttk.Label(map_side, text="S: 출발 / T: 도착 / 붉은 테두리: 대기열을 관찰할 도로").pack(
            anchor="w", pady=(5, 0)
        )
        ttk.Label(map_side, text="H: 주택 / J: 상점 / F: 공장 / P: 공원").pack(
            anchor="w", pady=(2, 0)
        )

        right = ttk.Frame(body, padding=(15, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        actions = ttk.Frame(right)
        actions.pack(fill="x")
        ttk.Button(actions, text="도로망 분석", command=self.analyze_graph).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="경로 비교", command=self.compare_paths).pack(side="left")
        ttk.Label(right, textvariable=self.summary, wraplength=640).pack(anchor="w", pady=(8, 7))

        self.path_tree = ttk.Treeview(
            right,
            columns=("algorithm", "distance", "time", "result"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        for key, title, width in (
            ("algorithm", "알고리즘", 135),
            ("distance", "이동거리", 100),
            ("time", "예상 시간", 105),
            ("result", "도달 여부", 100),
        ):
            self.path_tree.heading(key, text=title)
            self.path_tree.column(key, anchor="center", width=width, stretch=True)
        self.path_tree.pack(fill="x")
        self.path_tree.bind("<<TreeviewSelect>>", self.select_path)
        for name in ("BFS", "Dijkstra", "A*"):
            self.path_tree.insert("", "end", iid=name, values=(name, "—", "—", "—"))
        ttk.Label(right, textvariable=self.route_text, wraplength=640, foreground="#15517a").pack(
            anchor="w", pady=(6, 7)
        )

        accessibility = ttk.LabelFrame(right, text="일자리 접근성", padding=(9, 5))
        accessibility.pack(fill="x", pady=(0, 7))
        access_controls = ttk.Frame(accessibility)
        access_controls.pack(fill="x")
        ttk.Label(access_controls, text="시간 한도 ").pack(side="left")
        ttk.Entry(access_controls, textvariable=self.time_limit, width=5, justify="right").pack(
            side="left"
        )
        ttk.Label(access_controls, text=" 분").pack(side="left")
        ttk.Button(access_controls, text="계산", command=self.calculate_accessibility).pack(
            side="right"
        )
        ttk.Label(accessibility, textvariable=self.access_text, wraplength=605).pack(
            anchor="w", pady=(3, 0)
        )

        inspector_box = ttk.LabelFrame(right, text="선택한 셀", padding=(9, 7))
        inspector_box.pack(fill="x")
        ttk.Label(inspector_box, textvariable=self.inspector, wraplength=620).pack(anchor="w")

        queue_box = ttk.LabelFrame(outer, text="선택 도로의 대기열", padding=(9, 6))
        queue_box.pack(fill="both", expand=True, pady=(9, 0))
        controls = ttk.Frame(queue_box)
        controls.pack(fill="x")
        for label, variable, unit in (
            ("유입", self.arrivals_input, "대/분"),
            ("처리 용량", self.capacity_input, "대/분"),
            ("대기", self.queue_input, "대"),
        ):
            ttk.Label(controls, text=label + " ").pack(side="left")
            ttk.Entry(controls, textvariable=variable, width=5, justify="right").pack(side="left")
            ttk.Label(controls, text=" " + unit + "   ").pack(side="left")
        ttk.Button(controls, text="값 적용", command=self.apply_queue_values).pack(side="left")
        ttk.Button(controls, text="대기열 초기화", command=self.reset_queue).pack(side="right")
        ttk.Button(controls, text="1분 진행", command=self.advance_minute).pack(
            side="right", padx=(0, 6)
        )

        summary_row = ttk.Frame(queue_box)
        summary_row.pack(fill="x", pady=(5, 5))
        ttk.Label(summary_row, textvariable=self.queue_text, style="Stats.TLabel").pack(side="left")
        ttk.Label(summary_row, text="예상 시간은 현재 대기열을 기준으로 계산합니다.").pack(
            side="right"
        )

        history_frame = ttk.Frame(queue_box)
        history_frame.pack(fill="both", expand=True)
        self.queue_tree = ttk.Treeview(
            history_frame,
            columns=("minute", "road", "arrivals", "served", "queue"),
            show="headings",
            height=3,
        )
        for key, title in (
            ("minute", "시간(분)"),
            ("road", "관찰 도로"),
            ("arrivals", "유입(대)"),
            ("served", "처리(대)"),
            ("queue", "남은 대기(대)"),
        ):
            self.queue_tree.heading(key, text=title)
            self.queue_tree.column(key, anchor="center", width=130, stretch=True)
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.queue_tree.pack(side="left", fill="both", expand=True)

    def _fail(self, action, error):
        if isinstance(error, NotImplementedError):
            self.status.set(f"{action}: {error or '해당 TODO를 먼저 작성하세요.'}")
        else:
            self.status.set(f"{action} 실패: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)

    def _invalidate(self):
        self.graph = None
        self.components = None
        self.results = {}
        self.path = None
        self.active_algorithm = ""
        self.summary.set("도로망을 분석하면 연결 요소와 경로를 확인할 수 있습니다.")
        self.route_text.set("계산한 경로를 선택하면 지도에 표시합니다.")
        self.access_text.set("출발 도로와 현재 이동시간을 기준으로 계산합니다.")
        for name in ("BFS", "Dijkstra", "A*"):
            self.path_tree.item(name, values=(name, "—", "—", "—"))

    def refresh(self):
        state = self.transport

        road = state["selected_road"]
        self.arrivals_input.set(str(state["arrivals"]))
        self.capacity_input.set(str(state["capacities"].get(road, 0)))
        self.queue_input.set(str(state["queues"].get(road, 0)))
        self.queue_text.set(
            f"{state['minute']}분 / 도로 {road} / 대기 {state['queues'].get(road, 0)}대"
        )

        if self.selected is None:
            self.inspector.set("선택한 셀이 없습니다. 도시 편집기에서 도로를 배치하세요.")
        else:
            x, y = self.selected
            cell = self.city["grid"][y][x]
            if cell["road"]:
                base = state["base_times"][(x, y)]
                capacity = state["capacities"][(x, y)]
                queue = state["queues"][(x, y)]
                self.inspector.set(
                    f"도로 ({x}, {y}) / 기본 통과 시간 {base:g}분\n처리 용량 {capacity}대/분 / 대기 {queue}대"
                )
            else:
                building = self.city["buildings"].get(cell["building_id"])
                label = (
                    {"house": "주택", "shop": "상점", "factory": "공장", "park": "공원"}.get(
                        building["kind"], ""
                    )
                    if building
                    else ("물" if cell["terrain"] == "water" else "빈 땅")
                )
                self.inspector.set(
                    f"셀 ({x}, {y}) / {label}\n출발 / 도착 / 대기열 관찰은 도로 셀을 선택하세요."
                )
        self._draw_map()

    def _draw_map(self):
        # 지난주 도시 편집기의 지도 표시를 재사용한다.
        CityApp._draw_map(self)
        canvas = self.canvas
        state = self.transport
        centers = lambda node: (
            self.LEFT + (node[0] + 0.5) * self.CELL,
            self.TOP + (node[1] + 0.5) * self.CELL,
        )

        if self.graph is not None:
            for node, neighbors in self.graph.items():
                for neighbor in neighbors:
                    if node < neighbor:
                        canvas.create_line(
                            *centers(node), *centers(neighbor), fill="#515d68", width=6
                        )
            colors = ("#487fb5", "#ab689f", "#59a48f", "#bc9850")
            if self.components is not None:
                for node, index in self.components.items():
                    x, y = centers(node)
                    canvas.create_oval(
                        x - 7,
                        y - 7,
                        x + 7,
                        y + 7,
                        fill=colors[index % len(colors)],
                        outline="white",
                        width=2,
                    )

        if self.path:
            for first, second in zip(self.path, self.path[1:]):
                canvas.create_line(*centers(first), *centers(second), fill="#1677c8", width=8)
            for node in self.path:
                x, y = centers(node)
                canvas.create_oval(
                    x - 5, y - 5, x + 5, y + 5, fill="white", outline="#1677c8", width=2
                )

        for node, label, fill in (
            (state["start"], "S", "#247c59"),
            (state["goal"], "T", "#bd5d28"),
        ):
            if node is not None:
                x, y = centers(node)
                canvas.create_oval(
                    x - 14, y - 14, x + 14, y + 14, fill=fill, outline="white", width=2
                )
                canvas.create_text(
                    x, y, text=label, fill="white", font=(self.font_family, 12, "bold")
                )

        road = state["selected_road"]
        if road is not None:
            x, y = road
            left, top = self.LEFT + x * self.CELL, self.TOP + y * self.CELL
            canvas.create_rectangle(
                left + 4,
                top + 4,
                left + self.CELL - 4,
                top + self.CELL - 4,
                outline="#bf4141",
                width=3,
            )
            canvas.create_text(
                left + self.CELL / 2,
                top + 12,
                text=f"대기 {state['queues'][road]}",
                fill="#9a2626",
                font=(self.font_family, 11, "bold"),
            )

    def click_map(self, event):
        x, y = (event.x - self.LEFT) // self.CELL, (event.y - self.TOP) // self.CELL
        if not (0 <= x < 5 and 0 <= y < 4):
            return

        self.selected = (x, y)
        mode = self.mode.get()
        if mode != "inspect" and not self.city["grid"][y][x]["road"]:
            self.status.set("도로 셀을 선택하세요. 건물과 빈 땅은 경로의 노드에 포함하지 않습니다.")
            self.refresh()
            return
        if mode == "queue":
            self.transport["selected_road"] = (x, y)
        elif mode in ("start", "goal"):
            self.transport[mode] = (x, y)
            self._invalidate()
        self.refresh()

    def use_preset(self, name):
        try:
            city, state = traffic_data.make_scenario(name)
        except Exception as error:
            self._fail("도시 선택", error)
            return

        self._set_city(city, state)
        label = {"default": "기본", "congested": "혼잡", "disconnected": "단절"}[name]
        self.status.set(f"{label} 도시를 불러왔습니다. 도로망 분석과 경로 비교를 실행하세요.")

    def _set_city(self, city, state):
        self.city, self.transport = city, state
        self.baseline = deepcopy(state)
        self.selected = state["selected_road"]
        self.history.clear()
        self.queue_tree.delete(*self.queue_tree.get_children())
        self._invalidate()
        self.refresh()

    def analyze_graph(self):
        try:
            graph = traffic.build_road_graph(self.city)
            components = traffic.connected_components(graph)
        except Exception as error:
            self._fail("도로망 분석", error)
            return

        self.graph, self.components = graph, components
        edges = sum(map(len, graph.values())) // 2
        self.summary.set(
            f"도로 노드 {len(graph)}개 / 연결 구간 {edges}개 / 연결 요소 {len(set(components.values()))}개"
        )
        self.status.set("같은 색의 노드는 같은 연결 요소에 속합니다. 이제 경로를 비교하세요.")
        self.refresh()

    def compare_paths(self):
        try:
            graph = traffic.build_road_graph(self.city)
            costs = traffic_data.cost_snapshot(self.transport)
            start, goal = self.transport["start"], self.transport["goal"]
            if start is None or goal is None:
                raise ValueError("출발 도로와 도착 도로가 필요합니다.")
            calculated = {}
            failures = []
            for name, calculate in (
                ("BFS", lambda: traffic.bfs_path(graph, start, goal)),
                ("Dijkstra", lambda: routing.dijkstra_path(graph, start, goal, costs)),
                ("A*", lambda: routing.astar_path(graph, start, goal, costs)),
            ):
                try:
                    path = calculate()
                    metrics = traffic.route_metrics(path, costs)
                    calculated[name] = (path, metrics)
                except NotImplementedError as error:
                    failures.append(str(error))
            self.graph = graph
            self.results = calculated
            for name in ("BFS", "Dijkstra", "A*"):
                if name not in calculated:
                    values = (name, "—", "—", "—")
                else:
                    path, metrics = calculated[name]
                    values = (
                        name,
                        f"{metrics['distance_m']:g} m" if metrics is not None else "—",
                        f"{metrics['time_min']:g}분" if metrics is not None else "—",
                        "도달" if path is not None else "경로 없음",
                    )
                self.path_tree.item(name, values=values)
            selected = "Dijkstra" if "Dijkstra" in calculated else next(iter(calculated), None)
            if selected:
                self.path_tree.selection_set(selected)
                self._show_path(selected)
            else:
                self.path = None
            self.status.set(
                " / ".join(dict.fromkeys(failures))
                if failures
                else "행을 선택해 경로를 비교하세요. 출발 셀의 통과 시간은 합산하지 않습니다."
            )
            self.refresh()
        except Exception as error:
            self._fail("경로 비교", error)

    def _show_path(self, name):
        if name not in self.results:
            return
        self.path, metrics = self.results[name]
        self.active_algorithm = name
        if self.path is None:
            self.route_text.set(f"{name}: 출발 도로에서 도착 도로로 이어지는 경로가 없습니다.")
        else:
            positions = " → ".join(f"({x},{y})" for x, y in self.path)
            self.route_text.set(f"{name}: {positions}")

    def select_path(self, event=None):
        selected = self.path_tree.selection()
        if selected:
            self._show_path(selected[0])
            self._draw_map()

    def calculate_accessibility(self):
        try:
            limit = float(self.time_limit.get())
            if not (0 <= limit < float("inf")):
                raise ValueError("시간 한도는 0 이상의 유한한 숫자로 입력하세요.")
            graph = traffic.build_road_graph(self.city)
            costs = traffic_data.cost_snapshot(self.transport)
            start = self.transport["start"]
            if start is None:
                raise ValueError("출발 도로가 필요합니다.")
            destinations = traffic_data.job_destinations(self.city)
            times = routing.dijkstra_all(graph, start, costs)
            result = traffic.count_accessible_jobs(destinations, times, limit)
        except Exception as error:
            self._fail("접근성 계산", error)
            return
        self.access_text.set(f"도로 {start}에서 {limit:g}분 이내: 일자리 {result}개")
        self.status.set(
            "건물에 인접한 도로 중 가장 빨리 도달하는 입구를 사용합니다. 같은 건물은 한 번만 셉니다."
        )

    def apply_queue_values(self):
        try:
            state = deepcopy(self.transport)

            road = state["selected_road"]
            if road is None:
                raise ValueError("먼저 도로를 배치하세요.")
            arrivals, capacity, queue = (
                int(value.get())
                for value in (self.arrivals_input, self.capacity_input, self.queue_input)
            )
            if arrivals < 0 or capacity <= 0 or queue < 0:
                raise ValueError("유입과 대기는 0 이상, 처리 용량은 1 이상의 정수여야 합니다.")
            state["arrivals"] = arrivals
            state["capacities"][road] = capacity
            state["queues"][road] = queue
            traffic_data.validate_transport(self.city, state)
        except Exception as error:
            self._fail("대기열 값 적용", error)
            return
        self.transport = state
        self._invalidate()
        self.refresh()
        self.status.set(
            "대기열 값을 적용했습니다. 경로 비교를 다시 실행하면 변경된 예상 시간이 반영됩니다."
        )

    def advance_minute(self):
        try:
            candidate = traffic_data.step_selected_queue(self.transport)
            traffic_data.validate_transport(self.city, candidate)
        except Exception as error:
            self._fail("1분 진행", error)
            return
        self.transport = candidate
        road = candidate["selected_road"]
        row = (
            candidate["minute"],
            str(road),
            candidate["arrivals"],
            candidate["last_served"],
            candidate["queues"][road],
        )
        self.history.append(row)
        item = self.queue_tree.insert("", "end", values=row)
        self.queue_tree.see(item)
        self._invalidate()
        self.refresh()
        self.status.set(
            "선택한 도로의 대기열만 1분 진행했습니다. 경로 비교를 다시 실행해 예상 시간의 변화를 확인하세요."
        )

    def reset_queue(self):
        state = deepcopy(self.transport)
        state["minute"] = 0
        state["last_served"] = 0
        state["queues"] = {road: 0 for road in state["queues"]}
        self.transport = state
        self.history.clear()
        self.queue_tree.delete(*self.queue_tree.get_children())
        self._invalidate()
        self.refresh()
        self.status.set("모든 도로의 대기열과 실험 시간을 0으로 초기화했습니다.")

    def open_city_editor(self):
        window = tk.Toplevel(self.root)
        editor = CityApp(window)
        editor._start_from(deepcopy(self.city))
        window.title("도시 편집")
        controls = ttk.Frame(window, padding=8)
        controls.pack(side="bottom", fill="x", before=window.winfo_children()[0])
        ttk.Label(
            controls,
            text="도시를 수정한 뒤 교통 지도에 적용하세요. 교통 시간은 0분부터 다시 시작합니다.",
        ).pack(side="left")

        def apply_city():
            try:
                city = deepcopy(editor.city)
                city_data.validate_city(city)
                state = traffic_data.sync_transport(city, deepcopy(self.transport))
                state["minute"] = 0
                state["last_served"] = 0
                state["queues"] = {node: 0 for node in state["queues"]}
                traffic_data.validate_transport(city, state)
            except Exception as error:
                self._fail("도시 적용", error)
                return

            self._set_city(city, state)
            window.destroy()
            self.status.set("편집한 도시를 적용했습니다. 도로망 분석부터 다시 실행하세요.")

        ttk.Button(controls, text="교통 지도에 적용", command=apply_city).pack(side="right")
        return window, editor, apply_city

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="도시와 교통 상태 저장",
            defaultextension=".json",
            filetypes=[("도시와 교통 JSON", "*.json")],
            initialfile="my_traffic_city.json",
        )

        if not path:
            return
        try:
            traffic_data.save_scenario(self.city, self.transport, path)
        except Exception as error:
            self._fail("저장", error)
            return
        self.status.set("도시와 교통 상태를 저장했습니다.")

    def load_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="도시와 교통 상태 불러오기",
            filetypes=[("도시와 교통 JSON", "*.json")],
        )

        if not path:
            return
        try:
            city, state = traffic_data.load_scenario(path)
        except Exception as error:
            self._fail("불러오기", error)
            return

        self._set_city(city, state)
        self.status.set("도시와 교통 상태를 불러왔습니다.")


def launch(smoke=False):
    root = tk.Tk()
    TrafficApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        root.destroy()
        print("GUI smoke: 지도와 제어 화면 생성 성공")
    else:
        root.mainloop()

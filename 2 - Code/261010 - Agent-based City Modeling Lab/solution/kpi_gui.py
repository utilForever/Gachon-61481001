"""도시 지도와 KPI 화면. 이 파일은 수정하지 않고 사용한다."""

from copy import deepcopy
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

import city_data
from gui import CityApp
import kpi_support
import traffic_data
from traffic_gui import TrafficApp


class KpiApp:
    CELL = 84
    LEFT = 34
    TOP = 30

    def __init__(self, root):
        self.root = root
        root.title("가상 도시 / 도시 지표")
        root.geometry("1230x740")
        root.minsize(1130, 700)
        CityApp._set_fonts(self)

        self.session = kpi_support.make_lab_session()
        self.kpis = kpi_support.record_current(self.session)
        self.selected = self.session["transport"]["selected_road"]

        self.status = tk.StringVar(
            value="기본 도시를 불러왔습니다. 지표를 확인하고 1분씩 진행해 보세요."
        )
        self.overview = tk.StringVar()
        self.inspector = tk.StringVar()
        self.queue_summary = tk.StringVar()
        self.limit_input = tk.StringVar()
        self.threshold_input = tk.StringVar()
        self.arrivals_input = tk.StringVar()
        self.capacity_input = tk.StringVar()
        self.queue_input = tk.StringVar()
        self.plot_metric = tk.StringVar(value="평균 통근 시간")

        self._make_widgets()
        self.refresh()
        self._result_status("기본 도시를 불러왔습니다. 지표를 확인하고 1분씩 진행해 보세요.")

    @property
    def city(self):
        return self.session["city"]

    def _make_widgets(self):
        outer = ttk.Frame(self.root, padding=(12, 8))
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x", pady=(0, 7))
        ttk.Label(heading, text="도시 지표", style="Title.TLabel").pack(side="left")
        ttk.Label(heading, textvariable=self.overview, style="Stats.TLabel").pack(side="right")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 7))
        for label, name in (
            ("기본 도시", "default"),
            ("혼잡 도시", "congested"),
            ("단절 도시", "disconnected"),
        ):
            ttk.Button(
                controls, text=label, command=lambda value=name: self.use_preset(value)
            ).pack(side="left", padx=(0, 5))
        ttk.Button(controls, text="도시 편집", command=self.open_city_editor).pack(
            side="left", padx=(10, 5)
        )
        ttk.Button(controls, text="도로망과 교통", command=self.open_traffic).pack(side="left")
        ttk.Button(controls, text="불러오기", command=self.load_file).pack(side="right")
        ttk.Button(controls, text="상태 저장", command=self.save_file).pack(
            side="right", padx=(0, 5)
        )
        ttk.Button(controls, text="CSV 내보내기", command=self.export_csv).pack(
            side="right", padx=(0, 5)
        )

        setup = ttk.Frame(outer)
        setup.pack(fill="x", pady=(0, 7))
        for label, variable, unit in (
            ("통근 기준", self.limit_input, "분"),
            ("혼잡 기준: 대기", self.threshold_input, "대 이상"),
            ("유입", self.arrivals_input, "대/분"),
            ("처리 용량", self.capacity_input, "대/분"),
            ("대기 차량", self.queue_input, "대"),
        ):
            ttk.Label(setup, text=label + " ").pack(side="left")
            ttk.Entry(setup, textvariable=variable, width=4, justify="right").pack(side="left")
            ttk.Label(setup, text=" " + unit + "  ").pack(side="left")
        ttk.Button(setup, text="설정 적용", command=self.apply_settings).pack(side="right")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Label(
            actions, text="설정 / 도시 / 관찰 도로를 바꾸면 기존 기록을 지우고 0분부터 시작합니다."
        ).pack(side="left")
        ttk.Button(actions, text="5분 진행", command=lambda: self.advance(5)).pack(side="right")
        ttk.Button(actions, text="1분 진행", command=lambda: self.advance(1)).pack(
            side="right", padx=(0, 5)
        )
        ttk.Button(actions, text="지표 계산", command=self.calculate).pack(
            side="right", padx=(0, 5)
        )

        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Separator(footer).pack(fill="x", pady=(0, 5))
        ttk.Button(footer, text="계산 상태", command=self.show_errors).pack(side="right")
        ttk.Label(footer, textvariable=self.status, foreground="#15517a", wraplength=1020).pack(
            side="left", fill="x", expand=True
        )

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.dashboard = ttk.Frame(self.notebook, padding=(9, 9))
        self.timeline = ttk.Frame(self.notebook, padding=(9, 9))
        self.notebook.add(self.dashboard, text="도시 지표")
        self.notebook.add(self.timeline, text="시간에 따른 변화")
        self._make_dashboard()
        self._make_timeline()

    def _make_dashboard(self):
        left = ttk.Frame(self.dashboard)
        left.pack(side="left", anchor="n")
        self.canvas = tk.Canvas(
            left,
            width=464,
            height=378,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8bec4",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.click_map)
        ttk.Label(left, text="붉은 테두리: 관찰 도로 / 초록 점: 개발 가능한 셀").pack(
            anchor="w", pady=(5, 2)
        )
        ttk.Label(left, text="H / A: 주택 / J: 상점 / F: 공장 / P: 공원").pack(anchor="w")
        ttk.Label(left, textvariable=self.inspector, wraplength=435, foreground="#15517a").pack(
            anchor="w", pady=(7, 0)
        )

        right = ttk.Frame(self.dashboard, padding=(16, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="도시 현황과 통근 지표", style="Stats.TLabel").pack(
            anchor="w", pady=(0, 5)
        )
        self.metric_tree = ttk.Treeview(
            right, columns=("name", "value", "basis"), show="headings", height=12, selectmode="none"
        )
        for key, label, width in (
            ("name", "지표", 140),
            ("value", "값", 105),
            ("basis", "측정 기준", 340),
        ):
            self.metric_tree.heading(key, text=label)
            self.metric_tree.column(
                key, width=width, minwidth=width - 20, anchor="w" if key != "value" else "center"
            )
        self.metric_tree.pack(fill="x")
        ttk.Label(
            right, textvariable=self.queue_summary, style="Stats.TLabel", wraplength=690
        ).pack(anchor="w", pady=(12, 6))
        ttk.Label(
            right,
            text="모든 주민이 상점 J로 한 번씩 통근한다고 가정합니다.\n도달할 수 없는 주민은 평균에서 제외하고 별도로 셉니다.\n1분 진행할 때 선택한 도로의 대기열만 갱신합니다.",
            wraplength=685,
        ).pack(anchor="w")

    def _make_timeline(self):
        choices = ttk.Frame(self.timeline)
        choices.pack(fill="x", pady=(0, 5))
        ttk.Label(choices, text="그래프 ").pack(side="left")
        picker = ttk.Combobox(
            choices,
            textvariable=self.plot_metric,
            values=("평균 통근 시간", "기준 시간 이내 통근 비율", "선택 도로 대기 차량"),
            width=27,
            state="readonly",
        )
        picker.pack(side="left")
        picker.bind("<<ComboboxSelected>>", lambda event: self._draw_history())
        ttk.Label(choices, text="같은 시각의 기록은 중복으로 추가하지 않습니다.").pack(side="right")

        self.plot = tk.Canvas(
            self.timeline,
            height=190,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8bec4",
        )
        self.plot.pack(fill="x", pady=(0, 8))
        self.plot.bind("<Configure>", lambda event: self._draw_history())

        table_frame = ttk.Frame(self.timeline)
        table_frame.pack(fill="both", expand=True)
        columns = (
            ("minute", "시간(분)", 75),
            ("population", "인구(명)", 80),
            ("building_count", "건물(동)", 80),
            ("accessibility_ratio", "기준 이내(%)", 110),
            ("mean_time_min", "평균(분)", 90),
            ("median_time_min", "중앙값(분)", 95),
            ("p90_time_min", "P90(분)", 85),
            ("unreachable_trips", "도달 불가(명)", 110),
            ("current_queue", "대기(대)", 80),
            ("congested_minutes", "혼잡 시간(분)", 115),
        )
        self.history_tree = ttk.Treeview(
            table_frame, columns=tuple(key for key, _, _ in columns), show="headings", height=6
        )
        for key, label, width in columns:
            self.history_tree.heading(key, text=label)
            self.history_tree.column(key, width=width, minwidth=65, anchor="center")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.history_tree.pack(side="left", fill="both", expand=True)
        ttk.Label(
            self.timeline,
            text="—: 아직 계산하지 않았거나 계산할 대상이 없음 / 혼잡 시간은 진행한 1분 구간을 기준으로 누적합니다.",
        ).pack(anchor="w", pady=(6, 0))

    @staticmethod
    def display(value, unit="", percent=False):
        if value is None:
            return "—"
        if percent:
            return f"{value * 100:.0f}%"
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".") + unit
        return str(value) + unit

    def _fail(self, action, error):
        self.status.set(f"{action}: {error or '해당 TODO를 먼저 작성하세요.'}")
        if not isinstance(error, (ValueError, NotImplementedError)):
            traceback.print_exception(type(error), error, error.__traceback__)

    def _result_status(self, message):
        errors = self.kpis.get("_errors", [])
        self.status.set(
            message
            + (
                f" / 미완성 또는 오류 {len(errors)}개: ‘계산 상태’에서 확인하세요."
                if errors
                else ""
            )
        )

    def refresh(self):
        state, settings = self.session["transport"], self.session["settings"]
        self.overview.set(f"{state['minute']}분 / 기록 {len(self.session['history'])}개")
        self.limit_input.set(str(settings["limit_minutes"]))
        self.threshold_input.set(str(settings["queue_threshold"]))
        road = state["selected_road"]
        self.arrivals_input.set(str(state["arrivals"]))
        self.capacity_input.set(str(state["capacities"].get(road, 5)))
        self.queue_input.set(str(state["queues"].get(road, 0)))

        self.metric_tree.delete(*self.metric_tree.get_children())
        specifications = (
            ("거주 인구", "population", "명", "주택에 거주하는 전체 주민"),
            ("건물 수", "building_count", "동", "주택 / 상점 / 공장, 공원 제외"),
            (
                "통근 접근성",
                "accessibility_ratio",
                "%",
                f"전체 주민 중 {settings['limit_minutes']:g}분 이내에 도달",
            ),
            ("도달 불가", "unreachable_trips", "명", "상점 J까지 이어지는 경로가 없음"),
            ("평균 통근 시간", "mean_time_min", "분", "도달 가능한 주민만 포함"),
            ("중앙값", "median_time_min", "분", "통근 시간을 정렬했을 때의 가운데 값"),
            ("P90", "p90_time_min", "분", "도달 가능한 통근의 90%가 이 시간 이내"),
            ("개발 가능 토지", "developable_count", "셀", "보전 구역을 제외한 도로 인접 빈 땅"),
            ("관찰 시간", "observed_minutes", "분", "0분 이후 진행한 관찰 구간"),
            (
                "혼잡 시간",
                "congested_minutes",
                "분",
                f"구간 시작 시 대기 {settings['queue_threshold']}대 이상",
            ),
            ("최대 대기", "peak_queue", "대", "관찰한 대기 차량 수의 최댓값"),
            ("현재 대기", "current_queue", "대", "선택 도로의 현재 대기 차량 수"),
        )
        for label, key, unit, basis in specifications:
            self.metric_tree.insert(
                "",
                "end",
                values=(
                    label,
                    self.display(self.kpis.get(key), unit if unit != "%" else "", unit == "%"),
                    basis,
                ),
            )

        self.queue_summary.set(
            f"관찰 도로 {road if road is not None else '없음'} / 현재 대기 {self.display(self.kpis.get('current_queue'), '대')}"
        )
        self._draw_map()
        self._refresh_history()

    def _draw_map(self):
        CityApp._draw_map(self)
        protected = set(map(tuple, self.session["settings"]["protected"]))
        cells = self.kpis.get("developable_cells") or []
        for x, y in cells:
            cx, cy = self.LEFT + (x + 0.5) * self.CELL, self.TOP + (y + 0.5) * self.CELL
            self.canvas.create_oval(
                cx - 6, cy - 6, cx + 6, cy + 6, fill="#328362", outline="white", width=2
            )
        for x, y in protected:
            self.canvas.create_text(
                self.LEFT + (x + 0.5) * self.CELL,
                self.TOP + (y + 0.5) * self.CELL,
                text="보전 구역",
                fill="#586578",
                font=(self.font_family, 10),
            )

        road = self.session["transport"]["selected_road"]
        if road is not None:
            x, y = road
            left, top = self.LEFT + x * self.CELL, self.TOP + y * self.CELL
            self.canvas.create_rectangle(
                left + 3,
                top + 3,
                left + self.CELL - 3,
                top + self.CELL - 3,
                outline="#bd4141",
                width=3,
            )

        if self.selected is None:
            self.inspector.set("셀을 선택하면 내용을 확인할 수 있습니다.")
            return

        x, y = self.selected
        cell = self.city["grid"][y][x]
        building = self.city["buildings"].get(cell["building_id"])
        if building:
            kind = {"house": "주택", "shop": "상점", "factory": "공장", "park": "공원"}[
                building["kind"]
            ]
            detail = f"{building['id']} / {kind}"
        elif cell["road"]:
            detail = "도로 / 이 도로의 대기열을 관찰합니다."
        elif (x, y) in protected:
            detail = "보전 구역 / 개발 대상에서 제외합니다."
        else:
            detail = "물" if cell["terrain"] == "water" else "빈 땅"
        self.inspector.set(f"선택한 셀 ({x}, {y}): {detail}")

    def _refresh_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        keys = self.history_tree["columns"]
        for row in self.session["history"]:
            values = [
                self.display(row.get(key), percent=(key == "accessibility_ratio")) for key in keys
            ]
            item = self.history_tree.insert("", "end", values=values)
        if self.session["history"]:
            self.history_tree.see(item)
        self._draw_history()

    def _draw_history(self):
        canvas = self.plot
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 700), max(canvas.winfo_height(), 190)
        key, unit, factor = {
            "평균 통근 시간": ("mean_time_min", "분", 1),
            "기준 시간 이내 통근 비율": ("accessibility_ratio", "%", 100),
            "선택 도로 대기 차량": ("current_queue", "대", 1),
        }[self.plot_metric.get()]
        rows = self.session["history"]
        points = [(row["minute"], row.get(key)) for row in rows]
        values = [value * factor for _, value in points if value is not None]
        if not values:
            if not rows:
                message = "아직 지표 기록이 없습니다. ‘지표 계산’을 누르고 계산 상태를 확인하세요."
            elif key == "mean_time_min":
                message = "도달 가능한 통근이 없어 평균 통근 시간을 표시할 수 없습니다."
            elif key == "accessibility_ratio":
                message = "통근 대상 주민이 없어 통근 접근성을 표시할 수 없습니다."
            else:
                message = "관찰할 도로가 없어 대기 차량 수를 표시할 수 없습니다."
            canvas.create_text(
                width / 2, height / 2, text=message, fill="#647382", font=(self.font_family, 12)
            )
            return

        left, top, right, bottom = 58, 22, width - 25, height - 35
        ymax = 100 if factor == 100 else max(1, math.ceil(max(values) * 1.15))
        xmax = max(1, max(minute for minute, _ in points))
        for ratio in (0, 0.5, 1):
            y = bottom - ratio * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#e1e5e9")
            canvas.create_text(
                left - 8,
                y,
                text=f"{ymax*ratio:g}",
                anchor="e",
                fill="#4f5b66",
                font=(self.font_family, 10),
            )
        canvas.create_text(
            8, 10, text=unit, anchor="w", fill="#4f5b66", font=(self.font_family, 10)
        )
        canvas.create_line(left, top, left, bottom, right, bottom, fill="#80909d")

        prior = None
        for minute, value in points:
            if value is None:
                prior = None
                continue
            x = left + minute / xmax * (right - left)
            y = bottom - (value * factor) / ymax * (bottom - top)
            if prior:
                canvas.create_line(*prior, x, y, fill="#246da6", width=3)
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#246da6", outline="white")
            prior = (x, y)

        for minute in sorted({0, xmax // 2, xmax}):
            x = left + minute / xmax * (right - left)
            canvas.create_text(
                x, bottom + 16, text=f"{minute}분", fill="#4f5b66", font=(self.font_family, 10)
            )

    def calculate(self):
        try:
            self.kpis = kpi_support.record_current(self.session)
            self.refresh()
            self._result_status("현재 시각의 지표를 계산했습니다.")
        except Exception as error:
            self._fail("지표 계산", error)

    def advance(self, count=1):
        try:
            self.kpis = kpi_support.advance_minutes(self.session, count)
            self.refresh()
            self._result_status(
                f"{count}분 진행했습니다. 시간에 따른 변화 탭에서 기록을 확인하세요."
            )
        except Exception as error:
            self._fail("시간 진행", error)

    def _reset_run(self, message):
        self.kpis = kpi_support.reset_observation(self.session)
        if self.kpis is None:
            self.kpis = kpi_support.record_current(self.session)
        self.refresh()
        self._result_status(message + " 기존 기록을 지우고 0분부터 시작합니다.")

    def apply_settings(self):
        try:
            limit = float(self.limit_input.get())
            threshold, arrivals, capacity, queue = [
                int(value.get())
                for value in (
                    self.threshold_input,
                    self.arrivals_input,
                    self.capacity_input,
                    self.queue_input,
                )
            ]
            if not math.isfinite(limit) or limit < 0:
                raise ValueError("통근 기준은 0 이상의 유한한 수여야 합니다.")
            if threshold < 1 or capacity < 1 or arrivals < 0 or queue < 0:
                raise ValueError(
                    "혼잡 기준과 처리 용량은 1 이상, 유입과 대기는 0 이상의 정수여야 합니다."
                )
            state = deepcopy(self.session["transport"])
            road = state["selected_road"]
            if road is None:
                raise ValueError("먼저 도로를 배치하세요.")
            state["arrivals"], state["capacities"][road], state["queues"][road] = (
                arrivals,
                capacity,
                queue,
            )
            traffic_data.validate_transport(self.city, state)
            self.session["transport"] = state
            self.session["settings"].update(limit_minutes=limit, queue_threshold=threshold)
            self._reset_run("설정을 적용했습니다.")
        except Exception as error:
            self._fail("설정 적용", error)

    def click_map(self, event):
        x, y = (event.x - self.LEFT) // self.CELL, (event.y - self.TOP) // self.CELL
        if not (0 <= x < 5 and 0 <= y < 4):
            return
        self.selected = (x, y)
        if self.city["grid"][y][x]["road"] and self.session["transport"]["selected_road"] != (x, y):
            self.session["transport"]["selected_road"] = (x, y)
            self._reset_run("관찰 도로를 바꿨습니다.")
        else:
            self._draw_map()

    def use_preset(self, name):
        try:
            self.session = kpi_support.make_lab_session(name)
            self.kpis = kpi_support.record_current(self.session)
            self.selected = self.session["transport"]["selected_road"]
            self.refresh()
            label = {"default": "기본", "congested": "혼잡", "disconnected": "단절"}[name]
            self._result_status(f"{label} 도시로 새 기록을 시작합니다.")
        except Exception as error:
            self._fail("도시 선택", error)

    def _apply_city(self, city, transport=None):
        city_data.validate_city(city)
        state = traffic_data.sync_transport(city, deepcopy(transport or self.session["transport"]))
        self.session["city"], self.session["transport"] = deepcopy(city), state
        self.selected = state["selected_road"]
        self._reset_run("도시와 교통 상태를 적용했습니다.")

    def open_city_editor(self):
        window = tk.Toplevel(self.root)
        editor = CityApp(window)
        editor._start_from(deepcopy(self.city))
        window.title("도시 편집")
        controls = ttk.Frame(window, padding=8)
        controls.pack(side="bottom", fill="x", before=window.winfo_children()[0])
        ttk.Label(controls, text="편집한 도시를 적용하면 KPI 기록이 0분부터 다시 시작됩니다.").pack(
            side="left"
        )

        def apply_city():
            try:
                self._apply_city(editor.city)
                window.destroy()
            except Exception as error:
                self._fail("도시 적용", error)

        ttk.Button(controls, text="도시 적용", command=apply_city).pack(side="right")
        return window, editor, apply_city

    def open_traffic(self):
        window = tk.Toplevel(self.root)
        viewer = TrafficApp(window)
        viewer._set_city(deepcopy(self.city), deepcopy(self.session["transport"]))
        viewer.analyze_graph()
        viewer.compare_paths()
        window.title("도로망과 교통")
        controls = ttk.Frame(window, padding=8)
        controls.pack(side="bottom", fill="x", before=window.winfo_children()[0])
        ttk.Label(controls, text="변경한 상태를 적용하면 KPI 기록이 0분부터 다시 시작됩니다.").pack(
            side="left"
        )

        def apply_traffic():
            try:
                self._apply_city(viewer.city, viewer.transport)
                window.destroy()
            except Exception as error:
                self._fail("교통 상태 적용", error)

        ttk.Button(controls, text="현재 상태 적용", command=apply_traffic).pack(side="right")
        return window, viewer, apply_traffic

    def show_errors(self):
        errors = self.kpis.get("_errors", [])
        messagebox.showinfo(
            "계산 상태",
            (
                "\n\n".join(errors)
                if errors
                else "모든 지표를 계산했습니다.\n‘—’는 계산할 대상이 없는 항목입니다."
            ),
            parent=self.root,
        )

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="도시 상태와 기록 저장",
            defaultextension=".json",
            filetypes=[("도시 상태 JSON", "*.json")],
            initialfile="city_kpi.json",
        )
        if not path:
            return
        try:
            kpi_support.save_session(self.session, path)
            self.status.set("도시 / 교통 / 설정 / 관찰 / 지표 기록을 저장했습니다.")
        except Exception as error:
            self._fail("상태 저장", error)

    def load_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="도시 상태와 기록 불러오기",
            filetypes=[("도시 상태 JSON", "*.json")],
        )
        if not path:
            return
        try:
            candidate = kpi_support.load_session(path)
            self.session = candidate
            self.selected = candidate["transport"]["selected_road"]
            self.kpis = kpi_support.calculate_kpis(candidate)
            self.refresh()
            self._result_status("저장한 도시와 기록을 복원했습니다. 이어서 진행할 수 있습니다.")
        except Exception as error:
            self._fail("불러오기", error)

    def export_csv(self):
        if not self.session["history"]:
            self.status.set("내보낼 기록이 없습니다. 지표 계산과 기록 기능을 먼저 작성하세요.")
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="지표 기록 내보내기",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="city_kpi_history.csv",
        )
        if not path:
            return
        try:
            kpi_support.export_history_csv(self.session, path)
            self.status.set("지표 기록을 CSV로 내보냈습니다.")
        except Exception as error:
            self._fail("CSV 내보내기", error)


def launch(smoke=False):
    root = tk.Tk()
    app = KpiApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        app.calculate()
        root.destroy()
        print("GUI smoke: 도시 지도와 KPI 화면 생성 성공")
    else:
        root.mainloop()

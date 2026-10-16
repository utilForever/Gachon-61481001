"""서비스 권역, 진료 대기열, 기반시설과 환경 상태를 표시하는 Tkinter GUI."""

import tkinter as tk
from tkinter import filedialog, ttk

from abm_gui import AgentApp
import abm_support
from neighborhood import Neighborhood
import service_support as support


class ServiceApp(AgentApp):
    def __init__(self, root):
        super().__init__(root)
        support.reset_services(self.session)
        self.refresh()

        root.title("가상 도시 / 공공서비스와 환경")
        root.minsize(1230, 840)
        self.notebook.select(self.service_tab)
        self._refresh_services()
        self._result_status("서비스 조건을 확인하고 한 시간씩 진행하세요.")

    def _make_widgets(self):
        super()._make_widgets()
        self.service_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.service_tab, text="공공서비스 / 환경")

        controls = ttk.Frame(self.service_tab)
        controls.pack(fill="x", pady=(0, 5))
        self.scenario_var = tk.StringVar(value="기본 조건")
        picker = ttk.Combobox(
            controls,
            textvariable=self.scenario_var,
            values=tuple(support.SCENARIOS.values()),
            state="readonly",
            width=13,
        )
        picker.pack(side="left")
        ttk.Button(controls, text="조건 적용 / 초기화", command=self.reset_service_run).pack(
            side="left", padx=5
        )
        self.service_clock = tk.StringVar()
        ttk.Label(controls, textvariable=self.service_clock, style="Stats.TLabel").pack(
            side="left", padx=10
        )
        ttk.Button(controls, text="시간별 CSV", command=self.export_services).pack(side="right")
        for count in (24, 6, 1):
            ttk.Button(
                controls, text=f"{count}시간 진행", command=lambda n=count: self.advance_services(n)
            ).pack(side="right", padx=3)
        ttk.Label(
            self.service_tab,
            text="서비스 수요: 지역별 100명, 총 400명 / 행위자 탭: 시민 3명 / 같은 도로를 사용하며 분·시간·월은 따로 진행합니다.",
        ).pack(anchor="w", pady=(0, 5))

        self.service_notebook = ttk.Notebook(self.service_tab)
        self.service_notebook.pack(fill="both", expand=True)
        self.coverage_tab = ttk.Frame(self.service_notebook, padding=8)
        self.resources_tab = ttk.Frame(self.service_notebook, padding=8)
        self.records_tab = ttk.Frame(self.service_notebook, padding=8)
        for tab, title in (
            (self.coverage_tab, "권역과 진료"),
            (self.resources_tab, "기반시설과 환경"),
            (self.records_tab, "시간별 기록"),
        ):
            self.service_notebook.add(tab, text=title)

        left = ttk.Frame(self.coverage_tab)
        left.pack(side="left", fill="y")
        self.service_map = tk.Canvas(
            left,
            width=425,
            height=265,
            background="white",
            highlightthickness=1,
            highlightbackground="#aeb7bf",
        )
        self.service_map.pack()
        ttk.Label(
            left,
            text="H: 병원 입구 / 도로 한 칸 2분 + 지역 내 접근시간\nA 2분 / B 2분 / C 8분 / D 12분",
            justify="left",
        ).pack(anchor="w", pady=5)

        self.coverage_tree = self._tree(
            left,
            (
                ("area", "지역", 65),
                ("time", "이동(분)", 95),
                ("condition", "서비스 권역", 120),
                ("requests", "요청(명/시간)", 120),
            ),
            4,
        )
        self.coverage_tree.pack(fill="x")

        right = ttk.Frame(self.coverage_tab, padding=(18, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        self.service_summary = tk.StringVar()
        ttk.Label(
            right, textvariable=self.service_summary, style="Stats.TLabel", justify="left"
        ).pack(anchor="w", pady=(0, 10))

        self.queue_chart = tk.Canvas(
            right, height=175, width=630, background="white", highlightthickness=0
        )
        self.queue_chart.pack(fill="x")

        self.school_tree = self._tree(
            right,
            (
                ("school", "학교 / 지역", 135),
                ("capacity", "정원", 75),
                ("assigned", "배정", 75),
                ("vacancy", "남는 자리", 95),
                ("unassigned", "미배정", 85),
            ),
            2,
        )
        self.school_tree.pack(fill="x", pady=5)

        self.fire_text = tk.StringVar()
        ttk.Label(right, textvariable=self.fire_text, wraplength=650, justify="left").pack(
            anchor="w", pady=5
        )

        self.resources_tab.columnconfigure(0, weight=1)
        self.resources_tab.columnconfigure(1, weight=1)
        self.power_chart = tk.Canvas(
            self.resources_tab, width=560, height=235, background="white", highlightthickness=0
        )
        self.power_chart.grid(row=0, column=0, sticky="nsew", padx=3)
        self.water_chart = tk.Canvas(
            self.resources_tab, width=560, height=235, background="white", highlightthickness=0
        )
        self.water_chart.grid(row=0, column=1, sticky="nsew", padx=3)
        self.pollution_chart = tk.Canvas(
            self.resources_tab, width=560, height=190, background="white", highlightthickness=0
        )
        self.pollution_chart.grid(row=1, column=0, sticky="nsew", padx=3)
        self.resource_details = tk.StringVar()
        ttk.Label(
            self.resources_tab, textvariable=self.resource_details, wraplength=545, justify="left"
        ).grid(row=1, column=1, sticky="nw", padx=14, pady=10)

        self.service_record_tree = self._tree(
            self.records_tab,
            (
                ("hour", "시간", 50),
                ("reach", "권역(%)", 75),
                ("blocked", "경로 없음(명)", 110),
                ("served", "진료(명)", 80),
                ("queue", "대기(명)", 80),
                ("water", "저장(m³)", 85),
                ("unmet", "급수 부족(m³)", 115),
                ("battery", "배터리(kWh)", 115),
                ("waste", "도시/시설(t)", 125),
            ),
            14,
        )
        self.service_record_tree.pack(fill="both", expand=True)

    def refresh(self):
        super().refresh()
        if hasattr(self, "service_tab"):
            self._refresh_services()

    def _result_status(self, message):
        pending = support.pending_tasks()
        suffix = " / 미구현: TODO " + ", ".join(map(str, pending)) if pending else ""
        self.status.set(message + suffix)

    @staticmethod
    def number(value):
        return "—" if value is None else f"{value:g}"

    def _refresh_services(self):
        state = support.ensure_state(self.session)
        self.scenario_var.set(support.SCENARIOS[state["scenario"]])
        self.service_clock.set(f"{state['hour']}시간")

        times = support.travel_times(self.session, support.conditions(state)["closed_roads"])
        issue = ""
        try:
            _, coverage = support.current_coverage(self.session)
            if not isinstance(coverage, dict) or not isinstance(coverage["covered"], list):
                raise ValueError("covered 목록을 포함한 딕셔너리를 반환하세요.")
            if any(area not in support.POPULATIONS for area in coverage["covered"]):
                raise ValueError("covered에는 A / B / C / D만 넣으세요.")
            for key in ("population", "ratio", "unreachable_population"):
                if not isinstance(coverage[key], (int, float)):
                    raise ValueError(key + " 값은 숫자여야 합니다.")
        except NotImplementedError:
            coverage, issue = None, "미구현"
        except Exception:
            coverage, issue = None, "반환값 확인 필요"

        self._draw_service_map(times, coverage)
        self.coverage_tree.delete(*self.coverage_tree.get_children())
        for area in support.POPULATIONS:
            minutes = times[area]
            condition = (
                issue
                if coverage is None
                else (
                    "경로 없음"
                    if minutes is None
                    else ("포함" if area in coverage["covered"] else "기준 초과")
                )
            )
            self.coverage_tree.insert(
                "", "end", values=(area, self.number(minutes), condition, support.REQUESTS[area])
            )

        if coverage is None:
            headline = "서비스 권역: " + issue
        else:
            headline = f"15분 이내 {coverage['population']}명 / {coverage['ratio']:.0%}  |  경로 없음 {coverage['unreachable_population']}명"
        last = state["last"]
        result = (
            "초기 대기 0명 / 시간 갱신 전"
            if last is None
            else f"이번 진료 {last['served']}명 / 종료 대기 {state['queue']}명 / 미배정 {last['unassigned']}명"
        )
        self.service_summary.set(headline + "\n" + result)

        self._line_plot(
            self.queue_chart,
            "병원 대기 인원 (명)",
            [(0, 0)] + [(row["hour"], row["queue"]) for row in state["history"]],
            "#9a3d34",
        )

        self.school_tree.delete(*self.school_tree.get_children())
        for row in support.school_allocation():
            self.school_tree.insert(
                "",
                "end",
                values=(
                    row["school"] + " / " + row["areas"],
                    row["capacity"],
                    row["assigned"],
                    row["vacancy"],
                    row["unassigned"],
                ),
            )

        fire = "소방 차량 2대 / 1시간째 요청 3건 / 출동한 차량은 2시간 뒤 복귀"
        if last:
            fire += f"\n이번 출동 {last['fire_dispatched']}대 / 출동 중 {last['fire_busy']}대 / 대기 {last['fire_waiting']}건"
        self.fire_text.set(fire)

        self._draw_resources(state)

        self.service_record_tree.delete(*self.service_record_tree.get_children())
        for row in state["history"]:
            self.service_record_tree.insert(
                "",
                "end",
                values=(
                    row["hour"],
                    f"{row['coverage_ratio'] * 100:.0f}",
                    row["unreachable_population"],
                    row["served"],
                    row["queue"],
                    self.number(row["water_stored"]),
                    self.number(row["water_unmet"]),
                    self.number(row["battery_kwh"]),
                    f"{row['waste_city']:g} / {row['waste_plant']:g}",
                ),
            )

        children = self.service_record_tree.get_children()
        if children:
            self.service_record_tree.see(children[-1])

    def _draw_service_map(self, times, coverage):
        canvas = self.service_map
        canvas.delete("all")
        rows, columns = len(self.city["grid"]), len(self.city["grid"][0])
        cell_w, cell_h = 385 / columns, 240 / rows

        def origin(x, y):
            return 20 + x * cell_w, 12 + y * cell_h

        graph_roads = {
            (x, y)
            for y, row in enumerate(self.city["grid"])
            for x, cell in enumerate(row)
            if cell["road"]
        }
        closed = set(support.conditions(self.session["services"])["closed_roads"])
        for y in range(rows):
            for x in range(columns):
                left, top = origin(x, y)
                color = "#eff2f5"
                if (x, y) in graph_roads:
                    color = "#c6cbd0" if (x, y) not in closed else "#e4a8a2"
                canvas.create_rectangle(
                    left,
                    top,
                    left + cell_w - 5,
                    top + cell_h - 5,
                    fill=color,
                    outline="white",
                    width=2,
                )
                if (x, y) in closed:
                    canvas.create_text(
                        left + (cell_w - 5) / 2,
                        top + (cell_h - 5) / 2,
                        text="통행\n중단",
                        font=(self.font_family, 10, "bold"),
                    )

        for area in support.POPULATIONS:
            building = self.city["buildings"][area]
            left, top = origin(building["x"], building["y"])
            included = coverage is not None and area in coverage["covered"]
            color = "#d6e8f4" if included else "#fae0b8"
            canvas.create_rectangle(
                left, top, left + cell_w - 5, top + cell_h - 5, fill=color, outline="#3c4b57"
            )
            canvas.create_text(
                left + (cell_w - 5) / 2,
                top + (cell_h - 5) / 2,
                text=f"{area}\n100명",
                font=(self.font_family, 11),
            )

        hx, hy = origin(0, 2)
        hx += (cell_w - 5) / 2
        hy += (cell_h - 5) / 2
        canvas.create_oval(
            hx - 18, hy - 18, hx + 18, hy + 18, fill="#315b7b", outline="white", width=2
        )
        canvas.create_text(hx, hy, text="H", fill="white", font=(self.font_family, 14, "bold"))

        for ident in ("X", "Y", "P"):
            building = self.city["buildings"].get(ident)
            if building:
                left, top = origin(building["x"], building["y"])
                canvas.create_text(
                    left + (cell_w - 5) / 2,
                    top + (cell_h - 5) / 2,
                    text=ident,
                    font=(self.font_family, 12),
                )

    def _line_plot(self, canvas, title, points, color):
        canvas.delete("all")
        width = max(canvas.winfo_width(), int(canvas.cget("width")))
        height = int(canvas.cget("height"))
        left, top, right, bottom = 45, 40, width - 35, height - 32
        canvas.create_text(12, 13, text=title, anchor="w", font=(self.font_family, 12, "bold"))
        maximum = max(1, max(value for _, value in points))
        end = max(1, points[-1][0])

        canvas.create_line(left, top, left, bottom, right, bottom, fill="#8d99a3")
        for fraction in (0, 0.5, 1):
            y = bottom - (bottom - top) * fraction
            canvas.create_text(
                left - 8, y, text=f"{maximum * fraction:g}", anchor="e", font=(self.font_family, 9)
            )
            canvas.create_line(left, y, right, y, fill="#e4e8eb")

        coordinates = [
            (left + (right - left) * hour / end, bottom - (bottom - top) * value / maximum)
            for hour, value in points
        ]
        if len(coordinates) > 1:
            canvas.create_line(
                *[number for point in coordinates for number in point], fill=color, width=3
            )
        for x, y in coordinates:
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)

        canvas.create_text(left, bottom + 14, text="0", font=(self.font_family, 9))
        canvas.create_text(
            right, bottom + 14, text=f"{points[-1][0]}시간", font=(self.font_family, 9)
        )
        canvas.create_text(
            right,
            top - 15,
            text=f"현재 {points[-1][1]:g}",
            anchor="e",
            font=(self.font_family, 10),
            fill=color,
        )

    def _draw_resources(self, state):
        canvas = self.power_chart
        canvas.delete("all")
        last = state["last"]
        canvas.create_text(
            12, 16, text="전력 공급 / 수요 (kW)", anchor="w", font=(self.font_family, 12, "bold")
        )
        labels = {"hospital": "병원", "pump": "펌프", "housing": "주거", "industry": "산업"}
        for index, facility in enumerate(support.PRIORITY):
            y = 48 + index * 42
            demand = support.DEMANDS[facility]
            amount = last[facility + "_kw"] if last else None
            canvas.create_text(
                62, y + 12, text=labels[facility], anchor="e", font=(self.font_family, 11)
            )
            canvas.create_rectangle(80, y, 80 + demand * 6, y + 26, fill="#e5e9ed", outline="")
            if amount is not None:
                canvas.create_rectangle(80, y, 80 + amount * 6, y + 26, fill="#6b9fbe", outline="")
            canvas.create_text(
                395,
                y + 12,
                text=f"{self.number(amount)} / {demand}",
                anchor="w",
                font=(self.font_family, 11),
            )

        caption = (
            "시간 갱신 전"
            if last is None
            else f"비상전원 {last['backup_kw']:g} kW / 남은 에너지 {state['battery_kwh']:g} kWh"
        )
        canvas.create_text(12, 224, text=caption, anchor="w", font=(self.font_family, 10))

        self._line_plot(
            self.water_chart,
            "물탱크 저장량 (m³)",
            [(0, 10)] + [(row["hour"], row["water_stored"]) for row in state["history"]],
            "#256a96",
        )

        canvas = self.pollution_chart
        canvas.delete("all")
        canvas.create_text(
            12, 16, text="오염물질의 이동 / 제거", anchor="w", font=(self.font_family, 12, "bold")
        )
        for index, amount in enumerate(state["pollution"]):
            left = 15 + index * 173
            intensity = min(1, amount / 100)
            fill = "#%02x%02x%02x" % (248, int(240 - intensity * 112), int(222 - intensity * 132))
            canvas.create_rectangle(
                left, 45, left + 155, 105, fill=fill, outline="#545d65", width=2
            )
            canvas.create_text(
                left + 77, 75, text=f"셀 {index + 1}\n{amount:.2f}", font=(self.font_family, 12)
            )
        canvas.create_text(
            15,
            127,
            text="초기 1회 배출 100단위 / 동쪽 이동 20% / 이후 제거 10%",
            anchor="w",
            font=(self.font_family, 10),
        )
        canvas.create_text(
            15,
            151,
            text="동쪽 끝은 닫힌 경계 / 값은 실제 대기 농도가 아닙니다.",
            anchor="w",
            font=(self.font_family, 10),
        )

        supplied = "—" if last is None else f"{last['water_supplied']:g}"
        text = (
            f"급수: 이번 공급 {supplied} / 수요 8 m³\n"
            f"폐기물: 도시 {state['waste_city']:g} t / 처리시설 {state['waste_plant']:g} t\n"
            "폐기물은 24시간마다 발생 8 / 수거 능력 6 / 처리 능력 5 t\n\n"
            f"독립된 70 dB 음원 2개: {support.noise_total([70, 70]):.1f} dB\n"
            f"빗물 유출: 포장 {support.runoff_volume(0.05, 1000, 0.8):g} m³ / 녹지 {support.runoff_volume(0.05, 1000, 0.4):g} m³\n"
            "오염과 공원 접근성은 주택 환경 점수에 반영합니다."
        )
        self.resource_details.set(text)

    def advance_services(self, count=1):
        try:
            for _ in range(count):
                support.advance_hour(self.session)
            self.refresh()
            self._result_status(
                f"서비스를 {count}시간 진행했습니다. 행위자의 월과 교통의 분은 바뀌지 않습니다."
            )
        except Exception as error:
            self.refresh()
            self._fail("서비스 진행", error)

    def reset_service_run(self):
        scenario = next(
            key for key, label in support.SCENARIOS.items() if label == self.scenario_var.get()
        )
        support.reset_services(self.session, scenario)
        self.refresh()
        self._result_status("같은 현재 도로에서 서비스 상태를 0시간으로 되돌렸습니다.")

    def use_preset(self, name):
        super().use_preset(name)
        support.reset_services(self.session)
        self.refresh()

    def _reset_run(self, message):
        super()._reset_run(message)
        support.reset_services(self.session)
        self._refresh_services()

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".json",
            filetypes=[("도시 상태", "*.json")],
            initialfile="city_services.json",
        )
        if path:
            try:
                support.save_session(self.session, path)
                self.status.set("도시 / 행위자 / 서비스 상태를 저장했습니다.")
            except Exception as error:
                self._fail("저장", error)

    def load_file(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("도시 상태", "*.json")])
        if path:
            try:
                self.session = support.load_session(path)
                self.selected = self.session["transport"]["selected_road"]
                self.neighborhood = Neighborhood()
                self.threshold.set("0.5")
                self.refresh()
                self._result_status("도시 / 행위자 / 서비스 상태를 복원했습니다.")
            except Exception as error:
                self._fail("불러오기", error)

    def export_services(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="services_hours.csv",
        )
        if path:
            try:
                support.export_history(self.session, path)
                self.status.set("시간별 서비스 기록을 저장했습니다.")
            except Exception as error:
                self._fail("시간별 CSV", error)


def launch(smoke=False):
    root = tk.Tk()
    app = ServiceApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        app.calculate()
        root.destroy()
        print("GUI 확인: 기존 도시 / 행위자 / 공공서비스 화면 생성 성공")
    else:
        root.mainloop()

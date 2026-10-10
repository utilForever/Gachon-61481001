"""시민 / 가구 / 기업의 상태와 이웃 격자를 표시하는 Tkinter GUI."""

import ast
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import abm_support
import kpi_support
from kpi_gui import KpiApp
from gui import CityApp
from neighborhood import Neighborhood
from traffic_data import step_selected_queue, sync_transport


class AgentApp(KpiApp):
    def __init__(self, root):
        self.neighborhood = Neighborhood()
        super().__init__(root)
        root.title("가상 도시 / 행위자")
        root.geometry("1440x880")
        root.minsize(1230, 780)
        self.notebook.select(self.agent_tab)
        self._result_status("가구의 주거지와 시민의 일자리를 확인하세요.")

    def _make_widgets(self):
        super()._make_widgets()
        self.agent_tab = ttk.Frame(self.notebook, padding=10)
        self.neighbor_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.agent_tab, text="시민 / 가구 / 기업")
        self.notebook.add(self.neighbor_tab, text="이웃과 도시 변화")

        row = ttk.Frame(self.agent_tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="행위자 상태", style="Title.TLabel").pack(side="left")
        ttk.Button(row, text="월별 CSV", command=self.export_months).pack(side="right")
        ttk.Button(row, text="6개월 진행", command=lambda: self.advance_months(6)).pack(
            side="right", padx=5
        )
        ttk.Button(row, text="1개월 진행", command=self.advance_months).pack(side="right")

        left = ttk.Frame(self.agent_tab)
        left.pack(side="left", anchor="n")
        self.agent_canvas = tk.Canvas(
            left,
            width=464,
            height=378,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8bec4",
        )
        self.agent_canvas.pack()
        ttk.Label(left, text="A~D: 주택 / X~Y: 사업장 / P: 공원").pack(anchor="w", pady=5)
        self.person_tree = self._tree(
            left,
            (
                ("id", "시민", 65),
                ("household", "가구", 70),
                ("home", "주택", 70),
                ("firm", "기업", 75),
                ("commute", "통근(분)", 95),
            ),
            3,
        )
        self.person_tree.pack(fill="x", pady=6)
        ttk.Label(
            left,
            text="주거지는 소속 가구에서 조회합니다.\n통근 시간은 현재 도로와 사업장 위치로 계산합니다.",
            wraplength=450,
        ).pack(anchor="w")

        right = ttk.Frame(self.agent_tab, padding=(18, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="가구", style="Stats.TLabel").pack(anchor="w")
        self.household_tree = self._tree(
            right,
            (
                ("id", "가구", 65),
                ("home", "주택", 65),
                ("score", "만족도", 80),
                ("savings", "저축", 80),
                ("months", "연속 불만(월)", 120),
                ("cooldown", "대기(월)", 95),
            ),
            2,
        )
        self.household_tree.pack(fill="x", pady=(3, 10))

        picker_row = ttk.Frame(right)
        picker_row.pack(fill="x")
        ttk.Label(picker_row, text="조사할 가구 ").pack(side="left")
        self.household_selection = tk.StringVar(value="H1")
        picker = ttk.Combobox(
            picker_row,
            textvariable=self.household_selection,
            values=("H1", "H2"),
            state="readonly",
            width=8,
        )
        picker.pack(side="left")
        picker.bind("<<ComboboxSelected>>", lambda event: self._refresh_agents())
        ttk.Label(picker_row, text="순서대로 최대 3곳 / 개선 폭 10점 이상").pack(side="right")
        self.candidate_tree = self._tree(
            right,
            (
                ("home", "후보 주택", 110),
                ("score", "만족도", 100),
                ("rent", "임대료", 100),
                ("available", "입주 가능", 100),
            ),
            3,
        )
        self.candidate_tree.pack(fill="x", pady=(4, 12))
        ttk.Label(right, text="기업", style="Stats.TLabel").pack(anchor="w")

        self.firm_tree = self._tree(
            right,
            (
                ("firm", "기업", 75),
                ("site", "사업장", 80),
                ("profit", "월 이익", 100),
                ("cash", "이전 자금", 100),
                ("workers", "고용 시민", 190),
            ),
            1,
        )
        self.firm_tree.pack(fill="x", pady=(4, 8))
        ttk.Label(
            right, text="분기마다 이전 검토 / 앞으로의 6개월 이익 비교 / 시민의 고용 관계 유지"
        ).pack(anchor="w")

        self.event_list = tk.Listbox(
            right, height=4, relief="flat", background="#f3f5f7", font=(self.font_family, 11)
        )
        self.event_list.pack(fill="both", expand=True, pady=(10, 0))

        self._make_neighborhood()
        self._replace_labels(self.root)

    @staticmethod
    def _tree(parent, columns, height):
        tree = ttk.Treeview(
            parent,
            columns=tuple(c[0] for c in columns),
            show="headings",
            height=height,
            selectmode="none",
        )
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=55, anchor="center")
        return tree

    def _replace_labels(self, widget):
        replacements = {
            "도시 지표": "가상 도시",
            "H / A: 주택 / J: 상점 / F: 공장 / P: 공원": "A~D: 주택 / X~Y: 사업장 / P: 공원",
            "모든 주민이 상점 J로 한 번씩 통근한다고 가정합니다.\n도달할 수 없는 주민은 평균에서 제외하고 별도로 셉니다.\n1분 진행할 때 선택한 도로의 대기열만 갱신합니다.": "통근 지표는 취업 시민만 대상으로 합니다.\n목적지는 각 시민이 고용된 기업의 현재 사업장입니다.\n교통의 분 단위 시간과 행위자의 월 단위 시간은 독립적입니다.",
            "설정 / 도시 / 관찰 도로를 바꾸면 기존 기록을 지우고 0분부터 시작합니다.": "분: 교통 대기열 갱신 / 월: 가구와 기업의 의사결정",
        }
        if isinstance(widget, ttk.Label):
            text = widget.cget("text")
            if text in replacements:
                widget.configure(text=replacements[text])

        for child in widget.winfo_children():
            self._replace_labels(child)

    def _make_neighborhood(self):
        row = ttk.Frame(self.neighbor_tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="이웃과 도시 변화", style="Title.TLabel").pack(side="left")
        self.threshold = tk.StringVar(value="0.5")
        ttk.Label(row, text="만족 기준 ").pack(side="left", padx=(20, 0))
        ttk.Combobox(
            row,
            textvariable=self.threshold,
            values=("0.25", "0.5", "0.75"),
            state="readonly",
            width=6,
        ).pack(side="left")
        ttk.Button(row, text="초기화", command=self.reset_neighbors).pack(side="left", padx=5)
        ttk.Button(row, text="10회 진행", command=lambda: self.advance_neighbors(10)).pack(
            side="right"
        )
        ttk.Button(row, text="1회 진행", command=self.advance_neighbors).pack(side="right", padx=5)

        self.neighbor_canvas = tk.Canvas(
            self.neighbor_tab, width=610, height=555, background="white", highlightthickness=0
        )
        self.neighbor_canvas.pack(side="left", anchor="n")

        right = ttk.Frame(self.neighbor_tab, padding=15)
        right.pack(side="left", fill="both", expand=True)
        self.neighbor_summary = tk.StringVar()
        ttk.Label(
            right, textvariable=self.neighbor_summary, style="Stats.TLabel", justify="left"
        ).pack(anchor="w", pady=(0, 20))
        ttk.Label(
            right,
            text="주변 8칸에서 거주자가 있는 칸만 셉니다.\n주변 거주자가 없으면 만족한 것으로 처리합니다.\n불만족한 행위자는 만족할 수 있는 빈칸으로 이동합니다.\n\nA / B는 임의의 두 유형입니다.\n이 격자는 이웃 규칙을 관찰하는 별도 모형입니다.\n도시의 주택 / 기업 모형에는 영향을 주지 않습니다.",
            wraplength=590,
            justify="left",
        ).pack(anchor="w")
        self.neighbor_tree = self._tree(
            right,
            (
                ("round", "회차", 75),
                ("moved", "이번 이동", 110),
                ("unhappy", "불만족", 100),
                ("ratio", "이웃 비율 평균", 155),
            ),
            10,
        )
        self.neighbor_tree.pack(fill="both", expand=True, pady=(20, 0))

    def refresh(self):
        if "agents" not in self.session:
            self.session = abm_support.make_session()
            self.selected = self.session["transport"]["selected_road"]

        self.kpis = abm_support.calculate_kpis(self.session)
        super().refresh()

        state = self.session["agents"]
        self.overview.set(
            f"{state['month']}개월 / 교통 {self.session['transport']['minute']}분 / 시민 3명"
        )
        items = self.metric_tree.get_children()
        replacements = {
            2: "취업 시민 중 기준 시간 이내 도달",
            3: "현재 사업장까지 이어지는 경로가 없음",
            4: "도달 가능한 취업 시민만 포함",
        }
        for index, text in replacements.items():
            values = list(self.metric_tree.item(items[index], "values"))
            values[2] = text
            self.metric_tree.item(items[index], values=values)

        self._refresh_agents()
        self._refresh_neighbors()

    def _refresh_agents(self):
        if "agents" not in self.session:
            return

        state = self.session["agents"]
        original = self.canvas
        self.canvas = self.agent_canvas
        CityApp._draw_map(self)
        self.canvas = original

        for tree in (self.person_tree, self.household_tree, self.candidate_tree, self.firm_tree):
            tree.delete(*tree.get_children())

        trips = {
            trip["citizen_id"]: trip["time_min"]
            for trip in abm_support.commute_records(self.session)
        }
        for ident, person in state["citizens"].items():
            home = state["households"][person["household_id"]]["home_id"]
            self.person_tree.insert(
                "",
                "end",
                values=(
                    ident,
                    person["household_id"],
                    home,
                    person["employer_id"] or "없음",
                    self.display(trips.get(ident)),
                ),
            )

        for ident, household in state["households"].items():
            try:
                score = abm_support.score_home(self.session, ident, household["home_id"])
            except (NotImplementedError, TypeError, ValueError):
                score = None
            self.household_tree.insert(
                "",
                "end",
                values=(
                    ident,
                    household["home_id"],
                    self.display(score),
                    household["savings"],
                    household["dissatisfied_months"],
                    household["cooldown"],
                ),
            )
        try:
            candidates = abm_support.home_candidates(self.session, self.household_selection.get())
        except (NotImplementedError, TypeError, ValueError):
            candidates = []

        for candidate in candidates[:3]:
            home = candidate["home_id"]
            self.candidate_tree.insert(
                "",
                "end",
                values=(
                    home,
                    self.display(candidate["score"]),
                    state["houses"][home]["rent"],
                    "가능" if candidate["feasible"] else "불가",
                ),
            )

        for ident, firm in state["firms"].items():
            self.firm_tree.insert(
                "",
                "end",
                values=(
                    ident,
                    firm["site_id"],
                    firm["profit"],
                    firm["cash"],
                    " / ".join(firm["employees"]),
                ),
            )

        self.event_list.delete(0, "end")
        for event in state["events"]:
            self.event_list.insert("end", event)

    def _refresh_neighbors(self):
        canvas = self.neighbor_canvas
        canvas.delete("all")
        for y, row in enumerate(self.neighborhood.labels()):
            for x, label in enumerate(row):
                left, top = 22 + x * 63, 20 + y * 63
                color = {"A": "#c8def3", "B": "#f4d8aa", None: "#ffffff"}[label]
                canvas.create_rectangle(
                    left, top, left + 61, top + 61, fill=color, outline="#9daab3"
                )
                if label:
                    canvas.create_text(
                        left + 30, top + 30, text=label, font=(self.font_family, 18, "bold")
                    )
        try:
            snapshot = self.neighborhood.snapshot()
            value = str(snapshot["dissatisfied"])
        except (NotImplementedError, TypeError, ValueError):
            value = "—"
        self.neighbor_summary.set(
            f"{self.neighborhood.round}회차 / 시드 {self.neighborhood.seed}\n유형 A 25명 / 유형 B 25명 / 빈칸 14개\n불만족 {value}명 / 누적 이동 {self.neighborhood.moves_total}회"
        )

        self.neighbor_tree.delete(*self.neighbor_tree.get_children())
        for row in self.neighborhood.history:
            self.neighbor_tree.insert(
                "",
                "end",
                values=(
                    row["round"],
                    row["moves"],
                    row["dissatisfied"],
                    self.display(row["mean_ratio"], percent=True),
                ),
            )

    def _result_status(self, message):
        source = ast.parse(Path(__file__).with_name("agent_rules.py").read_text(encoding="utf-8"))
        functions = [node for node in source.body if isinstance(node, ast.FunctionDef)]
        pending = [
            str(index)
            for index, node in enumerate(functions, 1)
            if any(isinstance(child, ast.Raise) for child in ast.walk(node))
        ]
        self.status.set(message + (" / 미완료: TODO " + ", ".join(pending) if pending else ""))

    def calculate(self):
        self.kpis = abm_support.record_current(self.session)
        self.refresh()
        self._result_status("현재 시민의 고용 관계를 기준으로 지표를 계산했습니다.")

    def advance(self, count=1):
        try:
            for _ in range(count):
                state = self.session["transport"]
                node = state["selected_road"]
                self.session["observations"].append(
                    dict(
                        start_minute=state["minute"],
                        duration_min=1,
                        queue=state["queues"][node],
                        road=node,
                    )
                )
                self.session["transport"] = step_selected_queue(state)
                abm_support.record_current(self.session)
            self.refresh()
            self._result_status(f"교통을 {count}분 진행했습니다. 행위자의 월은 바뀌지 않습니다.")
        except Exception as error:
            self._fail("교통 진행", error)

    def advance_months(self, count=1):
        try:
            for _ in range(count):
                abm_support.advance_month(self.session)
            self.refresh()
            self._result_status(f"{count}개월 진행했습니다. 교통의 분은 바뀌지 않습니다.")
        except Exception as error:
            self._fail("월 진행", error)

    def advance_neighbors(self, count=1):
        try:
            for _ in range(count):
                self.neighborhood.advance()
                if self.neighborhood.history[-1]["moves"] == 0:
                    break
            self._refresh_neighbors()
            self._result_status("이웃의 변화와 불만족 인원을 비교하세요.")
        except Exception as error:
            self._fail("이웃 갱신", error)

    def reset_neighbors(self):
        self.neighborhood = Neighborhood(threshold=float(self.threshold.get()))
        self._refresh_neighbors()

    def _reset_run(self, message):
        self.session["transport"]["minute"] = 0
        self.session["transport"]["last_served"] = 0
        self.session["history"] = []
        self.session["observations"] = []
        self.calculate()
        self._result_status(message)

    def use_preset(self, name):
        self.session = abm_support.make_session(name)
        self.selected = self.session["transport"]["selected_road"]
        self.refresh()
        self._result_status("도시와 행위자를 초기화했습니다.")

    def _apply_city(self, city, transport=None):
        candidate = deepcopy(self.session)
        for ident in candidate["agents"]["houses"]:
            if ident not in city["buildings"] or city["buildings"][ident]["kind"] != "house":
                raise ValueError("행위자가 참조하는 A~D 주택은 유지하세요.")
        for ident in candidate["agents"]["sites"]:
            if ident not in city["buildings"] or city["buildings"][ident]["kind"] not in (
                "shop",
                "factory",
            ):
                raise ValueError("기업이 참조하는 X / Y 사업장은 유지하세요.")

        candidate["city"] = deepcopy(city)
        candidate["transport"] = sync_transport(city, deepcopy(transport or candidate["transport"]))
        abm_support.synchronize_buildings(candidate)
        abm_support.validate_agents(candidate)

        self.session = candidate
        self.selected = candidate["transport"]["selected_road"]
        self._reset_run("도시와 교통 상태를 적용했습니다. 분 단위 기록을 초기화했습니다.")

    def show_errors(self):
        messagebox.showinfo("계산 상태", self.status.get(), parent=self.root)

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".json",
            filetypes=[("도시 상태", "*.json")],
            initialfile="city_abm.json",
        )

        if path:
            try:
                abm_support.save_session(self.session, path)
                self.status.set(
                    "도시와 행위자 상태를 저장했습니다. 이웃 격자는 별도로 초기화됩니다."
                )
            except Exception as error:
                self._fail("저장", error)

    def load_file(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("도시 상태", "*.json")])

        if path:
            try:
                self.session = abm_support.load_session(path)
                self.selected = self.session["transport"]["selected_road"]
                self.neighborhood = Neighborhood()
                self.threshold.set("0.5")
                self.refresh()
                self._result_status("도시와 행위자 상태를 복원했습니다.")
            except Exception as error:
                self._fail("불러오기", error)

    def export_months(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="agents_months.csv",
        )

        if path:
            try:
                abm_support.export_months(self.session, path)
                self.status.set("월별 행위자 기록을 저장했습니다.")
            except Exception as error:
                self._fail("월별 CSV", error)


def launch(smoke=False):
    root = tk.Tk()
    app = AgentApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        app.calculate()
        root.destroy()
        print("GUI 확인: 도시 / 행위자 / 이웃 화면 생성 성공")
    else:
        root.mainloop()

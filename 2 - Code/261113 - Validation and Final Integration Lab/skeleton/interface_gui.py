"""도시 조회, 지도 표시, 시간별 기록과 관측 자료를 연결하는 Tkinter GUI."""

import tkinter as tk
from tkinter import filedialog, ttk
import math

from economy_gui import EconomyApp
from gui import CityApp
from neighborhood import Neighborhood
import interface_rules as rules
import interface_support as support
import service_support

BLUE = "#0078D4"
INK = "#242424"
MUTED = "#616161"
BACKGROUND = "#F4F6F9"
BORDER = "#DCE2E8"
WHITE = "#FFFFFF"
REASONS = {
    "applied": "반영",
    "stale": "이전 관측이라 제외",
    "duplicate": "같은 관측 시각이라 제외",
    "target_mismatch": "대상 ID가 달라 제외",
    "unit_mismatch": "단위가 달라 제외",
    "missing": "값이 없어 제외",
}


class InterfaceApp(EconomyApp):
    def __init__(self, root):
        self.view_target = "H"
        self.view_hour = None
        self._view_pending = set()
        self._plot_hits = []
        self._map_hits = []
        super().__init__(root)
        root.title("가상 도시 / 인터페이스와 데이터")
        root.geometry("1440x940")
        root.minsize(1280, 900)
        self.notebook.select(self.view_tab)
        self._switch_controls()
        self.refresh()
        self._result_status(
            "지도의 대상을 고르거나 그래프의 점을 눌러 같은 시점의 기록을 확인하세요."
        )

    def _set_fonts(self):
        CityApp._set_fonts(self)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=(self.font_family, 11), background=BACKGROUND, foreground=INK)
        style.configure("TFrame", background=BACKGROUND)
        style.configure("TLabel", background=BACKGROUND, foreground=INK)
        style.configure(
            "TButton",
            padding=(12, 7),
            anchor="center",
            background=WHITE,
            bordercolor=BORDER,
            lightcolor=WHITE,
            darkcolor=WHITE,
        )
        style.map("TButton", background=[("active", "#EAF2FA"), ("pressed", "#DCEBFA")])
        style.configure("Accent.TButton", background=BLUE, foreground=WHITE)
        style.map("Accent.TButton", background=[("active", "#005EA6"), ("pressed", "#004F8C")])
        style.configure("TCombobox", padding=5, fieldbackground=WHITE, background=WHITE)
        style.map(
            "TCombobox", fieldbackground=[("readonly", WHITE)], foreground=[("readonly", INK)]
        )
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(11, 7), background="#E8EDF3")
        style.map(
            "TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", BLUE)]
        )
        style.configure(
            "Treeview",
            rowheight=26,
            background=WHITE,
            fieldbackground=WHITE,
            foreground=INK,
            borderwidth=0,
        )
        style.configure("Selection.Treeview", rowheight=24)
        style.configure(
            "Treeview.Heading",
            padding=(8, 5),
            background="#E9EEF4",
            foreground=INK,
            font=(self.font_family, 11, "bold"),
        )
        style.configure("Title.TLabel", font=(self.font_family, 18, "bold"))
        style.configure("Stats.TLabel", font=(self.font_family, 12, "bold"), anchor="center")
        self.root.configure(background=BACKGROUND)

    def _make_widgets(self):
        self._set_fonts()
        super()._make_widgets()
        siblings = self.notebook.master.winfo_children()
        self._old_controls = [(widget, widget.pack_info()) for widget in siblings[2:4]]

        self.view_tab = ttk.Frame(self.notebook, padding=10)
        self.data_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.view_tab, text="도시 보기")
        self.notebook.add(self.data_tab, text="지도 자료 / 관측")
        self._make_city_view()
        self._make_data_view()
        self.notebook.bind("<<NotebookTabChanged>>", lambda event: self._switch_controls(), add="+")

    def _switch_controls(self):
        if not hasattr(self, "_old_controls"):
            return

        compact = self.notebook.select() in (str(self.view_tab), str(self.data_tab))

        for widget, options in self._old_controls:
            if compact:
                widget.pack_forget()
            elif not widget.winfo_manager():
                widget.pack(**dict(options, before=self.notebook))

    def _make_city_view(self):
        self.view_tab.columnconfigure(0, weight=1)
        self.view_tab.rowconfigure(2, weight=1)

        controls = ttk.Frame(self.view_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(2, 10))
        controls.columnconfigure(5, weight=1)
        ttk.Label(controls, text="공공서비스", style="Stats.TLabel", anchor="center").grid(
            row=0, column=0, padx=(0, 14), sticky="ns"
        )
        self.view_scenario = tk.StringVar(value="기본 조건")
        ttk.Combobox(
            controls,
            textvariable=self.view_scenario,
            values=tuple(service_support.SCENARIOS.values()),
            state="readonly",
            width=12,
            justify="center",
        ).grid(row=0, column=1, sticky="ns")
        ttk.Button(controls, text="조건 적용 / 초기화", command=self.reset_view).grid(
            row=0, column=2, padx=7
        )
        ttk.Button(controls, text="1시간 진행", command=lambda: self.advance_view(1)).grid(
            row=0, column=3, padx=(0, 7)
        )
        ttk.Button(
            controls,
            text="6시간 진행",
            style="Accent.TButton",
            command=lambda: self.advance_view(6),
        ).grid(row=0, column=4)
        self.view_clock = tk.StringVar()
        ttk.Label(controls, textvariable=self.view_clock, foreground=MUTED, anchor="e").grid(
            row=0, column=5, sticky="nsew", padx=(12, 0)
        )

        self.cards = {}
        self.card_value_labels = {}

        cards = ttk.Frame(self.view_tab)
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        for column, (key, title, color) in enumerate(
            (
                ("queue", "병원 H  대기 인원", BLUE),
                ("capacity", "병원 H  시간당 진료 가능 인원", INK),
                ("water", "급수 시설 W  공급 부족량", "#CA5010"),
            )
        ):
            cards.columnconfigure(column, weight=1, uniform="cards")

            card = tk.Frame(cards, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
            tk.Label(
                card, text=title, bg=WHITE, fg=MUTED, anchor="center", font=(self.font_family, 11)
            ).pack(fill="x", padx=12, pady=(7, 2))
            value = tk.StringVar(value="—")
            value_label = tk.Label(
                card,
                textvariable=value,
                bg=WHITE,
                fg=color,
                anchor="center",
                font=(self.font_family, 24, "bold"),
            )
            value_label.pack(fill="x", padx=12, pady=(0, 6))
            self.cards[key] = value
            self.card_value_labels[key] = value_label

        main = ttk.Frame(self.view_tab)
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1, uniform="main")
        main.columnconfigure(1, weight=1, uniform="main")
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        row = ttk.Frame(left)
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(1, weight=1)
        ttk.Label(row, text="도시 지도", style="Stats.TLabel", anchor="center").grid(
            row=0, column=0, sticky="ns"
        )

        target_controls = ttk.Frame(row)
        target_controls.grid(row=0, column=1, sticky="w", padx=12)
        ttk.Button(
            target_controls, text="병원 H", command=lambda: self.select_view_target("H")
        ).pack(side="left")
        ttk.Button(
            target_controls, text="급수 W 상태", command=lambda: self.select_view_target("W")
        ).pack(side="left", padx=(5, 0))
        self.layer = tk.StringVar(value="기본 지도")
        layer_picker = ttk.Combobox(
            row,
            textvariable=self.layer,
            values=("기본 지도", "병원 접근시간"),
            state="readonly",
            width=14,
            justify="center",
        )
        layer_picker.grid(row=0, column=2, sticky="ns")
        layer_picker.bind("<<ComboboxSelected>>", lambda event: self._refresh_interface())

        self.view_map = tk.Canvas(
            left,
            height=200,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER,
            takefocus=True,
        )
        self.view_map.pack(fill="both", expand=True)
        self.view_map.bind("<Configure>", lambda event: self._draw_view_map())
        self.view_map.bind("<Button-1>", self._pick_map)
        self.view_map.bind("<Left>", lambda event: self._move_map_selection(-1))
        self.view_map.bind("<Right>", lambda event: self._move_map_selection(1))

        self.map_legend = tk.Canvas(left, height=55, bg=WHITE, highlightthickness=0)
        self.map_legend.pack(fill="x")
        self.map_legend.bind("<Configure>", lambda event: self._draw_legend())

        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        self.selection_title = tk.StringVar(value="선택한 대상")
        ttk.Label(
            right, textvariable=self.selection_title, style="Stats.TLabel", anchor="center"
        ).pack(fill="x", pady=(6, 9))

        self.selection_tree = self._tree(right, (("label", "항목", 180), ("value", "상태", 390)), 3)
        self.selection_tree.configure(show="", style="Selection.Treeview")
        self.selection_tree.pack(fill="x")
        self.warning = tk.StringVar()

        self.warning_box = tk.Frame(
            right, bg="#FFF4E5", highlightbackground="#F2D2A3", highlightthickness=1
        )
        self.warning_box.pack(fill="x", pady=(10, 10))
        self.warning_label = tk.Label(
            self.warning_box,
            textvariable=self.warning,
            bg="#FFF4E5",
            fg="#8A3700",
            font=(self.font_family, 10),
            justify="left",
            anchor="w",
            padx=12,
            pady=9,
        )
        self.warning_label.pack(fill="x")
        self.warning_box.bind(
            "<Configure>", lambda e: self.warning_label.configure(wraplength=max(200, e.width - 28))
        )
        self.log_title = tk.StringVar(value="같은 시점의 이벤트")
        ttk.Label(right, textvariable=self.log_title, style="Stats.TLabel", anchor="center").pack(
            fill="x", pady=(0, 7)
        )

        log_holder = tk.Frame(right, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        log_holder.pack(fill="both", expand=True)
        self.view_log = tk.Text(
            log_holder,
            height=5,
            wrap="word",
            relief="flat",
            bg=WHITE,
            fg=INK,
            font=(self.font_family, 10),
            padx=12,
            pady=8,
            state="disabled",
            cursor="arrow",
            spacing3=8,
        )
        scroll = ttk.Scrollbar(log_holder, orient="vertical", command=self.view_log.yview)
        self.view_log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.view_log.pack(side="left", fill="both", expand=True)
        self.view_log.tag_configure(
            "event_title",
            foreground="#8A3700",
            font=(self.font_family, 10, "bold"),
            spacing1=3,
            spacing3=3,
        )
        self.view_log.tag_configure("event_body", foreground=INK, spacing3=9)
        self.view_log.tag_configure("empty", foreground=MUTED)

        chart_bar = ttk.Frame(self.view_tab)
        chart_bar.grid(row=3, column=0, sticky="ew", pady=(10, 6))
        ttk.Label(chart_bar, text="병원 H  시간별 대기 인원", style="Stats.TLabel").pack(
            side="left"
        )
        ttk.Label(
            chart_bar, text="점 선택 또는 ← → 이동: 같은 시점의 상태와 기록 확인", foreground=MUTED
        ).pack(side="right")

        self.view_plot = tk.Canvas(
            self.view_tab,
            height=160,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER,
            takefocus=True,
        )
        self.view_plot.grid(row=4, column=0, sticky="ew")
        self.view_plot.bind("<Configure>", lambda event: self._draw_view_plot())
        self.view_plot.bind("<Button-1>", self._pick_plot)
        self.view_plot.bind("<Left>", lambda event: self._move_plot_selection(-1))
        self.view_plot.bind("<Right>", lambda event: self._move_plot_selection(1))

    def _make_data_view(self):
        self.data_notebook = ttk.Notebook(self.data_tab)
        self.data_notebook.pack(fill="both", expand=True)

        self.map_data_tab = ttk.Frame(self.data_notebook, padding=12)
        self.observation_tab = ttk.Frame(self.data_notebook, padding=12)
        self.data_notebook.add(self.map_data_tab, text="공간 자료를 셀로 변환")
        self.data_notebook.add(self.observation_tab, text="관측 자료 확인")
        ttk.Label(
            self.map_data_tab, text="점·선·면 자료를 격자에서 확인하기", style="Stats.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            self.map_data_tab,
            text="가상 OSM 구조 자료 / 좌표 단위: m / 기존 도시에는 자동 반영하지 않습니다.",
            foreground=MUTED,
        ).pack(anchor="w", pady=(5, 14))

        row = ttk.Frame(self.map_data_tab)
        row.pack(fill="x")
        self.point_x = tk.StringVar(value="45")
        self.point_y = tk.StringVar(value="30")

        for label, var in (("동쪽 좌표 x", self.point_x), ("북쪽 좌표 y", self.point_y)):
            ttk.Label(row, text=label + " ").pack(side="left")
            ttk.Entry(row, textvariable=var, width=8).pack(side="left", padx=(0, 12))

        ttk.Button(row, text="셀 좌표 확인", command=self.convert_point).pack(side="left")
        ttk.Button(row, text="지도 자료 변환", command=self.preview_map).pack(side="right")
        self.point_result = tk.StringVar(
            value="왼쪽 아래가 원점입니다. 행 0은 화면의 맨 위에 있습니다."
        )
        ttk.Label(self.map_data_tab, textvariable=self.point_result, foreground=BLUE).pack(
            anchor="w", pady=(9, 10)
        )

        self.preview_canvas = tk.Canvas(
            self.map_data_tab,
            height=330,
            bg="white",
            highlightthickness=1,
            highlightbackground="#DFE3E8",
        )
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda event: self._draw_map_preview())
        self.preview_summary = tk.StringVar()
        ttk.Label(
            self.map_data_tab, textvariable=self.preview_summary, wraplength=1250, justify="left"
        ).pack(anchor="w", pady=(9, 0))
        self._preview = None
        self._point_cell = None

        row = ttk.Frame(self.observation_tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="병원 H  대기 인원", style="Stats.TLabel").pack(side="left")
        ttk.Button(row, text="초기화", command=self.reset_observations).pack(side="right")
        ttk.Button(row, text="다음 관측 받기", command=self.receive_observation).pack(
            side="right", padx=5
        )
        ttk.Label(
            self.observation_tab,
            text="예제 관측 자료입니다. 관측한 시각과 받은 시각을 구분해 확인하세요.",
            foreground=MUTED,
        ).pack(anchor="w", pady=(0, 12))
        self.observation_summary = tk.StringVar()

        comparison = ttk.Frame(self.observation_tab)
        comparison.pack(fill="x", pady=(0, 15))
        self.observation_cards = {}

        for column, (key, title, color) in enumerate(
            (("model", "모형 계산값", BLUE), ("observed", "예제 관측값", "#6F137C"))
        ):
            comparison.columnconfigure(column, weight=1, uniform="observation")

            card = tk.Frame(comparison, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
            value, detail = tk.StringVar(), tk.StringVar()
            tk.Label(card, text=title, bg=WHITE, fg=MUTED, font=(self.font_family, 11)).pack(
                fill="x", pady=(8, 2)
            )
            tk.Label(
                card, textvariable=value, bg=WHITE, fg=color, font=(self.font_family, 23, "bold")
            ).pack(fill="x")
            tk.Label(
                card, textvariable=detail, bg=WHITE, fg=MUTED, font=(self.font_family, 10)
            ).pack(fill="x", pady=(3, 8))
            self.observation_cards[key] = (value, detail)

        columns = (
            ("id", "대상", 65),
            ("value", "값", 70),
            ("unit", "단위", 70),
            ("observed", "관측 시각", 115),
            ("received", "수신 시각", 115),
            ("result", "처리 결과", 280),
        )

        self.observation_tree = self._tree(self.observation_tab, columns, 8)
        self.observation_tree.pack(fill="both", expand=True)
        self.observation_tree.tag_configure("accepted", foreground="#107C10")
        self.observation_tree.tag_configure("rejected", foreground="#8A3700")
        ttk.Label(
            self.observation_tab,
            text="모형 계산값과 관측값은 따로 보관합니다. 관측 시각과 단위를 확인한 뒤 비교하세요.\n이 자료는 가상 예제이며, 실제 도시와 실시간으로 연결되어 있지 않습니다.",
            foreground=MUTED,
            justify="left",
        ).pack(anchor="w", pady=(13, 0))

    def _call_view(self, stage, function, *args):
        try:
            result = function(*args)
            self._view_pending.discard(stage)

            return result
        except NotImplementedError:
            self._view_pending.add(stage)
            return None
        except Exception as error:
            self._result_status(f"화면 계산을 확인하세요: {error}")
            return None

    def _result_status(self, message):
        pending = sorted(getattr(self, "_view_pending", ()))
        if pending:
            message = "아직 작성하지 않은 표시 기능이 있습니다. 코드를 저장한 뒤 다시 실행하세요."

        self.status.set(message)

    def refresh(self):
        super().refresh()
        if hasattr(self, "view_plot"):
            self._refresh_interface()

    def _refresh_interface(self):
        state = support.ensure_state(self.session)
        current_hour = self.session["services"]["hour"]
        if self.view_hour is None or self.view_hour > current_hour:
            self.view_hour = current_hour

        state["selected_target"] = self.view_target
        state["selected_hour"] = self.view_hour
        self.view_scenario.set(service_support.SCENARIOS[self.session["services"]["scenario"]])
        self.view_clock.set(f"현재 {current_hour}시간째    선택 {self.view_hour}시간째")
        feature = support.selection_feature(self.session, self.view_target, self.view_hour)
        info = self._call_view(1, rules.build_selection_info, feature, self.view_hour)
        self.selection_tree.delete(*self.selection_tree.get_children())
        self.selection_title.set("선택한 대상" if info is None else info["title"])
        if info is not None:
            for label, value in (
                ("선택 시점", info["time_label"]),
                (info["metric"], info["value_label"]),
                ("자료 출처", info["source_label"]),
            ):
                self.selection_tree.insert("", "end", values=(label, value))

        dashboard = support.dashboard(self.session, self.view_hour)

        for key, target in (("queue", "H"), ("water", "W")):
            card_feature = support.selection_feature(self.session, target, self.view_hour)
            card_info = self._call_view(1, rules.build_selection_info, card_feature, self.view_hour)
            self.cards[key].set("—" if card_info is None else card_info["value_label"])

        capacity_feature = {
            "id": "H",
            "name": "병원 H",
            "metric": "진료 가능 인원",
            "value": dashboard["capacity"],
            "unit": "명/시간",
            "source": "simulation",
        }
        capacity_info = self._call_view(
            1, rules.build_selection_info, capacity_feature, self.view_hour
        )
        self.cards["capacity"].set("—" if capacity_info is None else capacity_info["value_label"])
        water = dashboard["water_unmet"]
        self.card_value_labels["water"].configure(
            fg="#CA5010" if water is not None and water > 0 else INK
        )
        if water is not None and water > 0:
            self.warning.set(
                f"급수 부족 {water:g}m³: 급수 공급량과 병원의 시간당 진료 가능 인원을 확인하세요."
            )
            self.warning_box.configure(bg="#FFF4E5", highlightbackground="#F2D2A3")
            self.warning_label.configure(bg="#FFF4E5", fg="#8A3700")
        else:
            self.warning.set("급수 상태 정상  공급 부족량이 없습니다.")
            self.warning_box.configure(bg="#F0F7F2", highlightbackground="#CEE3D3")
            self.warning_label.configure(bg="#F0F7F2", fg="#27623A")

        events = self._call_view(
            4, rules.find_events, support.event_log(self.session), self.view_hour, self.view_target
        )
        self.log_title.set(f"{self.view_hour}시간째 기록  {feature['name']}")
        self.view_log.configure(state="normal")
        self.view_log.delete("1.0", "end")

        for index, event in enumerate(events or []):
            label = "주의" if event.get("severity") == "warning" else "안내"
            self.view_log.insert(
                "end", f"{label}  {event.get('title', '도시 상태 변경')}\n", "event_title"
            )
            self.view_log.insert("end", event["message"] + "\n", "event_body")

        if not events:
            self.view_log.insert(
                "end",
                (
                    "같은 시점의 이벤트가 없습니다."
                    if events is not None
                    else "표시할 기록을 준비 중입니다."
                ),
                "empty",
            )

        self.view_log.configure(state="disabled")
        self._draw_view_map()
        self._draw_legend()
        self._draw_view_plot()
        self._refresh_observations()
        if self._view_pending:
            self._result_status("")

    def _draw_view_map(self):
        if not hasattr(self, "view_map"):
            return

        canvas = self.view_map
        canvas.delete("all")
        self._map_hits = []
        rows, cols = len(self.city["grid"]), len(self.city["grid"][0])
        width, height = max(480, canvas.winfo_width()), max(150, canvas.winfo_height())
        cw, ch = (width - 40) / cols, (height - 36) / rows
        times = support.travel_times(self.session)

        for y, row in enumerate(self.city["grid"]):
            for x, cell in enumerate(row):
                left, top = 20 + x * cw, 18 + y * ch
                color = "#C9CDD2" if cell["road"] else "#F0F3F6"
                canvas.create_rectangle(
                    left, top, left + cw - 4, top + ch - 4, fill=color, outline="white"
                )

        for ident, building in self.city["buildings"].items():
            x, y = building["x"], building["y"]
            left, top = 20 + x * cw, 18 + y * ch
            label, color = ident, "#E4E9EE"
            if ident in times:
                value = times[ident]
                label = f"주거지 {ident}\n100명"
                color = "#DCEBF8"
                if self.layer.get() == "병원 접근시간":
                    style = self._call_view(2, rules.layer_style, value)
                    color = style["color"] if style else "#E4E9EE"
                    label = (
                        f"{ident}\n{'경로 없음' if value is None else f'{value:g}분'}"
                        if style
                        else f"{ident}\n—"
                    )

                self._map_hits.append((left, top, left + cw - 4, top + ch - 4, ident))
            elif ident == "P":
                label, color = "공원 P", "#DFF0DE"
            else:
                label = f"사업장 {ident}"

            selected = ident == self.view_target
            canvas.create_rectangle(
                left,
                top,
                left + cw - 4,
                top + ch - 4,
                fill=color,
                outline="#111111" if selected else "white",
                width=4 if selected else 1,
            )
            dark = (
                self.layer.get() == "병원 접근시간"
                and ident in times
                and 2 not in self._view_pending
            )
            canvas.create_text(
                left + (cw - 4) / 2,
                top + (ch - 4) / 2,
                text=label,
                justify="center",
                anchor="center",
                fill="white" if dark else INK,
                font=(self.font_family, 11, "bold"),
            )

        left, top = 20, 18 + 2 * ch
        radius = min(cw, ch) * 0.43
        cx, cy = left + (cw - 4) / 2, top + (ch - 4) / 2
        canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=BLUE,
            outline=INK if self.view_target == "H" else "white",
            width=4,
        )
        canvas.create_text(
            cx,
            cy,
            text="H\n병원",
            justify="center",
            anchor="center",
            fill="white",
            font=(self.font_family, 10, "bold"),
        )
        self._map_hits.append((cx - radius, cy - radius, cx + radius, cy + radius, "H"))
        canvas.create_text(
            width - 23,
            height - 6,
            text="현재 도로망 기준  /  굵은 테두리: 선택한 대상",
            anchor="se",
            fill=MUTED,
            font=(self.font_family, 9),
        )

    def _draw_legend(self):
        if not hasattr(self, "map_legend"):
            return

        canvas = self.map_legend
        canvas.delete("all")
        width = max(480, canvas.winfo_width())
        if self.layer.get() == "기본 지도":
            for index, label in enumerate(("A~D  주거지", "H  병원", "X·Y  사업장", "P  공원")):
                canvas.create_text(
                    (index + 0.5) * width / 4,
                    26,
                    text=label,
                    anchor="center",
                    justify="center",
                    fill=MUTED,
                    font=(self.font_family, 10),
                )

            return

        for index, value in enumerate((5, 15, 16, None)):
            style = self._call_view(2, rules.layer_style, value)
            cx = (index + 0.5) * width / 4
            color = style["color"] if style else "#E4E9EE"
            label = style["label"] if style else "—"
            canvas.create_rectangle(cx - 22, 9, cx + 22, 16, fill=color, outline="")
            canvas.create_text(
                cx,
                34,
                text=label,
                anchor="center",
                justify="center",
                fill=INK,
                font=(self.font_family, 9),
            )

    def _draw_view_plot(self):
        if not hasattr(self, "view_plot"):
            return

        canvas = self.view_plot
        canvas.delete("all")
        self._plot_hits = []
        points = self._call_view(
            3, rules.build_time_series, support.service_history(self.session), "queue"
        )
        if points is None:
            canvas.create_text(
                24,
                55,
                text="표시할 기록을 준비 중입니다.",
                anchor="w",
                fill=MUTED,
                font=(self.font_family, 11),
            )
            return
        if not points:
            canvas.create_text(
                24,
                55,
                text="1시간 진행하면 시간별 기록이 쌓입니다.",
                anchor="w",
                fill=MUTED,
                font=(self.font_family, 11),
            )
            return

        width, height = max(canvas.winfo_width(), 800), max(canvas.winfo_height(), 150)
        left, right, top, bottom = 62, width - 62, 39, height - 52
        maximum = max(5, max((value for _, value in points if value is not None), default=0))
        step = max(1, math.ceil(maximum / 4))
        if step > 5:
            step = math.ceil(step / 5) * 5

        maximum = step * math.ceil(maximum / step)
        first_hour, last_hour = min(hour for hour, _ in points), max(hour for hour, _ in points)
        span = max(1, last_hour - first_hour)
        canvas.create_text(
            15, 18, text="대기 인원(명)", anchor="w", fill=MUTED, font=(self.font_family, 10)
        )
        canvas.create_text(
            right,
            height - 12,
            text="서비스 경과 시간(시간)",
            anchor="e",
            fill=MUTED,
            font=(self.font_family, 10),
        )

        for tick in range(0, maximum + 1, step):
            y = bottom - tick / maximum * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#E4E9EF")
            canvas.create_text(
                left - 12, y, text=str(tick), anchor="e", fill=MUTED, font=(self.font_family, 10)
            )

        selected_point = next(
            ((hour, value) for hour, value in points if hour == self.view_hour), None
        )
        if selected_point:
            x = left + (selected_point[0] - first_hour) / span * (right - left)
            canvas.create_line(x, top - 7, x, bottom, fill="#84B4DD", dash=(4, 4), width=1)

        previous = None
        label_step = max(1, math.ceil(len(points) / 10))

        for index, (hour, value) in enumerate(points):
            x = left + (hour - first_hour) / span * (right - left)
            if index % label_step == 0 or hour == last_hour or hour == self.view_hour:
                canvas.create_text(
                    x, bottom + 19, text=str(hour), fill=MUTED, font=(self.font_family, 10)
                )

            if value is None:
                previous = None
                canvas.create_text(
                    x, bottom - 11, text="자료 없음", fill=MUTED, font=(self.font_family, 9)
                )
                continue

            y = bottom - value / maximum * (bottom - top)
            if previous:
                canvas.create_line(*previous, x, y, fill=BLUE, width=3)

            selected = hour == self.view_hour
            radius = 6 if selected else 3.5
            canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=BLUE,
                outline=INK if selected else WHITE,
                width=2,
            )
            if selected:
                anchor = "e" if x > right - 85 else "w"
                offset = -12 if anchor == "e" else 12
                canvas.create_text(
                    x + offset,
                    y - 14,
                    text=f"{hour}시간째  {value:g}명",
                    anchor=anchor,
                    fill=BLUE,
                    font=(self.font_family, 11, "bold"),
                )

            self._plot_hits.append((x, y, hour))
            previous = (x, y)

    def _move_map_selection(self, direction):
        targets = ("A", "B", "C", "D", "H", "W")
        position = targets.index(self.view_target) if self.view_target in targets else 0
        self.select_view_target(targets[(position + direction) % len(targets)])

        return "break"

    def _move_plot_selection(self, direction):
        if self._plot_hits:
            hours = [item[2] for item in self._plot_hits]
            position = min(range(len(hours)), key=lambda i: abs(hours[i] - self.view_hour))
            self.view_target, self.view_hour = (
                "H",
                hours[max(0, min(len(hours) - 1, position + direction))],
            )
            self._refresh_interface()

        return "break"

    def _pick_map(self, event):
        self.view_map.focus_set()

        for left, top, right, bottom, ident in reversed(self._map_hits):
            if left <= event.x <= right and top <= event.y <= bottom:
                self.select_view_target(ident)
                return

    def select_view_target(self, ident):
        self.view_target = ident
        if ident in ("A", "B", "C", "D"):
            self.view_hour = self.session["services"]["hour"]

        self._refresh_interface()

    def _pick_plot(self, event):
        self.view_plot.focus_set()
        if not self._plot_hits:
            return

        x, y, hour = min(
            self._plot_hits, key=lambda item: (item[0] - event.x) ** 2 + (item[1] - event.y) ** 2
        )
        if (x - event.x) ** 2 + (y - event.y) ** 2 > 24**2:
            return

        self.view_target, self.view_hour = "H", hour
        self._refresh_interface()

    def advance_view(self, count):
        try:
            for _ in range(count):
                support.advance_hour(self.session)
            self.view_hour = self.session["services"]["hour"]
            self.refresh()
            self._result_status(
                f"공공서비스를 {count}시간 진행했습니다. 재정과 교통 시계는 그대로입니다."
            )
        except Exception as error:
            self._fail("공공서비스 진행", error)

    def reset_view(self):
        name = next(
            key
            for key, value in service_support.SCENARIOS.items()
            if value == self.view_scenario.get()
        )
        service_support.reset_services(self.session, name)
        self.view_hour, self.view_target = 0, "H"
        self.refresh()
        self._result_status("공공서비스를 0시간으로 초기화했습니다.")

    def convert_point(self):
        try:
            x, y = float(self.point_x.get()), float(self.point_y.get())
            self._point_cell = self._call_view(5, rules.point_to_cell, x, y, 0, 0, 20, 4, 5)
            if 5 in self._view_pending:
                self.point_result.set("—")
            elif self._point_cell is None:
                self.point_result.set(f"({x:g}, {y:g})m: 지도 범위 밖")
            else:
                row, col = self._point_cell
                self.point_result.set(f"({x:g}, {y:g})m: {row}행, {col}열   셀 크기 20m × 20m")

            self._draw_map_preview()
            self._result_status("미터 좌표를 셀의 행·열로 바꾸었습니다.")
        except ValueError:
            self._result_status("좌표에는 숫자를 입력하세요.")

    def preview_map(self):
        self._preview = self._call_view(5, support.map_preview)
        self._draw_map_preview()
        self._result_status("점·선·면 자료를 격자로 단순화했습니다. 기존 도시는 바뀌지 않습니다.")

    def _draw_map_preview(self):
        if not hasattr(self, "preview_canvas"):
            return

        canvas = self.preview_canvas
        canvas.delete("all")
        width, height = max(700, canvas.winfo_width()), max(300, canvas.winfo_height())
        cell = min((width - 140) / 5, (height - 70) / 4)
        left, top = (width - 5 * cell) / 2, 35
        roads = (
            set(tuple(item) for item in self._preview.get("road_cells", []))
            if self._preview
            else set()
        )
        buildings = (
            set(tuple(item) for item in self._preview.get("building_cells", []))
            if self._preview
            else set()
        )

        for row in range(4):
            for col in range(5):
                x, y = left + col * cell, top + row * cell
                color = (
                    "#B8D6F2"
                    if (row, col) in buildings
                    else "#B7BCC3" if (row, col) in roads else "#F5F7FA"
                )
                canvas.create_rectangle(x, y, x + cell, y + cell, fill=color, outline="#CAD1D9")
                if (row, col) in buildings:
                    canvas.create_text(
                        x + cell / 2,
                        y + cell / 2,
                        text="건물",
                        fill="#164B78",
                        font=(self.font_family, 12, "bold"),
                    )

                if self._point_cell == (row, col):
                    canvas.create_rectangle(
                        x + 3, y + 3, x + cell - 3, y + cell - 3, outline=BLUE, width=4
                    )

                canvas.create_text(
                    x + 7,
                    y + 7,
                    text=f"{row}행 {col}열",
                    fill=MUTED,
                    anchor="nw",
                    font=(self.font_family, 10),
                )

        if self._preview:
            for item in self._preview["points"]:
                x, y = left + item["x"] / 20 * cell, top + (4 - item["y"] / 20) * cell
                canvas.create_oval(
                    x - 7, y - 7, x + 7, y + 7, fill="#881798", outline="white", width=2
                )
                canvas.create_text(
                    x + 12,
                    y,
                    text=item["name"],
                    anchor="w",
                    fill="#6F137C",
                    font=(self.font_family, 11, "bold"),
                )

        canvas.create_text(
            left - 15,
            top - 8,
            text="북쪽 y ↑",
            anchor="sw",
            fill=MUTED,
            font=(self.font_family, 10),
        )
        canvas.create_text(
            left,
            top + 4 * cell + 15,
            text="원점 (0, 0)m",
            anchor="w",
            fill=MUTED,
            font=(self.font_family, 10),
        )
        canvas.create_text(
            left + 5 * cell,
            top + 4 * cell + 15,
            text="동쪽 x →",
            anchor="e",
            fill=MUTED,
            font=(self.font_family, 10),
        )
        if self._preview:
            point_count = len(self._preview["points"])
            outside_count = len(self._preview["outside"])
            self.preview_summary.set(
                f"점 시설 {point_count}개 / 도로 셀 {len(roads)}개 / 건물 셀 {len(buildings)}개 / 범위 밖 자료 {outside_count}개 제외\n보라색 점은 시설, 회색은 도로, 파란색은 건물입니다. 선의 폭과 곡선, 건물 모양은 단순해집니다."
            )
        else:
            self.preview_summary.set(
                "지도 자료 변환을 누르면 같은 원점·셀 크기로 도로와 건물을 표시합니다."
            )

    @staticmethod
    def _clock(minutes):
        return "—" if minutes is None else f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _refresh_observations(self):
        state = support.ensure_state(self.session)
        current = state["observation"]
        value = (
            "자료 없음" if current["value"] is None else f"{current['value']:g}{current['unit']}"
        )
        queue = self.session["services"]["queue"]
        hour = self.session["services"]["hour"]
        self.observation_summary.set(
            f"모형 계산값: {hour}시간째 {queue}명\n최근 관측값: {value} / 관측 {self._clock(current['observed_at'])} / 수신 {self._clock(current['received_at'])}"
        )
        self.observation_cards["model"][0].set(f"{queue}명")
        self.observation_cards["model"][1].set(f"서비스 {hour}시간째")
        self.observation_cards["observed"][0].set(value)
        self.observation_cards["observed"][1].set(
            f"관측 {self._clock(current['observed_at'])}    수신 {self._clock(current['received_at'])}"
        )
        self.observation_tree.delete(*self.observation_tree.get_children())

        for item in state["observation_log"]:
            incoming = item["incoming"]
            values = (
                incoming["target_id"],
                "자료 없음" if incoming["value"] is None else f"{incoming['value']:g}",
                incoming["unit"],
                self._clock(incoming["observed_at"]),
                self._clock(incoming["received_at"]),
                REASONS[item["reason"]],
            )
            self.observation_tree.insert(
                "", "end", values=values, tags=("accepted" if item["accepted"] else "rejected",)
            )

    def receive_observation(self):
        result = self._call_view(6, support.receive_next_observation, self.session)
        self._refresh_observations()
        if 6 in self._view_pending:
            self._result_status("")
        elif result is None:
            self._result_status("모든 관측 행을 확인했습니다. 초기화하면 다시 볼 수 있습니다.")
        else:
            self._result_status("관측 자료: " + REASONS[result["reason"]])

    def reset_observations(self):
        support.reset_observations(self.session)
        self._refresh_observations()
        self._result_status("관측 자료를 초기 상태로 되돌렸습니다.")

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".json",
            filetypes=[("도시 상태", "*.json")],
            initialfile="city_interface.json",
        )
        if path:
            try:
                support.save_session(self.session, path)
                self._result_status("도시 상태와 관측 기록을 저장했습니다.")
            except Exception as error:
                self._fail("상태 저장", error)

    def load_file(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("도시 상태", "*.json")])
        if path:
            try:
                self.session = support.load_session(path)
                self.selected = self.session["transport"]["selected_road"]
                self.neighborhood = Neighborhood()
                self.threshold.set("0.5")
                state = support.ensure_state(self.session)
                self.view_target, self.view_hour = state["selected_target"], state["selected_hour"]
                self.refresh()
                self._result_status("도시 상태와 관측 기록을 불러왔습니다.")
            except Exception as error:
                self._fail("상태 불러오기", error)


def launch(smoke=False):
    root = tk.Tk()
    app = InterfaceApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        app.calculate()
        app.advance_view(6)
        app.preview_map()
        app.receive_observation()
        root.update()
        root.destroy()
        print("GUI 확인: 기존 도시 화면과 새 인터페이스 화면 생성 성공")
    else:
        root.mainloop()

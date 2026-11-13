"""병원 대기열의 반복 비교, 용량별 비교와 실험 저장 / 재현을 연결하는 Tkinter GUI."""

from time import perf_counter
import math
import tkinter as tk
from tkinter import filedialog, ttk

from interface_gui import InterfaceApp, BACKGROUND, BLUE, BORDER, INK, MUTED, WHITE
import validation_rules as rules
import validation_support as support

ORANGE = "#CA5010"


def number(value, unit="명"):
    return "자료 없음" if value is None else f"{value:,.2f}{unit}"


class ValidationApp(InterfaceApp):
    def __init__(self, root):
        self.experiment = None
        self.generated_arrivals = None
        self.selected_record = None
        super().__init__(root)
        root.title("가상 도시 / 반복 실험과 검증")
        width = min(1440, max(1180, root.winfo_screenwidth() - 65))
        height = min(940, max(800, root.winfo_screenheight() - 85))
        root.geometry(f"{width}x{height}")
        root.minsize(1180, 800)
        self.notebook.select(self.validation_tab)
        self._switch_controls()
        self._result_status("조건을 정한 뒤 방문 인원을 생성하거나 반복 비교를 실행하세요.")

    def _make_widgets(self):
        super()._make_widgets()
        style = ttk.Style(self.root)
        style.configure("Validation.Treeview", rowheight=22)
        style.configure("Validation.Treeview.Heading", padding=(6, 3))

        self.validation_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.validation_tab, text="반복 실험")
        tab = self.validation_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(4, weight=1)

        settings = ttk.Frame(tab)
        settings.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.inputs = {}
        names = [
            ("first_seed", "시작 시드"),
            ("count", "반복 횟수"),
            ("hours", "실행 시간"),
            ("low", "최소 방문(명)"),
            ("high", "최대 방문(명)"),
            ("baseline_capacity", "기준 용량(명/시간)"),
            ("policy_capacity", "비교 용량(명/시간)"),
        ]

        for column, (key, label) in enumerate(names):
            settings.columnconfigure(column, weight=1, uniform="settings")

            frame = ttk.Frame(settings)
            frame.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
            ttk.Label(frame, text=label, anchor="center").pack(fill="x", pady=(0, 3))
            variable = tk.StringVar(value=str(support.DEFAULT_SETTINGS[key]))
            ttk.Entry(frame, textvariable=variable, justify="center", width=8).pack(fill="x")
            self.inputs[key] = variable
            variable.trace_add("write", self.settings_changed)

        buttons = ttk.Frame(tab)
        buttons.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        for label, command in (
            ("방문 인원 생성", self.generate),
            ("1회 실행", self.single_run),
            ("반복 비교", self.compare),
            ("용량별 비교", self.sensitivity),
        ):
            ttk.Button(
                buttons,
                text=label,
                command=command,
                style="Accent.TButton" if label == "반복 비교" else "TButton",
            ).pack(side="left", padx=(0, 7))

        for label, command in (
            ("불러오기", self.load_experiment),
            ("실험 저장", self.save_experiment),
            ("CSV 내보내기", self.export_experiment),
        ):
            ttk.Button(buttons, text=label, command=command).pack(side="right", padx=(7, 0))

        self.scope = tk.StringVar(
            value="병원 H / 매번 대기 0명에서 시작 / 도로·전력·급수 고정 / 확충 비용 제외 / 현재 도시는 유지"
        )
        ttk.Label(tab, textvariable=self.scope, foreground=MUTED, anchor="w").grid(
            row=2, column=0, sticky="ew", pady=(0, 6)
        )
        self.stat_labels = []
        self.stat_values = []

        cards = ttk.Frame(tab)
        cards.grid(row=3, column=0, sticky="ew", pady=(0, 7))

        for column, label in enumerate(
            ("기준 평균 대기", "비교 평균 대기", "평균 감소 인원", "비교 표본 표준편차")
        ):
            cards.columnconfigure(column, weight=1, uniform="stats")

            frame = tk.Frame(cards, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
            frame.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
            title = tk.StringVar(value=label)
            value = tk.StringVar(value="—")
            tk.Label(
                frame,
                textvariable=title,
                bg=WHITE,
                fg=MUTED,
                font=(self.font_family, 11),
                anchor="center",
            ).pack(fill="x", pady=(5, 1))
            tk.Label(
                frame,
                textvariable=value,
                bg=WHITE,
                fg=BLUE if column != 1 else ORANGE,
                font=(self.font_family, 20, "bold"),
                anchor="center",
            ).pack(fill="x", pady=(0, 5))
            self.stat_labels.append(title)
            self.stat_values.append(value)

        main = ttk.Frame(tab)
        main.grid(row=4, column=0, sticky="nsew")
        main.columnconfigure(0, weight=4)
        main.columnconfigure(1, weight=6)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        self.result_label = tk.StringVar(value="회차별 결과 / 실행 후 표시")
        ttk.Label(
            left, textvariable=self.result_label, font=(self.font_family, 12, "bold"), anchor="w"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 7))

        self.result_tabs = ttk.Notebook(left)
        self.result_tabs.grid(row=1, column=0, sticky="nsew")

        runs = ttk.Frame(self.result_tabs)
        capacity = ttk.Frame(self.result_tabs)
        self.result_tabs.add(runs, text="회차별 결과")
        self.result_tabs.add(capacity, text="용량별 비교")

        self.runs_tree = self._validation_tree(
            runs,
            [
                ("seed", "시드", 68),
                ("baseline", "기준(명)", 88),
                ("policy", "비교(명)", 88),
                ("reduction", "감소(명)", 88),
            ],
        )
        self.runs_tree.bind("<<TreeviewSelect>>", self.select_record)

        self.capacity_tree = self._validation_tree(
            capacity,
            [
                ("capacity", "용량(명/시간)", 116),
                ("mean", "평균(명)", 90),
                ("sd", "표준편차", 90),
                ("max", "최대(명)", 80),
            ],
        )
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1, minsize=167)

        heading = ttk.Frame(right)
        heading.grid(row=0, column=0, sticky="ew")
        self.selected_label = tk.StringVar(value="선택한 회차")
        ttk.Label(
            heading,
            textvariable=self.selected_label,
            font=(self.font_family, 12, "bold"),
            anchor="w",
        ).pack(side="left")
        ttk.Button(heading, text="선택 회차 다시 실행", command=self.replay).pack(side="right")
        self.arrival_label = tk.StringVar(
            value="방문 인원을 생성하면 시간별 입력을 확인할 수 있습니다."
        )
        ttk.Label(
            right, textvariable=self.arrival_label, foreground=MUTED, wraplength=650, anchor="w"
        ).grid(row=1, column=0, sticky="ew", pady=(5, 6))

        history_frame = ttk.Frame(right)
        history_frame.grid(row=2, column=0, sticky="ew")

        self.validation_history_tree = self._validation_tree(
            history_frame,
            [
                ("hour", "시간", 56),
                ("arrivals", "방문", 65),
                ("base_served", "기준 진료", 86),
                ("base_queue", "기준 대기", 86),
                ("policy_served", "비교 진료", 86),
                ("policy_queue", "비교 대기", 86),
            ],
            height=6,
        )
        self.validation_plot = tk.Canvas(
            right, bg=WHITE, highlightthickness=1, highlightbackground=BORDER, height=225
        )
        self.validation_plot.grid(row=3, column=0, sticky="nsew", pady=(7, 0))
        self.validation_plot.bind("<Configure>", lambda event: self.draw_plot())
        self.experiment_info = tk.StringVar(
            value="결과는 각 실행 종료 시점의 대기 인원입니다. 환자의 평균 대기시간과 구분합니다."
        )
        ttk.Label(
            tab, textvariable=self.experiment_info, foreground=MUTED, anchor="w", wraplength=1200
        ).grid(row=5, column=0, sticky="ew", pady=(9, 0))

    def _validation_tree(self, parent, columns, height=8):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            parent,
            columns=[key for key, _, _ in columns],
            show="headings",
            selectmode="browse",
            height=height,
            style="Validation.Treeview",
        )
        tree.grid(row=0, column=0, sticky="nsew")

        for key, label, width in columns:
            tree.heading(key, text=label, anchor="center")
            tree.column(key, width=width, minwidth=45, anchor="center", stretch=True)

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        return tree

    def _switch_controls(self):
        super()._switch_controls()
        if hasattr(self, "validation_tab") and self.notebook.select() == str(self.validation_tab):
            for widget, _ in self._old_controls:
                widget.pack_forget()

    def read_settings(self):
        try:
            settings = {key: int(value.get()) for key, value in self.inputs.items()}
        except ValueError as error:
            raise ValueError("설정에는 정수를 입력하세요.") from error

        return support.checked_settings(settings)

    def settings_changed(self, *args):
        if self.experiment is not None:
            self._result_status(
                "설정이 바뀌었습니다. 표와 그래프에는 직전 실험 결과가 남아 있으며, 실행 버튼을 누르면 새 설정을 적용합니다."
            )

    def _action(self, function):
        try:
            return function()
        except NotImplementedError as error:
            self._result_status(f"{error} / validation_rules.py를 작성하고 앱을 다시 실행하세요.")
        except Exception as error:
            self._result_status(f"확인할 내용: {type(error).__name__}: {error}")

        return None

    def generate(self):
        def execute():
            settings = self.read_settings()
            self.generated_arrivals = rules.make_arrivals(
                settings["first_seed"], settings["hours"], settings["low"], settings["high"]
            )
            self.experiment = None
            self.selected_record = None

            for tree in (self.runs_tree, self.capacity_tree, self.validation_history_tree):
                tree.delete(*tree.get_children())

            for value in self.stat_values:
                value.set("—")

            self.result_label.set("방문 인원 생성 / 아직 실행하지 않음")
            self.selected_label.set(f"시드 {settings['first_seed']} / 생성한 입력")
            self.experiment_info.set(
                "생성한 입력을 확인한 뒤 1회 실행 또는 반복 비교를 선택하세요."
            )
            self.draw_plot()
            shown = " / ".join(str(value) for value in self.generated_arrivals[:12])
            suffix = " / …" if len(self.generated_arrivals) > 12 else ""
            self.arrival_label.set(
                f"시드 {settings['first_seed']} / 시간별 방문: {shown}{suffix}명"
            )
            self._result_status("같은 시드로 다시 생성해 방문 인원 목록이 같은지 확인하세요.")

        self._action(execute)

    def single_run(self):
        def execute():
            settings = self.read_settings()
            settings["count"] = 1
            started = perf_counter()
            arrivals = rules.make_arrivals(
                settings["first_seed"], settings["hours"], settings["low"], settings["high"]
            )
            baseline = rules.run_scenario(arrivals, settings["baseline_capacity"])
            policy = rules.run_scenario(arrivals, settings["policy_capacity"])
            row = {
                "seed": settings["first_seed"],
                "arrivals": arrivals,
                "baseline": baseline,
                "policy": policy,
                "reduction": baseline["final_queue"] - policy["final_queue"],
            }
            self.experiment = support.make_bundle(
                settings, [row], (perf_counter() - started) * 1000
            )
            self.show_records(single=True)
            self._result_status(
                "두 조건에 같은 방문 인원을 넣었습니다. 시간별 진료 인원과 남은 인원을 확인하세요."
            )

        self._action(execute)

    def compare(self):
        def execute():
            bundle = support.run_comparison(self.read_settings())
            self.experiment = bundle
            self.show_records()
            self._result_status(
                f"{len(bundle['records'])}회 비교를 마쳤습니다. 표에서 회차를 고르면 같은 입력의 두 결과를 볼 수 있습니다."
            )

        self._action(execute)

    def sensitivity(self):
        def execute():
            settings = self.read_settings()
            if self.experiment is None or self.experiment["settings"] != settings:
                self.experiment = support.run_comparison(settings)
                self.show_records()

            values, elapsed = support.run_sensitivity(settings)
            self.experiment["sensitivity"] = values
            self.experiment["sensitivity_elapsed_ms"] = elapsed
            self.show_sensitivity()
            self.result_tabs.select(1)
            self._result_status(
                "용량별 비교를 마쳤습니다. 모든 용량에 같은 회차별 방문 인원을 사용했습니다."
            )

        self._action(execute)

    def show_records(self, single=False):
        bundle = self.experiment
        settings = bundle["settings"]
        self.runs_tree.delete(*self.runs_tree.get_children())

        for index, row in enumerate(bundle["records"]):
            self.runs_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row["seed"],
                    row["baseline"]["final_queue"],
                    row["policy"]["final_queue"],
                    row["reduction"],
                ),
            )

        self.result_label.set(f"{len(bundle['records'])}회 / {settings['hours']}시간 후 대기 인원")
        if single:
            row = bundle["records"][0]
            labels = ["기준 대기", "비교 대기", "감소 인원", "비교 표본 표준편차"]
            values = [
                f"{row['baseline']['final_queue']}명",
                f"{row['policy']['final_queue']}명",
                f"{row['reduction']}명",
                "자료 없음",
            ]
        else:
            baseline = rules.summarize(
                [row["baseline"]["final_queue"] for row in bundle["records"]]
            )
            policy = rules.summarize([row["policy"]["final_queue"] for row in bundle["records"]])
            reductions = rules.summarize([row["reduction"] for row in bundle["records"]])
            labels = ["기준 평균 대기", "비교 평균 대기", "평균 감소 인원", "비교 표본 표준편차"]
            values = [
                number(baseline["mean"]),
                number(policy["mean"]),
                number(reductions["mean"]),
                number(policy["stddev"]),
            ]

        for label, value, title, metric in zip(labels, values, self.stat_labels, self.stat_values):
            title.set(label)
            metric.set(value)

        self.experiment_info.set(
            f"계산 시간 {bundle.get('elapsed_ms', 0):.2f}ms / Python {bundle.get('python_version', '?')} / "
            f"코드 {bundle.get('code_version', '?')} / 지표: {settings['hours']}시간 후 대기 인원"
        )
        self.show_sensitivity()
        self.result_tabs.select(0)
        self.runs_tree.selection_set("0")
        self.select_record()

    def show_sensitivity(self):
        self.capacity_tree.delete(*self.capacity_tree.get_children())

        for row in self.experiment.get("sensitivity", []):
            summary = row["summary"]
            self.capacity_tree.insert(
                "",
                "end",
                values=(
                    row["capacity"],
                    f"{summary['mean']:.2f}",
                    "—" if summary["stddev"] is None else f"{summary['stddev']:.2f}",
                    summary["maximum"],
                ),
            )

    def select_record(self, event=None):
        selected = self.runs_tree.selection()
        if not selected or self.experiment is None:
            return

        self.selected_record = int(selected[0])
        row = self.experiment["records"][self.selected_record]
        settings = self.experiment["settings"]
        self.selected_label.set(f"시드 {row['seed']} / 같은 입력 비교")
        shown = " / ".join(str(value) for value in row["arrivals"][:12])
        suffix = " / …" if len(row["arrivals"]) > 12 else ""
        self.arrival_label.set(
            f"시간별 방문: {shown}{suffix}명 / 용량: 기준 {settings['baseline_capacity']}명/시간, 비교 {settings['policy_capacity']}명/시간"
        )
        self.validation_history_tree.delete(*self.validation_history_tree.get_children())

        for baseline, policy in zip(row["baseline"]["history"], row["policy"]["history"]):
            self.validation_history_tree.insert(
                "",
                "end",
                values=(
                    f"{baseline['hour']}시간",
                    baseline["arrivals"],
                    baseline["served"],
                    baseline["queue"],
                    policy["served"],
                    policy["queue"],
                ),
            )

        self.draw_plot()

    def draw_plot(self):
        canvas = self.validation_plot
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 20 or self.experiment is None or self.selected_record is None:
            if width > 20:
                canvas.create_text(
                    width / 2,
                    height / 2,
                    text="실행 후 시간별 대기 인원을 표시합니다.",
                    fill=MUTED,
                    font=(self.font_family, 11),
                )

            return

        row = self.experiment["records"][self.selected_record]
        baseline = [0] + [step["queue"] for step in row["baseline"]["history"]]
        policy = [0] + [step["queue"] for step in row["policy"]["history"]]
        highest = max(5, max(baseline), max(policy))
        magnitude = 10 ** math.floor(math.log10(highest / 5))
        step = next(
            value * magnitude for value in (1, 2, 5, 10) if value * magnitude >= highest / 5
        )
        step = max(1, math.ceil(step))
        tick_count = math.ceil(highest / step)
        maximum = step * tick_count
        top, left, right, bottom = 38, 48, width - 46, height - 33
        span = max(1, len(baseline) - 1)

        for index in range(tick_count + 1):
            value = step * index
            y = bottom - (bottom - top) * index / tick_count
            canvas.create_line(left, y, right, y, fill="#E6EBF0")
            canvas.create_text(
                left - 8, y, text=f"{value:g}", anchor="e", fill=MUTED, font=(self.font_family, 9)
            )

        canvas.create_text(
            left,
            16,
            text="대기 인원(명)",
            anchor="w",
            fill=INK,
            font=(self.font_family, 10, "bold"),
        )

        for index, (label, color, dashed) in enumerate(
            (("기준", BLUE, False), ("비교", ORANGE, True))
        ):
            x = right - 140 + index * 80
            canvas.create_line(
                x, 16, x + 22, 16, fill=color, width=3, dash=(6, 3) if dashed else ()
            )
            canvas.create_text(
                x + 28, 16, text=label, anchor="w", fill=INK, font=(self.font_family, 10)
            )

        positions = sorted(set(round(span * i / min(span, 6)) for i in range(min(span, 6) + 1)))

        for hour in positions:
            x = left + (right - left) * hour / span
            canvas.create_text(
                x, bottom + 18, text=f"{hour}시간", fill=MUTED, font=(self.font_family, 9)
            )

        for values, color, dashed in ((baseline, BLUE, False), (policy, ORANGE, True)):
            points = []
            for index, value in enumerate(values):
                points.extend(
                    (
                        left + (right - left) * index / span,
                        bottom - (bottom - top) * value / maximum,
                    )
                )
            canvas.create_line(*points, fill=color, width=3, dash=(6, 3) if dashed else ())
            if len(values) <= 13:
                for index in range(0, len(points), 2):
                    x, y = points[index : index + 2]
                    if dashed:
                        canvas.create_rectangle(
                            x - 3, y - 3, x + 3, y + 3, outline=color, fill=WHITE, width=2
                        )
                    else:
                        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, outline=color, fill=color)

            y = points[-1] + (-9 if values is baseline else 10)
            canvas.create_text(
                right + 7,
                max(top, min(bottom, y)),
                text=str(values[-1]),
                anchor="w",
                fill=color,
                font=(self.font_family, 10, "bold"),
            )

    def replay(self):
        def execute():
            if self.experiment is None or self.selected_record is None:
                raise ValueError("먼저 회차별 결과를 선택하세요.")

            result = support.replay_record(self.experiment, self.selected_record)
            if not result["matches"]:
                raise ValueError(
                    "현재 코드의 결과가 저장된 기록과 다릅니다. 코드 버전과 계산 규칙을 확인하세요."
                )

            self._result_status(
                "저장한 방문 인원으로 다시 계산했습니다. 시간별 기록과 최종 대기가 모두 일치합니다."
            )

        self._action(execute)

    def save_experiment(self):
        if self.experiment is None:
            self._result_status("먼저 실험을 실행하세요.")
            return

        path = filedialog.asksaveasfilename(
            title="실험 저장",
            defaultextension=".json",
            initialfile="hospital_experiment.json",
            filetypes=[("실험 기록", "*.json")],
        )
        if path:

            def execute():
                support.save_experiment(self.experiment, path)
                self._result_status(f"실험 파일 저장 위치: {path}")

            self._action(execute)

    def load_experiment(self):
        path = filedialog.askopenfilename(
            title="실험 불러오기", filetypes=[("실험 기록", "*.json")]
        )
        if not path:
            return

        def execute():
            bundle = support.load_experiment(path)
            self.experiment = bundle

            for key, value in bundle["settings"].items():
                self.inputs[key].set(str(value))

            self.show_records(single=len(bundle["records"]) == 1)
            same_code = bundle.get("code_sha256") == support.ACTIVE_CODE_HASHES
            self._result_status(
                "실험 기록을 불러왔습니다. 선택 회차를 다시 실행해 결과를 확인하세요."
                + ("" if same_code else " 저장 당시와 코드가 다릅니다.")
            )

        self._action(execute)

    def export_experiment(self):
        if self.experiment is None:
            self._result_status("먼저 실험을 실행하세요.")
            return

        path = filedialog.asksaveasfilename(
            title="시간별 기록 내보내기",
            defaultextension=".csv",
            initialfile="hospital_experiment.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:

            def execute():
                support.export_csv(self.experiment, path)
                self._result_status(f"CSV 저장 위치: {path}")

            self._action(execute)


def launch(smoke=False):
    root = tk.Tk()
    app = ValidationApp(root)
    if smoke:
        root.update()
        app.generate()
        app.single_run()
        app.compare()
        app.sensitivity()
        app.replay()
        app.notebook.select(app.view_tab)
        app.advance_view(6)
        app.notebook.select(app.validation_tab)
        root.update()
        root.destroy()
        print("GUI 확인: 기존 도시와 반복 실험 화면 생성 성공")
    else:
        root.mainloop()

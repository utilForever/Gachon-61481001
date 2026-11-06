import tkinter as tk
from tkinter import filedialog, ttk

from neighborhood import Neighborhood
from service_gui import ServiceApp
import economy_support as support

POLICY_COLORS = {"normal": "#616161", "hospital": "#CA5010", "water": "#0F6CBD", "both": "#008272"}


class EconomyApp(ServiceApp):
    def __init__(self, root):
        super().__init__(root)
        root.title("가상 도시 / 경제와 재정")
        root.geometry("1440x940")
        root.minsize(1280, 880)
        root.bind("<Configure>", self._resize_comparison, add="+")
        self.notebook.select(self.economy_tab)
        self.refresh()
        self._result_status("운영안을 선택한 뒤 월별 재정과 서비스 성과를 비교하세요.")

    def _resize_comparison(self, event):
        if event.widget is not self.root or not hasattr(self, "comparison_plot"):
            return
        height = max(150, min(220, self.root.winfo_height() - 760))
        if int(self.comparison_plot.cget("height")) != height:
            self.comparison_plot.configure(height=height)
            self._draw_comparison()

    def _make_widgets(self):
        super()._make_widgets()

        self.economy_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.economy_tab, text="경제 / 재정")

        controls = ttk.Frame(self.economy_tab)
        controls.pack(fill="x", pady=(0, 6))
        self.policy_var = tk.StringVar(value="기준")
        ttk.Label(controls, text="운영안 ").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.policy_var,
            values=tuple(support.POLICIES.values()),
            state="readonly",
            width=12,
        ).pack(side="left")

        self.income_tax_var = tk.StringVar(value="10")
        self.profit_tax_var = tk.StringVar(value="10")
        for label, variable in (
            ("가구 세율", self.income_tax_var),
            ("기업 세율", self.profit_tax_var),
        ):
            ttk.Label(controls, text=label + " ").pack(side="left", padx=(14, 0))
            ttk.Entry(controls, textvariable=variable, width=5, justify="right").pack(side="left")
            ttk.Label(controls, text="%").pack(side="left", padx=(3, 0))
        ttk.Button(controls, text="적용 / 재정 초기화", command=self.reset_finance_run).pack(
            side="left", padx=12
        )
        ttk.Button(controls, text="월별 CSV", command=self.export_finance).pack(side="right")
        ttk.Button(controls, text="3개월 진행", command=lambda: self.advance_finance(3)).pack(
            side="right", padx=4
        )
        ttk.Button(controls, text="1개월 진행", command=self.advance_finance).pack(side="right")

        self.finance_clock = tk.StringVar()
        ttk.Label(self.economy_tab, textvariable=self.finance_clock).pack(anchor="w", pady=(0, 8))

        self.economy_notebook = ttk.Notebook(self.economy_tab)
        self.economy_notebook.pack(fill="both", expand=True)
        self.finance_tab = ttk.Frame(self.economy_notebook, padding=10)
        self.comparison_tab = ttk.Frame(self.economy_notebook, padding=10)
        self.behavior_tab = ttk.Frame(self.economy_notebook, padding=10)
        for tab, label in (
            (self.finance_tab, "월별 재정"),
            (self.comparison_tab, "정책 비교"),
            (self.behavior_tab, "세금과 행동"),
        ):
            self.economy_notebook.add(tab, text=label)

        self._make_finance()
        self._make_comparison()
        self._make_behavior()

    def _make_finance(self):
        self.finance_summary = tk.StringVar()
        ttk.Label(
            self.finance_tab,
            textvariable=self.finance_summary,
            style="Stats.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(0, 4))
        self.finance_inputs = tk.StringVar()
        ttk.Label(self.finance_tab, textvariable=self.finance_inputs).pack(anchor="w", pady=(0, 6))

        self.debt_plot = tk.Canvas(
            self.finance_tab, height=210, background="white", highlightthickness=0
        )
        self.debt_plot.pack(fill="x", pady=(0, 8))
        self.debt_plot.bind("<Configure>", lambda event: self._draw_finance())

        holder = ttk.Frame(self.finance_tab)
        holder.pack(fill="both", expand=True)
        columns = (
            ("month", "월", 50),
            ("revenue", "세금 수입", 100),
            ("maintenance", "유지비", 90),
            ("services", "운영비", 90),
            ("interest", "이자", 90),
            ("construction", "건설비", 90),
            ("balance", "월 수지", 100),
            ("borrowing", "신규 차입", 100),
            ("repayment", "원금 상환", 100),
            ("cash", "월말 현금", 100),
            ("debt", "월말 부채", 105),
        )
        self.finance_tree = self._tree(holder, columns, 8)
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=self.finance_tree.yview)
        self.finance_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.finance_tree.pack(side="left", fill="both", expand=True)

        ttk.Label(
            self.finance_tab,
            text="금액 단위: 예산 단위 / 이자는 월초 부채에 적용하며, 건설비는 첫 달에 한 번 반영합니다.",
        ).pack(anchor="w", pady=(7, 0))

    def _make_comparison(self):
        row = ttk.Frame(self.comparison_tab)
        row.pack(fill="x", pady=(0, 7))
        ttk.Label(row, text="같은 초기 도시에서 운영안 비교", style="Stats.TLabel").pack(
            side="left"
        )
        ttk.Button(row, text="네 가지 운영안 비교", command=self.run_policy_comparison).pack(
            side="right"
        )

        self.comparison_description = tk.StringVar(
            value="서비스 24시간과 재정 3개월을 각각 실행합니다. 현재 진행 중인 도시의 시계는 바뀌지 않습니다."
        )
        ttk.Label(self.comparison_tab, textvariable=self.comparison_description).pack(
            anchor="w", pady=(0, 8)
        )

        columns = (
            ("name", "운영안", 160),
            ("queue6", "6시간 대기(명)", 135),
            ("queue24", "24시간 대기(명)", 145),
            ("coverage", "권역 인구(%)", 130),
            ("cash", "3개월 말 현금", 145),
            ("debt", "3개월 말 부채", 150),
        )
        self.comparison_tree = self._tree(self.comparison_tab, columns, 4)
        self.comparison_tree.pack(fill="x")
        for key, color in POLICY_COLORS.items():
            self.comparison_tree.tag_configure(key, foreground=color)

        self.comparison_plot = tk.Canvas(
            self.comparison_tab, height=180, background="white", highlightthickness=0
        )
        self.comparison_plot.pack(fill="x", pady=8)
        self.comparison_plot.bind("<Configure>", lambda event: self._draw_comparison())

        ttk.Label(self.comparison_tab, text="기준 대비 변화량", style="Stats.TLabel").pack(
            anchor="w", pady=(0, 5)
        )
        delta_columns = (
            ("name", "운영안", 160),
            ("queue6", "6시간 대기 차이(명)", 190),
            ("queue24", "24시간 대기 차이(명)", 190),
            ("debt", "부채 차이", 160),
            ("coverage", "권역 비율 차이(%p)", 190),
        )
        self.delta_tree = self._tree(self.comparison_tab, delta_columns, 3)
        self.delta_tree.pack(fill="x")

    def _make_behavior(self):
        ttk.Label(self.behavior_tab, text="가구 소득과 소비", style="Stats.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        self.income_tree = self._tree(
            self.behavior_tab, (("item", "항목", 300), ("amount", "금액 / 예산 단위", 240)), 6
        )
        self.income_tree.pack(fill="x")
        ttk.Label(
            self.behavior_tab,
            text="취업자 200명 × 월 임금 5 / 세후 소득의 5/9는 지역 소비, 2/9는 도시 밖 지출, 2/9는 저축으로 둡니다.",
            wraplength=1190,
            justify="left",
        ).pack(anchor="w", pady=(8, 18))

        ttk.Label(self.behavior_tab, text="기업 F1의 이전 판단", style="Stats.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        self.firm_economy_tree = self._tree(
            self.behavior_tab,
            (
                ("before", "이전 전 월 이익", 190),
                ("after", "이전 후 월 이익", 190),
                ("move", "이전비", 170),
                ("tax", "기업 세율", 170),
                ("gain", "6개월 세후 순편익", 250),
            ),
            1,
        )
        self.firm_economy_tree.pack(fill="x")

        self.firm_judgment = tk.StringVar()
        ttk.Label(self.behavior_tab, textvariable=self.firm_judgment, style="Stats.TLabel").pack(
            anchor="w", pady=(10, 6)
        )
        ttk.Label(
            self.behavior_tab,
            text="F1의 금액 단위는 만원입니다. 시민 3명의 행위자 예제를 별도로 관찰하며, 위의 집계 재정에 합산하지 않습니다.\n소비·이전 예제는 비교를 위한 계산입니다. 고용 증가나 기업 이전이 자동으로 실행되지는 않습니다.",
            wraplength=1190,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

    def refresh(self):
        super().refresh()
        if hasattr(self, "economy_tab"):
            self._refresh_economy()

    def _result_status(self, message):
        pending = support.pending_tasks()
        suffix = " / 미구현: TODO " + ", ".join(map(str, pending)) if pending else ""
        self.status.set(message + suffix)

    def _refresh_economy(self):
        state = support.ensure_state(self.session)
        self.policy_var.set(support.POLICIES[state["policy"]])
        self.income_tax_var.set(f"{state['income_tax_rate'] * 100:g}")
        self.profit_tax_var.set(f"{state['profit_tax_rate'] * 100:g}")
        self.finance_clock.set(
            f"재정 {state['month']}개월 / 공공서비스 {self.session['services']['hour']}시간 / 행위자 {self.session['agents']['month']}개월 / 각 시계는 따로 진행합니다."
        )
        self.finance_summary.set(
            f"{support.POLICIES[state['policy']]} / 현금 {state['cash']:.2f} / 부채 {state['debt']:.2f}"
        )

        try:
            row = support.preview(self.session)
            self.finance_inputs.set(
                f"도로 {row['road_cells']}칸 / 월 세금 수입 {row['revenue']:.2f} / 유지비 {row['maintenance']:.2f} / 운영비 {row['services']:.2f} / 다음 결산 건설비 {row['construction']:.2f}"
            )
        except NotImplementedError:
            self.finance_inputs.set("세금 수입 / 비용: 미구현")
        except Exception as error:
            self.finance_inputs.set(f"계산 결과 확인 필요: {error}")

        self.finance_tree.delete(*self.finance_tree.get_children())
        for row in state["history"]:
            keys = (
                "revenue",
                "maintenance",
                "services",
                "interest",
                "construction",
                "balance",
                "borrowing",
                "repayment",
                "cash",
                "debt",
            )
            self.finance_tree.insert(
                "", "end", values=(row["month"], *(f"{row[key]:.2f}" for key in keys))
            )
        children = self.finance_tree.get_children()
        if children:
            self.finance_tree.see(children[-1])

        self._draw_finance()
        self._refresh_comparison()
        self._refresh_behavior()

    def _refresh_comparison(self):
        report = support.ensure_state(self.session)["comparison"]
        for tree in (self.comparison_tree, self.delta_tree):
            tree.delete(*tree.get_children())

        if report:
            self.comparison_description.set(
                f"마지막 비교 조건: 도로 {report['road_cells']}칸 / 가구 세율 {report['income_tax_rate']:.0%} / 기업 세율 {report['profit_tax_rate']:.0%} / 서비스 {report['hours']}시간 / 재정 {report['months']}개월"
            )
            for row in report["results"]:
                self.comparison_tree.insert(
                    "",
                    "end",
                    values=(
                        row["name"],
                        row["queue6"],
                        row["queue24"],
                        f"{row['coverage'] * 100:.0f}",
                        f"{row['cash']:.2f}",
                        f"{row['debt']:.2f}",
                    ),
                    tags=(row["policy"],),
                )
            for row in report["deltas"]:
                if row["policy"] == "normal":
                    continue
                self.delta_tree.insert(
                    "",
                    "end",
                    values=(
                        row["name"],
                        f"{row['queue6']:+g}",
                        f"{row['queue24']:+g}",
                        f"{row['debt']:+.2f}",
                        f"{row['coverage'] * 100:+.0f}",
                    ),
                )
        else:
            self.comparison_description.set(
                "서비스 24시간과 재정 3개월을 각각 실행합니다. 현재 진행 중인 도시의 시계는 바뀌지 않습니다."
            )

        self._draw_comparison()

    def _refresh_behavior(self):
        self.income_tree.delete(*self.income_tree.get_children())
        self.firm_economy_tree.delete(*self.firm_economy_tree.get_children())

        try:
            row = support.behavior_examples(self.session)
            for title, key in (
                ("과세 전 소득", "income"),
                ("가구 세금", "tax"),
                ("세후 소득", "disposable"),
                ("지역 소비", "local_consumption"),
                ("도시 밖 지출", "outside_spending"),
                ("저축", "saving"),
            ):
                self.income_tree.insert("", "end", values=(title, f"{row[key]:.2f}"))
            self.firm_economy_tree.insert(
                "",
                "end",
                values=(
                    f"{row['firm_before']:g}",
                    f"{row['firm_after']:g}",
                    f"{row['move_cost']:g}",
                    f"{row['profit_tax_rate']:.0%}",
                    f"{row['gain6']:.2f}",
                ),
            )
            judgment = "이전할 유인이 있음" if row["gain6"] > 0 else "현재 위치 유지"
            self.firm_judgment.set(judgment)
        except NotImplementedError:
            self.firm_judgment.set("세금과 행동: 미구현")
        except Exception as error:
            self.firm_judgment.set(f"계산 결과 확인 필요: {error}")

    def _draw_finance(self):
        if not hasattr(self, "debt_plot"):
            return
        state = support.ensure_state(self.session)
        series = {state["policy"]: [{"month": 0, "debt": 200}] + state["history"]}
        self._plot_debt(self.debt_plot, series)

    def _draw_comparison(self):
        if not hasattr(self, "comparison_plot"):
            return

        report = support.ensure_state(self.session)["comparison"]
        if report:
            self._plot_debt(self.comparison_plot, report["series"])
        else:
            self.comparison_plot.delete("all")
            self.comparison_plot.create_text(
                20,
                30,
                text="‘네 가지 운영안 비교’를 누르면 월별 부채를 표시합니다.",
                anchor="w",
                fill="#616161",
                font=(self.font_family, 11),
            )

    def _plot_debt(self, canvas, series):
        canvas.delete("all")
        width = max(1080, canvas.winfo_width())
        height = int(canvas.cget("height"))
        left, top, right, bottom = 60, 43, width - 110, height - 30
        canvas.create_text(
            12,
            15,
            text="월말 부채 / 예산 단위",
            anchor="w",
            font=(self.font_family, 11, "bold"),
            fill="#242424",
        )

        maximum = max(1, *(row["debt"] for rows in series.values() for row in rows))
        maximum = max(20, ((int(maximum) // 20) + 1) * 20)
        end = max(1, *(row["month"] for rows in series.values() for row in rows))

        for fraction in (0, 0.5, 1):
            y = bottom - (bottom - top) * fraction
            canvas.create_line(left, y, right, y, fill="#E5E5E5")
            canvas.create_text(
                left - 9,
                y,
                text=f"{maximum * fraction:g}",
                anchor="e",
                fill="#616161",
                font=(self.font_family, 10),
            )

        for month in sorted({row["month"] for rows in series.values() for row in rows}):
            x = left + (right - left) * month / end
            canvas.create_text(
                x, bottom + 15, text=f"{month}개월", fill="#616161", font=(self.font_family, 10)
            )

        for index, (policy, rows) in enumerate(series.items()):
            color = POLICY_COLORS[policy]
            legend_x = 360 + index * 150
            canvas.create_line(legend_x, 15, legend_x + 24, 15, fill=color, width=3)
            canvas.create_text(
                legend_x + 30,
                15,
                text=support.POLICIES[policy],
                anchor="w",
                fill=color,
                font=(self.font_family, 10),
            )
            points = [
                (
                    left + (right - left) * row["month"] / end,
                    bottom - (bottom - top) * row["debt"] / maximum,
                )
                for row in rows
            ]
            if len(points) > 1:
                canvas.create_line(
                    *[value for point in points for value in point], fill=color, width=3
                )
            for x, y in points:
                if policy == "hospital":
                    canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)
                elif policy == "water":
                    canvas.create_polygon(x, y - 4, x + 4, y, x, y + 4, x - 4, y, fill=color)
                elif policy == "both":
                    canvas.create_polygon(x, y - 4, x + 4, y + 4, x - 4, y + 4, fill=color)
                else:
                    canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)
            if len(series) == 1:
                x, y = points[-1]
                canvas.create_text(
                    x + 8,
                    y,
                    text=f"{rows[-1]['debt']:.2f}",
                    anchor="w",
                    fill=color,
                    font=(self.font_family, 10, "bold"),
                )

    def reset_finance_run(self):
        try:
            policy = next(
                key for key, value in support.POLICIES.items() if value == self.policy_var.get()
            )
            income_tax = float(self.income_tax_var.get()) / 100
            profit_tax = float(self.profit_tax_var.get()) / 100
            if not (0 <= income_tax <= 1 and 0 <= profit_tax <= 1):
                raise ValueError("세율은 0~100% 사이로 입력하세요.")
            support.reset_finance(self.session, policy, income_tax, profit_tax)
            self.refresh()
            self._result_status("선택한 조건으로 재정만 0개월로 초기화했습니다.")
        except Exception as error:
            self._fail("재정 초기화", error)

    def advance_finance(self, months=1):
        try:
            for _ in range(months):
                support.advance_month(self.session)
            self.refresh()
            self._result_status(
                f"재정을 {months}개월 진행했습니다. 서비스와 행위자 시계는 그대로입니다."
            )
        except Exception as error:
            self.refresh()
            self._fail("재정 진행", error)

    def run_policy_comparison(self):
        try:
            report = support.run_comparison(self.session)
            support.ensure_state(self.session)["comparison"] = report
            self._refresh_comparison()
            self.economy_notebook.select(self.comparison_tab)
            self._result_status(
                "같은 현재 도로와 세율에서 네 운영안을 비교했습니다. 각 대안은 초기 상태에서 시작합니다."
            )
        except Exception as error:
            self._fail("정책 비교", error)

    def use_preset(self, name):
        super().use_preset(name)
        support.reset_finance(self.session)
        self.refresh()

    def _reset_run(self, message):
        super()._reset_run(message)
        support.ensure_state(self.session)["comparison"] = None
        if hasattr(self, "economy_tab"):
            self._refresh_economy()

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".json",
            filetypes=[("도시 상태", "*.json")],
            initialfile="city_economy.json",
        )
        if path:
            try:
                support.save_session(self.session, path)
                self._result_status("도시 / 행위자 / 공공서비스 / 재정 상태를 저장했습니다.")
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
                self._result_status("도시와 각 시계의 상태를 복원했습니다.")
            except Exception as error:
                self._fail("불러오기", error)

    def export_finance(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="finance_months.csv",
        )
        if path:
            try:
                support.export_history(self.session, path)
                self._result_status("월별 재정 기록을 저장했습니다.")
            except Exception as error:
                self._fail("월별 CSV", error)


def launch(smoke=False):
    root = tk.Tk()
    app = EconomyApp(root)
    if smoke:
        root.update_idletasks()
        root.update()
        app.calculate()
        root.destroy()
        print("GUI 확인: 도시 / 행위자 / 공공서비스 / 재정 화면 생성 성공")
    else:
        root.mainloop()

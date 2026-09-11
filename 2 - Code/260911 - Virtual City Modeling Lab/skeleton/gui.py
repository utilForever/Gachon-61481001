"""도시 지도와 상태를 표시하는 Tkinter GUI."""

from copy import deepcopy
import tkinter as tk
from tkinter import filedialog, font as tkfont, ttk
import traceback

import city_data
import model


class CityApp:
    CELL = 90
    LEFT = 38
    TOP = 30

    def __init__(self, root):
        self.root = root
        root.title("가상 도시")
        width = min(1100, max(980, root.winfo_screenwidth() - 80))
        height = min(780, max(700, root.winfo_screenheight() - 80))
        root.geometry(f"{width}x{height}")
        root.minsize(980, 700)
        self._set_fonts()

        self.city = city_data.make_city()
        self.baseline = deepcopy(self.city)
        self.has_stepped = False
        self.selected = (1, 1)
        self.mode = tk.StringVar(value="inspect")
        self.power = tk.BooleanVar(value=True)
        self.summary = tk.StringVar()
        self.status = tk.StringVar(value="도구를 선택하고 지도를 클릭하세요.")
        self.history = []

        self._make_widgets()
        self.refresh(record=True)

    def _set_fonts(self):
        families = set(tkfont.families(self.root))
        family = next(
            (
                name
                for name in (
                    "Pretendard",
                    "맑은 고딕",
                    "Malgun Gothic",
                    "Apple SD Gothic Neo",
                    "Noto Sans CJK KR",
                )
                if name in families
            ),
            "TkDefaultFont",
        )
        self.font_family = family
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            options = {"size": 11}
            if family != "TkDefaultFont":
                options["family"] = family
            tkfont.nametofont(name).configure(**options)

        style = ttk.Style(self.root)
        style.configure("TButton", padding=(9, 5))
        style.configure("Treeview", rowheight=25)
        style.configure("Title.TLabel", font=(family, 18, "bold"))
        style.configure("Stats.TLabel", font=(family, 14, "bold"))

    def _make_widgets(self):
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="가상 도시", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        presets = ttk.Frame(outer)
        presets.pack(fill="x", pady=(0, 5))
        for text, name in (
            ("기본 도시", "default"),
            ("공원 없는 도시", "no_park"),
            ("빈 지도", "empty"),
        ):
            ttk.Button(presets, text=text, command=lambda value=name: self.use_preset(value)).pack(
                side="left", padx=(0, 6)
            )

        ttk.Button(presets, text="불러오기", command=self.load_file).pack(side="right", padx=(6, 0))
        ttk.Button(presets, text="저장", command=self.save_file).pack(side="right")

        tools = ttk.Frame(outer)
        tools.pack(fill="x", pady=(0, 5))
        ttk.Label(tools, text="지도 도구  ").pack(side="left")
        self.edit_radios = []
        for text, value in (
            ("조회", "inspect"),
            ("도로", "road"),
            ("주택", "house"),
            ("공원", "park"),
            ("삭제", "erase"),
        ):
            radio = ttk.Radiobutton(tools, text=text, value=value, variable=self.mode)
            radio.pack(side="left", padx=(0, 13))
            if value != "inspect":
                self.edit_radios.append(radio)

        self.power_check = ttk.Checkbutton(
            tools, text="외부 전력", variable=self.power, command=self.change_power
        )
        self.power_check.pack(side="right")

        stats = ttk.Frame(outer)
        stats.pack(fill="x", pady=(0, 6))
        ttk.Label(stats, textvariable=self.summary, style="Stats.TLabel").pack(side="left")
        ttk.Button(stats, text="1일 진행", command=self.advance_day).pack(side="right", padx=(7, 0))
        ttk.Button(stats, text="실험 시작으로", command=self.reset_experiment).pack(side="right")

        # 상태 메시지 공간을 먼저 확보한다.
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x")
        ttk.Separator(footer).pack(fill="x", pady=(5, 4))
        ttk.Label(footer, textvariable=self.status, wraplength=930, foreground="#15517a").pack(
            anchor="w", pady=(4, 0)
        )

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)

        map_side = ttk.Frame(body)
        map_side.pack(side="left", anchor="n")
        self.canvas = tk.Canvas(
            map_side,
            width=500,
            height=405,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8bec4",
        )
        self.canvas.pack(anchor="nw")
        self.canvas.bind("<Button-1>", self.click_map)
        ttk.Label(
            map_side,
            text="연두: 공원    /    노랑: 주택    /    회색: 도로    /    파랑: 물",
        ).pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(body, padding=(16, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)

        inspector_frame = ttk.LabelFrame(right, text="선택한 셀", padding=10)
        inspector_frame.pack(fill="x")
        self.inspector = tk.StringVar()
        ttk.Label(
            inspector_frame, textvariable=self.inspector, justify="left", wraplength=400
        ).pack(anchor="w")

        history_frame = ttk.LabelFrame(right, text="실행 기록", padding=8)
        history_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(
            history_frame,
            columns=("day", "population", "budget"),
            show="headings",
            height=6,
        )
        for column, title, width in (
            ("day", "일", 55),
            ("population", "전체 인구", 95),
            ("budget", "예산(코인)", 110),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=50, anchor="center")

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

    def _fail(self, action, error):
        if isinstance(error, NotImplementedError):
            detail = str(error) or "해당 기능이 아직 구현되지 않았습니다."
            self.status.set(f"{action}: 아직 미구현입니다. {detail}")
        else:
            self.status.set(f"{action} 실패: {error}")
            traceback.print_exc()

    def _population_text(self):
        try:
            return str(model.total_population(deepcopy(self.city)))
        except NotImplementedError:
            return "미구현"
        except Exception as error:
            self._fail("전체 인구 계산", error)
            return "오류"

    def _inspector_text(self):
        x, y = self.selected
        cell = self.city["grid"][y][x]
        terrain = "육지" if cell["terrain"] == "land" else "물"
        lines = [
            f"좌표 ({x}, {y})",
            f"지형: {terrain}    도로: {'있음' if cell['road'] else '없음'}",
        ]

        building_id = cell["building_id"]
        if building_id is None:
            lines.append("건물: 없음")
        else:
            building = self.city["buildings"][building_id]
            label = "주택" if building["kind"] == "house" else "공원"
            status = {
                "operating": "운영 중",
                "construction": "건설 중",
                "closed": "운영 중지",
            }[building["status"]]
            lines.extend([f"건물 ID: {building_id}  ({label})", f"상태: {status}"])

            if building["kind"] == "house":
                lines.append(f"인구 / 수용량: {building['population']} / {building['capacity']}")

                try:
                    # 조회 함수에는 복사본을 전달해 현재 상태를 보호한다.
                    snapshot = deepcopy(self.city)
                    eligible = model.eligible(snapshot, snapshot["buildings"][building_id])
                    lines.append(f"입주 조건: {'충족' if eligible else '미충족'}")
                except NotImplementedError:
                    lines.append("입주 조건: 미구현")
                except Exception as error:
                    lines.append("입주 조건: 계산 오류")
                    self._fail("입주 조건 조회", error)

                try:
                    snapshot = deepcopy(self.city)
                    count = model.arrivals(snapshot, snapshot["buildings"][building_id])
                    lines.append(f"다음 하루 입주: {count}명")
                except NotImplementedError:
                    lines.append("다음 하루 입주: 미구현")
                except Exception as error:
                    lines.append("다음 하루 입주: 계산 오류")
                    self._fail("입주량 조회", error)

        return "\n".join(lines)

    def refresh(self, record=False):
        population = self._population_text()
        self.summary.set(
            f"{self.city['day']}일    인구 {population}    예산 {self.city['budget']} 코인"
        )
        self.power.set(self.city["external_power"])

        editing = self.city["day"] == 0
        for widget in self.edit_radios + [self.power_check]:
            widget.configure(state="normal" if editing else "disabled")
        if not editing:
            self.mode.set("inspect")

        self.inspector.set(self._inspector_text())
        self._draw_map()

        row = (self.city["day"], population, self.city["budget"])
        if record:
            if self.history and self.history[-1][0] == row[0]:
                self.history[-1] = row
            else:
                self.history.append(row)

        self.tree.delete(*self.tree.get_children())
        for values in self.history:
            item = self.tree.insert("", "end", values=values)
        if self.history:
            self.tree.see(item)

    def _draw_map(self):
        c = self.canvas
        c.delete("all")
        f = self.font_family

        for x in range(5):
            c.create_text(self.LEFT + (x + 0.5) * self.CELL, 17, text=str(x), font=(f, 13))

        for y in range(4):
            c.create_text(20, self.TOP + (y + 0.5) * self.CELL, text=str(y), font=(f, 13))

            for x in range(5):
                cell = self.city["grid"][y][x]
                left, top = self.LEFT + x * self.CELL, self.TOP + y * self.CELL
                right, bottom = left + self.CELL, top + self.CELL
                fill = "#d7ecfa" if cell["terrain"] == "water" else "#f6f3e9"
                c.create_rectangle(left, top, right, bottom, fill=fill, outline="#b8bec4")

                if cell["terrain"] == "water":
                    c.create_text(
                        (left + right) / 2,
                        (top + bottom) / 2,
                        text="물",
                        fill="#326984",
                        font=(f, 15),
                    )

                if cell["road"]:
                    c.create_rectangle(
                        left + 1,
                        top + 22,
                        right - 1,
                        bottom - 22,
                        fill="#818993",
                        outline="",
                    )
                    c.create_line(
                        left + 5,
                        (top + bottom) / 2,
                        right - 5,
                        (top + bottom) / 2,
                        fill="white",
                        width=2,
                        dash=(9, 7),
                    )

                building_id = cell["building_id"]
                if building_id is not None:
                    building = self.city["buildings"][building_id]
                    house = building["kind"] == "house"
                    fill = "#f9e6a7" if house else "#cee7c7"
                    if building["status"] != "operating":
                        fill = "#dedede"
                    c.create_rectangle(
                        left + 10,
                        top + 10,
                        right - 10,
                        bottom - 10,
                        fill=fill,
                        outline="#535b62",
                        width=2,
                    )
                    c.create_text(
                        (left + right) / 2,
                        top + 29,
                        text=building_id,
                        font=(f, 15, "bold"),
                    )
                    label = (
                        f"{building['population']} / {building['capacity']}" if house else "공원"
                    )
                    c.create_text((left + right) / 2, top + 60, text=label, font=(f, 12))

                if self.selected == (x, y):
                    c.create_rectangle(
                        left + 3,
                        top + 3,
                        right - 3,
                        bottom - 3,
                        outline="#1d6eae",
                        width=3,
                    )

    def use_preset(self, name):
        try:
            candidate = (
                city_data.make_empty_city()
                if name == "empty"
                else city_data.make_city(with_park=name != "no_park")
            )
            city_data.validate_city(candidate)
        except Exception as error:
            self._fail("지도 선택", error)
            return

        self._start_from(candidate)
        self.status.set("새 도시를 불러왔습니다.")

    def _start_from(self, city):
        self.city = city
        self.baseline = deepcopy(city)
        self.has_stepped = False
        self.history = []
        self.mode.set("inspect")
        self.refresh(record=True)

    def click_map(self, event):
        x = (event.x - self.LEFT) // self.CELL
        y = (event.y - self.TOP) // self.CELL
        if not (0 <= x < 5 and 0 <= y < 4):
            return

        self.selected = (x, y)
        mode = self.mode.get()
        if mode == "inspect":
            self.refresh()
            return

        if self.city["day"] != 0:
            self.status.set("지도는 0일에만 편집할 수 있습니다.")
            self.refresh()
            return

        candidate = deepcopy(self.city)
        try:
            if mode == "road":
                city_data.edit_road(candidate, x, y)
            elif mode == "erase":
                city_data.erase_at(candidate, x, y)
            else:
                model.place_building(candidate, x, y, mode)
            city_data.validate_city(candidate)
        except Exception as error:
            self._fail("지도 편집", error)
            self.refresh()
            return

        self.city = candidate
        self.status.set(f"({x}, {y}) 셀을 변경했습니다.")
        self.refresh(record=True)

    def change_power(self):
        if self.city["day"] != 0:
            self.power.set(self.city["external_power"])
            self.status.set("외부 전력은 0일에만 변경할 수 있습니다.")
            return

        candidate = deepcopy(self.city)
        candidate["external_power"] = bool(self.power.get())
        try:
            city_data.validate_city(candidate)
        except Exception as error:
            self._fail("전력 변경", error)
            self.power.set(self.city["external_power"])
            return

        self.city = candidate
        self.status.set("외부 전력을 변경했습니다.")
        self.refresh(record=True)

    def advance_day(self):
        before = deepcopy(self.city)
        try:
            # 검증을 통과한 다음 상태만 실제 도시에 반영한다.
            candidate = model.step(deepcopy(before))
            city_data.validate_city(candidate)
            if candidate["day"] != before["day"] + 1:
                raise ValueError("step()은 day를 정확히 1 증가시킨 새 도시를 반환해야 합니다.")
        except Exception as error:
            self._fail("1일 진행", error)
            return

        if not self.has_stepped:
            self.baseline = before
            self.has_stepped = True

        self.city = candidate
        self.status.set(f"{self.city['day']}일로 진행했습니다.")
        self.refresh(record=True)

    def reset_experiment(self):
        self.city = deepcopy(self.baseline)
        self.has_stepped = False
        self.history = []
        self.refresh(record=True)
        self.status.set(f"시작 상태({self.city['day']}일)로 돌아왔습니다.")

    def save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="도시 상태 저장",
            defaultextension=".json",
            filetypes=[("도시 JSON", "*.json")],
            initialfile="my_city.json",
        )
        if not path:
            return
        try:
            city_data.save_city(self.city, path)
        except Exception as error:
            self._fail("저장", error)
            return

        self.status.set("도시를 저장했습니다.")

    def load_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="도시 상태 불러오기",
            filetypes=[("도시 JSON", "*.json")],
        )
        if not path:
            return
        try:
            candidate = city_data.load_city(path)
            city_data.validate_city(candidate)
        except Exception as error:
            self._fail("불러오기", error)
            return

        self._start_from(candidate)
        self.status.set(f"{self.city['day']}일 상태를 불러왔습니다.")


def launch(smoke=False):
    root = tk.Tk()
    CityApp(root)

    if smoke:
        root.update_idletasks()
        root.update()
        root.destroy()
        print("GUI smoke: Tk 창 생성과 최초 화면 갱신 성공")
    else:
        root.mainloop()

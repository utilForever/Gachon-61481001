"""
이웃의 같은 유형 비율에 따른 격자 이동 실험.

8×8 격자에 A 25명 / B 25명 / 빈칸 14개를 배치하고 회차별로 이동한다.
grid는 행위자 ID를 저장하며, labels()로 유형 A / B / None의 격자를 얻는다.
한 회차의 이동은 순서대로 반영한다. 도시의 월별 / 분 단위 실험과는 별개이다.
"""

import random
from copy import deepcopy

import agent_rules


class Neighborhood:
    def __init__(self, seed=42, threshold=0.5):
        self.seed, self.threshold = seed, threshold
        self.rng = random.Random(seed)

        cells = ["A"] * 25 + ["B"] * 25 + [None] * 14
        self.rng.shuffle(cells)

        self.grid = [[None] * 8 for _ in range(8)]
        self.groups, self.positions = {}, {}
        ident = 0

        for index, group in enumerate(cells):
            if group is not None:
                y, x = divmod(index, 8)
                self.grid[y][x] = ident
                self.groups[ident] = group
                self.positions[ident] = (x, y)
                ident += 1

        self.round = self.moves_total = 0
        self.history = []

    def labels(self):
        """행위자 ID 대신 유형 A / B / None을 담은 새 격자를 반환한다."""
        return [
            [None if ident is None else self.groups[ident] for ident in row] for row in self.grid
        ]

    def ratio(self, ident, destination=None):
        """현재 위치 또는 후보 위치의 이웃 비율을 구한다. 후보 평가 시 출발지는 비운다."""
        grid = self.labels()
        x, y = self.positions[ident]
        if destination is not None:
            grid[y][x] = None
            x, y = destination
            grid[y][x] = self.groups[ident]

        return agent_rules.same_type_ratio(grid, x, y)

    def satisfied(self, ident, destination=None):
        """같은 유형 비율이 기준 이상인지 판단한다. 거주 이웃이 없으면 만족한 상태이다."""
        value = self.ratio(ident, destination)
        return value is None or value >= self.threshold

    def snapshot(self, moves=0):
        """현재 회차의 이동 / 불만족 / 평균 이웃 비율을 기록용 dict로 반환한다."""
        ratios = [self.ratio(ident) for ident in sorted(self.positions)]
        measured = [value for value in ratios if value is not None]

        return dict(
            round=self.round,
            moves=moves,
            moves_total=self.moves_total,
            dissatisfied=sum(value is not None and value < self.threshold for value in ratios),
            mean_ratio=sum(measured) / len(measured) if measured else None,
        )

    def _advance(self):
        """회차 시작 때 불만족한 행위자의 순서를 섞어 이동하고 회차 기록을 추가한다."""
        order = [ident for ident in sorted(self.positions) if not self.satisfied(ident)]
        self.rng.shuffle(order)
        moved = 0

        for ident in order:
            if self.satisfied(ident):
                continue

            candidates = [
                (x, y)
                for y in range(8)
                for x in range(8)
                if self.grid[y][x] is None and self.satisfied(ident, (x, y))
            ]
            if candidates:
                nx, ny = self.rng.choice(candidates)
                x, y = self.positions[ident]
                self.grid[y][x] = None
                self.grid[ny][nx] = ident
                self.positions[ident] = (nx, ny)
                moved += 1

        self.round += 1
        self.moves_total += moved
        self.history.append(self.snapshot(moved))

    def advance(self):
        """복사본에서 한 회차를 마친 뒤 반영한다. 계산 실패 시 기존 상태를 보존한다."""
        candidate = deepcopy(self)
        if not candidate.history:
            candidate.history.append(candidate.snapshot())

        candidate._advance()

        self.__dict__.update(candidate.__dict__)

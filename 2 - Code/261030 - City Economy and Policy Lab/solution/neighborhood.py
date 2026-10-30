"""같은 유형의 이웃 비율을 기준으로 이동하는 8×8 행위자 격자."""

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
        return [
            [None if ident is None else self.groups[ident] for ident in row] for row in self.grid
        ]

    def ratio(self, ident, destination=None):
        grid = self.labels()
        x, y = self.positions[ident]
        if destination is not None:
            grid[y][x] = None
            x, y = destination
            grid[y][x] = self.groups[ident]
        return agent_rules.same_type_ratio(grid, x, y)

    def satisfied(self, ident, destination=None):
        value = self.ratio(ident, destination)
        return value is None or value >= self.threshold

    def snapshot(self, moves=0):
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
        candidate = deepcopy(self)
        if not candidate.history:
            candidate.history.append(candidate.snapshot())

        candidate._advance()
        self.__dict__.update(candidate.__dict__)

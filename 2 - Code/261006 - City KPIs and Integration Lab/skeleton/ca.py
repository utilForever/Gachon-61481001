def ca_step(grid):
    if not grid or not grid[0]:
        raise ValueError("격자는 한 칸 이상이어야 합니다.")

    height = len(grid)
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("모든 행의 길이는 같아야 합니다.")
    if any(type(value) is not int or value not in (0, 1) for row in grid for value in row):
        raise ValueError("셀 값은 정수 0 또는 1이어야 합니다.")

    new = []

    for y in range(height):
        row = []
        for x in range(width):
            count = 0
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx = x + dx
                ny = y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    count += grid[ny][nx]

            row.append(1 if count >= 2 else 0)
        new.append(row)

    return new

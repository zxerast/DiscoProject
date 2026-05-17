from map import GameMap


grid = [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [4, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
]

doors = {
    (0, 1): {"target": "test", "spawn": (14, 1)},
}

room = GameMap(grid, doors=doors)

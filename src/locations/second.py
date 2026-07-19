import os

from map import GameMap
from settings import BASE_DIR


ROOM_ASSET_DIR = os.path.join(BASE_DIR, "assets", "locations", "second")

ROOM_LAYERS = [
    {"image": os.path.join(ROOM_ASSET_DIR, "save_terminal.png"), "x": 320, "y_offset": 128, "tile": (5, 2), "approach": (5, 3)},
]


grid = [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [4, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 5, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
]

doors = {
    (0, 1): {"target": "awaken_chamber", "spawn": (13, 4)},
}

room = GameMap(
    grid,
    doors=doors,
    map_layers=ROOM_LAYERS,
    tile_alpha=110,
)

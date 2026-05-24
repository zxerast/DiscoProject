import os

from map import GameMap
from settings import BASE_DIR


ROOM_BACKGROUND = os.path.join(BASE_DIR, "assets", "locations", "awaken_chamber.png")
ROOM_BACKGROUND_SIZE = (1672, 941)

grid = [
    [1, 0, 0, 1, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 4],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 3, 0, 0, 0, 2, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
]

npc_dialogues = {
    (6, 5): "start",      #   Торговец
    (11, 8): "guard",     #   Стражник
    (12, 1): "change_to_door",
    (13, 2): "change_to_chest",
    (14, 3): "change_to_npc",
}

chests = {
    (9, 2): {
        "cols": 3,
        "rows": 2,
        "set_flag_on_take": "hasPass",
        "items": [
            {"id": "apple", "count": 2},
            {"id": "book", "count": 1},
            None,
            {"id": "old_pass", "count": 1},
        ],
    },
}

doors = {
    (15, 1): {"target": "second", "spawn": (1, 1)},
}

tile_changes = {
    "door_to_kitchen": {
        "tile": 4,
        "door": {"target": "second", "spawn": (1, 1)},
    },
    "chest_with_pass": {
        "tile": 3,
        "chest": {
            "cols": 2,
            "rows": 1,
            "set_flag_on_take": "hasPass",
            "items": [
                {"id": "old_pass", "count": 1},
            ],
        },
    },
    "guard_npc": {
        "tile": 2,
        "dialogue": "guard",
    },
}

room = GameMap(
    grid,
    npc_dialogues=npc_dialogues,
    chests=chests,
    doors=doors,
    tile_changes=tile_changes,
    background_image=ROOM_BACKGROUND,
    background_size=ROOM_BACKGROUND_SIZE,
    show_tiles=True,
    tile_alpha=110,
)

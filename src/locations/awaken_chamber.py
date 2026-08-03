import os

from map import GameMap
from settings import BASE_DIR


ROOM_ASSET_DIR = os.path.join(BASE_DIR, "assets", "locations", "awakening_chamber")
ROOM_BACKGROUND = os.path.join(ROOM_ASSET_DIR, "hall.png")
ROOM_BACKGROUND_SIZE = (1664, 960)

ROOM_LAYERS = [
    # Оставляем только тайловые координаты
    {"image": os.path.join(ROOM_ASSET_DIR, "barrel.png"), "tile": (10, 5), "approach": (5, 5)},
    {"image": os.path.join(ROOM_ASSET_DIR, "our_camera.png"), "tile": (3, 3), "approach": (3, 4)},
]

ROOM_DEPTH_LAYERS = [
    # Добавляем ключ "tile" вместо "x", "y_offset" и "y"
    {"image": os.path.join(ROOM_ASSET_DIR, "back_fence.png"), "tile": (3, 9)}, 
    {"image": os.path.join(ROOM_ASSET_DIR, "desk.png"), "tile": (36, 10)},
    {"image": os.path.join(ROOM_ASSET_DIR, "front_fence.png"), "tile": (2, 17)},
]

grid = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2 ,1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 3, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,1, 1, 1, 1, 1],
]

npc_dialogues = {
    (13, 3): "exit_locked",
    (19, 7): "computer",
    (3, 3): "our_camera",
#    (3, 7): "another_camera"
}

chests = {
    (10, 5): {
        "cols": 3,
        "rows": 2,
        "items": [
            {"id": "crowbar", "count": 1, "set_flag_on_take": ["has_crowbar", "force_breakout_stage_1_completed", "force_breakout_stage_2"]},
            {"id": "medkit", "count": 3},
            {"id": "casette", "count": 1, "set_flag_on_take": "has_casette"},
            {"id": "letter", "count": 1},
            {"id": "colt", "count": 1}
        ],
    },
}

tile_changes = {
    "exit": {
        "tile": 4,
        "door": {"target": "second", "spawn": (1, 1)},
    }
}

bonfires = {}

room = GameMap(
    grid,
    npc_dialogues=npc_dialogues,
    chests=chests,
#   doors=doors,
    tile_changes=tile_changes,
#    background_image=ROOM_BACKGROUND,
#    background_size=ROOM_BACKGROUND_SIZE,
    map_layers=ROOM_LAYERS,
#    depth_layers=ROOM_DEPTH_LAYERS,
    show_tiles=True,
    bonfires=bonfires,
    tile_alpha=255,
)

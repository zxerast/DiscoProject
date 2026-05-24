import os

from map import GameMap
from settings import BASE_DIR


ROOM_ASSET_DIR = os.path.join(BASE_DIR, "assets", "locations", "awakening_chamber")
ROOM_BACKGROUND = os.path.join(ROOM_ASSET_DIR, "hall.png")
ROOM_BACKGROUND_SIZE = (1664, 960)

ROOM_LAYERS = [
    {"image": os.path.join(ROOM_ASSET_DIR, "barrel.png"), "x": 185, "y_offset": 694, "tile": (4, 12), "approach": (4, 13)},
    {"image": os.path.join(ROOM_ASSET_DIR, "computer_interaction.png"), "x": 1344, "y_offset": 387},
    {"image": os.path.join(ROOM_ASSET_DIR, "cryo_cam_interaction.png"), "x": 224, "y_offset": 336},
    {"image": os.path.join(ROOM_ASSET_DIR, "door_interaction.png"), "x": 690, "y_offset": 76, "tile": (13, 3), "approach": (13, 4)},
]

ROOM_DEPTH_LAYERS = [
    {"image": os.path.join(ROOM_ASSET_DIR, "back_fence.png"), "x": 102, "y_offset": 306, "y": 480},
    {"image": os.path.join(ROOM_ASSET_DIR, "desk.png"), "x": 1179, "y_offset": 329, "y": 513},
    {"image": os.path.join(ROOM_ASSET_DIR, "front_fence.png"), "x": 67, "y_offset": 548, "y": 635},
]

grid = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1 ,1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 3, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1 ,1, 1, 1, 1, 1],
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ,1, 1, 1, 1, 1],
]

npc_dialogues = {
    (13, 3): "exit_locked",
}

chests = {
    (4, 12): {
        "cols": 3,
        "rows": 1,
        "set_flag_on_take": "has_crowbar",
        "items": [
            {"id": "crowbar", "count": 1},
        ],
    },
}

tile_changes = {
    "exit": {
        "tile": 4,
        "door": {"target": "second", "spawn": (1, 1)},
    }
}

room = GameMap(
    grid,
    npc_dialogues=npc_dialogues,
    chests=chests,
#   doors=doors,
    tile_changes=tile_changes,
    background_image=ROOM_BACKGROUND,
    background_size=ROOM_BACKGROUND_SIZE,
    map_layers=ROOM_LAYERS,
    depth_layers=ROOM_DEPTH_LAYERS,
    show_tiles=False,
    tile_alpha=110,
)

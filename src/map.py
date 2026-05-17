import pygame
import copy
from collections import deque

class GameMap:
    def __init__(self, grid, tile_size=64, npc_dialogues=None, chests=None, doors=None, tile_changes=None):
        self.base_tile_size = tile_size
        self.grid = grid    #   Принимаем текущую карту с её интерактивными объектами
        self.tile_size = tile_size
        self.npc_dialogues = npc_dialogues or {}  #   {(x, y): "dialogue_id"}
        self.chests = chests or {}  # {(x, y): {"cols": int, "rows": int, "items": list}}
        self.doors = doors or {}  # {(x, y): {"target": "location_id", "spawn": (x, y)}}
        self.tile_changes = tile_changes or {}

        self.height = len(grid)
        self.width = max(len(row) for row in grid)

    def set_scale(self, scale):
        self.tile_size = max(1, int(round(self.base_tile_size * scale)))

    def is_walkable(self, x, y):    #   Принимаем координаты точки назначения
        if x < 0 or y < 0:
            return False

        if x >= self.width or y >= self.height:
            return False

        if x >= len(self.grid[y]):
            return False
        return self.grid[y][x] == 0 #   Если номер клетки в массиве 0 то возвращаем True иначе False

    def is_interactive(self, x, y):
        if x < 0 or y < 0:
            return False

        if x >= self.width or y >= self.height:
            return False
        
        if x >= len(self.grid[y]):
            return False
        return self.grid[y][x] in (2, 3, 4, 5)

    def is_npc(self, x, y):
        return self._tile_at(x, y) == 2

    def is_chest(self, x, y):
        return self._tile_at(x, y) == 3

    def is_door(self, x, y):
        return self._tile_at(x, y) == 4

    def is_bonfire(self, x, y):
        return self._tile_at(x, y) == 5

    def _tile_at(self, x, y):
        if x < 0 or y < 0:
            return None

        if x >= self.width or y >= self.height:
            return None

        if x >= len(self.grid[y]):
            return None
        return self.grid[y][x]

    def get_dialogue_id(self, x, y):
        return self.npc_dialogues.get((x, y))

    def get_chest(self, x, y):
        return self.chests.get((x, y))

    def get_door(self, x, y):
        return self.doors.get((x, y))

    def _pack_points(self, data):
        return {f"{x},{y}": copy.deepcopy(value) for (x, y), value in data.items()}

    def _unpack_points(self, data):
        result = {}
        for key, value in data.items():
            x, y = key.split(",", 1)
            result[(int(x), int(y))] = copy.deepcopy(value)
        return result

    def to_state(self): #   Преобразование состояния комнаты в json для сохранение
        return {
            "grid": copy.deepcopy(self.grid),
            "npc_dialogues": self._pack_points(self.npc_dialogues),
            "chests": self._pack_points(self.chests),
            "doors": self._pack_points(self.doors),
        }

    def load_state(self, state):    #   Обратное преобразование для загрузки
        self.grid = copy.deepcopy(state["grid"])
        self.npc_dialogues = self._unpack_points(state.get("npc_dialogues", {}))
        self.chests = self._unpack_points(state.get("chests", {}))
        self.doors = self._unpack_points(state.get("doors", {}))
        self.height = len(self.grid)
        self.width = max(len(row) for row in self.grid)

    def change_tile(self, x, y, change_id):
        change = self.tile_changes[change_id]
        pos = (x, y)
        tile = change["tile"]

        self.grid[y][x] = tile
        self.npc_dialogues.pop(pos, None)
        self.chests.pop(pos, None)
        self.doors.pop(pos, None)

        if tile == 2:
            self.npc_dialogues[pos] = change["dialogue"]
        elif tile == 3:
            self.chests[pos] = copy.deepcopy(change["chest"])
        elif tile == 4:
            self.doors[pos] = copy.deepcopy(change["door"])

    def get_adjacent_walkable(self, gx, gy):
        for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
            nx, ny = gx + dx, gy + dy
            if self.is_walkable(nx, ny):
                return (nx, ny)
        return None

    def pixel_to_grid(self, px, py):
        return int(px // self.tile_size), int(py // self.tile_size)

    def grid_to_pixel_center(self, gx, gy):
        return gx * self.tile_size + self.tile_size // 2, gy * self.tile_size + self.tile_size // 2

    def find_path(self, start, end):
        sx, sy = start
        ex, ey = end

        if not self.is_walkable(ex, ey):
            return []

        queue = deque([(sx, sy)])   #   Двухсторонняя очередь
        came_from = {(sx, sy): None}    #   Парный словарь где None - откуда пришли, (sx, sy) - где мы сейчас

        while queue:
            cx, cy = queue.popleft()    #   Достаём последнюю добавленную клетку

            if (cx, cy) == (ex, ey):    #   Если последняя взятая клетка конец пути
                path = []
                node = (ex, ey)
                while node is not None: #   Восстанавливаем путь от конца к началу по словарю
                    path.append(node)
                    node = came_from[node]
                path.reverse()      #   Разворачиваем путь
                return path

            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:   #   Проверяем всех соседей у текущей клетки
                nx, ny = cx + dx, cy + dy
                if self.is_walkable(nx, ny) and (nx, ny) not in came_from:
                    came_from[(nx, ny)] = (cx, cy)
                    queue.append((nx, ny))

        return []
    
    def draw(self, screen, cam_x=0, cam_y=0):

        for y in range(self.height):
            for x in range(len(self.grid[y])):     #   Рисуем карту по описанию
                rect = pygame.Rect(
                    x * self.tile_size - cam_x,
                    y * self.tile_size - cam_y,
                    self.tile_size,
                    self.tile_size,
                )

                if self.grid[y][x] == 2:
                    pygame.draw.rect(screen, (180, 140, 60), rect)  #   Разные прямоугольники - разный функционал
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)
                elif self.grid[y][x] == 3:
                    pygame.draw.rect(screen, (40, 200, 200), rect)
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)
                elif self.grid[y][x] == 4:
                    pygame.draw.rect(screen, (90, 55, 25), rect)
                    pygame.draw.rect(screen, (220, 180, 90), rect, 2)
                elif self.grid[y][x] == 5:
                    pygame.draw.rect(screen, (130, 30, 20), rect)
                    pygame.draw.circle(screen, (255, 140, 40), rect.center, max(4, self.tile_size // 4))
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)
                elif self.grid[y][x] == 1:
                    pygame.draw.rect(screen, (120, 120, 120), rect)
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)

                elif self.grid[y][x] == 0:
                    pygame.draw.rect(screen, (40, 100, 100), rect)
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)

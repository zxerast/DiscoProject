import pygame
import copy
from collections import deque

class GameMap:
    def __init__(
        self,
        grid,
        tile_size=32,
        npc_dialogues=None,
        chests=None,
        doors=None,
        tile_changes=None,
        background_image=None,
        background_size=None,
        map_layers=None,
        depth_layers=None,
        show_tiles=True,
        bonfires=None,
        tile_alpha=255,
    ):
        self.base_tile_size = tile_size
        self.grid = grid    #   Принимаем текущую карту с её интерактивными объектами
        self.tile_size = tile_size
        self.scale = 1
        self.npc_dialogues = npc_dialogues or {}  #   {(x, y): "dialogue_id"}
        self.chests = chests or {}  # {(x, y): {"cols": int, "rows": int, "items": list}}
        self.doors = doors or {}  # {(x, y): {"target": "location_id", "spawn": (x, y)}}
        self.tile_changes = tile_changes or {}
        self.background_image = background_image
        self.background_size = background_size
        self.map_layers = [self._normalize_layer(layer) for layer in (map_layers or [])]
        self.depth_layers = [self._normalize_layer(layer) for layer in (depth_layers or [])]
        self.show_tiles = show_tiles
        self.tile_alpha = tile_alpha
        self.bonfires = bonfires or {}
        self._background_original = None
        self._background_scaled = None
        self._background_scaled_size = None
        self._layer_originals = {}
        self._layer_scaled = {}
        self._layer_masks = {}
        self._layer_outlines = {}

        self.height = len(grid)
        self.width = max(len(row) for row in grid)

    def set_scale(self, scale):
        self.scale = scale
        self.tile_size = max(1, int(round(self.base_tile_size * scale)))
        self._background_scaled = None
        self._background_scaled_size = None
        self._layer_scaled = {}
        self._layer_masks = {}
        self._layer_outlines = {}

    def _normalize_layer(self, layer):
        if isinstance(layer, str):
            return {"image": layer}
        return copy.deepcopy(layer)

    def _get_background(self):
        if not self.background_image:
            return None

        if self._background_original is None:
            self._background_original = pygame.image.load(self.background_image).convert_alpha()

        base_width, base_height = self.background_size or self._background_original.get_size()
        size = (
            max(1, int(round(base_width * self.scale))),
            max(1, int(round(base_height * self.scale))),
        )

        if self._background_scaled is None or self._background_scaled_size != size:
            if size == self._background_original.get_size():
                self._background_scaled = self._background_original
            else:
                self._background_scaled = pygame.transform.scale(self._background_original, size)
            self._background_scaled_size = size

        return self._background_scaled

    def _get_layer_image(self, layer):
        image_path = layer["image"]

        if image_path not in self._layer_originals:
            self._layer_originals[image_path] = pygame.image.load(image_path).convert_alpha()

        original = self._layer_originals[image_path]
        base_width, base_height = layer.get("size") or original.get_size()
        size = (
            max(1, int(round(base_width * self.scale))),
            max(1, int(round(base_height * self.scale))),
        )
        cache_key = (image_path, size)

        if cache_key not in self._layer_scaled:
            if size == original.get_size():
                self._layer_scaled[cache_key] = original
            else:
                self._layer_scaled[cache_key] = pygame.transform.scale(original, size)

        return self._layer_scaled[cache_key]

    def _get_layer_mask(self, layer):
        image = self._get_layer_image(layer)
        cache_key = (layer["image"], image.get_size())

        if cache_key not in self._layer_masks:
            self._layer_masks[cache_key] = pygame.mask.from_surface(image)

        return self._layer_masks[cache_key]

    def _get_layer_outline(self, layer):
        image = self._get_layer_image(layer)
        cache_key = (layer["image"], image.get_size())

        if cache_key not in self._layer_outlines:
            self._layer_outlines[cache_key] = self._get_layer_mask(layer).outline()

        return self._layer_outlines[cache_key]

    def _get_layer_rect(self, layer, cam_x=0, cam_y=0):
        image = self._get_layer_image(layer)
        gx, gy = layer.get("tile", (0, 0))
        
        # Выравниваем центр спрайта по центру тайла по горизонтали
        x = gx * self.tile_size + (self.tile_size - image.get_width()) // 2 - cam_x
        
        # Выравниваем НИЗ спрайта по НИЗУ тайла
        y = gy * self.tile_size + self.tile_size - image.get_height() - cam_y
        
        return pygame.Rect(x, y, image.get_width(), image.get_height())

    def _draw_layer(self, screen, layer, cam_x=0, cam_y=0):
        image = self._get_layer_image(layer)
        screen.blit(image, self._get_layer_rect(layer, cam_x, cam_y))

    def get_interactive_sprite_at(self, pos, cam_x=0, cam_y=0):
        for layer in reversed(self.map_layers + self.depth_layers):
            if "tile" not in layer or "approach" not in layer:
                continue

            rect = self._get_layer_rect(layer, cam_x, cam_y)
            if not rect.collidepoint(pos):
                continue

            local_pos = (pos[0] - rect.x, pos[1] - rect.y)
            if self._get_layer_mask(layer).get_at(local_pos):
                return layer

        return None

    def draw_hover_outline(self, screen, pos, cam_x=0, cam_y=0):
        layer = self.get_interactive_sprite_at(pos, cam_x, cam_y)
        if not layer:
            return

        rect = self._get_layer_rect(layer, cam_x, cam_y)
        points = [(rect.x + x, rect.y + y) for x, y in self._get_layer_outline(layer)]
        if len(points) > 1:
            pygame.draw.lines(screen, (255, 255, 255), True, points, max(1, int(round(2 * self.scale))))

    def draw_depth_layers(self, screen, player_y, in_front, cam_x=0, cam_y=0):
        for layer in self.depth_layers:
            # Получаем прямоугольник слоя без учета камеры, чтобы узнать его абсолютные мировые координаты
            rect = self._get_layer_rect(layer, 0, 0)
            
            # Точка глубины объекта — это нижняя граница его спрайта
            layer_y = rect.bottom
            
            layer_in_front = player_y <= layer_y

            if layer_in_front == in_front:
                self._draw_layer(screen, layer, cam_x, cam_y)

    def is_walkable(self, x, y):    #   Принимаем координаты точки назначения
        if x < 0 or y < 0:
            return False

        if x >= self.width or y >= self.height:
            return False

        if x >= len(self.grid[y]):
            return False
        return self.grid[y][x] == 0 #   Если номер клетки в массиве 0 то возвращаем True иначе False

    def get_dialogue_id(self, x, y):
        return self.npc_dialogues.get((x, y))

    def get_chest(self, x, y):
        return self.chests.get((x, y))

    def get_door(self, x, y):
        return self.doors.get((x, y))
    
    def get_bonfire(self, x, y):
        return self.bonfires.get((x, y))

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

        if "dialogue" in change:
            self.npc_dialogues[pos] = change["dialogue"]

        if "chest" in change:
            self.chests[pos] = copy.deepcopy(change["chest"])

        if "door" in change:
            self.doors[pos] = copy.deepcopy(change["door"])

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
        background = self._get_background()
        if background:
            screen.blit(background, (-cam_x, -cam_y))

        for layer in self.map_layers:
            self._draw_layer(screen, layer, cam_x, cam_y)

        if not self.show_tiles:
            return

        tile_alpha = max(0, min(255, self.tile_alpha))
        tile_layer = screen
        if tile_alpha < 255:
            tile_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        def tile_color(color):
            if tile_alpha >= 255:
                return color
            return color + (tile_alpha,)

        for y in range(self.height):
            for x in range(len(self.grid[y])):     #   Рисуем карту по описанию
                rect = pygame.Rect(
                    x * self.tile_size - cam_x,
                    y * self.tile_size - cam_y,
                    self.tile_size,
                    self.tile_size,
                )

                if self.grid[y][x] == 2:
                    pygame.draw.rect(tile_layer, tile_color((180, 140, 60)), rect)  #   Разные прямоугольники - разный функционал
                    pygame.draw.rect(tile_layer, tile_color((60, 60, 60)), rect, 1)
                elif self.grid[y][x] == 3:
                    pygame.draw.rect(tile_layer, tile_color((40, 200, 200)), rect)
                    pygame.draw.rect(tile_layer, tile_color((60, 60, 60)), rect, 1)
                elif self.grid[y][x] == 4:
                    pygame.draw.rect(tile_layer, tile_color((90, 55, 25)), rect)
                    pygame.draw.rect(tile_layer, tile_color((220, 180, 90)), rect, 2)
                elif self.grid[y][x] == 5:
                    pygame.draw.rect(tile_layer, tile_color((130, 30, 20)), rect)
                    pygame.draw.rect(tile_layer, tile_color((60, 60, 60)), rect, 1)
                elif self.grid[y][x] == 1:
                    pygame.draw.rect(tile_layer, tile_color((120, 120, 120)), rect)
                    pygame.draw.rect(tile_layer, tile_color((60, 60, 60)), rect, 1)

                elif self.grid[y][x] == 0:
                    pygame.draw.rect(tile_layer, tile_color((40, 100, 100)), rect)
                    pygame.draw.rect(tile_layer, tile_color((60, 60, 60)), rect, 1)

        if tile_layer is not screen:
            screen.blit(tile_layer, (0, 0))

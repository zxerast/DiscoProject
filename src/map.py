import pygame
from collections import deque

class GameMap:
    def __init__(self, grid, tile_size=64, npc_dialogues=None):
        self.grid = grid    #   Принимаем текущую карту с её интерактивными объектами
        self.tile_size = tile_size
        self.npc_dialogues = npc_dialogues or {}  #   {(x, y): "dialogue_id"}

        self.height = len(grid)
        self.width = len(grid[0])

    def is_walkable(self, x, y):    #   Принимаем координаты точки назначения
        if x < 0 or y < 0:
            return False

        if x >= self.width or y >= self.height:
            return False

        return self.grid[y][x] == 0 #   Если номер клетки в массиве 0 то возвращаем True иначе False

    def is_interactive(self, x, y):
        if x < 0 or y < 0:
            return False

        if x >= self.width or y >= self.height:
            return False
        
        return self.grid[y][x] == 2

    def get_dialogue_id(self, x, y):
        return self.npc_dialogues.get((x, y))

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
            for x in range(self.width):     #   Рисуем карту по описанию
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
                elif self.grid[y][x] == 1:
                    pygame.draw.rect(screen, (120, 120, 120), rect)
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)

                elif self.grid[y][x] == 0:
                    pygame.draw.rect(screen, (40, 100, 100), rect)
                    pygame.draw.rect(screen, (60, 60, 60), rect, 1)
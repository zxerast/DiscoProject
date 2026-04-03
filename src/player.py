import pygame
import os
import json
from settings import get_scale, BASE_DIR
from skills import SKILL_GROUPS

SAVE_PATH = os.path.join(BASE_DIR, "player.json")


# Размер спрайта персонажа (для базового разрешения 1366x768)
PLAYER_WIDTH = 80
PLAYER_HEIGHT = 160


class Player:
    def __init__(self, grid_x, grid_y, game_map, screen):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.game_map = game_map

        sx, sy = get_scale(screen)

        ts = game_map.tile_size     #   Размер клетки
        self.x = float(grid_x * ts + ts // 2) # Переводим координаты персонажа в координаты клетки
        self.y = float(grid_y * ts + ts // 2)

        self.width = int(PLAYER_WIDTH * sx)
        self.height = int(PLAYER_HEIGHT * sy)
        self.speed = 3

        base = BASE_DIR   #   Место откуда берём анимации

        self.walking_up = []    #   Место куда кладём анимации
        self.walking_left = []
        self.walking_right = []
        self.walking_down = []

        for i in range(10):     #   Собираем все кадры
            frame = f"frame_{i:03d}.png"
            self.walking_up.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "up", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_left.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "left", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_down.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "down", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_right.append(pygame.transform.scale(pygame.transform.flip(pygame.image.load(os.path.join(base, "assets", "left", frame)).convert_alpha(), True, False), (self.width, self.height)))

        self.direction = self.walking_down
        self.current_frame = 0
        self.animation_speed = 0.1
        self.image = self.direction[0]
        self.rect = self.image.get_rect()   #   Создаём прямоугольник для персонажа
        self.rect.midbottom = (int(self.x), int(self.y) + game_map.tile_size // 2)  #   Ставим этот прямоугольник нижней частью на пол

        self.path = []
        self.target_x = self.x
        self.target_y = self.y
        self.is_moving = False

        # Загружаем состояние из JSON
        self._load_save()

    def _load_save(self):
        with open(SAVE_PATH, "r", encoding="utf-8") as f: data = json.load(f)
        self.level = data["level"]
        self.skill_points = data["skill_points"]
        self.attributes = data["attributes"]
        self.skills = data["skills"]
        self.flags = data.get("flags", {})
        self.location = data.get("location", "test")

        # Позиция из сейва (перезаписывает аргументы __init__)
        self.grid_x = data["position"]["grid_x"]
        self.grid_y = data["position"]["grid_y"]
        
        ts = self.game_map.tile_size
        self.x = float(self.grid_x * ts + ts // 2)
        self.y = float(self.grid_y * ts + ts // 2)
        self.rect.midbottom = (int(self.x), int(self.y) + ts // 2)

    def save(self):
        data = {
            "level": self.level,
            "skill_points": self.skill_points,
            "attributes": self.attributes,
            "skills": self.skills,
            "position": {"grid_x": self.grid_x, "grid_y": self.grid_y},
            "location": self.location,
            "flags": self.flags,
        }
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def set_flag(self, flag_name, value=True):
        self.flags[flag_name] = value

    def get_flag(self, flag_name):
        return self.flags.get(flag_name, False)

    def get_skill(self, skill_name):    #   Получить значение скилла по имени
        return self.skills.get(skill_name, 0)

    def get_attr_for_skill(self, skill_name):   #   Получить индекс основного атрибута, к которому относится скилл
        for attr_idx, group in enumerate(SKILL_GROUPS):
            if skill_name in group:
                return attr_idx
        return -1

    def level_up(self):
        self.level += 1
        self.skill_points += 1

    def set_target(self, mouse_x, mouse_y):
        gx, gy = self.game_map.pixel_to_grid(mouse_x, mouse_y)  #   Корды точки назначения в корды по клеткам
        start = (self.grid_x, self.grid_y)
        end = (gx, gy)

        if start == end:
            return

        path = self.game_map.find_path(start, end)  #   Ищем путь
        if len(path) > 1:
            self.path = path[1:]    #   Отбрасываем первую точку на которой мы стоим и начинаем путь со второй
            self._next_waypoint()

    def _next_waypoint(self):
        if not self.path:   #   Если в пути закончились клетки
            self.is_moving = False  #   Останавливаемя
            self.current_frame = 0
            self.image = self.direction[0]
            return

        next_gx, next_gy = self.path[0]     #   Вторая клетка - начало пути
        self.target_x, self.target_y = self.game_map.grid_to_pixel_center(next_gx, next_gy) #Обратно переводим корды конца в пиксели т.к перс движется по пикселям
        self.is_moving = True

        dx = next_gx - self.grid_x
        dy = next_gy - self.grid_y

        if dy < 0:
            self.direction = self.walking_up
        elif dy > 0:
            self.direction = self.walking_down
        elif dx < 0:
            self.direction = self.walking_left
        elif dx > 0:
            self.direction = self.walking_right

    def update(self):
        if not self.is_moving:
            return

        dx = self.target_x - self.x #   Расстояние по x и y в пикселях до цели
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5   #   Длина вектора расстония как возведение в степень 0,5

        if dist <= self.speed:  #   Если осталось меньше одного шага до следующей клетки то сразу встаём в неё, чтобы не крутиться вокруг неё по пикселям
            self.x = self.target_x
            self.y = self.target_y
            self.grid_x, self.grid_y = self.path.pop(0) #   Убираем её из пути, мы на неё пришли
            self._next_waypoint()   #   Ищем следующую клетку
        else:
            self.x += (dx / dist) * self.speed  #   Медленно попиксельно идём к клетке пока не дойдём до её центра
            self.y += (dy / dist) * self.speed

        if self.is_moving:  #   Проигрываем анимацию пока идём
            self.current_frame += self.animation_speed
            if self.current_frame >= 10:
                self.current_frame = 1
            self.image = self.direction[int(self.current_frame)]

        self.rect.midbottom = (int(self.x), int(self.y) + self.game_map.tile_size // 2) #   Держим ноги внизу чтобы не улетели

    def draw(self, screen, cam_x=0, cam_y=0):
        draw_rect = self.rect.move(-cam_x, -cam_y)
        screen.blit(self.image, draw_rect)

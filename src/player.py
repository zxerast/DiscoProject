import pygame
import os
import json
from settings import BASE_DIR, SAVE_DIR
from skills import SKILL_GROUPS

SAVE_PATH = os.path.join(BASE_DIR, "player.json")
QUESTS_PATH = os.path.join(BASE_DIR, "quests.json")
SAVE_QUESTS_PATH = os.path.join(SAVE_DIR, "quests.json")


# Размер спрайта персонажа (для базового разрешения 1366x768)
PLAYER_WIDTH = 48
PLAYER_HEIGHT = 98


class Player:
    def __init__(self, game_map, screen, scale, save_path=SAVE_PATH):
        self.save_path = save_path  #   Данные об игроке
        self.game_map = game_map    #   Загруженная карта

        self.width = int(PLAYER_WIDTH * scale)
        self.height = int(PLAYER_HEIGHT * scale)
        self.speed = 2 * scale

        base = BASE_DIR   #   Место откуда берём анимации

        self.walking_up = []    #   Место куда кладём анимации
        self.walking_left = []
        self.walking_right = []
        self.walking_down = []

        for i in range(5):     #   Собираем все кадры
            frame = f"frame_{i:03d}.png"
            self.walking_up.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "up", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_left.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "left", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_down.append(pygame.transform.scale(pygame.image.load(os.path.join(base, "assets", "down", frame)).convert_alpha(), (self.width, self.height)))
            self.walking_right.append(pygame.transform.scale(pygame.transform.flip(pygame.image.load(os.path.join(base, "assets", "left", frame)).convert_alpha(), True, False), (self.width, self.height)))

        self.direction = self.walking_down  #   По умолчанию смотрим вниз
        self.current_frame = 0
        self.animation_speed = 0.1
        self.image = self.direction[0]
        self.rect = self.image.get_rect()   #   Создаём прямоугольник для персонажа
        self.rect.midbottom = (0, game_map.tile_size // 2)  #   Позиция ниже загрузится из сохранения

        self.path = []  #   Путь движения игрока
        self.is_moving = False

        # Загружаем состояние из JSON
        self._load_save()

    def _load_save(self):
        with open(self.save_path, "r", encoding="utf-8") as f: data = json.load(f)
        self.level = data["level"]
        self.skill_points = data["skill_points"]
        self.health_points = data["HP"]
        self.xp_points = data["XP"]
        self.xp_cap = data["XP_cap"]
        self.attributes = data["attributes"]
        self.skills = data["skills"]
        self.flags = data.get("flags", {})
        self.active_quests = data.get("active_quests", {})
        self.inventory = data.get("inventory", [])
        self.location = data.get("location", "awaken_chamber")

        # Позиция из сейва (перезаписывает аргументы __init__)
        self.grid_x = data["position"]["grid_x"]
        self.grid_y = data["position"]["grid_y"]
        
        ts = self.game_map.tile_size
        self.x = float(self.grid_x * ts + ts // 2)
        self.y = float(self.grid_y * ts + ts // 2)
        self.target_x = self.x
        self.target_y = self.y
        self.rect.midbottom = (int(self.x), int(self.y) + ts // 2)
        self.health_points = max(1, min(self.health_points, self.get_max_health()))

    def save(self):
        data = {
            "level": self.level,
            "skill_points": self.skill_points,
            "HP": self.health_points,
            "XP": self.xp_points,
            "XP_cap": self.xp_cap,
            "attributes": self.attributes,
            "skills": self.skills,
            "position": {"grid_x": self.grid_x, "grid_y": self.grid_y},
            "location": self.location,
            "inventory": self.inventory,
            "flags": self.flags,
            "active_quests": self.active_quests,
        }
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)    #   Сохраняемся дампя всё собранное 

    def set_flag(self, flag_name, value=True):
        # Оптимизация: если флаг уже стоит, ничего не делаем
        if self.flags.get(flag_name) == value:
            return 
            
        self.flags[flag_name] = value

        # Если флаг получен (а не снят) и у игрока есть подключенный менеджер квестов
        if value is True and hasattr(self, 'quest_manager'):
            self.quest_manager.process_flag(flag_name)

   
    def get_flag(self, flag_name):      #   Получить имя флага из списка
        return self.flags.get(flag_name, False)

    def get_skill(self, skill_name):    #   Получить значение скилла по имени
        return self.skills.get(skill_name, 0)

    def get_attr_for_skill(self, skill_name):   #   Получить индекс основного атрибута, к которому относится скилл
        for attr_idx, group in enumerate(SKILL_GROUPS):
            if skill_name in group:
                return attr_idx
        return -1

    def award_completed_quest_xp(self): #   Выдаём XP за выполнение квеста
        path = SAVE_QUESTS_PATH if os.path.exists(SAVE_QUESTS_PATH) else QUESTS_PATH

        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            quests = json.load(f)

        for quest_id, quest in quests.items():
            reward_flag = f"{quest_id}_xp_awarded"
            if self.flags.get(reward_flag):
                continue

            stage_flags = [
                stage.get("complete_flag")
                for stage in quest.get("stages", [])
                if stage.get("complete_flag")
            ]
            if stage_flags and all(self.flags.get(f"{flag}_completed") is True for flag in stage_flags):
                self.add_xp(quest.get("xp_reward", 0))
                self.flags[reward_flag] = True

    def add_xp(self, xp):
        self.xp_points += xp
        while self.xp_points >= self.xp_cap:
            self.level += 1
            self.skill_points += 1
            self.xp_points -= self.xp_cap 
            self.xp_cap += 25

    def get_max_health(self):
        return max(1, self.get_skill("fortitude"))  #   За здоровье отвечает скилл Стойкость

    def take_damage(self, damage=1):
        self.health_points -= damage

    def heal(self, heal_points):
        self.health_points = min(self.get_max_health(), self.health_points + heal_points)

    def set_map_position(self, game_map, grid_x, grid_y, location=None):    #   Устанавливаем корды в тайлах 
        self.game_map = game_map
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.path = []
        self.is_moving = False
        self.target_x, self.target_y = game_map.grid_to_pixel_center(grid_x, grid_y)
        self.x = float(self.target_x)
        self.y = float(self.target_y)
        self.current_frame = 0
        self.image = self.direction[0]
        self.rect.midbottom = (int(self.x), int(self.y) + game_map.tile_size // 2)
        if location:
            self.location = location

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

        was_moving = self.is_moving
        next_gx, next_gy = self.path[0]     #   Вторая клетка - следующая цель пути
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

        if not was_moving:
            self.current_frame = 1
        self.image = self.direction[int(self.current_frame)]

    def update(self):
        if not self.is_moving:  #   Здешний update работает только когда персонаж двигается
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
            if self.current_frame >= 5:
                self.current_frame = 1
            self.image = self.direction[int(self.current_frame)]

        self.rect.midbottom = (int(self.x), int(self.y) + self.game_map.tile_size // 2) #   Держим ноги внизу чтобы не улетели

    def draw(self, screen, cam_x=0, cam_y=0):
        draw_rect = self.rect.move(-cam_x, -cam_y)
        screen.blit(self.image, draw_rect)

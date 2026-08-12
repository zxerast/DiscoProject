import pygame
import math
import sys
import os
from player import Player
from locations.awaken_chamber import room as awaken_chamber
from locations.second import room as second_room
from dialogue import DialogueWindow, load_dialogue
from skills import SkillsWindow
from inventory import InventoryWindow
from chest import ChestWindow
from settings import get_uniform_scale, SAVE_DIR, BASE_DIR
from utils import FONT_PATH, find_hovered
from dice import SkillCheck
from quests import QuestsWindow, load_quests_catalog, QuestManager
from action_bar import ActionBar
from save_manager import ensure_initial_save, get_saved_location, json_file, load_rooms_state, save_game, SAVE_PLAYER_PATH
from combat_manager import CombatManager


rooms = {
    "awaken_chamber": awaken_chamber,
    "second": second_room,
}

START_LOCATION = "awaken_chamber"

DEATH_FADE_MS = 2000
DEATH_TITLE_FADE_MS = 1400
DEATH_CONTINUE_DELAY_MS = 1000
DEATH_CONTINUE_FADE_MS = 800
START_FADE_MS = 1800
INITIAL_SKILL_POINTS = 8
INITIAL_SKILL_SETUP_FLAG = "initial_skill_setup_done"


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Disco")

        self.sw, self.sh = self.screen.get_size()   #   Размер экрана
        self.scale = get_uniform_scale(self.screen)

        self.clock = pygame.time.Clock()
        self.running = True

        self.startup_state = "main_menu"    #   Открываем окно загрузки игры
        self.start_fade_started_at = 0
        self.main_button_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_button_rect = pygame.Rect(0, 0, 0, 0)
        self.start_menu_font = pygame.font.Font(FONT_PATH, int(42 * self.scale))
        self.save_existed_on_launch = os.path.isdir(SAVE_DIR)
        self.pause_active = False

        self.current_map = None
        self.player = None
        self.camera_x = 0
        self.camera_y = 0

        self.camera_free = False
        self.camera_speed = 10 * self.scale        # Скорость свободного полета
        self.max_camera_offset = 500 * self.scale  # Максимальное расстояние от игрока (можно настроить вручную)

        self.dialogue_active = False    #   Сейчас в диалоге?
        self.dialogue = None    #   Окно диалога
        self.dialogue_source_pos = None
        self.pending_dialogue = False   #   Нужно ли открыть диалог по достижении цели?
        self.pending_dialogue_id = None #   Какой диалог открыть
        self.pending_dialogue_pos = None
        self.pending_chest = None
        self.pending_door = None
        self.pending_save = False
        self.chest_window = None
        self.pending_interaction_target = None

        self.waypoint = pygame.transform.scale(pygame.image.load(os.path.join(BASE_DIR, "assets", "actions", "waypoint.png")).convert_alpha(), (32 * self.scale, 32 * self.scale))
        self.active_waypoint_pos = None 
        self.preview_path = []           # Тайлы для превью маршрута
        self.preview_waypoint_pos = None # Координаты waypoint для курсора

        self.menu_active = False        # Открыто ли меню (табы)?
        self.menu_tab = 0               # 0=Навыки, 1=Инвентарь, 2=Задания

        self.skills_window = None
        self.inventory_window = None
        self.quests_window = None
        self.menu_windows = []

        # Табы вверху меню
        self._init_tabs()

        self.skill_check = False    #   Открыто ли окно с кубиком
        self.dice_window = SkillCheck(self.screen, self.scale)
        self.hud_font = pygame.font.Font(FONT_PATH, int(28 * self.scale))
        self.death_active = False
        self.death_started_at = 0
        self.death_title_font = pygame.font.Font(FONT_PATH, int(96 * self.scale))
        self.death_continue_font = pygame.font.Font(FONT_PATH, int(36 * self.scale))
        self.death_continue_rect = pygame.Rect(0, 0, 0, 0)

    def _start_selected_game(self):     #   Запускаем игру
        if self.save_existed_on_launch:
            ensure_initial_save(rooms)  #   Запускаем с последнего сейва
        else:                           
            ensure_initial_save(rooms)      #   Запускаем новую игру
            player_data = json_file(SAVE_PLAYER_PATH)
            player_data["level"] = 1
            player_data["skill_points"] = INITIAL_SKILL_POINTS
            player_data.setdefault("flags", {})
            player_data["flags"][INITIAL_SKILL_SETUP_FLAG] = False
            json_file(SAVE_PLAYER_PATH, player_data)

        load_rooms_state(rooms)
        location = self._get_saved_location()
        self.current_map = rooms[location]
        self.current_map.set_scale(self.scale)

        self.player = Player(self.current_map, self.screen, self.scale, save_path=SAVE_PLAYER_PATH) #   Ставим игрока
        self.player.location = location

        catalog = load_quests_catalog()
        self.quest_manager = QuestManager(self.player, catalog)
        self.player.quest_manager = self.quest_manager # Внедряем зависимость в игрока

        self._rebuild_player_windows()
        self._reset_runtime_state()
        self.camera_x = self.player.x - self.sw // 2
        self.camera_y = self.player.y - self.sh // 2
        self.death_active = False

        if self.player is not None and self.player.flags.get(INITIAL_SKILL_SETUP_FLAG) is False:
            self.startup_state = "initial_skills"
            self.menu_active = True
            self.menu_tab = 0
            self.chest_window = None
            return

        self._start_intro_fade()

    def _start_intro_fade(self):
        self.startup_state = "fade_to_game"
        self.start_fade_started_at = pygame.time.get_ticks()
        self._reset_runtime_state()

    def _finish_initial_skill_setup(self):
        if self.player.flags.get(INITIAL_SKILL_SETUP_FLAG) is True or self.player.skill_points > 0:
            return

        self.skills_window.confirm()
        self.player.flags[INITIAL_SKILL_SETUP_FLAG] = True
        save_game(self.player, rooms)
        self._start_intro_fade()

    def _change_room(self, door):
        target_location = door["target"]    #   Куда переносит дверь
        target_map = rooms[target_location]
        target_map.set_scale(self.scale)
        spawn_x, spawn_y = door["spawn"]

        self.current_map = target_map
        self.player.set_map_position(target_map, spawn_x, spawn_y, target_location)
        self.camera_x = self.player.x - self.sw // 2
        self.camera_y = self.player.y - self.sh // 2
        self.chest_window = None
        self.pending_chest = None
        self.pending_save = False
        self.pending_dialogue = False
        self.pending_dialogue_id = None
        self.pending_dialogue_pos = None
        self.dialogue_source_pos = None

    def _reset_runtime_state(self):     #   Сброс всех состояний
        self.dialogue_active = False
        self.dialogue = None
        self.dialogue_source_pos = None
        self.pending_dialogue = False
        self.pending_dialogue_id = None
        self.pending_dialogue_pos = None
        self.pending_chest = None
        self.pending_door = None
        self.pending_save = False
        self.pending_interaction_target = None
        self.chest_window = None
        self.menu_active = False
        self.menu_tab = 0
        self.skill_check = False
        self.pause_active = False
        self.pause_active = False
        self.camera_free = False  # <--- Сбрасываем режим свободной камеры
        self.active_waypoint_pos = None
        self.dice_window.reset()

    def _rebuild_player_windows(self):  #   После смерти игрока объект пересоздаётся поэтому мы заново привязываем к нему окна
        self.skills_window = SkillsWindow(self.screen, self.player, self.scale)
        self.inventory_window = InventoryWindow(self.screen, self.player, self.scale)
        self.quests_window = QuestsWindow(self.screen, self.player, self.scale)
        self.menu_windows = [self.skills_window, self.inventory_window, self.quests_window]
        self.action_bar = ActionBar(self.screen, self.player, self.scale, self.inventory_window, cam_centerer = self._center_camera_on_player)
        self.combat_manager = CombatManager(self.player, self.scale)
        self.player.combat_manager = self.combat_manager

    def _get_saved_location(self):
        location = get_saved_location(START_LOCATION)
        if location in rooms:
            return location
        return START_LOCATION

    def _reload_player_from_save(self): #   Загружаемся из сейва
        load_rooms_state(rooms)
        location = self._get_saved_location()
        self.current_map = rooms[location]
        self.current_map.set_scale(self.scale)
        self.player = Player(self.current_map, self.screen, self.scale, save_path=SAVE_PLAYER_PATH) #   Пересоздаём игрока
        self.player.location = location
        catalog = load_quests_catalog()
        self.quest_manager = QuestManager(self.player, catalog)
        self.player.quest_manager = self.quest_manager
        self._rebuild_player_windows()
        self._reset_runtime_state()     #   Сбрасываем состояния
        self.camera_x = self.player.x - self.sw // 2
        self.camera_y = self.player.y - self.sh // 2
        self.action_bar.player = self.player
        self.death_active = False

    def _start_death_screen(self):  #   Умерли
        self.death_active = True
        self.death_started_at = pygame.time.get_ticks()
        self._reset_runtime_state()

    def _save_at_bonfire(self):     #   Сохранились
        self.player.save_path = SAVE_PLAYER_PATH
        save_game(self.player, rooms)   #   save manager -> сохранение прогресса

    def _death_continue_visible(self):  #   Экран смерти
        elapsed = pygame.time.get_ticks() - self.death_started_at
        return elapsed >= DEATH_FADE_MS + DEATH_TITLE_FADE_MS + DEATH_CONTINUE_DELAY_MS

    def _init_tabs(self):
        size = self.scale

        # Базовое (оригинальное) разрешение всех ассетов
        BASE_W = 960
        BASE_H = 540

        # Высчитываем реальный размер игровой зоны на текущем экране
        game_w = int(BASE_W * size)
        game_h = int(BASE_H * size)

        # Считаем отступы, чтобы центрировать базовую зону (полезно для 16:10, 21:9 и т.д.)
        offset_x = (self.sw - game_w) // 2
        offset_y = (self.sh - game_h) // 2

        self.tab_names = ["Skills", "Inventory", "Quests"]

        # ---------- Размеры вкладок ----------
        TAB_W = int(233 * size)
        TAB_H = int(50 * size)
        TAB_GAP = int(17 * size)

        # Координаты теперь считаются относительно отцентрированной игровой зоны.
        # Заменили 45 на 15, так как настоящий отступ в оригинале был именно таким!
        start_x = offset_x + int(100 * size)
        start_y = offset_y + int(15 * size) 

        # ---------- Шрифт ----------
        self.tab_font = pygame.font.Font(FONT_PATH, int(25 * size))

        # ---------- Прямоугольники ----------
        self.tab_rects = []

        for i in range(3):
            rect = pygame.Rect(
                start_x + i * (TAB_W + TAB_GAP),
                start_y,
                TAB_W,
                TAB_H,
            )
            self.tab_rects.append(rect)
    
    def _draw_tabs(self):   #   Рисует 3 таба вверху экрана.
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.tab_rects):
            # Цвет надписи: выбранный — чёрный, hover — белый, обычный — жёлтый
            if i == self.menu_tab:
                color = (0, 0, 0)
            elif rect.collidepoint(mouse_pos):
                color = (255, 255, 255)
            else:
                color = (215, 161, 37)

            label = self.tab_font.render(self.tab_names[i], True, color)
            lx = rect.x + (rect.w - label.get_width()) // 2
            ly = rect.y + (rect.h - label.get_height()) // 2
            # Тень только для невыделенных вкладок

            if i != self.menu_tab:
                shadow = self.tab_font.render(self.tab_names[i], True, (0, 0, 0))
                self.screen.blit(shadow, (lx + 2 * self.scale, ly + 1 * self.scale))

            self.screen.blit(label, (lx, ly))

    def _draw_start_button(self, rect, text):
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        border = (255, 200, 0) if hovered else (120, 120, 120)
        text_color = (255, 220, 80) if hovered else (230, 230, 230)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=4)
        label = self.start_menu_font.render(text, True, text_color)
        label_rect = label.get_rect(center=rect.center)
        self.screen.blit(label, label_rect)

    def _draw_black_button_menu(self, main_text):
        self.screen.fill((0, 0, 0))
        scale = self.scale
        min_button_w = int(360 * scale)
        max_text_w = max(self.start_menu_font.size(main_text)[0], self.start_menu_font.size("Выход")[0])
        button_w = max(min_button_w, max_text_w + int(90 * scale))
        button_w = min(button_w, self.sw - int(80 * scale))
        button_h = int(82 * scale)
        gap = int(28 * scale)
        start_y = self.sh // 2 - button_h - gap // 2
        x = (self.sw - button_w) // 2

        self.main_button_rect = pygame.Rect(x, start_y, button_w, button_h)
        self.exit_button_rect = pygame.Rect(x, start_y + button_h + gap, button_w, button_h)

        self._draw_start_button(self.main_button_rect, main_text)
        self._draw_start_button(self.exit_button_rect, "Выход")

    def _draw_start_menu(self):
        main_text = "Продолжить" if self.save_existed_on_launch else "Новая игра"
        self._draw_black_button_menu(main_text)

    def _draw_pause_menu(self):
        self._draw_black_button_menu("Загрузиться с сохранения")

    def _draw_start_fade(self):
        elapsed = pygame.time.get_ticks() - self.start_fade_started_at
        if elapsed >= START_FADE_MS:
            return

        alpha = 255 - self._fade_value(elapsed, 0, START_FADE_MS)
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

    def _center_camera_on_player(self):     #Метод для центрирования камеры на персонаже
        self.camera_free = False
        if self.player:
            self.camera_x = self.player.x - self.sw // 2
            self.camera_y = self.player.y - self.sh // 2

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # Нажатие кнопки в главном меню
            if self.startup_state == "main_menu":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    continue
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.main_button_rect.collidepoint(event.pos):
                        self._start_selected_game()
                    elif self.exit_button_rect.collidepoint(event.pos):
                        self.running = False
                continue

            # Первичное распределение навыков
            if self.startup_state == "initial_skills":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                    self._finish_initial_skill_setup()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.skills_window.handle_click(event.pos)
                continue

            # Первичное появление
            if self.startup_state == "fade_to_game":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.startup_state = "game"
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.action_bar.is_targeting:
                        self.action_bar.selected_action = None
                        self.action_bar.is_targeting = False
                        self.action_bar.weapon_select_mode = False

                    elif not self.death_active:
                        self.pause_active = not self.pause_active
                    continue

                elif event.key == pygame.K_e:
                    self.player.add_xp(1000)

                elif event.key == pygame.K_q:
                    print("Текущие квесты:", self.player.active_quests)
                    print("Полученные флаги:", self.player.flags)

                elif event.key == pygame.K_F6 and not self.pause_active:
                    # Быстрая загрузка
                    self._reload_player_from_save()
                    continue

                elif event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d) and not self.dialogue_active:
                    self.camera_free = True  # Отвязываем камеру при нажатии WASD

                elif event.key == pygame.K_c:  # Кнопка для вызова метода центрирования
                    self._center_camera_on_player()
                    continue

                elif event.key == pygame.K_TAB:
                    if self.menu_active:
                        self.skills_window.confirm()    #   Закрыли меню и подтвердили распределение очков
                    self.menu_active = not self.menu_active
                    if self.menu_active:
                        self.chest_window = None
                        self.menu_tab = 0  # открываем на вкладке навыков
                    continue
                
                elif event.key == pygame.K_f and not self.pause_active and not self.dialogue_active:
                    if hasattr(self, 'combat_manager'):
                        self.combat_manager.toggle_mode()
                    continue

            if self.pause_active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.main_button_rect.collidepoint(event.pos):
                        self._reload_player_from_save()
                        self.pause_active = False

                    elif self.exit_button_rect.collidepoint(event.pos):
                        self.running = False

                continue

            if self.death_active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  #   Загрузка после смерти
                    if self._death_continue_visible() and self.death_continue_rect.collidepoint(event.pos):
                        self._reload_player_from_save()
                continue

            elif event.type == pygame.MOUSEWHEEL:
                if self.dialogue_active and self.dialogue:  #   Прокрутка в окне диалогов
                    self.dialogue.handle_scroll(event.y)
                elif self.menu_active and self.menu_tab == 2:
                    self.quests_window.handle_scroll(event.y)   #   Прорутка на вкладке квестов
                continue

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  #   Отпускание мыши в разных интерфейсах
                if self.dialogue_active and self.dialogue:
                    self.dialogue.handle_mouseup()
                elif self.chest_window:
                    self.chest_window.handle_mouseup(event.pos)
                elif self.menu_active and self.menu_tab == 1:
                    result = self.inventory_window.handle_mouseup(event.pos)
                    if isinstance(result, dict) and result.get("action") == "inspect":
                        dialogue_data = load_dialogue(result["dialogue_id"])
                        self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player, self.scale)
                        self.dialogue_source_pos = None
                        self.dialogue_active = True
                        self.menu_active = False
                elif self.menu_active and self.menu_tab == 2:
                    self.quests_window.handle_mouseup(event.pos)
                continue

            elif event.type == pygame.MOUSEMOTION:  #   Перемещение мыши в разных интерфейсах
                if self.dialogue_active and self.dialogue:
                    self.dialogue.handle_mousemotion(event.pos)
                elif self.chest_window:
                    self.chest_window.handle_mousemotion(event.pos)
                elif self.menu_active and self.menu_tab == 1:
                    self.inventory_window.handle_mousemotion(event.pos)
                elif self.menu_active and self.menu_tab == 2:
                    self.quests_window.handle_mousemotion(event.pos)
                elif hasattr(self, 'action_bar'): # <--- Новая строка
                    self.action_bar.handle_mousemotion(event.pos) # <--- Новая строка
                
                if not self.dialogue_active and not self.menu_active and not self.chest_window:
                    # Если мышь наведена на панель или идёт прицеливание — отключаем превью хода по тайлам
                    if hasattr(self, 'action_bar') and (self.action_bar.rect.collidepoint(event.pos) or self.action_bar.is_targeting):
                        self.player.preview_path = []
                    else:
                        world_x = event.pos[0] + self.camera_x
                        world_y = event.pos[1] + self.camera_y
                    
                        # Проверяем, в пошаговом ли мы режиме
                        max_ap = None
                        if hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based:
                            max_ap = self.combat_manager.current_ap
                        
                        self.player.update_preview(world_x, world_y, max_ap)

                
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:    #   Клик
                if self.skill_check:
                    self.dice_window.handle_click(event.pos)    #   Клик по кубику
                    continue

                if not self.dialogue_active and not self.menu_active and not self.skill_check:
                    if hasattr(self, 'action_bar'):
                        # Передаем координаты клика, позицию камеры и объект игрока для проверки прицеливания
                        res = self.action_bar.handle_mousedown(
                            event.pos, 
                            camera_x=self.camera_x, 
                            camera_y=self.camera_y, 
                            player_world_pos=(self.player.x, self.player.y)
                        )
                        if isinstance(res, dict) and res.get("target") == "player":
                            action_cost = res.get("cost", 0)
                            action_name = res.get("action")
                                
                            # Если идет пошаговый бой — проверяем и списываем AP
                            if hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based:
                                if self.combat_manager.current_ap >= action_cost:
                                    self.combat_manager.current_ap -= action_cost
                                    # --- ЗАГЛУШКА ЭФФЕКТА ДЕЙСТВИЯ ---
                                    print(f"[ЭФФЕКТ]: Применено действие '{action_name}' на игрока! Потрачено AP: {action_cost}")
                                else:
                                    print(f"[ОШИБКА]: Недостаточно AP для действия '{action_name}' (нужно {action_cost}, есть {self.combat_manager.current_ap})")
                            else:
                                # Вне пошагового боя
                                print(f"[ЭФФЕКТ]: Применено действие '{action_name}' на игрока (вне боя)!")

                        if res:
                            continue # Прерываем дальнейшую обработку, чтобы клик не ушел на тайлы карты

                if self.menu_active:            # Клик по табам
                    tab_clicked = False
                    for i, rect in enumerate(self.tab_rects):
                        if rect.collidepoint(event.pos):
                            if self.menu_tab == 0:
                                self.skills_window.confirm()
                            self.menu_tab = i
                            tab_clicked = True
                            break
                    if not tab_clicked:
                        if self.menu_tab == 1:
                            result = self.inventory_window.handle_mousedown(event.pos)  #   Решили осмотреть предмет в инвентаре
                            if isinstance(result, dict) and result.get("action") == "inspect":
                                dialogue_data = load_dialogue(result["dialogue_id"])
                                self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player, self.scale)
                                self.dialogue_source_pos = None
                                self.dialogue_active = True
                                self.menu_active = False
                        else:
                            if self.menu_tab == 0:  #   Не в инвентаре, обрабатываем по своему
                                self.skills_window.handle_click(event.pos)
                            elif self.menu_tab == 2:
                                self.quests_window.handle_mousedown(event.pos)
                    continue

                if self.dialogue_active:
                    choice = self.dialogue.handle_mousedown(event.pos, event.button)

                    if isinstance(choice, dict) and choice.get("action") == "change_tile":  #   Выбор реплики которая меняет тайл
                        self.current_map.change_tile(*self.dialogue_source_pos, choice["change_to"])
                        self.dialogue_active = False
                        self.dialogue = None
                        self.dialogue_source_pos = None
                        continue

                    if choice == "check":   #   Выбор реплики с активной проверкой
                        check = self.dialogue.pending_check
                        skill_name = check.get("skill")
                        skill_value = self.player.get_skill(skill_name) if skill_name else 0
                        self.dice_window.start_check(check["dc"], skill_name, skill_value)

                        # Добавляем условные модификаторы из диалога
                        for mod in check.get("modifiers", []):  #   Какие модификаторы могут быть
                            if self.player.get_flag(mod["flag"]):   #   Какие флаги у нас есть под них
                                self.dice_window.add_modifier(mod["label"], mod["value"])

                        self.skill_check = True
                        self.dialogue_active = False    # Прячем диалог на время броска


                    if choice == "close":
                        self.dialogue_active = False
                        self.dialogue = None
                        self.dialogue_source_pos = None
                    continue

                if self.chest_window and find_hovered(self.chest_window.cell_rects, event.pos) is not None:
                    self.chest_window.handle_mousedown(event.pos)
                    continue
                elif self.chest_window:
                    self.chest_window = None

                world_x = event.pos[0] + self.camera_x  #   event.pos - точка клика мыши
                world_y = event.pos[1] + self.camera_y
                clicked_sprite = self.current_map.get_interactive_sprite_at(event.pos, self.camera_x, self.camera_y)

                if not clicked_sprite:
                    self.chest_window = None
                    self.pending_chest = None
                    self.pending_door = None
                    self.pending_save = False
                    self.pending_dialogue = False   #   Если это обычная клетка
                    self.pending_dialogue_pos = None
                    self.pending_interaction_target = None
                    self.player.set_target(world_x, world_y)    #   То просто идём
                    
                    # 1. Проверяем очки действия (AP), если мы в бою
                    max_ap = None
                    if hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based:
                        max_ap = self.combat_manager.current_ap

                    # Переводим пиксели в координаты сетки
                    grid_x = int(world_x // self.current_map.tile_size)
                    grid_y = int(world_y // self.current_map.tile_size)
                    
                    # Получаем идеальный центр тайла клика
                    target_x, target_y = self.current_map.grid_to_pixel_center(grid_x, grid_y)

                    # 2. Идем в центр тайла (здесь желательно, чтобы set_target тоже принимал max_ap, 
                    # если обрезка пути происходит прямо там)
                    self.player.set_target(target_x, target_y)

                    # 3. Синхронизируем waypoint с РЕАЛЬНЫМ концом пути
                    if hasattr(self.player, 'path') and self.player.path:
                        last_gx, last_gy = self.player.path[-1]
                        real_target_x, real_target_y = self.current_map.grid_to_pixel_center(last_gx, last_gy)
                        self.active_waypoint_pos = (real_target_x, real_target_y)
                    else:
                        # Если пути нет (например, стоим на месте), ставим по старому методу
                        self.active_waypoint_pos = (target_x, target_y)
        
                    continue

                gx, gy = clicked_sprite["tile"]
                approach_x, approach_y = clicked_sprite["approach"]

                self.pending_dialogue = False
                self.pending_dialogue_id = None
                self.pending_dialogue_pos = None
                self.pending_chest = None
                self.pending_door = None
                self.pending_save = False
                self.pending_interaction_target = (approach_x, approach_y)
                is_turn_based = hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based

                if self.current_map.get_chest(gx, gy):
                    self.pending_chest = (gx, gy)

                elif self.current_map.get_door(gx, gy):
                    self.pending_door = self.current_map.get_door(gx, gy)

                elif self.current_map.get_dialogue_id(gx, gy):
                    if not is_turn_based: # <--- Запрет на вход в диалог в пошаговом режиме
                        self.pending_dialogue = True
                        self.pending_dialogue_id = self.current_map.get_dialogue_id(gx, gy)
                        self.pending_dialogue_pos = (gx, gy)
                    else:
                        # Если бой активен, сбрасываем цель, чтобы персонаж даже не пытался идти к NPC
                        self.pending_interaction_target = None

                # если в будущем появятся костры
                elif self.current_map.get_bonfire(gx, gy):
                    self.pending_save = True

                # Идем к цели только если она валидна
                if self.pending_interaction_target:
                    target = self.current_map.grid_to_pixel_center(approach_x, approach_y)
                    self.player.set_target(target[0], target[1])

                    # Синхронизируем waypoint с РЕАЛЬНЫМ концом пути (учитывая обрезку по AP)
                    if hasattr(self.player, 'path') and self.player.path:
                        last_gx, last_gy = self.player.path[-1]
                        real_target_x, real_target_y = self.current_map.grid_to_pixel_center(last_gx, last_gy)
                        self.active_waypoint_pos = (real_target_x, real_target_y)
                    else:
                        self.active_waypoint_pos = (target[0], target[1])

    def update(self):
        if self.startup_state == "main_menu":
            return

        if self.startup_state == "initial_skills":
            return

        if self.startup_state == "fade_to_game":
            elapsed = pygame.time.get_ticks() - self.start_fade_started_at
            if elapsed >= START_FADE_MS:
                self.startup_state = "game"
            return

        if self.pause_active:
            return

        if self.death_active:   #   Умерли
            return

        if self.player is None:
            return

        if self.player.health_points <= 0:  #   Умираем
            self._start_death_screen()
            return

        if self.skill_check:
            self.dice_window.update()       #   Проверяем свою удачу
            if self.dice_window.finished:
                check = self.dialogue.pending_check
                next_node = check[self.dice_window.check_result]
                self.dialogue.set_node(next_node)
                self.dialogue_active = True
                self.skill_check = False
                self.dice_window.reset()
            return

        if self.menu_active:
            return

        self.player.update()
        if self.player.is_moving:
            self.chest_window = None
            self.preview_path = []
            self.preview_waypoint_pos = None
        else: 
            self.active_waypoint_pos = None 

        if not self.camera_free:
            self.camera_x = self.player.x - self.sw // 2    #   Камера центрирована на игроке
            self.camera_y = self.player.y - self.sh // 2
        else:
            # Свободный полет камеры по WASD / стрелочкам
            keys = pygame.key.get_pressed()
            cam_dx = 0
            cam_dy = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                cam_dy -= self.camera_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                cam_dy += self.camera_speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                cam_dx -= self.camera_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                cam_dx += self.camera_speed
            
            self.camera_x += cam_dx
            self.camera_y += cam_dy

            # Ограничение максимального отдаления от персонажа вручную задаваемым радиусом
            cam_center_x = self.camera_x + self.sw // 2
            cam_center_y = self.camera_y + self.sh // 2
            
            dist = math.hypot(cam_center_x - self.player.x, cam_center_y - self.player.y)
            if dist > self.max_camera_offset:
                angle = math.atan2(cam_center_y - self.player.y, cam_center_x - self.player.x)
                limited_center_x = self.player.x + self.max_camera_offset * math.cos(angle)
                limited_center_y = self.player.y + self.max_camera_offset * math.sin(angle)
                
                self.camera_x = limited_center_x - self.sw // 2
                self.camera_y = limited_center_y - self.sh // 2

        # Обновленный блок обработки действий при остановке игрока
        if not self.player.is_moving:
            # Проверяем, дошел ли игрок до целевой клетки
            reached_target = True
            if hasattr(self, 'pending_interaction_target') and self.pending_interaction_target:
                tx, ty = self.pending_interaction_target
                # Сверяем координаты сетки игрока с координатами approach
                if self.player.grid_x != tx or self.player.grid_y != ty:
                    reached_target = False

            if self.pending_chest:
                if reached_target:
                    chest = self.current_map.get_chest(*self.pending_chest)
                    if chest:
                        self.chest_window = ChestWindow(self.screen, self.player, chest, self.pending_chest, self.scale)
                self.pending_chest = None
                self.pending_interaction_target = None

            if self.pending_door:
                if reached_target:
                    self._change_room(self.pending_door)
                self.pending_door = None
                self.pending_interaction_target = None

            if self.pending_save:
                if reached_target:
                    self._save_at_bonfire()
                self.pending_save = False
                self.pending_interaction_target = None

            if self.pending_dialogue:
                if reached_target:
                    dialogue_data = load_dialogue(self.pending_dialogue_id)
                    self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player, self.scale)
                    self.dialogue_source_pos = self.pending_dialogue_pos
                    self.dialogue_active = True
                    self._center_camera_on_player()
                self.pending_dialogue = False
                self.pending_dialogue_id = None
                self.pending_dialogue_pos = None
                self.pending_interaction_target = None

    def render(self):
        if self.startup_state == "main_menu":
            self._draw_start_menu()
            pygame.display.flip()
            return

        if self.startup_state == "initial_skills":
            self.skills_window.draw()
            pygame.display.flip()
            return

        if self.pause_active:
            self._draw_pause_menu()
            pygame.display.flip()
            return

        self.screen.fill((0, 0, 0)) #   Фон
        if self.current_map is None or self.player is None:
            pygame.display.flip()
            return

        self.current_map.draw(self.screen, self.camera_x, self.camera_y)    #   Карта
        self.current_map.draw_depth_layers(self.screen, self.player.y, False, self.camera_x, self.camera_y)

        # Отрисовка превью маршрута (линия и waypoint)
        if not self.action_bar.is_targeting and not self.player.is_moving and self.player.preview_path:
            # Отрисовка только если мы в пошаговом режиме (или можно оставить для обоих)
            if hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based:
                path_points = [(self.player.x - self.camera_x, self.player.y - self.camera_y)]
                
                for gx, gy in self.player.preview_path:
                    px, py = self.current_map.grid_to_pixel_center(gx, gy)
                    path_points.append((px - self.camera_x, py - self.camera_y))
                
                if len(path_points) > 1:
                    x1, y1 = path_points[0]
                    x2, y2 = path_points[1]

                    dx = x2 - x1
                    dy = y2 - y1

                    offset = 16 * self.scale
                    if abs(dx) > abs(dy):
                     # Горизонтальное движение
                        start_point = (x1 + offset * (1 if dx > 0 else -1), y1)
                    else:
                        # Вертикальное движение
                        start_point = (x1, y1 + offset * (1 if dy > 0 else -1))


                    x1, y1 = path_points[-2]
                    x2, y2 = path_points[-1]

                    dx = x2 - x1
                    dy = y2 - y1

                    if abs(dx) > abs(dy):
                    # Горизонтальное движение
                        end_point = (x2 - offset * (1 if dx > 0 else -1), y2)
                    else:
                        # Вертикальное движение
                        end_point = (x2, y2 - offset * (1 if dy > 0 else -1))

                    # Заменяем только первую и последнюю точки
                    path_points[0] = start_point
                    path_points[-1] = end_point
            
                    pygame.draw.lines(self.screen, (200, 200, 200), False, path_points, max(1, int(2 * self.scale)))

                # Отрисовка Waypoint на конце превью
                last_gx, last_gy = self.player.preview_path[-1]
                wp_px, wp_py = self.current_map.grid_to_pixel_center(last_gx, last_gy)
                wp_x = wp_px - self.camera_x - self.waypoint.get_width() // 2
                wp_y = wp_py - self.camera_y - self.waypoint.get_height() // 2
                self.screen.blit(self.waypoint, (wp_x, wp_y))
            
        # Отрисовка Waypoint во время самого движения (если кликнули)
        elif self.active_waypoint_pos:
            wp_x = self.active_waypoint_pos[0] - self.camera_x - self.waypoint.get_width() // 2
            wp_y = self.active_waypoint_pos[1] - self.camera_y - self.waypoint.get_height() // 2
            self.screen.blit(self.waypoint, (wp_x, wp_y))
            
            # Отрисовка линии реального пути за спиной (по желанию)
            if hasattr(self, 'combat_manager') and self.combat_manager.is_turn_based and self.player.path:
                path_points = [(self.player.x - self.camera_x, self.player.y - self.camera_y)]
                for gx, gy in self.player.path:
                    px, py = self.current_map.grid_to_pixel_center(gx, gy)
                    path_points.append((px - self.camera_x, py - self.camera_y))
                if len(path_points) > 1:
                    x1, y1 = path_points[0]
                    x2, y2 = path_points[1]

                    dx = x2 - x1
                    dy = y2 - y1

                    offset = 16 * self.scale
                    if abs(dx) > abs(dy):
                     # Горизонтальное движение
                        start_point = (x1 + offset * (1 if dx > 0 else -1), y1)
                    else:
                        # Вертикальное движение
                        start_point = (x1, y1 + offset * (1 if dy > 0 else -1))


                    x1, y1 = path_points[-2]
                    x2, y2 = path_points[-1]

                    dx = x2 - x1
                    dy = y2 - y1

                    if abs(dx) > abs(dy):
                    # Горизонтальное движение
                        end_point = (x2 - offset * (1 if dx > 0 else -1), y2)
                    else:
                        # Вертикальное движение
                        end_point = (x2, y2 - offset * (1 if dy > 0 else -1))

                    # Заменяем только первую и последнюю точки
                    path_points[0] = start_point
                    path_points[-1] = end_point
            

                    pygame.draw.lines(self.screen, (150, 150, 150), False, path_points, max(1, int(2 * self.scale)))

        if self.action_bar.is_targeting:
            player_screen_pos = (self.player.rect.centerx - self.camera_x, self.player.rect.centery - self.camera_y)
            pygame.draw.line(self.screen, (255, 255, 255), player_screen_pos, pygame.mouse.get_pos(), width=2)

        self.player.draw(self.screen, self.camera_x, self.camera_y) #   Игрок

        if self.action_bar.is_targeting:
            mouse_pos = pygame.mouse.get_pos()
            player_screen_rect = self.player.rect.move(-self.camera_x, -self.camera_y)
            
            # Если мышь наведена на игрока — рисуем контур с помощью маски
            if player_screen_rect.collidepoint(mouse_pos):
                mask = pygame.mask.from_surface(self.player.image)
                for pt in mask.outline():
                    x = pt[0] + player_screen_rect.x
                    y = pt[1] + player_screen_rect.y
                    self.screen.set_at((x, y), (255, 255, 255))

        self.current_map.draw_depth_layers(self.screen, self.player.y, True, self.camera_x, self.camera_y)
        if not self.dialogue_active and not self.menu_active and not self.chest_window:
            self.current_map.draw_hover_outline(self.screen, pygame.mouse.get_pos(), self.camera_x, self.camera_y)

        if self.dialogue_active and self.dialogue:  #   Диалоговое окно
            self.dialogue.draw()

        if self.chest_window and not self.player.is_moving:
            self.chest_window.draw(self.camera_x, self.camera_y, self.current_map.tile_size)

        if not self.dialogue_active and not self.menu_active and not self.skill_check:
            self.action_bar.draw(camera_x=self.camera_x, camera_y=self.camera_y)
            if hasattr(self, 'combat_manager'):
                preview_cost = 0
                if self.combat_manager.is_turn_based:
                    if self.action_bar.is_targeting:
                        # В режиме выбора действия передаем стоимость выбранного действия
                        preview_cost = self.action_bar.get_selected_action_cost()
                    elif self.player.is_moving:
                        # Во время движения показываем оставшиеся шаги текущего маршрута
                        preview_cost = max(0, len(self.player.path) - 1)
                    else:
                        # При наведении покажем стоимость планируемого пути
                        preview_cost = len(self.player.preview_path)
                self.combat_manager.draw(self.screen, preview_cost=preview_cost)

        if self.menu_active:  #   Окно меню (навыки/инвентарь/задания)
            self.menu_windows[self.menu_tab].draw()
            self._draw_tabs()

        if self.skill_check:   #   Окно броска кубика
            self.dice_window.draw()

        if self.death_active:
            self._draw_death_screen()

        if self.startup_state == "fade_to_game":
            self._draw_start_fade()

        pygame.display.flip()

    def _fade_value(self, elapsed, start_ms, duration_ms):
        return max(0, min(255, int((elapsed - start_ms) / duration_ms * 255)))

    def _draw_death_screen(self):
        elapsed = pygame.time.get_ticks() - self.death_started_at

        black_alpha = self._fade_value(elapsed, 0, DEATH_FADE_MS)
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, black_alpha))
        self.screen.blit(overlay, (0, 0))

        title_alpha = self._fade_value(elapsed, DEATH_FADE_MS, DEATH_TITLE_FADE_MS)
        if title_alpha > 0:
            title = self.death_title_font.render("You died", True, (170, 0, 0))
            title.set_alpha(title_alpha)
            title_rect = title.get_rect(center=(self.sw // 2, self.sh // 2 - int(48 * self.scale)))
            self.screen.blit(title, title_rect)

        continue_start = DEATH_FADE_MS + DEATH_TITLE_FADE_MS + DEATH_CONTINUE_DELAY_MS
        continue_alpha = self._fade_value(elapsed, continue_start, DEATH_CONTINUE_FADE_MS)
        if continue_alpha > 0:
            label = self.death_continue_font.render("продолжить?", True, (170, 0, 0))
            label.set_alpha(continue_alpha)
            self.death_continue_rect = label.get_rect(
                center=(self.sw // 2, self.sh // 2 + int(56 * self.scale))
            )
            self.screen.blit(label, self.death_continue_rect)
        else:
            self.death_continue_rect = pygame.Rect(0, 0, 0, 0)

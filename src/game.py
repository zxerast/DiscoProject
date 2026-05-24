import pygame
import sys
import os
from player import Player
from locations.awaken_chamber import room as awaken_chamber
from locations.second import room as second_room
from dialogue import DialogueWindow, load_dialogue
from skills import SkillsWindow
from inventory import InventoryWindow
from quests import QuestsWindow
from chest import ChestWindow
from settings import get_uniform_scale, SAVE_DIR
from utils import MENU_NATIVE_W, MENU_NATIVE_H, FONT_PATH, find_hovered
from dice import SkillCheck
from save_manager import ensure_initial_save, get_saved_location, json_file, load_rooms_state, save_game, SAVE_PLAYER_PATH


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

        self.clock = pygame.time.Clock()
        self.running = True

        self.startup_state = "main_menu"    #   Открываем окно загрузки игры
        self.start_fade_started_at = 0
        self.main_button_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_button_rect = pygame.Rect(0, 0, 0, 0)
        self.start_menu_font = pygame.font.Font(FONT_PATH, int(42 * get_uniform_scale(self.screen)))
        self.save_existed_on_launch = os.path.isdir(SAVE_DIR)
        self.pause_active = False

        self.current_map = None
        self.player = None
        self.camera_x = 0
        self.camera_y = 0

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

        self.menu_active = False        # Открыто ли меню (табы)?
        self.menu_tab = 0               # 0=Навыки, 1=Инвентарь, 2=Задания

        self.skills_window = None
        self.inventory_window = None
        self.quests_window = None
        self.menu_windows = []

        # Табы вверху меню
        self._init_tabs()

        self.skill_check = False    #   Открыто ли окно с кубиком
        self.dice_window = SkillCheck(self.screen)
        self.hud_font = pygame.font.Font(FONT_PATH, int(28 * get_uniform_scale(self.screen)))
        self.death_active = False
        self.death_started_at = 0
        self.death_title_font = pygame.font.Font(FONT_PATH, int(96 * get_uniform_scale(self.screen)))
        self.death_continue_font = pygame.font.Font(FONT_PATH, int(36 * get_uniform_scale(self.screen)))
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
        self.current_map.set_scale(get_uniform_scale(self.screen))

        self.player = Player(self.current_map, self.screen, save_path=SAVE_PLAYER_PATH) #   Ставим игрока
        self.player.location = location
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
        target_map.set_scale(get_uniform_scale(self.screen))
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
        self.chest_window = None
        self.menu_active = False
        self.menu_tab = 0
        self.skill_check = False
        self.pause_active = False
        self.dice_window.reset()

    def _rebuild_player_windows(self):  #   После смерти игрока объект пересоздаётся поэтому мы заново привязываем к нему окна
        self.skills_window = SkillsWindow(self.screen, self.player)
        self.inventory_window = InventoryWindow(self.screen, self.player)
        self.quests_window = QuestsWindow(self.screen, self.player)
        self.menu_windows = [self.skills_window, self.inventory_window, self.quests_window]

    def _get_saved_location(self):
        location = get_saved_location(START_LOCATION)
        if location in rooms:
            return location
        return START_LOCATION

    def _reload_player_from_save(self): #   Загружаемся из сейва
        load_rooms_state(rooms)
        location = self._get_saved_location()
        self.current_map = rooms[location]
        self.current_map.set_scale(get_uniform_scale(self.screen))
        self.player = Player(self.current_map, self.screen, save_path=SAVE_PLAYER_PATH) #   Пересоздаём игрока
        self.player.location = location
        self._rebuild_player_windows()
        self._reset_runtime_state()     #   Сбрасываем состояния
        self.camera_x = self.player.x - self.sw // 2
        self.camera_y = self.player.y - self.sh // 2
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

    def _init_tabs(self):   #   Создаёт прямоугольники и текстовые поверхности для 3 табов.
        size = min(self.sw / MENU_NATIVE_W, self.sh / MENU_NATIVE_H)
        menu_w = int(MENU_NATIVE_W * size)
        menu_h = int(MENU_NATIVE_H * size)
        offset_x = (self.sw - menu_w) // 2
        offset_y = (self.sh - menu_h) // 2

        tab_names = ["Навыки  ", "  Инвентарь ", "  Задания"]

        tab_h = int(111 * size)
        tab_gap = int(21 * size)
        tab_y = offset_y + int(17 * size)

        self.tab_font = pygame.font.Font(FONT_PATH, int(50 * size))
        self.tab_names = tab_names

        # Ширина каждого таба подгоняется под текст + отступы
        padding = int(40 * size)
        self.tab_rects = []
        x = offset_x + int(270 * size)
        for name in tab_names:
            text_w = self.tab_font.size(name)[0]
            tab_w = text_w + padding * 2
            rect = pygame.Rect(x, tab_y, tab_w, tab_h)
            self.tab_rects.append(rect)
            x += tab_w + tab_gap

    def _draw_tabs(self):   #   Рисует 3 таба вверху экрана.
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.tab_rects):
            # Цвет надписи: выбранный — чёрный, hover — белый, обычный — жёлтый
            if i == self.menu_tab:
                color = (0, 0, 0)
            elif rect.collidepoint(mouse_pos):
                color = (255, 255, 255)
            else:
                color = (255, 200, 0)

            label = self.tab_font.render(self.tab_names[i], True, color)
            lx = rect.x + (rect.w - label.get_width()) // 2
            ly = rect.y + (rect.h - label.get_height()) // 2
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
        scale = get_uniform_scale(self.screen)
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

            if self.startup_state == "main_menu":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    continue
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.main_button_rect.collidepoint(event.pos):
                        self._start_selected_game()
                    elif self.exit_button_rect.collidepoint(event.pos):
                        self.running = False
                continue

            if self.startup_state == "initial_skills":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                    self._finish_initial_skill_setup()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.skills_window.handle_click(event.pos)
                continue

            if self.startup_state == "fade_to_game":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.startup_state = "game"
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: 
                if not self.death_active:
                    self.pause_active = not self.pause_active
                continue

            if self.pause_active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.main_button_rect.collidepoint(event.pos):
                        self._reload_player_from_save()
                        self.pause_active = False
                    elif self.exit_button_rect.collidepoint(event.pos):
                        self.running = False
                continue

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F6: #   Быстрая загрузка по F6
                self._reload_player_from_save()
                continue

            if self.death_active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  #   Загрузка после смерти
                    if self._death_continue_visible() and self.death_continue_rect.collidepoint(event.pos):
                        self._reload_player_from_save()
                continue

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                if self.menu_active:
                    self.skills_window.confirm()    #   Закрыли меню и подтвердили распределение очков
                self.menu_active = not self.menu_active
                if self.menu_active:
                    self.chest_window = None
                    self.menu_tab = 0  # открываем на вкладке навыков
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
                        self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
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
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:    #   Клик
                if self.skill_check:
                    self.dice_window.handle_click(event.pos)    #   Клик по кубику
                    continue

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
                                self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
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
                    self.player.set_target(world_x, world_y)    #   То просто идём
                    continue

                gx, gy = clicked_sprite["tile"]
                approach_x, approach_y = clicked_sprite["approach"]
                if not self.current_map.is_interactive(gx, gy):
                    continue

                self.pending_dialogue = False
                self.pending_dialogue_id = None
                self.pending_dialogue_pos = None
                self.pending_chest = None
                self.pending_door = None
                self.pending_save = False

                if self.current_map.is_chest(gx, gy):
                    self.pending_chest = (gx, gy)
                elif self.current_map.is_door(gx, gy):
                    self.pending_door = self.current_map.get_door(gx, gy)
                elif self.current_map.is_bonfire(gx, gy):
                    self.pending_save = True
                else:
                    self.pending_dialogue = True    # То откроем диалог
                    self.pending_dialogue_id = self.current_map.get_dialogue_id(gx, gy)  # Запоминаем какой
                    self.pending_dialogue_pos = (gx, gy)

                target = self.current_map.grid_to_pixel_center(approach_x, approach_y)
                self.player.set_target(target[0], target[1])    #   Мы готовы идти, пошли

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
        self.camera_x = self.player.x - self.sw // 2    #   Камера у нас центрирована
        self.camera_y = self.player.y - self.sh // 2

        if self.pending_chest and not self.player.is_moving:    #   Сундук открыт пока мы стоим
            chest = self.current_map.get_chest(*self.pending_chest)
            if chest:
                self.chest_window = ChestWindow(self.screen, self.player, chest, self.pending_chest)
            self.pending_chest = None

        if self.pending_door and not self.player.is_moving: #   На подходе к двери переносимся
            self._change_room(self.pending_door)
            self.pending_door = None

        if self.pending_save and not self.player.is_moving: #   На подходе к сейвруму -> сейвимся, вот это да
            self._save_at_bonfire()
            self.pending_save = False

        if self.pending_dialogue and not self.player.is_moving: #   Грузим окно диалога
            dialogue_data = load_dialogue(self.pending_dialogue_id)
            self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
            self.dialogue_source_pos = self.pending_dialogue_pos
            self.dialogue_active = True
            self.pending_dialogue = False
            self.pending_dialogue_id = None
            self.pending_dialogue_pos = None

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
        self.player.draw(self.screen, self.camera_x, self.camera_y) #   Игрок
        self.current_map.draw_depth_layers(self.screen, self.player.y, True, self.camera_x, self.camera_y)
        if not self.dialogue_active and not self.menu_active and not self.chest_window:
            self.current_map.draw_hover_outline(self.screen, pygame.mouse.get_pos(), self.camera_x, self.camera_y)

        if self.dialogue_active and self.dialogue:  #   Диалоговое окно
            self.dialogue.draw()

        if self.chest_window and not self.player.is_moving:
            self.chest_window.draw(self.camera_x, self.camera_y, self.current_map.tile_size)

        self._draw_hud()

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
            title_rect = title.get_rect(center=(self.sw // 2, self.sh // 2 - int(48 * get_uniform_scale(self.screen))))
            self.screen.blit(title, title_rect)

        continue_start = DEATH_FADE_MS + DEATH_TITLE_FADE_MS + DEATH_CONTINUE_DELAY_MS
        continue_alpha = self._fade_value(elapsed, continue_start, DEATH_CONTINUE_FADE_MS)
        if continue_alpha > 0:
            label = self.death_continue_font.render("продолжить?", True, (170, 0, 0))
            label.set_alpha(continue_alpha)
            self.death_continue_rect = label.get_rect(
                center=(self.sw // 2, self.sh // 2 + int(56 * get_uniform_scale(self.screen)))
            )
            self.screen.blit(label, self.death_continue_rect)
        else:
            self.death_continue_rect = pygame.Rect(0, 0, 0, 0)

    def _draw_hud(self):
        pad = int(24 * get_uniform_scale(self.screen))
        xp_text = f"{self.player.xp_points}/{self.player.xp_cap}"
        hp_text = str(self.player.health_points)

        xp_surf = self.hud_font.render(xp_text, True, (255, 255, 255))
        hp_surf = self.hud_font.render(hp_text, True, (220, 30, 30))

        hp_x = pad
        hp_y = self.sh - pad - hp_surf.get_height()
        xp_x = pad
        xp_y = hp_y - xp_surf.get_height() - int(4 * get_uniform_scale(self.screen))

        self.screen.blit(xp_surf, (xp_x, xp_y))
        self.screen.blit(hp_surf, (hp_x, hp_y))

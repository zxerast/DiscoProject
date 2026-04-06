import pygame
import sys
from player import Player
from locations.test import room
from dialogue import DialogueWindow, load_dialogue
from skills import SkillsWindow
from inventory import InventoryWindow
from quests import QuestsWindow
from settings import BASE_WIDTH, BASE_HEIGHT
from utils import MENU_NATIVE_W, MENU_NATIVE_H, FONT_PATH
from dice import SkillCheck


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Disco")

        self.sw, self.sh = self.screen.get_size()

        self.clock = pygame.time.Clock()
        self.running = True

        self.current_map = room
        self.player = Player(1, 1, self.current_map, self.screen)

        self.camera_x = 0
        self.camera_y = 0

        self.dialogue_active = False    #   Сейчас в диалоге?
        self.dialogue = None    #   Окно диалога
        self.pending_dialogue = False   #   Нужно ли открыть диалог по достижении цели?
        self.pending_dialogue_id = None #   Какой диалог открыть

        self.menu_active = False        # Открыто ли меню (табы)?
        self.menu_tab = 0               # 0=Навыки, 1=Инвентарь, 2=Задания
        self.skills_active = False      # alias для обратной совместимости

        self.skills_window = SkillsWindow(self.screen, self.player)
        self.inventory_window = InventoryWindow(self.screen, self.player)
        self.quests_window = QuestsWindow(self.screen, self.player)

        self.menu_windows = [self.skills_window, self.inventory_window, self.quests_window]

        # Табы вверху меню
        self._init_tabs()

        self.skill_check = False    #   Открыто ли окно с кубиком
        self.dice_window = SkillCheck(self.screen)

    def _init_tabs(self):   #   Создаёт прямоугольники и текстовые поверхности для 3 табов.
        size = min(self.sw / MENU_NATIVE_W, self.sh / MENU_NATIVE_H)

        tab_names = ["Навыки  ", "  Инвентарь ", "  Задания"]

        tab_h = int(111 * size)
        tab_gap = int(21 * size)
        tab_y = int(17 * size)

        self.tab_font = pygame.font.Font(FONT_PATH, int(50 * size))
        self.tab_names = tab_names

        # Ширина каждого таба подгоняется под текст + отступы
        padding = int(40 * size)
        self.tab_rects = []
        x = int(270 * size)
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

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
                continue

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                if self.menu_active:
                    self.skills_window.confirm()
                self.menu_active = not self.menu_active
                self.skills_active = self.menu_active
                if self.menu_active:
                    self.menu_tab = 0  # открываем на вкладке навыков
                continue


            elif event.type == pygame.KEYDOWN and event.scancode == pygame.KSCAN_E:
                self.player.level_up()
                continue

            # --- Прокрутка колёсиком в диалоге ---
            elif event.type == pygame.MOUSEWHEEL:
                if self.dialogue_active and self.dialogue:
                    self.dialogue.handle_scroll(event.y)
                continue

            # --- Отпускание кнопки мыши ---
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dialogue_active and self.dialogue:
                    self.dialogue.handle_mouseup()
                elif self.menu_active and self.menu_tab == 1:
                    result = self.inventory_window.handle_mouseup(event.pos)
                    if isinstance(result, dict) and result.get("action") == "inspect":
                        dialogue_data = load_dialogue(result["dialogue_id"])
                        self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
                        self.dialogue_active = True
                        self.menu_active = False
                        self.skills_active = False
                continue

            # --- Перемещение мыши ---
            elif event.type == pygame.MOUSEMOTION:
                if self.dialogue_active and self.dialogue:
                    self.dialogue.handle_mousemotion(event.pos)
                elif self.menu_active and self.menu_tab == 1:
                    self.inventory_window.handle_mousemotion(event.pos)
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.skill_check:
                    self.dice_window.handle_click(event.pos)
                    continue

                if self.menu_active:
                    # Проверяем клик по табам
                    tab_clicked = False
                    for i, rect in enumerate(self.tab_rects):
                        if rect.collidepoint(event.pos):
                            if self.menu_tab == 0:
                                self.skills_window.confirm()
                            self.menu_tab = i
                            self.skills_active = (i == 0)
                            tab_clicked = True
                            break
                    if not tab_clicked:
                        if self.menu_tab == 1:
                            result = self.inventory_window.handle_mousedown(event.pos)
                            if isinstance(result, dict) and result.get("action") == "inspect":
                                dialogue_data = load_dialogue(result["dialogue_id"])
                                self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
                                self.dialogue_active = True
                                self.menu_active = False
                                self.skills_active = False
                        else:
                            self.menu_windows[self.menu_tab].handle_click(event.pos)
                    continue

                if self.dialogue_active:
                    choice = self.dialogue.handle_mousedown(event.pos, event.button)

                    if choice == "check":
                        check = self.dialogue.pending_check
                        skill_name = check.get("skill")
                        skill_value = self.player.get_skill(skill_name) if skill_name else 0
                        self.dice_window.start_check(check["dc"], skill_name, skill_value)

                        # Добавляем условные модификаторы из диалога
                        for mod in check.get("modifiers", []):
                            if self.player.get_flag(mod["flag"]):
                                self.dice_window.add_modifier(mod["label"], mod["value"])

                        self.skill_check = True
                        self.dialogue_active = False    # Прячем диалог на время броска


                    if choice == "close":
                        self.dialogue_active = False
                        self.dialogue = None
                    continue

                world_x = event.pos[0] + self.camera_x  #   event.pos - точка клика мыши
                world_y = event.pos[1] + self.camera_y
                gx, gy = self.current_map.pixel_to_grid(world_x, world_y)   #   Переводим координаты клика в координаты комнаты

                if self.current_map.is_interactive(gx, gy): #   Если мы кликнули на интерактивный тайл
                    adjacent = self.current_map.get_adjacent_walkable(gx, gy)   #   Ближайшая проходимая клетка
                    if adjacent:    #   Когда придём
                        self.pending_dialogue = True    # То откроем диалог
                        self.pending_dialogue_id = self.current_map.get_dialogue_id(gx, gy)  # Запоминаем какой
                        target = self.current_map.grid_to_pixel_center(*adjacent)   #И встанем сюда
                        self.player.set_target(target[0], target[1])    #   Мы готовы идти, пошли
                else:
                    self.pending_dialogue = False   #   Если это обычная клетка
                    self.player.set_target(world_x, world_y)    #   То просто идём

    def update(self):
        if self.skill_check:
            self.dice_window.update()
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
        self.camera_x = self.player.x - self.sw // 2
        self.camera_y = self.player.y - self.sh // 2

        if self.pending_dialogue and not self.player.is_moving:
            dialogue_data = load_dialogue(self.pending_dialogue_id)
            self.dialogue = DialogueWindow(self.screen, dialogue_data, self.player)
            self.dialogue_active = True
            self.pending_dialogue = False
            self.pending_dialogue_id = None

    def render(self):
        self.screen.fill((0, 0, 0)) #   Фон
        self.current_map.draw(self.screen, self.camera_x, self.camera_y)    #   Карта
        self.player.draw(self.screen, self.camera_x, self.camera_y) #   Игрок

        if self.dialogue_active and self.dialogue:  #   Диалоговое окно
            self.dialogue.draw()

        if self.menu_active:  #   Окно меню (навыки/инвентарь/задания)
            self.menu_windows[self.menu_tab].draw()
            self._draw_tabs()

        if self.skill_check:   #   Окно броска кубика
            self.dice_window.draw()

        pygame.display.flip()

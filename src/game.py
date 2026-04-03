import pygame
import sys
from player import Player
from locations.test import room
from dialogue import DialogueWindow, load_dialogue
from skills import SkillsWindow
from settings import BASE_WIDTH, BASE_HEIGHT
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

        self.skills_active = False  #   Открыто ли окно навыков?
        self.skills_window = SkillsWindow(self.screen, self.player)

        self.skill_check = False    #   Открыто ли окно с кубиком
        self.dice_window = SkillCheck(self.screen)

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
                if self.skills_active:
                    self.skills_window.confirm()
                self.skills_active = not self.skills_active
                continue


            elif event.type == pygame.KEYDOWN and event.scancode == pygame.KSCAN_E:
                self.player.level_up()
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.skill_check:
                    self.dice_window.handle_click(event.pos)
                    continue

                if self.skills_active:
                    self.skills_window.handle_click(event.pos)
                    continue

                if self.dialogue_active:
                    choice = self.dialogue.handle_click(event.pos)   #   Клик по варианту ответа

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

        if self.skills_active:
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

        if self.skills_active:  #   Окно навыков
            self.skills_window.draw()

        if self.skill_check:   #   Окно броска кубика
            self.dice_window.draw()

        pygame.display.flip()

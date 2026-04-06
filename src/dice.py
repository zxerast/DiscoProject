import pygame
import os
import random
from settings import get_scale, BASE_DIR
from skills import SKILL_DISPLAY_NAMES
from utils import FONT_PATH

# Размер кубика в базовом разрешении (1366x768)
DICE_BASE_W = 350
DICE_BASE_H = 350

# Скорость анимации (кадров игры между сменой фреймов)
ANIM_SPEED = 4

# Тайминги фаз после броска (в кадрах, 60 = 1 секунда)
PHASE_WAIT_BEFORE_MODS = 60    # 1 сек после выпадения числа
PHASE_MOD_INTERVAL = 30        # 0.5 сек между исчезновением модификаторов
PHASE_WAIT_BEFORE_RESULT = 60  # 1 сек после последнего модификатора
PHASE_RESULT_FADE_SPEED = 3    # скорость появления надписи Успех/Провал (прирост альфы за тик)


class SkillCheck:
    def __init__(self, screen):
        self.screen = screen
        sw, sh = screen.get_size()

        # Загружаем кадры анимации
        self.roll_animation = []
        for i in range(21):
            frame = f"frame_{i:02d}.png"
            img = pygame.image.load(os.path.join(BASE_DIR, "assets", "d20_animation", frame)).convert_alpha()
            self.roll_animation.append(img)

        self.final_states = []
        for i in range(4):
            state = f"state_{i}.png"
            img = pygame.image.load(os.path.join(BASE_DIR, "assets", "d20_final_states", state)).convert_alpha()
            self.final_states.append(img)

        # Масштаб кубика
        scale_x, scale_y = get_scale(screen)
        self.width = int(DICE_BASE_W * scale_x)
        self.height = int(DICE_BASE_H * scale_y)

        # Масштабируем все кадры
        self.frames = [
            pygame.transform.scale(f, (self.width, self.height))
            for f in self.roll_animation
        ]

        self.states = [
            pygame.transform.scale(f, (self.width, self.height))
            for f in self.final_states
        ]

        # Позиция кубика — по центру экрана
        self.dice_x = (sw - self.width) // 2
        self.dice_y = (sh - self.height) // 2
        self.dice_rect = pygame.Rect(self.dice_x, self.dice_y, self.width, self.height)

        # Полупрозрачный оверлей
        self.overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))

        # Шрифт для числа на кубике
        scale = min(scale_x, scale_y)
        self.font = pygame.font.Font(FONT_PATH, int(42 * scale))

        # Шрифты для надписей над/под кубиком
        self.dc_label_font = pygame.font.Font(FONT_PATH, int(24 * scale))
        self.dc_value_font = pygame.font.Font(FONT_PATH, int(40 * scale))
        self.mod_font = pygame.font.Font(FONT_PATH, int(24 * scale))
        self.result_font = pygame.font.Font(FONT_PATH, int(48 * scale))

        self.reset()

    def reset(self):
        self.current_frame = 0
        self.animating = False
        self.anim_timer = 0
        self.roll_value = 20
        self.text_alpha = 255
        self.final_state = self.frames[0]
        self.dc = None
        self.check_result = None
        self.finished = False
        self.modifiers = []

        # Фазы после броска
        #   "rolling"          — анимация кубика
        #   "wait_before_mods" — пауза 1 сек после выпадения числа
        #   "absorb_mods"      — модификаторы исчезают по одному
        #   "wait_before_result"— пауза 1 сек перед надписью
        #   "fade_result"      — плавное появление Успех/Провал
        #   "done"             — ждём клика
        self.phase = "idle"
        self.phase_timer = 0

        # Отображаемое число (roll + поглощённые модификаторы)
        self.display_value = 20

        # Цвет DC (меняется на зелёный/красный в конце)
        self.dc_color = (255, 220, 100)

        # Надпись результата
        self.result_text = ""
        self.result_color = (255, 255, 255)
        self.result_alpha = 0

    def start_check(self, dc, skill_name=None, skill_value=0):
        self.reset()
        self.dc = dc
        self.phase = "idle"     # ждём клика по кубику

        if skill_name is not None:
            display = SKILL_DISPLAY_NAMES.get(skill_name, skill_name)
            self.add_modifier(display, skill_value)

    def add_modifier(self, label, value):
        self.modifiers.append({"label": label, "value": value})

    def handle_click(self, pos):
        # Клик в фазе "done" — закрываем
        if self.phase == "done":
            self.finished = True
            return

        # Клик по кубику — запуск анимации
        if self.phase == "idle" and not self.animating:
            if self.dice_rect.collidepoint(pos):
                self.animating = True
                self.current_frame = 1
                self.anim_timer = 0
                self.text_alpha = 0
                self.phase = "rolling"

    def update(self):
        # === Фаза: анимация кубика ===
        if self.phase == "rolling":
            self.anim_timer += 1
            if self.anim_timer >= ANIM_SPEED:
                self.anim_timer = 0
                self.current_frame += 1

                if self.current_frame >= len(self.frames):
                    self.current_frame = 0
                    self.animating = False
                    self.roll_value = random.randint(1, 20)
                    self.display_value = self.roll_value
                    self.text_alpha = 255
                    self.final_state = random.choice(self.states)
                    # Сразу выносим вердикт при критическом успехе/провале
                    if self.display_value == 20 or self.display_value == 1:
                        self.modifiers = None
                        self.phase = "wait_before_result"
                    else:
                    # Переходим к паузе перед модификаторами
                        self.phase = "wait_before_mods"
                        self.phase_timer = 0
            return

        # === Фаза: пауза после выпадения числа ===
        if self.phase == "wait_before_mods":
            self.phase_timer += 1
            if self.phase_timer >= PHASE_WAIT_BEFORE_MODS:
                if self.modifiers:
                    self.phase = "absorb_mods"
                    self.phase_timer = 0
                else:
                    self.phase = "wait_before_result"
                    self.phase_timer = 0
            return

        # === Фаза: поглощение модификаторов по одному ===
        if self.phase == "absorb_mods":
            self.phase_timer += 1
            if self.phase_timer >= PHASE_MOD_INTERVAL:
                self.phase_timer = 0
                mod = self.modifiers.pop(0)
                self.display_value += mod["value"]

                if not self.modifiers:
                    self.phase = "wait_before_result"
                    self.phase_timer = 0
            return

        # === Фаза: пауза перед показом результата ===
        if self.phase == "wait_before_result":
            self.phase_timer += 1
            if self.phase_timer >= PHASE_WAIT_BEFORE_RESULT:
                # Определяем результат
                if self.display_value == 20 and self.roll_value == self.display_value:
                    self.check_result = "success"
                    self.dc_color = (80, 220, 80)
                    self.result_text = "Критический успех"
                    self.result_color = (80, 220, 80)
                elif self.display_value == 1 and self.roll_value == self.display_value:
                    self.check_result = "failure"
                    self.dc_color = (220, 60, 60)
                    self.result_text = "Критический провал"
                    self.result_color = (220, 60, 60)
                elif self.display_value >= self.dc:
                    self.check_result = "success"
                    self.dc_color = (80, 220, 80)
                    self.result_text = "Успех"
                    self.result_color = (80, 220, 80)
                else:
                    self.check_result = "failure"
                    self.dc_color = (220, 60, 60)
                    self.result_text = "Провал"
                    self.result_color = (220, 60, 60)
                self.result_alpha = 0
                self.phase = "fade_result"
            return

        # === Фаза: плавное появление надписи ===
        if self.phase == "fade_result":
            self.result_alpha = min(255, self.result_alpha + PHASE_RESULT_FADE_SPEED)
            if self.result_alpha >= 255:
                self.phase = "done"
            return

    def draw(self):
        self.screen.blit(self.overlay, (0, 0))

        # Надписи "Класс сложности" и значение DC над кубиком
        if self.dc is not None:
            label_surf = self.dc_label_font.render("Класс сложности", True, (200, 200, 200))
            value_surf = self.dc_value_font.render(str(self.dc), True, self.dc_color)

            label_x = self.dice_x + (self.width - label_surf.get_width()) // 2
            value_x = self.dice_x + (self.width - value_surf.get_width()) // 2

            label_y = self.dice_y - label_surf.get_height() - value_surf.get_height() - 8
            value_y = self.dice_y - value_surf.get_height() - 4

            self.screen.blit(label_surf, (label_x, label_y))
            self.screen.blit(value_surf, (value_x, value_y))

        # Кубик
        if self.animating:
            self.screen.blit(self.frames[self.current_frame], (self.dice_x, self.dice_y))
        else:
            self.screen.blit(self.final_state, (self.dice_x, self.dice_y))

        # Число поверх кубика
        if not self.animating and self.text_alpha > 0:
            text_surf = self.font.render(str(self.display_value), True, (255, 180, 0))
            text_surf.set_alpha(self.text_alpha)
            tx = self.dice_x + (self.width - text_surf.get_width()) // 2 - 2
            ty = self.dice_y + (self.height - text_surf.get_height()) // 2 - 6
            self.screen.blit(text_surf, (tx, ty))

        # Модификаторы под кубиком (исчезают по мере поглощения)
        if self.modifiers:
            mod_y = self.dice_y + self.height + 8
            for mod in self.modifiers:
                sign = "+" if mod["value"] >= 0 else ""
                name_surf = self.mod_font.render(f"{mod['label']}: ", True, (200, 200, 200))
                val_surf = self.mod_font.render(f"{sign}{mod['value']}", True, (255, 220, 100))

                total_w = name_surf.get_width() + val_surf.get_width()
                start_x = self.dice_x + (self.width - total_w) // 2
                self.screen.blit(name_surf, (start_x, mod_y))
                self.screen.blit(val_surf, (start_x + name_surf.get_width(), mod_y))
                mod_y += name_surf.get_height() + 4

        # Надпись "Успех" / "Провал"
        if self.result_text and self.result_alpha > 0:
            result_surf = self.result_font.render(self.result_text, True, self.result_color)
            result_surf.set_alpha(self.result_alpha)
            rx = self.dice_x + (self.width - result_surf.get_width()) // 2
            ry = self.dice_y + self.height + 12
            self.screen.blit(result_surf, (rx, ry))

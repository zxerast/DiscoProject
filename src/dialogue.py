import pygame
import os
import json
import random
from settings import BASE_WIDTH, BASE_HEIGHT, get_scale, BASE_DIR

ASSETS_PATH = os.path.join(BASE_DIR, "assets", "dialogue_window")
DIALOGUES_PATH = os.path.join(BASE_DIR, "dialogues")
FONT_PATH = os.path.join(BASE_DIR, "assets", "font", "web_ibm_mda.ttf")


def load_dialogue(dialogue_id):
    path = os.path.join(DIALOGUES_PATH, f"{dialogue_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

COLOR_TEXT = (0, 0, 0)          # Цвета
COLOR_OPTION = (0, 255, 0)
COLOR_OPTION_HOVER = (255, 240, 200)
COLOR_OPTION_BG = (40, 35, 30, 0)
COLOR_OPTION_BG_HOVER = (60, 50, 40, 0)


class DialogueWindow:
    def __init__(self, screen, dialogue_data, player, node_id=None):
        self.screen = screen
        sw, sh = screen.get_size()
        sx, sy = get_scale(screen)

        raw = pygame.image.load(os.path.join(ASSETS_PATH, "window.png")).convert_alpha()
        chanses = pygame.image.load(os.path.join(ASSETS_PATH, "bonuses.png")).convert_alpha()

        w = sw - int(200 * sx)
        h = int(raw.get_height() * w / raw.get_width())

        self.image = pygame.transform.scale(raw, (w, h))
        self.bonuses_image = pygame.transform.scale(chanses, (w, h))

        self.rect = self.image.get_rect(midbottom=(sw // 2, sh - sy))   # Расположение окна диалога

        self.font = pygame.font.Font(FONT_PATH, int(22 * sy))  # Текст ответа
        self.option_font = pygame.font.Font(FONT_PATH, int(20 * sy))   # Текст вопросов

        # Область текста NPC (все значения для базового 1366x768, масштабируются)
        self.text_offset_x = int(280 * sx)
        self.text_offset_y = int(290 * sy)
        self.text_width = self.rect.width - int(640 * sx)
        self.text_line_height = int(28 * sy)

        # Область кнопок ответов
        self.options_offset_x = int(850 * sx)
        self.options_offset_y = int(290 * sy)
        self.options_width = self.rect.width - int(930 * sx)
        self.option_line_height = int(24 * sy)
        self.option_padding_y = int(6 * sy)
        self.button_gap = int(8 * sy)
        self.option_text_pad_x = int(12 * sx)
        self.option_wrap_pad = int(24 * sx)

        self.dialogue_data = dialogue_data  #   Дерево текущего диалога
        self.player = player
        self.active = True

        # Определяем стартовый узел через entry или напрямую
        if node_id is None:
            node_id = self._resolve_entry()
        self.set_node(node_id)      #   Устанавливаем первый узел (строит кнопки внутри)

    def _build_option_rects(self):  #   Строит прямоугольники для каждого варианта ответа.
        self.option_rects = []
        self.option_lines = []  # Завёрнутые строки для каждой кнопки
        start_x = self.rect.x + self.options_offset_x   #   Сдвиг относительно окна диалога
        current_y = self.rect.y + self.options_offset_y

        for i in range(len(self.options)):  #   Добавляем все ответы на экран
            prefix = f"{i + 1}. "   #   Номер ответа
            lines = self._wrap_text(prefix + self.options[i], self.option_font, self.options_width - self.option_wrap_pad) # Ужимаем линии чтобы вместить в кнопку
            self.option_lines.append(lines) #   Добавляем сжатые линии

            btn_height = len(lines) * self.option_line_height + 2 * self.option_padding_y
            rect = pygame.Rect(start_x, current_y, self.options_width, btn_height)
            self.option_rects.append(rect)
            current_y += btn_height + self.button_gap

    def handle_click(self, pos):
        if not self.active:
            return None

        for i, rect in enumerate(self.option_rects):
            if rect.collidepoint(pos):
                opt = self.option_data[i]

                #   Вариант с проверкой навыка
                if "check" in opt:
                    self.pending_check = opt["check"]
                    return "check"

                #   Обычный вариант
                next_node = opt.get("next")
                if next_node is None:
                    self.active = False
                    return "close"
                else:
                    self.set_node(next_node)
                    return "continue"

        return None

    def _resolve_entry(self):   #   Выбирает стартовый узел: проверяет entry-правила сверху вниз, возвращает первый подходящий.
        entry = self.dialogue_data.get("entry")
        if entry:
            for rule in entry:      #   Смотрим какое состояние сейчас у NPC
                flag = rule.get("flag")     
                if flag is None or self.player.get_flag(flag):  #   В зависимости от состояния запускаем стартовый диалог
                    return rule["node"]
        return "start"

    def set_node(self, node_id):
        node = self.dialogue_data[node_id]
        self.current_node_id = node_id

        # Ставим флаг, если узел его задаёт
        flag = node.get("set_flag")
        if flag:
            self.player.set_flag(flag)

        self.answer_text = node["text"]
        self.option_data = node["options"]  #   Полные данные вариантов (с check/next)
        self.options = [opt["text"] for opt in node["options"]]
        self._build_option_rects()

    def _wrap_text(self, text, font, max_width):    #   Разбивает текст на строки по ширине.
        words = text.split(' ')
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word    #   Соединяем текущее и следующее слово через пробел
            if font.size(test)[0] <= max_width:
                current = test  #   Если влезает в окно то оставляем
            else:
                if current:
                    lines.append(current)   #   Иначе переносим
                current = word
        if current:
            lines.append(current)   #   Если у нас только одно слово то просто оставляем
        return lines

    def draw(self):
        if not self.active:
            return

        self.screen.blit(self.image, self.rect)

        # --- Спрайт бонусов при наведении на 2-й вариант ---
        mouse_pos = pygame.mouse.get_pos()

        # --- Текст NPC ---
        text_x = self.rect.x + self.text_offset_x
        text_y = self.rect.y + self.text_offset_y
        lines = self._wrap_text(self.answer_text, self.font, self.text_width)
        for i in range(len(lines)):
            surf = self.font.render(lines[i], True, COLOR_TEXT)
            self.screen.blit(surf, (text_x, text_y + i * self.text_line_height))

        # --- Кнопки ответов ---
        for i in range(len(self.option_rects)):
            rect = self.option_rects[i]
            hovered = rect.collidepoint(mouse_pos)

            # Фон кнопки
            bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg.fill(COLOR_OPTION_BG_HOVER if hovered else COLOR_OPTION_BG)
            self.screen.blit(bg, rect.topleft)

            # Текст варианта (с переносом строк)
            color = COLOR_OPTION_HOVER if hovered else COLOR_OPTION
            lines = self.option_lines[i]
            for j in range(len(lines)):
                text_surf = self.option_font.render(lines[j], True, color)
                self.screen.blit(text_surf, (rect.x + self.option_text_pad_x, rect.y + self.option_padding_y + j * self.option_line_height))

import pygame
import os
import json
from settings import get_uniform_scale, BASE_DIR, SAVE_DIR
from utils import wrap_text, FONT_PATH, Scrollbar

ASSETS_PATH = os.path.join(BASE_DIR, "assets", "dialogue_window")
DIALOGUES_PATH = os.path.join(BASE_DIR, "dialogues")
SAVE_DIALOGUES_PATH = os.path.join(SAVE_DIR, "dialogues")
SKILLS_PATH = os.path.join(BASE_DIR, "assets", "skills")


def load_dialogue(dialogue_id):
    save_path = os.path.join(SAVE_DIALOGUES_PATH, f"{dialogue_id}.json")
    path = save_path if os.path.exists(save_path) else os.path.join(DIALOGUES_PATH, f"{dialogue_id}.json")
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
        scale = get_uniform_scale(screen)

        raw = pygame.image.load(os.path.join(ASSETS_PATH, "window.png")).convert_alpha()

        w = sw - int(200 * scale)
        h = int(raw.get_height() * w / raw.get_width())

        self.image = pygame.transform.scale(raw, (w, h))

        self.rect = self.image.get_rect(midbottom=(sw // 2, sh - scale))   # Расположение окна диалога

        self.font = pygame.font.Font(FONT_PATH, int(22 * scale))  # Текст ответа
        self.option_font = pygame.font.Font(FONT_PATH, int(20 * scale))   # Текст вопросов

        # Область текста NPC (все значения для базового 1366x768, масштабируются)
        self.text_offset_x = int(280 * scale)
        self.text_offset_y = int(290 * scale)
        self.text_width = self.rect.width - int(640 * scale)
        self.text_line_height = int(28 * scale)

        # Область кнопок ответов
        self.options_offset_x = int(850 * scale)
        self.options_offset_y = int(290 * scale)
        self.options_width = self.rect.width - int(930 * scale)
        self.option_line_height = int(24 * scale)
        self.option_padding_y = int(6 * scale)
        self.button_gap = int(8 * scale)
        self.option_text_pad_x = int(12 * scale)
        self.option_wrap_pad = int(24 * scale)
        self.options_clip_y = int(270 * scale)    # Верхняя граница clip-области (выше чем offset_y)
        self.options_height = self.rect.height - int(310 * scale)  # Видимая высота области ответов (от clip_y)
        self.scroll_speed = int(30 * scale)    # Скорость прокрутки колёсиком

        self.total_options_h = 0    # Полная высота всех кнопок
        self.scrollbar = Scrollbar(
            pygame.Rect(
                self.rect.x + self.options_offset_x + self.options_width - 10,
                self.rect.y + self.options_clip_y,
                8,
                self.options_height,
            ),
            self.scroll_speed,
            20,
        )

        # Область портрета навыка (левая часть окна диалога)
        # Единый масштаб от натурального размера window.png (1536x700)
        self.portrait_scale = min(w / 1536, h / 700)
        self.portrait_w = int(207 * self.portrait_scale)
        self.portrait_h = int(293 * self.portrait_scale)
        self.portrait_x = int(103 * self.portrait_scale)
        self.portrait_y = int(348 * self.portrait_scale)

        # Заглушка портрета NPC
        self.npc_portrait = self._build_npc_placeholder(dialogue_data.get("npc_name", "???"))

        self.dialogue_data = dialogue_data  #   Дерево текущего диалога
        self.player = player
        self.active = True

        # Состояние пассивных проверок
        self.passive_state = None       # None | "continue" (ждём клик "Продолжить")
        self.passive_queue = []         # Очередь успешных проверок для показа
        self.current_portrait = None    # Загруженный портрет навыка (Surface или None)

        # Определяем стартовый узел через entry или напрямую
        if node_id is None:
            node_id = self._resolve_entry()
        self.set_node(node_id)      #   Устанавливаем первый узел (строит кнопки внутри)

    def _build_option_rects(self):  #   Строит прямоугольники для каждого варианта ответа.
        self.option_rects = []
        self.option_lines = []  # Завёрнутые строки для каждой кнопки
        start_x = self.rect.x + self.options_offset_x   #   Сдвиг относительно окна диалога
        base_y = self.rect.y + self.options_offset_y     #   Верх области ответов
        current_y = base_y

        for i in range(len(self.options)):  #   Добавляем все ответы на экран
            prefix = f"{i + 1}. "   #   Номер ответа
            lines = wrap_text(prefix + self.options[i], self.option_font, self.options_width - self.option_wrap_pad)
            self.option_lines.append(lines)

            btn_height = len(lines) * self.option_line_height + 2 * self.option_padding_y
            rect = pygame.Rect(start_x, current_y, self.options_width, btn_height)
            self.option_rects.append(rect)
            current_y += btn_height + self.button_gap

        # Полная высота контента и максимальная прокрутка
        # Видимое пространство для контента = options_height - (offset_y - clip_y)
        self.total_options_h = current_y - base_y
        visible_content_h = self.options_height - (self.options_offset_y - self.options_clip_y)
        self.scrollbar.set_content(
            self.total_options_h,
            visible_content_h,
            thumb_visible_height=self.options_height,
            reset=True,
        )

    def handle_scroll(self, dy):    #   Прокрутка колёсиком мыши. dy > 0 — вверх, dy < 0 — вниз.
        if not self.active:
            return
        self.scrollbar.handle_scroll(dy)

    def handle_mousedown(self, pos, button):    #   Обработка нажатия кнопки мыши (ЛКМ — клик/захват ползунка).
        if not self.active:
            return None
        if button == 1 and self.scrollbar.handle_mousedown(pos):
            return None
        if button == 1:
            return self.handle_click(pos)
        return None

    def handle_mouseup(self):   #   Отпускание кнопки мыши — прекращаем перетаскивание.
        self.scrollbar.handle_mouseup()

    def handle_mousemotion(self, pos):  #   Перемещение мыши при зажатой кнопке — перетаскивание ползунка.
        self.scrollbar.handle_mousemotion(pos)

    def handle_click(self, pos):
        if not self.active:
            return None

        # Проверяем попадание с учётом прокрутки
        clip_rect = pygame.Rect(
            self.rect.x + self.options_offset_x,
            self.rect.y + self.options_clip_y,
            self.options_width, self.options_height
        )
        if not clip_rect.collidepoint(pos):
            return None

        for i, rect in enumerate(self.option_rects):
            scrolled = rect.move(0, -self.scrollbar.scroll_offset)
            if scrolled.collidepoint(pos):

                # Клик при пассивной проверке
                if self.passive_state == "continue":

                    # Отложенный переход на ветку (текст уже был показан)
                    if self.passive_pending_node:
                        node_id = self.passive_pending_node
                        self.passive_pending_node = None
                        self.passive_state = None
                        self.passive_queue = []
                        self.set_node(node_id)
                        return "continue"

                    check = self.passive_queue.pop(0)

                    # Показываем текст и портрет проверки
                    self.answer_text = check["text"]
                    self.current_portrait = self._load_portrait(check.get("portrait"))

                    # Кнопка после текст проверки — из option_text самой проверки
                    btn_text = check.get("option_text", ">_")

                    if check.get("success_node"):
                        # Следующий клик уведёт в ветку
                        self.passive_pending_node = check["success_node"]
                        self.option_data = [{"text": btn_text, "next": None}]
                        self.options = [btn_text]
                        self._build_option_rects()
                    elif self.passive_queue:
                        # Ещё есть проверки
                        self.option_data = [{"text": btn_text, "next": None}]
                        self.options = [btn_text]
                        self._build_option_rects()
                    else:
                        # Все проверки показаны — оригинальные ответы с фильтрацией по флагам
                        self.passive_state = None
                        node = self.dialogue_data[self.current_node_id]
                        visible = []
                        for opt in node["options"]:
                            required_flag = opt.get("flag")
                            if required_flag is None or self.player.get_flag(required_flag):
                                visible.append(opt)
                        self.option_data = visible
                        self.options = [opt["text"] for opt in visible]
                        self._build_option_rects()
                    return "continue"

                opt = self.option_data[i]
                damage = opt.get("damage_on_failure", 0)
                if damage:
                    self.player.take_damage(damage)

                self._apply_option_effects(opt)

                if "change_to" in opt:
                    self.active = False
                    return {"action": "change_tile", "change_to": opt["change_to"]}

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

    def _build_npc_placeholder(self, npc_name): #   Создаёт заглушку портрета NPC — серый прямоугольник с именем."""
        surf = pygame.Surface((self.portrait_w, self.portrait_h), pygame.SRCALPHA)
        surf.fill((60, 55, 50, 200))
        # Рамка
        pygame.draw.rect(surf, (120, 110, 100), surf.get_rect(), 2)
        # Имя NPC по центру
        label = self.font.render(npc_name, True, (200, 190, 170))
        lx = (self.portrait_w - label.get_width()) // 2
        ly = (self.portrait_h - label.get_height()) // 2
        surf.blit(label, (lx, ly))
        return surf

    def _load_portrait(self, skill_name):   #   Загружает и масштабирует портрет навыка из assets/skills/.
        if not skill_name:
            return None
        path = os.path.join(SKILLS_PATH, f"{skill_name}.png")
        if not os.path.exists(path):
            return None
        raw = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(raw, (self.portrait_w, self.portrait_h))

    def _set_flags(self, flags):
        if not flags:
            return
        if isinstance(flags, str):
            self.player.set_flag(flags)
            return
        if isinstance(flags, list):
            for flag in flags:
                if isinstance(flag, str):
                    self.player.set_flag(flag)

    def _remove_flags(self, flags):
        if not flags:
            return
        if isinstance(flags, str):
            self.player.flags.pop(flags, None)
            return
        if isinstance(flags, list):
            for flag in flags:
                if isinstance(flag, str):
                    self.player.flags.pop(flag, None)

    def _remove_item(self, item_data):
        if isinstance(item_data, str):
            item_id = item_data
            count = 1
        elif isinstance(item_data, dict):
            item_id = item_data.get("id")
            count = item_data.get("count", 1)
        else:
            return

        if not item_id:
            return

        remaining = max(1, int(count))
        for idx, slot in enumerate(self.player.inventory):
            if remaining <= 0:
                break
            if not slot or slot.get("id") != item_id:
                continue

            slot_count = slot.get("count", 1)
            if slot_count > remaining:
                slot["count"] = slot_count - remaining
                remaining = 0
            else:
                remaining -= slot_count
                self.player.inventory[idx] = None

    def _remove_items(self, items):
        if not items:
            return
        if isinstance(items, (str, dict)):
            self._remove_item(items)
            return
        if isinstance(items, list):
            for item in items:
                self._remove_item(item)

    def _apply_option_effects(self, opt):
        self._remove_flags(opt.get("remove_flag"))
        self._remove_items(opt.get("remove_item"))

    def set_node(self, node_id):
        node = self.dialogue_data[node_id]
        self.current_node_id = node_id

        # Ставим флаг, если узел его задаёт
        self._set_flags(node.get("set_flag"))

        self.answer_text = node["text"]

        # Портрет навыка из поля "portrait" узла (для узлов-реплик навыка)
        portrait_name = node.get("portrait")
        self.current_portrait = self._load_portrait(portrait_name) if portrait_name else None

        # Пассивные проверки навыков
        self.passive_state = None
        self.passive_queue = []
        self.passive_pending_node = None

        checks = node.get("passive_checks") or []

        for check in checks:
            skill_val = self.player.get_skill(check["skill"])
            if skill_val >= check["dc"]:
                self.passive_queue.append(check)
                # Ставим флаг при успешной проверке
                self._set_flags(check.get("set_flag"))

        # Вставки идут первыми, переходы на ветку — последними
        self.passive_queue.sort(key=lambda c: 1 if c.get("success_node") else 0)

        if self.passive_queue:
            self.passive_state = "continue"
            self.option_data = [{"text": ">_", "next": None}]
            self.options = [">_"]
            self._build_option_rects()
            return

        # Фильтруем опции по флагам — скрываем те, чей флаг не установлен
        visible = []
        for opt in node["options"]:
            required_flag = opt.get("flag")
            if required_flag is None or self.player.get_flag(required_flag):
                visible.append(opt)

        self.option_data = visible
        self.options = [opt["text"] for opt in visible]
        self._build_option_rects()

    def draw(self):
        if not self.active:
            return

        self.screen.blit(self.image, self.rect)

        # --- По��трет (навык или заглушка NPC) ---
        px = self.rect.x + self.portrait_x
        py = self.rect.y + self.portrait_y
        if self.current_portrait:
            self.screen.blit(self.current_portrait, (px, py))
        else:
            self.screen.blit(self.npc_portrait, (px, py))

        mouse_pos = pygame.mouse.get_pos()

        # --- Текст NPC ---
        text_x = self.rect.x + self.text_offset_x
        text_y = self.rect.y + self.text_offset_y
        lines = wrap_text(self.answer_text, self.font, self.text_width)
        for i in range(len(lines)):
            surf = self.font.render(lines[i], True, COLOR_TEXT)
            self.screen.blit(surf, (text_x, text_y + i * self.text_line_height))

        # --- Кнопки ответов (с прокруткой) ---
        clip_rect = pygame.Rect(
            self.rect.x + self.options_offset_x,
            self.rect.y + self.options_clip_y,
            self.options_width + 16, self.options_height
        )
        self.screen.set_clip(clip_rect)

        for i in range(len(self.option_rects)):
            rect = self.option_rects[i]
            # Смещаем по вертикали на scroll_offset
            draw_y = rect.y - self.scrollbar.scroll_offset
            hovered = pygame.Rect(rect.x, draw_y, rect.w, rect.h).collidepoint(mouse_pos)

            # Фон кнопки
            bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg.fill(COLOR_OPTION_BG_HOVER if hovered else COLOR_OPTION_BG)
            self.screen.blit(bg, (rect.x, draw_y))

            # Текст варианта (с переносом строк)
            color = COLOR_OPTION_HOVER if hovered else COLOR_OPTION
            lines = self.option_lines[i]
            for j in range(len(lines)):
                text_surf = self.option_font.render(lines[j], True, color)
                self.screen.blit(text_surf, (
                    rect.x + self.option_text_pad_x,
                    draw_y + self.option_padding_y + j * self.option_line_height
                ))

        # --- Ползунок прокрутки ---
        self.scrollbar.draw(self.screen)

        self.screen.set_clip(None)

import pygame
import os
import json
from settings import BASE_DIR, SAVE_DIR
from utils import FONT_PATH, init_menu_base, wrap_text, Scrollbar

QUESTS_JSON = os.path.join(BASE_DIR, "quests.json")
SAVE_QUESTS_JSON = os.path.join(SAVE_DIR, "quests.json")

# Область списка заданий в координатах menu.png

# ---------- Список квестов ----------

QUEST_LIST_X = 118
QUEST_LIST_Y = 105
QUEST_LIST_W = 238
QUEST_LIST_H = 411

# ---------- Краткое описание ----------

QUEST_DESCRIPTION_X = 400
QUEST_DESCRIPTION_Y = 105
QUEST_DESCRIPTION_W = 439
QUEST_DESCRIPTION_H = 155

# ---------- Текущие цели ----------

QUEST_GOALS_X = 400
QUEST_GOALS_Y = 285
QUEST_GOALS_W = 440
QUEST_GOALS_H = 231

# ---------- Отступы ----------

QUEST_TEXT_PAD_X = 14
QUEST_TEXT_PAD_Y = 14

# ---------- Размеры шрифтов ----------

QUEST_LIST_FONT_SIZE = 20

QUEST_DESCRIPTION_FONT_SIZE = 15

QUEST_GOALS_FONT_SIZE = 20

# ---------- Межстрочные интервалы ----------

QUEST_LINE_GAP = 2

QUEST_STAGE_GAP = 10

# ---------- Прокрутка ----------

QUEST_SCROLL_SPEED = 40

# ---------- Полоса прокрутки ----------

QUEST_SCROLLBAR_WIDTH = 6
QUEST_SCROLLBAR_MARGIN = 6


def load_quests_catalog():
    path = SAVE_QUESTS_JSON if os.path.exists(SAVE_QUESTS_JSON) else QUESTS_JSON
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class QuestManager:
    def __init__(self, player, catalog):
        self.player = player
        self.catalog = catalog
        self.triggers = self._build_triggers()

    def _build_triggers(self):
        """Создает инвертированный индекс (словарь) подписок на флаги при запуске игры."""
        triggers = {}
        for quest_id, quest_data in self.catalog.items():
            # 1. Триггеры начала квеста
            for start_flag in quest_data.get("start_triggers", []):
                triggers.setdefault(start_flag, []).append((quest_id, "start", None, None))
            
            # 2. Триггеры переходов по стадиям (адаптировано под новую структуру stages)
            for stage_id, stage_data in quest_data.get("stages", {}).items():
                for transition_flag, next_stage in stage_data.get("transitions", {}).items():
                    triggers.setdefault(transition_flag, []).append((quest_id, "transition", str(stage_id), str(next_stage)))
        return triggers

    def process_flag(self, flag_name):
        """Мгновенно проверяет, подписан ли какой-то квест на этот флаг."""
        if flag_name not in self.triggers:
            return # Если флаг обычный (например, "met_merchant_50"), ничего не делаем. Нагрузка = 0.

        if not hasattr(self.player, "active_quests"):
            self.player.active_quests = {}

        for action in self.triggers[flag_name]:
            quest_id, action_type, stage_id, next_stage = action
            current_stage = self.player.active_quests.get(quest_id)

            if action_type == "start":
                # Начинаем квест, если он еще не начат
                if not current_stage and current_stage not in ["completed", "failed"]:
                    self.player.active_quests[quest_id] = "1"
            
            elif action_type == "transition":
                # Переводим квест, только если он находится на ожидаемой стадии
                if str(current_stage) == stage_id:
                    self.player.active_quests[quest_id] = next_stage
                    
                    if next_stage == "completed":
                        self.player.add_xp(self.catalog[quest_id].get("xp_reward", 0))

class QuestsWindow:
    def __init__(self, screen, player, scale):
        self.screen = screen
        self.player = player

        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(BASE_DIR, "assets", "quests", "menu.png"), scale)
        self.size = size

        self.catalog = load_quests_catalog()
        self.quest_groups = {
            "main": [],
            "side": [],
            "completed": [],
        }

        # ----------------------------------------------------------
        # Область списка квестов
        # ----------------------------------------------------------

        self.list_rect = pygame.Rect(
            self.offset_x + int(QUEST_LIST_X * self.size),
            self.offset_y + int(QUEST_LIST_Y * self.size),
            int(QUEST_LIST_W * self.size),
            int(QUEST_LIST_H * self.size),
        )

        # ----------------------------------------------------------
        # Верхний блок (описание)
        # ----------------------------------------------------------

        self.description_rect = pygame.Rect(
            self.offset_x + int(QUEST_DESCRIPTION_X * self.size),
            self.offset_y + int(QUEST_DESCRIPTION_Y * self.size),
            int(QUEST_DESCRIPTION_W * self.size),
            int(QUEST_DESCRIPTION_H * self.size),
        )

        # ----------------------------------------------------------
        # Нижний блок (цели)
        # ----------------------------------------------------------

        self.goals_rect = pygame.Rect(
            self.offset_x + int(QUEST_GOALS_X * self.size),
            self.offset_y + int(QUEST_GOALS_Y * self.size),
            int(QUEST_GOALS_W * self.size),
            int(QUEST_GOALS_H * self.size),
        )

        self.list_font = pygame.font.Font(
            FONT_PATH,
            int(QUEST_LIST_FONT_SIZE * self.size),
        )

        self.description_font = pygame.font.Font(
            FONT_PATH,
            int(QUEST_DESCRIPTION_FONT_SIZE * self.size),
        )

        self.goals_font = pygame.font.Font(
            FONT_PATH,
            int(QUEST_GOALS_FONT_SIZE * self.size),
        )

        self.text_pad_x = int(QUEST_TEXT_PAD_X * self.size)
        self.text_pad_y = int(QUEST_TEXT_PAD_Y * self.size)
        self.line_gap = int(QUEST_LINE_GAP * self.size)
        self.stage_gap = int(QUEST_STAGE_GAP * self.size)
        self.scroll_speed = int(QUEST_SCROLL_SPEED * self.size)

        self.text_pad_x = int(QUEST_TEXT_PAD_X * size)
        self.text_pad_y = int(QUEST_TEXT_PAD_Y * size)
        self.scroll_speed = int(QUEST_SCROLL_SPEED * size)
        self.hovered_quest_id = None
        self.selected_quest_id = None

        self.total_content_h = 0
        
        self.scrollbar = Scrollbar(
            pygame.Rect(
                self.list_rect.right - int(QUEST_SCROLLBAR_MARGIN * self.size) - int(QUEST_SCROLLBAR_WIDTH * self.size),

                self.list_rect.y,

                int(QUEST_SCROLLBAR_WIDTH * self.size),

                self.list_rect.height,
            ),
            self.scroll_speed,
            int(20 * self.size),
        )

        self._rebuild_layout()

#   Отрисовка основного списка квестов

    def _refresh_quest_groups(self):    #       Формирует единый список отображаемых квестов.
        self.quest_entries = []

        if not hasattr(self.player, "active_quests"):
            return

        active = []
        completed = []

        for quest_id, quest in self.catalog.items():
            state = self.player.active_quests.get(quest_id)

            if state is None:
                continue

            if state == "failed":
                continue

            entry = {
                "id": quest_id,
                "quest": quest,
                "completed": state == "completed"
            }

            if state == "completed":
                completed.append(entry)
            else:
                active.append(entry)

        self.quest_entries = active + completed


    def _rebuild_layout(self):
        self._refresh_quest_groups()
        self.content_entries = []
        self.quest_block_rects = {}  # Словарь для хранения полных бесшовных блоков квестов

        y = self.list_rect.y + self.text_pad_y
        text_width = (
            self.list_rect.width
            - self.text_pad_x * 2
            - int(QUEST_SCROLLBAR_WIDTH * self.size)
            - int(QUEST_SCROLLBAR_MARGIN * self.size)
        )

        separator_needed = False
        half_gap = self.stage_gap // 2

        for entry in self.quest_entries:
            quest_id = entry["id"]
            quest = entry["quest"]

            lines = wrap_text(
                quest["title"],
                self.list_font,
                text_width
            )

            quest_start_y = y

            for line in lines:
                surf = self.list_font.render(line, True, (255, 255, 255))

                rect = surf.get_rect(
                    x=self.list_rect.x + self.text_pad_x,
                    y=y
                )

                self.content_entries.append({
                    "kind": "quest",
                    "id": quest_id,
                    "quest": quest,
                    "completed": entry["completed"],
                    "text": line,
                    "rect": rect
                })

                y += surf.get_height() + self.line_gap

            quest_end_y = y - self.line_gap

            # Создаем единую область наведения без зазоров по вертикали
            block_x = self.list_rect.x + self.text_pad_x - int(8 * self.size)
            block_w = text_width + int(16 * self.size)
            block_y = quest_start_y - half_gap
            block_h = (quest_end_y + half_gap) - block_y

            self.quest_block_rects[quest_id] = pygame.Rect(block_x, block_y, block_w, block_h)

            if entry["completed"] and not separator_needed:
                self.content_entries.append({
                    "kind": "separator",
                    "rect": pygame.Rect(
                        self.list_rect.x + self.text_pad_x,
                        y,
                        text_width,
                        1
                    )
                })
                y += int(10 * self.size)
                separator_needed = True

            y += self.stage_gap

        self.total_content_h = max(0, y - self.list_rect.y)

        self.scrollbar.set_content(
            self.total_content_h,
            self.list_rect.height,
            thumb_visible_height=self.list_rect.height
        )

#   Ползунок прокрутки и рендеринг

    def handle_scroll(self, dy):
        self.scrollbar.handle_scroll(dy)

    def handle_mousedown(self, pos):
        self.scrollbar.handle_mousedown(pos)
        
        # Если кликнули в область списка, закрепляем наведённый квест
        if self.list_rect.collidepoint(pos) and self.hovered_quest_id:
            self.selected_quest_id = self.hovered_quest_id
            
        return None

    def handle_mouseup(self, pos=None):
        self.scrollbar.handle_mouseup()

    def handle_mousemotion(self, pos):
        self.scrollbar.handle_mousemotion(pos)

    def _find_hovered_quest(self):
        self.hovered_quest_id = None
        mouse = pygame.mouse.get_pos()
        if not self.list_rect.collidepoint(mouse):
            return None

        # Проверяем коллизию с бесшовными блоками квестов
        for quest_id, block_rect in self.quest_block_rects.items():
            visible_rect = block_rect.move(0, -self.scrollbar.scroll_offset)
            if visible_rect.collidepoint(mouse):
                self.hovered_quest_id = quest_id
                return quest_id

        return None

    def _get_details_quest(self):
        # Описание и цели меняются ТОЛЬКО по клику (selected_quest_id)
        target_id = self.selected_quest_id

        if target_id and target_id in self.catalog:
            return target_id, self.catalog[target_id]

        # Если ничего не выбрано, выбираем первый квест в списке по умолчанию
        if self.quest_entries:
            quest_id = self.quest_entries[0]["id"]
            self.selected_quest_id = quest_id
            return quest_id, self.catalog[quest_id]

        return None, None

        return None, None

    def _draw_strike_line(self, rect, color):
        pygame.draw.line(
            self.screen,
            color,
            (rect.x, rect.centery),
            (rect.right, rect.centery),
            max(1, int(2 * self.size)),
        )

    def _draw_description(self):
        quest_id, quest = self._get_details_quest()
        if quest is None:
            return

        x = self.description_rect.x + self.text_pad_x
        y = self.description_rect.y + self.text_pad_y
        max_width = self.description_rect.width - self.text_pad_x * 2

        lines = wrap_text(
            quest.get("description", ""),
            self.description_font,
            max_width
        )

        color = (203, 169, 111)

        for line in lines:
            # Тень
            shadow = self.description_font.render(line, True, (0, 0, 0))
            self.screen.blit(shadow, (x + 2 * self.size, y + 1 * self.size))

            # Текст
            surf = self.description_font.render(line, True, color)
            self.screen.blit(surf, (x, y))

            y += surf.get_height() + self.line_gap

    def _draw_goals(self):
        quest_id, quest = self._get_details_quest()
        if quest is None:
            return

        current_stage = self.player.active_quests.get(quest_id)
        if current_stage is None:
            return

        stages = quest.get("stages", {})
        valid_stages = []

        for stage_id, stage in stages.items():
            try:
                s_id = int(stage_id)
                if current_stage == "completed":
                    completed = True
                    active = False
                elif current_stage != "failed":
                    c_id = int(current_stage)
                    completed = s_id < c_id
                    active = s_id == c_id
                else:
                    completed = False
                    active = False
            except ValueError:
                continue

            if not completed and not active:
                continue

            priority = 0 if active else 1
            valid_stages.append((priority, -s_id, stage, completed, active))

        valid_stages.sort(key=lambda item: (item[0], item[1]))

        x = self.goals_rect.x + self.text_pad_x
        y = self.goals_rect.y + self.text_pad_y
        max_width = self.goals_rect.width - self.text_pad_x * 2

        for _, _, stage, completed, active in valid_stages:
            # Темно-серый для зачеркнутых, бежевый для активных
            color = (140, 140, 140) if completed else (203, 169, 111)
            lines = wrap_text(stage["text"], self.goals_font, max_width)

            for line in lines:
                rect = pygame.Rect(x, y, 0, 0)
                
                # Тень
                shadow = self.goals_font.render(line, True, (0, 0, 0))
                self.screen.blit(shadow, (rect.x + 2 * self.size, rect.y + 1 * self.size))

                # Текст
                surf = self.goals_font.render(line, True, color)
                rect.size = surf.get_size()
                self.screen.blit(surf, rect)

                if completed:
                    self._draw_strike_line(rect, color)

                y += surf.get_height() + self.line_gap

            y += self.stage_gap

    def draw(self):
        self._rebuild_layout()
        self._find_hovered_quest()

        # Фон меню
        self.screen.fill((0, 0, 0))
        self.screen.blit(
            self.bg,
            (self.offset_x, self.offset_y)
        )

        # -------------------------------
        # Список квестов
        # -------------------------------
        self.screen.set_clip(self.list_rect)

        # 1. Отрисовка единого белого фона под наведённым квестом
        if self.hovered_quest_id and self.hovered_quest_id in self.quest_block_rects:
            hover_rect = self.quest_block_rects[self.hovered_quest_id].move(
                0, -self.scrollbar.scroll_offset
            )
            pygame.draw.rect(self.screen, (255, 255, 255), hover_rect)

        # 2. Отрисовка строк и разделителей
        for entry in self.content_entries:
            rect = entry["rect"].move(0, -self.scrollbar.scroll_offset)

            if not self.list_rect.colliderect(rect):
                continue

            # Разделитель
            if entry["kind"] == "separator":
                pygame.draw.line(
                    self.screen, (120, 120, 120),
                    (rect.x, rect.y), (rect.right, rect.y),
                    max(1, int(self.size))
                )
                continue

            is_hovered = (entry["id"] == self.hovered_quest_id)
            is_selected = (entry["id"] == self.selected_quest_id)
            is_completed = entry.get("completed", False)

            # Логика цветов
            if is_hovered:
                color = (0, 0, 0)         # Чёрный текст при наведении
            elif is_selected:
                color = (255, 255, 255)   # Белый для закреплённого квеста
            elif is_completed:
                color = (140, 140, 140)   # Тёмно-серый для выполненных
            else:
                color = (203, 169, 111)   # Бежевый по умолчанию

            # Тень текста (рисуем только если текст не чёрный)
            if not is_hovered:
                shadow_surf = self.list_font.render(entry["text"], True, (0, 0, 0))
                self.screen.blit(shadow_surf, (rect.x + 2 * self.size, rect.y + 1 * self.size))

            # Текст элемента
            text_surf = self.list_font.render(entry["text"], True, color)
            self.screen.blit(text_surf, rect)

            # Зачёркивание выполненных квестов
            if is_completed:
                self._draw_strike_line(rect, color)

        self.screen.set_clip(None)

        # -------------------------------
        # Правая часть окна
        # -------------------------------
        self._draw_description()
        self._draw_goals()

        # -------------------------------
        # Полоса прокрутки
        # -------------------------------
        self.scrollbar.draw(self.screen)
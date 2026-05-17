import pygame
import os
import json
from settings import BASE_DIR, SAVE_DIR
from utils import FONT_PATH, init_menu_base, wrap_text, Scrollbar

QUESTS_JSON = os.path.join(BASE_DIR, "quests.json")
SAVE_QUESTS_JSON = os.path.join(SAVE_DIR, "quests.json")

# Область списка заданий в координатах menu.png
QUEST_LIST_X = 226
QUEST_LIST_Y = 155
QUEST_LIST_W = 430
QUEST_LIST_H = 760

QUEST_TEXT_PAD_X = 38
QUEST_TEXT_PAD_Y = 32
QUEST_HEADER_SIZE = 46
QUEST_SECTION_GAP = 52
QUEST_TITLE_SIZE = 30
QUEST_TITLE_GAP = 18
QUEST_SCROLL_SPEED = 48

QUEST_DETAILS_X = 760
QUEST_DETAILS_Y = 210
QUEST_DETAILS_W = 800
QUEST_DETAILS_H = 720
QUEST_DETAILS_TITLE_SIZE = 46
QUEST_DETAILS_DESC_SIZE = 24
QUEST_DETAILS_STAGE_SIZE = 30
QUEST_DETAILS_LINE_GAP = 8
QUEST_DETAILS_BLOCK_GAP = 34
QUEST_STAGE_COMPLETED_SHIFT_Y = 14

QUEST_GROUPS = [
    ("main", "Основные:"),
    ("side", "Побочные:"),
    ("completed", "Завершённые:"),
]


def load_quests_catalog():
    path = SAVE_QUESTS_JSON if os.path.exists(SAVE_QUESTS_JSON) else QUESTS_JSON
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class QuestsWindow:
    def __init__(self, screen, player):
        self.screen = screen
        self.player = player

        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(BASE_DIR, "assets", "quests", "menu.png"))
        self.size = size

        self.catalog = load_quests_catalog()
        self.quest_groups = {
            "main": [],
            "side": [],
            "completed": [],
        }

        self.list_rect = pygame.Rect(
            self.offset_x + int(QUEST_LIST_X * size),
            self.offset_y + int(QUEST_LIST_Y * size),
            int(QUEST_LIST_W * size),
            int(QUEST_LIST_H * size),
        )
        self.header_font = pygame.font.Font(FONT_PATH, int(QUEST_HEADER_SIZE * size))
        self.title_font = pygame.font.Font(FONT_PATH, int(QUEST_TITLE_SIZE * size))
        self.details_title_font = pygame.font.Font(FONT_PATH, int(QUEST_DETAILS_TITLE_SIZE * size))
        self.details_desc_font = pygame.font.Font(FONT_PATH, int(QUEST_DETAILS_DESC_SIZE * size))
        self.details_stage_font = pygame.font.Font(FONT_PATH, int(QUEST_DETAILS_STAGE_SIZE * size))
        self.text_pad_x = int(QUEST_TEXT_PAD_X * size)
        self.text_pad_y = int(QUEST_TEXT_PAD_Y * size)
        self.section_gap = int(QUEST_SECTION_GAP * size)
        self.title_gap = int(QUEST_TITLE_GAP * size)
        self.scroll_speed = int(QUEST_SCROLL_SPEED * size)
        self.details_rect = pygame.Rect(
            self.offset_x + int(QUEST_DETAILS_X * size),
            self.offset_y + int(QUEST_DETAILS_Y * size),
            int(QUEST_DETAILS_W * size),
            int(QUEST_DETAILS_H * size),
        )
        self.details_line_gap = int(QUEST_DETAILS_LINE_GAP * size)
        self.details_block_gap = int(QUEST_DETAILS_BLOCK_GAP * size)
        self.completed_stage_shift_y = int(QUEST_STAGE_COMPLETED_SHIFT_Y * size)
        self.hovered_quest_id = None
        self.selected_quest_id = None

        self.total_content_h = 0
        self.scrollbar = Scrollbar(
            pygame.Rect(
                self.list_rect.right - int(16 * self.size),
                self.list_rect.y + int(18 * self.size),
                int(8 * self.size),
                self.list_rect.height - int(36 * self.size),
            ),
            self.scroll_speed,
            int(28 * self.size),
        )
        self._rebuild_layout()

#   Отрисовка основного списка квестов

    def _refresh_quest_groups(self):
        self.quest_groups = {
            "main": [],
            "side": [],
            "completed": [],
        }

        for quest_id, quest in self.catalog.items():
            stages = quest.get("stages", [])
            stage_flags = [stage.get("complete_flag") for stage in stages if stage.get("complete_flag")]
            if not stage_flags:
                continue

            active = any(self.player.flags.get(flag) is True for flag in stage_flags)
            completed = all(self.player.flags.get(f"{flag}_completed") is True for flag in stage_flags)

            if completed:
                self.quest_groups["completed"].append((quest_id, quest))
            elif active:
                group_id = quest.get("group", "side")
                if group_id not in self.quest_groups:
                    group_id = "side"
                self.quest_groups[group_id].append((quest_id, quest))

    def _rebuild_layout(self):
        self._refresh_quest_groups()

        y = self.list_rect.y + self.text_pad_y
        self.content_entries = []

        for group_id, title in QUEST_GROUPS:
            surf = self.header_font.render(title, True, (176, 176, 176))
            rect = surf.get_rect(x=self.list_rect.x + self.text_pad_x, y=y)
            self.content_entries.append({
                "kind": "header",
                "surf": surf,
                "rect": rect,
                "completed": False,
            })

            y = rect.bottom + self.title_gap
            for quest_id, quest in self.quest_groups[group_id]:
                quest_surf = self.title_font.render(quest["title"], True, (255, 255, 255))
                quest_rect = quest_surf.get_rect(x=self.list_rect.x + self.text_pad_x + int(18 * self.size), y=y)
                self.content_entries.append({
                    "kind": "quest",
                    "id": quest_id,
                    "quest": quest,
                    "surf": quest_surf,
                    "rect": quest_rect,
                    "completed": group_id == "completed",
                })
                y = quest_rect.bottom + self.title_gap

            y += self.section_gap

        self.total_content_h = y - (self.list_rect.y + self.text_pad_y)
        self.scrollbar.set_content(
            self.total_content_h,
            self.list_rect.height - self.text_pad_y * 2,
            thumb_visible_height=self.list_rect.height,
        )

#   Ползунок прокрутки и рендеринг

    def handle_scroll(self, dy):
        self.scrollbar.handle_scroll(dy)

    def handle_mousedown(self, pos):
        self.scrollbar.handle_mousedown(pos)
        return None

    def handle_mouseup(self, pos=None):
        self.scrollbar.handle_mouseup()

    def handle_mousemotion(self, pos):
        self.scrollbar.handle_mousemotion(pos)

    def _find_hovered_quest(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_quest_id = None

        if not self.list_rect.collidepoint(mouse_pos):
            return None

        for entry in self.content_entries:
            if entry["kind"] != "quest":
                continue
            rect = entry["rect"].move(0, -self.scrollbar.scroll_offset)
            hover_rect = rect.inflate(int(18 * self.size), int(10 * self.size))
            if hover_rect.collidepoint(mouse_pos):
                self.hovered_quest_id = entry["id"]
                self.selected_quest_id = entry["id"]
                return entry
        return None

    def _get_details_quest(self):
        if self.selected_quest_id and self.selected_quest_id in self.catalog:
            return self.selected_quest_id, self.catalog[self.selected_quest_id]

        for group_id, _title in QUEST_GROUPS:
            if self.quest_groups[group_id]:
                quest_id, quest = self.quest_groups[group_id][0]
                self.selected_quest_id = quest_id
                return quest_id, quest
        return None, None

    def _draw_strike_line(self, rect, color):
        pygame.draw.line(
            self.screen,
            color,
            (rect.x, rect.centery),
            (rect.right, rect.centery),
            max(1, int(2 * self.size)),
        )

    def _draw_quest_details(self):
        quest_id, quest = self._get_details_quest()
        if not quest:
            return

        x = self.details_rect.x
        y = self.details_rect.y
        max_width = self.details_rect.width

        title_lines = wrap_text(quest["title"], self.details_title_font, max_width)
        for line in title_lines:
            surf = self.details_title_font.render(line, True, (176, 176, 176))
            self.screen.blit(surf, (x, y))
            y += surf.get_height() + self.details_line_gap

        y += self.details_block_gap

        desc_lines = wrap_text(quest.get("description", ""), self.details_desc_font, max_width)
        for line in desc_lines:
            surf = self.details_desc_font.render(line, True, (255, 255, 255))
            self.screen.blit(surf, (x, y))
            y += surf.get_height() + self.details_line_gap

        y += self.details_block_gap

        for stage in quest.get("stages", []):
            flag = stage.get("complete_flag")
            if not flag:
                continue

            is_active = self.player.flags.get(flag) is True
            is_completed = self.player.flags.get(f"{flag}_completed") is True
            if not is_active and not is_completed:
                continue

            if is_completed:
                y += self.completed_stage_shift_y

            color = (130, 130, 130) if is_completed else (255, 255, 255)
            stage_lines = wrap_text(stage["text"], self.details_stage_font, max_width)
            for line in stage_lines:
                surf = self.details_stage_font.render(line, True, color)
                rect = surf.get_rect(x=x, y=y)
                self.screen.blit(surf, rect)
                if is_completed:
                    self._draw_strike_line(rect, color)
                y += surf.get_height() + self.details_line_gap

            y += self.details_line_gap

    def draw(self):
        self._rebuild_layout()
        self._find_hovered_quest()

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.bg, (self.offset_x, self.offset_y))

        self.screen.set_clip(self.list_rect)
        for entry in self.content_entries:
            rect = entry["rect"].move(0, -self.scrollbar.scroll_offset)
            surf = entry["surf"]
            if entry["kind"] == "quest" and entry["id"] == self.hovered_quest_id:
                hover_rect = rect.inflate(int(18 * self.size), int(10 * self.size))
                pygame.draw.rect(self.screen, (255, 255, 255), hover_rect)
                surf = self.title_font.render(entry["quest"]["title"], True, (0, 0, 0))
            self.screen.blit(surf, rect)
            if entry["completed"]:
                color = (0, 0, 0) if entry["id"] == self.hovered_quest_id else (255, 255, 255)
                self._draw_strike_line(rect, color)
        self.screen.set_clip(None)

        self._draw_quest_details()

        self.scrollbar.draw(self.screen)

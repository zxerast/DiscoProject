import pygame
import os
from settings import BASE_DIR
from utils import (
    FONT_PATH, PREVIEW_W, PREVIEW_H, init_menu_base,
    find_hovered, draw_hover_border, draw_zfill_value, Selection, PreviewPanel,
)

# 25 скиллов, сгруппированных по 5 основным атрибутам (индекс группы = индекс атрибута)
SKILL_GROUPS = [
    # СИЛ (0)
    ["fortitude", "endurance", "musculature", "close_combat", "survival"],
    # ЛОВ (1)
    ["balance", "initiative", "lock_picking", "theft", "accuracy"],
    # ПСИ (3)
    ["empathy", "authority", "persuation", "fear", "volition"],
    # ИНТ (2)
    ["logic", "knowledge", "technology", "short_memory", "analysis"],
    # ВОС (4)
    ["vision", "scent", "hearing", "tactility", "intuition"],
]


# Размер кнопок + и - (ширина, высота)
BUTTON_W = 16
BUTTON_H = 16

# Координаты пар кнопок (minus_x, plus_x, y) для каждой группы навыков
SKILL_BUTTONS = [
    {"minus_y": 131, "plus_y": 113, "x": 301},   # СИЛ
    {"minus_y": 207, "plus_y": 189, "x": 301},   # ЛОВ
    {"minus_y": 283, "plus_y": 265, "x": 301},   # ИНТ
    {"minus_y": 361, "plus_y": 343, "x": 301},   # ПСИ
    {"minus_y": 435, "plus_y": 417, "x": 301},   # ВОС
]

# Размер одной иконки скилла (в координатах menu.png)
SKILL_ICON_W = 52
SKILL_ICON_H = 72

SKILL_ICON_START_POS_X = 368
SKILL_ICON_START_POS_Y = 88

SKILL_ICON_GAP_X = 3
SKILL_ICON_GAP_Y = 4

# Центр маленького квадрата с числовым значением навыка
# относительно левого верхнего угла иконки.
SKILL_VALUE_CENTER_X = 44
SKILL_VALUE_CENTER_Y = 64

# Координаты счётчиков основных атрибутов (в системе menu.png)

ATTR_VAL_X = 337
ATTR_VAL_POSITIONS_Y = [121, 197, 273, 351, 425]  # СИЛ, ЛОВ, ИНТ, ПСИ, ВОС
ATTR_VAL_DIGIT_GAP = 4

# Отображаемые названия скиллов
SKILL_DISPLAY_NAMES = {
    "fortitude": "Стойкость",
    "endurance": "Выносливость",
    "musculature": "Мускулатура",
    "close_combat": "Ближний бой",
    "survival": "Выживание",
    "balance": "Баланс",
    "initiative": "Инициатива",
    "lock_picking": "Взлом",
    "theft": "Кража",
    "accuracy": "Меткость",
    "empathy": "Эмпатия",
    "authority": "Авторитет",
    "persuation": "Убеждение",
    "fear": "Страх",
    "volition": "Сила воли",
    "logic": "Логика",
    "knowledge": "Знания",
    "technology": "Техника",
    "short_memory": "Память",
    "analysis": "Анализ",
    "vision": "Зрение",
    "scent": "Обоняние",
    "hearing": "Слух",
    "tactility": "Тактильность",
    "intuition": "Интуиция",
}

# Имена скиллов (5 строк × 5 столбцов, строка за строкой)
SKILL_NAMES = [
    # СИЛ
    "fortitude", "endurance", "musculature", "close_combat", "survival",
    # ЛОВ
    "balance", "initiative", "lock_picking", "theft", "accuracy",
    # ПСИ
    "empathy", "authority", "persuation", "fear", "volition",
    # ИНТ
    "logic", "knowledge", "technology", "short_memory", "analysis",
    # ВОС
    "vision", "scent", "hearing", "tactility", "intuition",
]

# Ромбы (очки навыков): координаты центра первого ромба, размер и шаг
DIAMOND_X = 215
DIAMOND_Y = 505
DIAMOND_SIZE = 48
DIAMOND_GAP = 6


class SkillsWindow:
    def __init__(self, screen, player, scale):
        self.screen = screen
        self.player = player

        skills_dir = os.path.join(BASE_DIR, "assets", "skills")
        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = init_menu_base(screen, os.path.join(skills_dir, "menu.png"), scale)
        self.size = size
        
        # Масштабированный размер кнопок
        btn_w = int(BUTTON_W * size)
        btn_h = int(BUTTON_H * size)

        self.img_plus = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "plus.png")).convert_alpha(),
            (btn_w, btn_h),
        )
        self.img_plus_hover = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "plus_hover.png")).convert_alpha(),
            (btn_w, btn_h),
        )
        self.img_minus = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "minus.png")).convert_alpha(),
            (btn_w, btn_h),
        )
        self.img_minus_hover = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "minus_hover.png")).convert_alpha(),
            (btn_w, btn_h),
        )

        # Создаём rect-ы кнопок: координаты из menu.png * scale + смещение
        self.buttons = []
        for i in SKILL_BUTTONS:
            plus_rect = pygame.Rect(
                self.offset_x + int(i["x"] * size),
                self.offset_y + int(i["plus_y"] * size),
                btn_w, btn_h,
            )
            minus_rect = pygame.Rect(
                self.offset_x + int(i["x"] * size),
                self.offset_y + int(i["minus_y"] * size),
                btn_w, btn_h,
            )
            self.buttons.append({"minus": minus_rect, "plus": plus_rect})

        # Загрузка иконок скиллов
        icon_w = int(SKILL_ICON_W * size)
        icon_h = int(SKILL_ICON_H * size)

        self.skill_icons = []
        self.skill_previews = []
        for name in SKILL_NAMES:
            img = pygame.image.load(os.path.join(skills_dir, f"{name}.png")).convert_alpha()
            setattr(self, name.lower(), img)
            self.skill_icons.append(img)
            self.skill_previews.append(
                pygame.transform.scale(img, (int(PREVIEW_W * size), int(PREVIEW_H * size)))
            )

        # Rect-ы 25 иконок скиллов (индивидуальные координаты)
        self.skill_rects = []
        start_x = SKILL_ICON_START_POS_X * size
        start_y = SKILL_ICON_START_POS_Y * size
        gap_x = SKILL_ICON_GAP_X * size
        gap_y = SKILL_ICON_GAP_Y * size
        icon_width = SKILL_ICON_W * size
        icon_height = SKILL_ICON_H * size

        for row in range(5):
            for col in range(5):
                rect = pygame.Rect(
                    self.offset_x + start_x + col * (icon_width + gap_x),
                    self.offset_y + start_y + row * (icon_height + gap_y),
                    icon_w, icon_h,
                )
                self.skill_rects.append(rect)

        # Панель превью (общая с inventory)
        self.preview = PreviewPanel(screen, size, self.offset_x, self.offset_y)

        # Шрифт для счётчиков атрибутов (между кнопками +/-)
        self.curr_val_font = self.preview.val_font

        # Спрайты очков навыков
        dp_size = int(DIAMOND_SIZE * size)
        self.img_point_active = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "skill_point_active.png")).convert_alpha(),
            (dp_size, dp_size),
        )
        self.img_point_unactive = pygame.transform.scale(
            pygame.image.load(os.path.join(skills_dir, "skill_point_unactive.png")).convert_alpha(),
            (dp_size, dp_size),
        )
        self.diamond_gap = int(DIAMOND_GAP * size)
        self.diamond_start_x = self.offset_x + int(DIAMOND_X * size)
        self.diamond_y = self.offset_y + int(DIAMOND_Y * size) - dp_size // 2

        # Шрифт для отображения числовых значений скиллов на иконках
        self.skill_value_font = pygame.font.Font(FONT_PATH, int(13 * size))
        self.selection = Selection()

        # Сколько очков потрачено в текущей сессии (до подтверждения)
        self.pending_spent = [0, 0, 0, 0, 0]

    def _shift_skills(self, attr_idx, delta):   #   Сдвинуть значения 5 скиллов группы на delta (+1/-1)
        for skill_name in SKILL_GROUPS[attr_idx]:
            self.player.skills[skill_name] += delta

    def handle_click(self, pos):
        for i, pair in enumerate(self.buttons):
            if pair["plus"].collidepoint(pos):
                if self.player.skill_points > 0:
                    self.player.skill_points -= 1
                    self.player.attributes[i] += 1
                    self._shift_skills(i, +1)
                    self.pending_spent[i] += 1
                return None
            if pair["minus"].collidepoint(pos):
                if self.pending_spent[i] > 0:
                    self.player.skill_points += 1
                    self.player.attributes[i] -= 1
                    self._shift_skills(i, -1)
                    self.pending_spent[i] -= 1
                return None
        self.selection.handle_click(self.skill_rects, pos)
        return None

    def confirm(self):
        self.pending_spent = [0, 0, 0, 0, 0]

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.bg, (self.offset_x, self.offset_y))

        mouse_pos = pygame.mouse.get_pos()
        has_points = self.player.skill_points > 0

        # Кнопки +/- с учётом активности
        for i, pair in enumerate(self.buttons):
            can_minus = self.pending_spent[i] > 0
            can_plus = has_points

            # Кнопка «-»
            if can_minus and pair["minus"].collidepoint(mouse_pos):
                self.screen.blit(self.img_minus_hover, pair["minus"])
            else:
                self.screen.blit(self.img_minus, pair["minus"])

            # Кнопка «+»
            if can_plus and pair["plus"].collidepoint(mouse_pos):
                self.screen.blit(self.img_plus_hover, pair["plus"])
            else:
                self.screen.blit(self.img_plus, pair["plus"])

        # Счётчики основных атрибутов
        digit_gap = int(ATTR_VAL_DIGIT_GAP * self.size)
        cx = self.offset_x + int(ATTR_VAL_X * self.size)
        for i, attr_y in enumerate(ATTR_VAL_POSITIONS_Y):
            cy = self.offset_y + int(attr_y * self.size)
            draw_zfill_value(self.screen, self.curr_val_font, self.player.attributes[i], cx, cy, digit_gap)

        # Очки навыков — спрайты
        total_points = self.player.skill_points + sum(self.pending_spent)
        sp_w = self.img_point_active.get_width()
        for j in range(total_points):
            x = self.diamond_start_x + j * (sp_w + self.diamond_gap)
            img = self.img_point_active if j < self.player.skill_points else self.img_point_unactive
            self.screen.blit(img, (x, self.diamond_y))

        # Иконки скиллов: значение + белая обводка при наведении/закреплении + превью справа
        hovered_idx = find_hovered(self.skill_rects, mouse_pos)

        active_idx = (
            self.selection.selected_idx
            if self.selection.selected_idx is not None
            else hovered_idx
        )

        for i, rect in enumerate(self.skill_rects):
            # Отображаем числовое значение скилла под иконкой
            skill_name = SKILL_NAMES[i]
            skill_val = self.player.skills.get(skill_name, 0)
            val_surf = self.skill_value_font.render(str(skill_val), True, (0, 0, 0))
            val_rect = val_surf.get_rect(
                center=(
                    rect.x + int(SKILL_VALUE_CENTER_X * self.size),
                    rect.y + int(SKILL_VALUE_CENTER_Y * self.size),
                ),
            )
            self.screen.blit(val_surf, val_rect)

            if (i == hovered_idx or i == self.selection.selected_idx):
                draw_hover_border(self.screen, rect)

        if active_idx is not None:
            name = SKILL_NAMES[active_idx]
            display_name = SKILL_DISPLAY_NAMES.get(name, name)
            curr_val = self.player.skills.get(name, 0)
            self.preview.draw(
                icon=self.skill_previews[active_idx],
                name=display_name,
                value=curr_val,
            )

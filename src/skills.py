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
    # ИНТ (2)
    ["logic", "knowledge", "technology", "short_memory", "analysis"],
    # ПСИ (3)
    ["empathy", "authority", "persuation", "fear", "volition"],
    # ВОС (4)
    ["vision", "scent", "hearing", "tactility", "intuition"],
]

# =====================================================
#   КООРДИНАТЫ И РАЗМЕРЫ — МЕНЯЙ ЗДЕСЬ
#   Все значения заданы для натурального разрешения menu.png
#   (1820x1024). При другом разрешении экрана масштабируются
#   автоматически. Пропорции сохраняются — на нестандартных
#   соотношениях сторон появятся чёрные полосы по краям.
# =====================================================

# Размер кнопок + и - (ширина, высота)
BUTTON_W = 67
BUTTON_H = 67

# Координаты пар кнопок (minus_x, plus_x, y) для каждой группы навыков
SKILL_BUTTONS = [
    {"minus_x": 463, "plus_x": 263, "y": 213},   # СИЛ
    {"minus_x": 463, "plus_x": 263, "y": 365},   # ЛОВ
    {"minus_x": 463, "plus_x": 263, "y": 511},   # ИНТ
    {"minus_x": 463, "plus_x": 263, "y": 659},   # ПСИ
    {"minus_x": 463, "plus_x": 263, "y": 807},   # ВОС
]

# Размер одной иконки скилла (в координатах menu.png)
SKILL_ICON_W = 113
SKILL_ICON_H = 156

# Индивидуальные координаты каждого из 25 прямоугольников (x, y)
# Порядок соответствует SKILL_NAMES
SKILL_ICON_POSITIONS = [
    # СИЛ (ряд 1)
    (610, 173), (728, 173), (846, 173), (964, 173), (1082, 173),
    # ЛОВ (ряд 2)
    (610, 333), (728, 333), (846, 333), (964, 333), (1082, 333),
    # ИНТ (ряд 3)
    (610, 493), (728, 493), (846, 493), (964, 493), (1082, 493),
    # ПСИ (ряд 4)
    (610, 653), (728, 653), (846, 653), (964, 653), (1082, 653),
    # ВОС (ряд 5 — чуть ниже)
    (610, 809), (728, 809), (846, 809), (964, 809), (1082, 809),
]

# Координаты счётчиков основных атрибутов (в системе menu.png)
# Между кнопками +/- для каждой группы
ATTR_VAL_X = 548
ATTR_VAL_POSITIONS_Y = [227, 379, 525, 673, 821]  # СИЛ, ЛОВ, ИНТ, ПСИ, ВОС
ATTR_VAL_DIGIT_GAP = 8

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
    "logic": "Логика",
    "knowledge": "Знания",
    "technology": "Техника",
    "short_memory": "Память",
    "analysis": "Анализ",
    "empathy": "Эмпатия",
    "authority": "Авторитет",
    "persuation": "Убеждение",
    "fear": "Страх",
    "volition": "Сила воли",
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
    # ИНТ
    "logic", "knowledge", "technology", "short_memory", "analysis",
    # ПСИ
    "empathy", "authority", "persuation", "fear", "volition",
    # ВОС
    "vision", "scent", "hearing", "tactility", "intuition",
]

# Надписи: текст, x, y, размер шрифта, цвет (R, G, B)
SKILL_LABELS = [
    {"text": "СИЛ",     "x": 400, "y": 244, "size": 40, "color": (255, 200, 0)},
    {"text": "ЛОВ",     "x": 400, "y": 397, "size": 40, "color": (255, 200, 0)},
    {"text": "ИНТ",     "x": 400, "y": 543, "size": 40, "color": (255, 200, 0)},
    {"text": "ПСИ",     "x": 400, "y": 691, "size": 40, "color": (255, 200, 0)},
    {"text": "ВОС",     "x": 400, "y": 839, "size": 40, "color": (255, 200, 0)},
]

# Ромбы (очки навыков): координаты центра первого ромба, размер и шаг
DIAMOND_X = 275
DIAMOND_Y = 915
DIAMOND_SIZE = 25
DIAMOND_GAP = 6

# =====================================================


class SkillsWindow:
    def __init__(self, screen, player):
        self.screen = screen
        self.player = player

        skills_dir = os.path.join(BASE_DIR, "assets", "skills")
        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(skills_dir, "menu.png"))
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
            minus_rect = pygame.Rect(
                self.offset_x + int(i["minus_x"] * size),
                self.offset_y + int(i["y"] * size),
                btn_w, btn_h,
            )
            plus_rect = pygame.Rect(
                self.offset_x + int(i["plus_x"] * size),
                self.offset_y + int(i["y"] * size),
                btn_w, btn_h,
            )
            self.buttons.append({"minus": minus_rect, "plus": plus_rect})

        # Надписи: рендерим заранее, x/y — это центр надписи
        self.skill_labels = []
        for i in SKILL_LABELS:
            font = pygame.font.Font(FONT_PATH, int(i["size"] * size))
            surf = font.render(i["text"], True, i["color"])
            rect = surf.get_rect(center=(
                self.offset_x + int(i["x"] * size),
                self.offset_y + int(i["y"] * size),
            ))
            self.skill_labels.append((surf, rect))
        

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
        for x, y in SKILL_ICON_POSITIONS:
            rect = pygame.Rect(
                self.offset_x + int(x * size),
                self.offset_y + int(y * size),
                icon_w, icon_h,
            )
            self.skill_rects.append(rect)

        # Панель превью (общая с inventory)
        self.preview = PreviewPanel(screen, size, self.offset_x, self.offset_y)

        # Шрифт для счётчиков атрибутов (между кнопками +/-)
        self.curr_val_font = self.preview.val_font

        # Спрайты очков навыков
        dp_size = int(DIAMOND_SIZE * 2 * size)
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
        self.skill_value_font = pygame.font.Font(FONT_PATH, int(20 * size))

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

        # Надписи
        for surf, pos in self.skill_labels:
            self.screen.blit(surf, pos)

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
        active_idx = self.selection.get_active(self.skill_rects, mouse_pos)
        for i, rect in enumerate(self.skill_rects):
            # Отображаем числовое значение скилла под иконкой
            skill_name = SKILL_NAMES[i]
            skill_val = self.player.skills.get(skill_name, 0)
            val_surf = self.skill_value_font.render(str(skill_val), True, (0, 0, 0))
            val_rect = val_surf.get_rect(centerx=rect.centerx + 30, top=rect.bottom - 20)
            self.screen.blit(val_surf, val_rect)

            if i == hovered_idx or i == self.selection.selected_idx:
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


import pygame
import os
from settings import BASE_DIR

FONT_PATH = os.path.join(BASE_DIR, "assets", "font", "web_ibm_mda.ttf")

# Натуральный размер menu.png (общий для всех меню)
MENU_NATIVE_W = 1820
MENU_NATIVE_H = 1024

# Область превью (тёмная панель справа)
PREVIEW_X = 1228
PREVIEW_Y = 168
PREVIEW_W = 352
PREVIEW_H = 498

# Текст под превью
PREVIEW_TEXT_Y = 692
PREVIEW_TEXT_SIZE = 34

# Счётчик значения
CURR_VAL_SIZE = 37
CURR_VAL_X = 1286
CURR_VAL_Y = 878
CURR_VAL_DIGIT_GAP = 8


def wrap_text(text, font, max_width):   #   Разбивает текст на строки по ширине.
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
        lines.append(current)
    return lines


def find_hovered(rects, mouse_pos):     #   Возвращает индекс rect-а под курсором или None.
    for idx, rect in enumerate(rects):
        if rect.collidepoint(mouse_pos):
            return idx
    return None


def draw_hover_border(screen, rect):    #   Белая рамка вокруг rect-а.
    pygame.draw.rect(screen, (255, 255, 255), rect, 2)


def draw_zfill_value(screen, font, value, cx, cy, digit_gap, color=(0, 0, 0)):  #   Рисует двузначное число (zfill(2)) по центру cx, cy с промежутком между цифрами.
    digits = str(value).zfill(2)
    d0 = font.render(digits[0], True, color)
    d1 = font.render(digits[1], True, color)
    total_w = d0.get_width() + digit_gap + d1.get_width()
    start_x = cx - total_w // 2
    screen.blit(d0, (start_x, cy))
    screen.blit(d1, (start_x + d0.get_width() + digit_gap, cy))


class Selection:    #   Закрепление превью по клику. Общее для skills и inventory.

    def __init__(self):
        self.selected_idx = None

    def handle_click(self, rects, pos):     #   Клик по области — закрепить/открепить/сменить.
        clicked = find_hovered(rects, pos)
        if clicked is None:
            return
        if self.selected_idx == clicked:
            self.selected_idx = None
        else:
            self.selected_idx = clicked

    def get_active(self, rects, mouse_pos):     #   Возвращает индекс для превью: hover приоритетнее selected.
        hovered = find_hovered(rects, mouse_pos)
        return hovered if hovered is not None else self.selected_idx


def init_menu_base(screen, bg_path):    #   Вычисляет масштаб, смещение и загружает фон меню. Общее для skills и inventory.
    sw, sh = screen.get_size()
    size = min(sw / MENU_NATIVE_W, sh / MENU_NATIVE_H)
    menu_w = int(MENU_NATIVE_W * size)
    menu_h = int(MENU_NATIVE_H * size)
    offset_x = (sw - menu_w) // 2
    offset_y = (sh - menu_h) // 2
    bg = pygame.transform.scale(
        pygame.image.load(bg_path).convert_alpha(),
        (menu_w, menu_h),
    )
    return size, menu_w, menu_h, offset_x, offset_y, bg


class PreviewPanel:     #   Правая панель превью — общая для skills и inventory.

    def __init__(self, screen, size, offset_x, offset_y):
        self.screen = screen
        self.size = size

        self.rect = pygame.Rect(
            offset_x + int(PREVIEW_X * size),
            offset_y + int(PREVIEW_Y * size),
            int(PREVIEW_W * size),
            int(PREVIEW_H * size),
        )

        self.name_font = pygame.font.Font(FONT_PATH, int(PREVIEW_TEXT_SIZE * size))
        self.desc_font = pygame.font.Font(FONT_PATH, int(25 * size))
        self.val_font = pygame.font.Font(FONT_PATH, int(CURR_VAL_SIZE * size))

        self.text_cx = self.rect.centerx
        self.text_y = offset_y + int(PREVIEW_TEXT_Y * size)

        self.val_cx = offset_x + int(CURR_VAL_X * size)
        self.val_cy = offset_y + int(CURR_VAL_Y * size)
        self.val_digit_gap = int(CURR_VAL_DIGIT_GAP * size)

    def draw(self, icon, name, value=None, description=None):   #   Рисует превью: иконка, название, числовое значение (zfill), описание.

        # Большая иконка
        if icon:
            self.screen.blit(icon, self.rect)

        # Название под превью
        name_surf = self.name_font.render(name, True, (0, 0, 0))
        name_rect = name_surf.get_rect(centerx=self.text_cx, y=self.text_y)
        self.screen.blit(name_surf, name_rect)

        # Числовое значение (zfill(2) с digit_gap)
        if value is not None:
            draw_zfill_value(self.screen, self.val_font, value, self.val_cx, self.val_cy, self.val_digit_gap)

        # Описание с переносом строк
        if description:
            padding = int(12 * self.size)
            y = name_rect.bottom + int(12 * self.size)
            lines = wrap_text(description, self.desc_font, self.rect.width - padding * 2)
            for line in lines:
                line_surf = self.desc_font.render(line, True, (255, 255, 255))
                line_rect = line_surf.get_rect(centerx=self.text_cx, y=y)
                self.screen.blit(line_surf, line_rect)
                y += line_surf.get_height() + 4

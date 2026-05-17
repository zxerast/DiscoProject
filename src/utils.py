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


class Scrollbar:
    def __init__(
        self,
        track_rect,
        scroll_speed,
        min_thumb_height,
        track_color=(10, 34, 14),
        thumb_color=(29, 75, 31),
        thumb_drag_color=(30, 127, 34),
    ):
        self.track_rect = track_rect
        self.scroll_speed = scroll_speed
        self.min_thumb_height = min_thumb_height
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.thumb_drag_color = thumb_drag_color

        self.scroll_offset = 0
        self.content_height = 0
        self.visible_height = 0
        self.thumb_visible_height = track_rect.height
        self.max_scroll = 0
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_offset = 0

    def set_content(self, content_height, visible_height, thumb_visible_height=None, reset=False):
        self.content_height = max(1, content_height)
        self.visible_height = max(1, visible_height)
        self.thumb_visible_height = max(1, thumb_visible_height or self.track_rect.height)
        self.max_scroll = max(0, self.content_height - self.visible_height)
        if reset:
            self.scroll_offset = 0
        else:
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def handle_scroll(self, dy):
        if self.max_scroll == 0:
            return
        self.scroll_offset -= dy * self.scroll_speed
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def handle_mousedown(self, pos):
        if self.max_scroll == 0:
            return False

        thumb_rect = self.get_thumb_rect()
        if thumb_rect and thumb_rect.collidepoint(pos):
            self.dragging = True
            self.drag_start_y = pos[1]
            self.drag_start_offset = self.scroll_offset
            return True

        if self.track_rect.collidepoint(pos):
            ratio = (pos[1] - self.track_rect.y) / self.track_rect.height
            self.scroll_offset = int(ratio * self.max_scroll)
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            return True

        return False

    def handle_mouseup(self):
        self.dragging = False

    def handle_mousemotion(self, pos):
        if not self.dragging or self.max_scroll == 0:
            return

        thumb_h = self.get_thumb_height()
        drag_range = self.track_rect.height - thumb_h
        if drag_range > 0:
            dy = pos[1] - self.drag_start_y
            self.scroll_offset = self.drag_start_offset + int(dy / drag_range * self.max_scroll)
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def get_thumb_height(self):
        ratio = self.thumb_visible_height / self.content_height
        return max(self.min_thumb_height, int(self.track_rect.height * ratio))

    def get_thumb_rect(self):
        if self.max_scroll == 0:
            return None

        thumb_h = self.get_thumb_height()
        scroll_ratio = self.scroll_offset / self.max_scroll
        thumb_y = self.track_rect.y + int(scroll_ratio * (self.track_rect.height - thumb_h))
        return pygame.Rect(self.track_rect.x, thumb_y, self.track_rect.width, thumb_h)

    def draw(self, screen):
        if self.max_scroll == 0:
            return

        pygame.draw.rect(screen, self.track_color, self.track_rect)
        thumb = self.get_thumb_rect()
        if thumb:
            color = self.thumb_drag_color if self.dragging else self.thumb_color
            pygame.draw.rect(screen, color, thumb)


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

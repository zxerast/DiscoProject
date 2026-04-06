import pygame
import os
import json
from settings import BASE_DIR
from utils import (
    FONT_PATH, init_menu_base,
    find_hovered, draw_hover_border, Selection, PreviewPanel, wrap_text,
)

# Размер ячейки в натуральном разрешении menu.png
CELL_NATIVE_W = 99
CELL_NATIVE_H = 101

# Действия первого пункта контекстного меню по типу предмета
ITEM_ACTIONS = {
    "healing": {"label": "Использовать", "action": "use"},
    "inspect": {"label": "Осмотреть", "action": "inspect"},
}

# Сетка 9 столбцов x 7 строк
GRID_COLS = 9
GRID_ROWS = 7

# Левый верхний угол сетки (в координатах menu.png)
GRID_START_X = 276
GRID_START_Y = 200

ITEMS_JSON = os.path.join(BASE_DIR, "items", "items.json")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "items")


def load_items_catalog():
    with open(ITEMS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


class InventoryWindow:
    def __init__(self, screen, player):
        self.screen = screen
        self.player = player

        inv_dir = os.path.join(BASE_DIR, "assets", "inventory")
        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(inv_dir, "menu.png"))
        self.size = size

        # Масштабированная ячейка
        self.cell_w = int(CELL_NATIVE_W * size)
        self.cell_h = int(CELL_NATIVE_H * size)
        self.cell_img = pygame.transform.scale(
            pygame.image.load(os.path.join(inv_dir, "cell.png")).convert_alpha(),
            (self.cell_w, self.cell_h),
        )

        # Rect-ы ячеек сетки
        self.cell_rects = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = self.offset_x + int((GRID_START_X + col * CELL_NATIVE_W) * size)
                y = self.offset_y + int((GRID_START_Y + row * CELL_NATIVE_H) * size)
                self.cell_rects.append(pygame.Rect(x, y, self.cell_w, self.cell_h))

        # Панель превью (общая с skills)
        self.preview = PreviewPanel(screen, size, self.offset_x, self.offset_y)

        self.stack_font = pygame.font.Font(FONT_PATH, int(16 * size))

        self.selection = Selection()

        # Контекстное меню
        self.context_menu = None    # None или {"slot_idx", "actions", "rects"}
        self.ctx_font = pygame.font.Font(FONT_PATH, int(20 * size))
        self.ctx_pad_x = int(16 * size)
        self.ctx_pad_y = int(8 * size)
        self.ctx_line_h = int(28 * size)

        # Перетаскивание
        self.drag_src = None        # Индекс ячейки-источника
        self.drag_active = False    # Порог смещения пройден — идёт перетаскивание
        self.drag_start_pos = None  # Позиция mousedown (для порога)
        self.drag_threshold = int(6 * size)

        # Каталог предметов и кэш иконок
        self.catalog = load_items_catalog()
        self.icon_cache = {}

    def _get_icon(self, item_id):
        if item_id in self.icon_cache:
            return self.icon_cache[item_id]     #   Сразу нашли иконку в кэше
        item = self.catalog.get(item_id)        #   Сразу не нашли -> смотрим в общем каталоге

        if not item:
            return None     #   Не нашли
        icon_path = os.path.join(ICONS_DIR, item["icon"])   #   Ищем иконку к найденному в каталоге предмету

        if not os.path.exists(icon_path):
            return None
        # Масштабируем иконку под размер ячейки с небольшим отступом
        padding = 6
        raw = pygame.image.load(icon_path).convert_alpha()
        icon = pygame.transform.scale(raw, (self.cell_w - padding * 2, self.cell_h - padding * 2))
        self.icon_cache[item_id] = icon     #   Кэшируем её
        return icon

    def _get_preview_icon(self, item_id):   # Большая версия иконки для панели превью (тот же размер что preview скиллов).
        key = item_id + "_preview"
        if key in self.icon_cache:      #   Ищем по точно такому же методу что и мелкую
            return self.icon_cache[key]
        item = self.catalog.get(item_id)
        if not item:
            return None
        icon_path = os.path.join(ICONS_DIR, item["icon"])
        if not os.path.exists(icon_path):
            return None
        raw = pygame.image.load(icon_path).convert_alpha()
        icon = pygame.transform.scale(raw, (self.preview.rect.width, self.preview.rect.height))
        self.icon_cache[key] = icon
        return icon

    def _open_context_menu(self, slot_idx):     #   Строит контекстное меню для предмета.
        slot = self.player.inventory[slot_idx]
        item = self.catalog.get(slot["id"])
        if not item:
            return

        actions = []
        type_action = ITEM_ACTIONS.get(item.get("type"))
        if type_action:
            actions.append(type_action)
        actions.append({"label": "Выбросить", "action": "drop"})

        # Позиция — справа от ячейки
        cell_rect = self.cell_rects[slot_idx]
        menu_w = int(180 * self.size)
        menu_h = len(actions) * self.ctx_line_h + self.ctx_pad_y * 2
        mx = cell_rect.right + int(4 * self.size)
        my = cell_rect.y

        # Не выходим за правый край экрана
        sw = self.screen.get_width()
        if mx + menu_w > sw:
            mx = cell_rect.x - menu_w - int(4 * self.size)

        rects = []
        for i in range(len(actions)):
            r = pygame.Rect(mx, my + self.ctx_pad_y + i * self.ctx_line_h, menu_w, self.ctx_line_h)
            rects.append(r)

        self.context_menu = {
            "slot_idx": slot_idx,
            "actions": actions,
            "rects": rects,
            "bg_rect": pygame.Rect(mx, my, menu_w, menu_h),
        }

    def _handle_context_click(self, pos):   #   Обработка клика при открытом контекстном меню.
        for i, rect in enumerate(self.context_menu["rects"]):
            if rect.collidepoint(pos):
                action = self.context_menu["actions"][i]["action"]
                slot_idx = self.context_menu["slot_idx"]
                self.context_menu = None
                return self._execute_action(action, slot_idx)
        # Клик мимо — закрыть меню
        self.context_menu = None
        return None

    def _execute_action(self, action, slot_idx):
        if action == "drop":
            if slot_idx < len(self.player.inventory):
                self.player.inventory.pop(slot_idx)
                # Сбрасываем выделение если удалённый слот был выбран
                if self.selection.selected_idx == slot_idx:
                    self.selection.selected_idx = None
                elif self.selection.selected_idx is not None and self.selection.selected_idx > slot_idx:
                    self.selection.selected_idx -= 1
            return None
        if action == "use":
            # Заглушка — в будущем вызов метода лечения
            return None
        if action == "inspect":
            slot = self.player.inventory[slot_idx]
            item = self.catalog.get(slot["id"])
            if item and item.get("dialogue"):
                return {"action": "inspect", "dialogue_id": item["dialogue"]}
            return None
        return None

    def _get_slot(self, idx):  #   Возвращает слот инвентаря или None если ячейка пуста.
        if idx is not None and idx < len(self.player.inventory):
            return self.player.inventory[idx]
        return None

    def _swap_slots(self, src, dst):    #   Перемещает предмет из src в dst (свап если dst занят).
        inv = self.player.inventory
        # Расширяем список если dst за пределами
        while len(inv) <= dst:
            inv.append(None)
        inv[src], inv[dst] = inv[dst], inv[src]
        # Убираем хвостовые None
        while inv and inv[-1] is None:
            inv.pop()

    def handle_mousedown(self, pos):
        # Контекстное меню — обработать клик по нему
        if self.context_menu is not None:
            return self._handle_context_click(pos)

        clicked = find_hovered(self.cell_rects, pos)
        if self._get_slot(clicked) is not None:
            self.drag_src = clicked
            self.drag_start_pos = pos
            self.drag_active = False
        else:
            self.drag_src = None
            self.selection.selected_idx = None
        return None

    def handle_mousemotion(self, pos):
        if self.drag_src is not None and not self.drag_active:
            dx = pos[0] - self.drag_start_pos[0]
            dy = pos[1] - self.drag_start_pos[1]
            if dx * dx + dy * dy > self.drag_threshold ** 2:
                self.drag_active = True
                self.context_menu = None    # Закрываем меню при начале перетаскивания

    def handle_mouseup(self, pos):
        if self.drag_active:
            # Завершаем перетаскивание
            dst = find_hovered(self.cell_rects, pos)
            if dst is not None and dst != self.drag_src:
                self._swap_slots(self.drag_src, dst)
                # Корректируем выделение
                if self.selection.selected_idx == self.drag_src:
                    self.selection.selected_idx = dst
                elif self.selection.selected_idx == dst:
                    self.selection.selected_idx = self.drag_src
            self.drag_src = None
            self.drag_active = False
            return None

        # Не было перетаскивания — обычный клик
        src = self.drag_src
        self.drag_src = None
        self.drag_active = False

        if src is not None and self._get_slot(src) is not None:
            self.selection.handle_click(self.cell_rects, self.drag_start_pos)
            self._open_context_menu(src)
        return None

    def handle_click(self, pos):    #   Для совместимости (skills/quests вызывают handle_click)
        return self.handle_mousedown(pos)

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.bg, (self.offset_x, self.offset_y))

        mouse_pos = pygame.mouse.get_pos()
        hovered_idx = find_hovered(self.cell_rects, mouse_pos)
        active_idx = self.selection.get_active(self.cell_rects, mouse_pos)
        if active_idx is not None and self._get_slot(active_idx) is None:
            active_idx = self.selection.selected_idx

        # Сетка ячеек
        for idx, rect in enumerate(self.cell_rects):
            self.screen.blit(self.cell_img, rect)

            # Иконка предмета
            slot = self._get_slot(idx)
            if slot is not None:
                item_id = slot["id"]
                icon = self._get_icon(item_id)
                if icon:
                    # При перетаскивании делаем иконку-источник полупрозрачной
                    if self.drag_active and idx == self.drag_src:
                        ghost = icon.copy()
                        ghost.set_alpha(80)
                        draw_icon = ghost
                    else:
                        draw_icon = icon
                    ix = rect.x + (self.cell_w - icon.get_width()) // 2
                    iy = rect.y + (self.cell_h - icon.get_height()) // 2
                    self.screen.blit(draw_icon, (ix, iy))

                # Счётчик стака в правом нижнем углу ячейки
                item_data = self.catalog.get(item_id)
                if item_data and item_data.get("stackable") and slot["count"] > 1:
                    count_surf = self.stack_font.render(str(slot["count"]), True, (255, 255, 255))
                    cx = rect.right - count_surf.get_width() - 4
                    cy = rect.bottom - count_surf.get_height() - 2
                    self.screen.blit(count_surf, (cx, cy))

            # Белая рамка при наведении или закреплении
            if idx == hovered_idx or idx == self.selection.selected_idx:
                draw_hover_border(self.screen, rect)

        # Превью предмета в правой панели (hover приоритетнее закреплённого)
        if active_idx is not None and self._get_slot(active_idx) is not None:
            slot = self.player.inventory[active_idx]
            item = self.catalog.get(slot["id"])
            if item:
                self.preview.draw(
                    icon=self._get_preview_icon(slot["id"]),
                    name=item["name"],
                    value=slot["count"] if item.get("stackable") else None,
                    description=item["description"],
                )

        # Контекстное меню
        if self.context_menu is not None:
            self._draw_context_menu()

        # Иконка предмета под курсором при перетаскивании
        if self.drag_active and self.drag_src is not None:
            slot = self._get_slot(self.drag_src)
            if slot:
                icon = self._get_icon(slot["id"])
                if icon:
                    self.screen.blit(icon, (mouse_pos[0] - icon.get_width() // 2,
                                            mouse_pos[1] - icon.get_height() // 2))

    def _draw_context_menu(self):
        ctx = self.context_menu
        mouse_pos = pygame.mouse.get_pos()

        # Фон меню
        bg = pygame.Surface((ctx["bg_rect"].w, ctx["bg_rect"].h), pygame.SRCALPHA)
        bg.fill((30, 28, 24, 230))
        self.screen.blit(bg, ctx["bg_rect"])
        pygame.draw.rect(self.screen, (120, 110, 100), ctx["bg_rect"], 1)

        # Пункты
        for i, rect in enumerate(ctx["rects"]):
            hovered = rect.collidepoint(mouse_pos)
            if hovered:
                hl = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                hl.fill((80, 70, 55, 150))
                self.screen.blit(hl, rect)
            color = (255, 240, 200) if hovered else (200, 190, 170)
            label = self.ctx_font.render(ctx["actions"][i]["label"], True, color)
            self.screen.blit(label, (rect.x + self.ctx_pad_x, rect.y + (self.ctx_line_h - label.get_height()) // 2))

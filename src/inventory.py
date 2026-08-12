import pygame
import os
import json
from settings import BASE_DIR, SAVE_DIR
from utils import (
    FONT_PATH, init_menu_base,
    find_hovered, draw_hover_border, Selection, PreviewPanel,
)

# Размер ячейки в натуральном разрешении menu.png
CELL_NATIVE_W = 48
CELL_NATIVE_H = 48

# Действия первого пункта контекстного меню по типу предмета
ITEM_ACTIONS = {
    "healing": {"label": "Использовать", "action": "use"},
    "inspect": {"label": "Осмотреть", "action": "inspect"},
}

# Сетка 9 столбцов x 7 строк
GRID_COLS = 6
GRID_ROWS = 9

# Левый верхний угол сетки (в координатах menu.png)
GRID_START_X = 348
GRID_START_Y = 95

ITEMS_JSON = os.path.join(BASE_DIR, "items.json")
SAVE_ITEMS_JSON = os.path.join(SAVE_DIR, "items.json")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "items")
PREVIEW_DIR = os.path.join(BASE_DIR, "assets", "portraits")


def load_items_catalog():
    path = SAVE_ITEMS_JSON if os.path.exists(SAVE_ITEMS_JSON) else ITEMS_JSON
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class InventoryWindow:
    def __init__(self, screen, player, scale):
        self.screen = screen
        self.player = player

        inv_dir = os.path.join(BASE_DIR, "assets", "inventory")
        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(inv_dir, "menu.png"), scale)
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

        # Генерация ячеек быстрого доступа (индексы 54-57)
        QUICK_START_X = 120
        QUICK_START_Y = 213
        
        for i in range(4):
            x = self.offset_x + int((QUICK_START_X + i * CELL_NATIVE_W) * size)
            y = self.offset_y + int((QUICK_START_Y) * size)
            self.cell_rects.append(pygame.Rect(x, y, self.cell_w, self.cell_h))
        
        # Слоты оружия (индексы 58 и 59)
        W_START_X = 107
        W_START_Y = 93
        W_WIDTH = 108
        W_HEIGHT = 96
        W_GAP = 2 # Отступ между руками (располагаем их по горизонтали)

        for i in range(2):
            x = self.offset_x + int((W_START_X + i * (W_WIDTH + W_GAP)) * size)
            y = self.offset_y + int(W_START_Y * size)
            self.cell_rects.append(pygame.Rect(x, y, int(W_WIDTH * size), int(W_HEIGHT * size)))
            
        # Состояние всплывающего меню выбора оружия
        self.weapon_select_mode = False
        self.selected_weapon_slot = None
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
        icon_path = os.path.join(PREVIEW_DIR, item["icon"])
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
                slot = self.player.inventory[slot_idx]
                flags = slot.get("set_flag_on_take")
                if not flags:
                    self.player.inventory[slot_idx] = None
                    if self.selection.selected_idx == slot_idx:
                        self.selection.selected_idx = None
                    return

                if isinstance(flags, str):
                    self.player.flags.pop(flags, None)
                elif isinstance(flags, list):
                    for flag in flags:
                        if isinstance(flag, str):
                            self.player.flags.pop(flag, None)

                self.player.inventory[slot_idx] = None
                if self.selection.selected_idx == slot_idx:
                    self.selection.selected_idx = None
            return None
        if action == "use":
            if slot_idx >= len(self.player.inventory):
                return None

            slot = self.player.inventory[slot_idx]
            if slot is None:
                return None

            item = self.catalog.get(slot["id"])
            if item and item.get("type") == "healing":
                self.player.heal(item.get("heal_points", 1))
                slot["count"] = slot.get("count", 1) - 1
                if slot["count"] <= 0:
                    self.player.inventory[slot_idx] = None
            return None
        if action == "inspect":
            slot = self.player.inventory[slot_idx]
            if slot is None:
                return None
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
    
    def _get_inventory_weapons(self):
        weapons = []
        for i, slot in enumerate(self.player.inventory):
            if i in (58, 59) or slot is None:
                continue
            item = self.catalog.get(slot["id"])
            if item and item.get("type") in ("pistol", "rifle", "shotgun", "melee"):
                weapons.append((i, slot)) # Сохраняем индекс, чтобы знать откуда забирать
        return weapons

    def _get_available_weapon_choices(self):
        weapons = self._get_inventory_weapons()

        for equip_idx in (58, 59):
            if equip_idx >= len(self.player.inventory):
                continue
            if equip_idx == self.selected_weapon_slot:
                continue

            equipped = self.player.inventory[equip_idx]
            if equipped is not None:
                weapons.insert(0, (equip_idx, equipped))

        equipped = self._get_slot(self.selected_weapon_slot)
        if equipped is not None:
            weapons.insert(0, (self.selected_weapon_slot, equipped))

        return weapons

    def _get_weapon_rects(self):
        if not self.weapon_select_mode: return []
        weapons = self._get_available_weapon_choices()

        if not weapons:
            self.weapon_select_mode = False
            return []
            
        cell_size = int(CELL_NATIVE_W * self.size)
        gap = int(4 * self.size)
        
        slot_rect = self.cell_rects[self.selected_weapon_slot]
        total_width = len(weapons) * cell_size + max(0, len(weapons) - 1) * gap
        start_x = slot_rect.centerx - total_width // 2
        start_y = slot_rect.y - cell_size - int(12 * self.size)
        
        rects = []
        for i, (inv_idx, weapon) in enumerate(weapons):
            r = pygame.Rect(start_x + i * (cell_size + gap), start_y, cell_size, cell_size)
            rects.append((r, inv_idx, weapon))
        return rects
    
    def handle_mousedown(self, pos):
        # 1. Проверяем клик по всплывающему окну выбора оружия
        if self.weapon_select_mode:
            for r, inv_idx, weapon in self._get_weapon_rects():
                if r.collidepoint(pos):
                    if inv_idx == self.selected_weapon_slot:
                        # Снимаем оружие и кладем в первую свободную ячейку (0-53)
                        item = self.player.inventory[self.selected_weapon_slot]
                        for i in range(54):
                            if i < len(self.player.inventory):
                                if self.player.inventory[i] is None:
                                    self.player.inventory[i] = item
                                    self.player.inventory[self.selected_weapon_slot] = None
                                    break
                            else:
                                self.player.inventory.append(item)
                                self.player.inventory[self.selected_weapon_slot] = None
                                break
                    else:
                        self._swap_slots(inv_idx, self.selected_weapon_slot)
                    self.weapon_select_mode = False
                    return None
            self.weapon_select_mode = False # Клик мимо окна закрывает его

        # (Оставляем существующий код контекстного меню)
        if self.context_menu is not None:
            return self._handle_context_click(pos)

        clicked = find_hovered(self.cell_rects, pos)
        
        # 2. Если кликнули по пустому слоту оружия - открываем окно выбора
        if clicked in (58, 59) and self._get_slot(clicked) is None:
            self.selected_weapon_slot = clicked
            if self._get_available_weapon_choices():
                self.weapon_select_mode = True
            else:
                self.selected_weapon_slot = None
            self.drag_src = None
            return None
            
        # (Оставляем существующий код drag_src)
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
                # Проверка: если кладем в слоты рук, это должно быть оружие
                if dst in (58, 59):
                    item = self.catalog.get(self.player.inventory[self.drag_src]["id"])
                    if not item or item.get("type") not in ("pistol", "rifle", "shotgun", "melee"):
                        self.drag_src = None
                        self.drag_active = False
                        return None

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
        # Если просто кликнули по занятому слоту оружия - открываем меню (вместо контекстного)
            if src in (58, 59):
                self.weapon_select_mode = True
                self.selected_weapon_slot = src
            else:
                self.selection.handle_click(self.cell_rects, self.drag_start_pos)
                self._open_context_menu(src)
        return None

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
            if idx not in (58, 59):
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

                    # Увеличиваем спрайт в 2 раза только для слотов оружия инвентаря
                    if idx in (58, 59):
                        w, h = draw_icon.get_size()
                        draw_icon = pygame.transform.scale(draw_icon, (w * 2, h * 2))

                    ix = rect.x + (rect.w - draw_icon.get_width()) // 2
                    iy = rect.y + (rect.h - draw_icon.get_height()) // 2
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

        # Отрисовка всплывающего меню выбора оружия
        if self.weapon_select_mode:
            mouse_pos = pygame.mouse.get_pos()
            for rect, inv_idx, weapon in self._get_weapon_rects():
                cell_bg = pygame.transform.scale(self.cell_img, (rect.w, rect.h))
                self.screen.blit(cell_bg, rect.topleft)
                
                icon = self._get_icon(weapon["id"])
                if icon:
                    ix = rect.x + (rect.w - icon.get_width()) // 2
                    iy = rect.y + (rect.h - icon.get_height()) // 2
                    self.screen.blit(icon, (ix, iy))
                    
                if rect.collidepoint(mouse_pos):
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)

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

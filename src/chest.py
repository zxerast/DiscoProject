import os

import pygame

from inventory import CELL_NATIVE_H, CELL_NATIVE_W, GRID_COLS, GRID_ROWS, ICONS_DIR, load_items_catalog
from settings import BASE_DIR
from utils import FONT_PATH, MENU_NATIVE_H, MENU_NATIVE_W, draw_hover_border, find_hovered


CHEST_PAD = 8
CHEST_NAME_PAD = 10


class ChestWindow:
    def __init__(self, screen, player, chest, grid_pos):
        self.screen = screen
        self.player = player
        self.chest = chest
        self.grid_pos = grid_pos

        sw, sh = screen.get_size()
        self.size = min(sw / MENU_NATIVE_W, sh / MENU_NATIVE_H)
        self.cell_w = int(CELL_NATIVE_W * self.size)
        self.cell_h = int(CELL_NATIVE_H * self.size)
        self.pad = int(CHEST_PAD * self.size)

        self.cols = chest.get("cols", 3)
        self.rows = chest.get("rows", 2)
        self.slot_count = self.cols * self.rows
        self.items = chest.setdefault("items", [])
        while len(self.items) < self.slot_count:
            self.items.append(None)

        inv_dir = os.path.join(BASE_DIR, "assets", "inventory")
        self.cell_img = pygame.transform.scale(
            pygame.image.load(os.path.join(inv_dir, "cell.png")).convert_alpha(),
            (self.cell_w, self.cell_h),
        )

        self.catalog = load_items_catalog()
        self.icon_cache = {}
        self.name_font = pygame.font.Font(FONT_PATH, int(20 * self.size))
        self.stack_font = pygame.font.Font(FONT_PATH, int(16 * self.size))

        self.cell_rects = []
        self.drag_src = None
        self.drag_active = False
        self.drag_start_pos = None
        self.drag_threshold = int(6 * self.size)
        self.selected_idx = None

    def _get_slot(self, idx):
        if idx is not None and idx < len(self.items):
            return self.items[idx]
        return None

    def _get_icon(self, item_id):
        if item_id in self.icon_cache:
            return self.icon_cache[item_id]

        item = self.catalog.get(item_id)
        if not item:
            return None

        icon_path = os.path.join(ICONS_DIR, item["icon"])
        if not os.path.exists(icon_path):
            return None

        padding = int(6 * self.size)
        raw = pygame.image.load(icon_path).convert_alpha()
        icon = pygame.transform.scale(raw, (self.cell_w - padding * 2, self.cell_h - padding * 2))
        self.icon_cache[item_id] = icon
        return icon

    def _add_to_inventory(self, slot):
        item = self.catalog.get(slot["id"])
        if item and item.get("stackable"):
            for inv_slot in self.player.inventory:
                if inv_slot and inv_slot["id"] == slot["id"]:
                    inv_slot["count"] += slot.get("count", 1)
                    return True

        for idx, inv_slot in enumerate(self.player.inventory):
            if inv_slot is None:
                self.player.inventory[idx] = slot
                return True

        if len(self.player.inventory) < GRID_COLS * GRID_ROWS:
            self.player.inventory.append(slot)
            return True

        return False

    def _set_flags_on_take(self):
        flags = self.chest.get("set_flag_on_take")
        if not flags:
            return

        if isinstance(flags, str):
            self.player.set_flag(flags)
        elif isinstance(flags, list):
            for flag in flags:
                if isinstance(flag, str):
                    self.player.set_flag(flag)

    def _transfer_to_inventory(self, slot_idx):
        slot = self._get_slot(slot_idx)
        if slot is None:
            return

        if self._add_to_inventory(slot):
            self._set_flags_on_take()
            self.items[slot_idx] = None
            if self.selected_idx == slot_idx:
                self.selected_idx = None

    def _swap_slots(self, src, dst):
        self.items[src], self.items[dst] = self.items[dst], self.items[src]

    def _layout(self, cam_x, cam_y, tile_size):
        gx, gy = self.grid_pos
        ts = tile_size

        chest_screen_x = gx * ts - cam_x
        chest_screen_y = gy * ts - cam_y
        grid_w = self.cols * self.cell_w
        grid_h = self.rows * self.cell_h

        x = int(chest_screen_x + ts // 2 - grid_w // 2)
        y = int(chest_screen_y - grid_h - self.pad)

        sw, sh = self.screen.get_size()
        x = max(self.pad, min(x, sw - grid_w - self.pad))
        y = max(self.pad, min(y, sh - grid_h - self.pad))

        self.cell_rects = []
        for row in range(self.rows):
            for col in range(self.cols):
                self.cell_rects.append(pygame.Rect(
                    x + col * self.cell_w,
                    y + row * self.cell_h,
                    self.cell_w,
                    self.cell_h,
                ))

    def handle_mousedown(self, pos):
        clicked = find_hovered(self.cell_rects, pos)
        if self._get_slot(clicked) is not None:
            self.drag_src = clicked
            self.drag_start_pos = pos
            self.drag_active = False
        else:
            self.drag_src = None
            self.selected_idx = None

    def handle_mousemotion(self, pos):
        if self.drag_src is not None and not self.drag_active:
            dx = pos[0] - self.drag_start_pos[0]
            dy = pos[1] - self.drag_start_pos[1]
            if dx * dx + dy * dy > self.drag_threshold ** 2:
                self.drag_active = True

    def handle_mouseup(self, pos):
        if self.drag_active:
            dst = find_hovered(self.cell_rects, pos)
            if dst is not None and dst != self.drag_src:
                self._swap_slots(self.drag_src, dst)
                if self.selected_idx == self.drag_src:
                    self.selected_idx = dst
                elif self.selected_idx == dst:
                    self.selected_idx = self.drag_src
            self.drag_src = None
            self.drag_active = False
            return

        src = self.drag_src
        self.drag_src = None
        self.drag_active = False
        if src is not None and self._get_slot(src) is not None:
            self._transfer_to_inventory(src)

    def draw(self, cam_x, cam_y, tile_size):
        self._layout(cam_x, cam_y, tile_size)

        mouse_pos = pygame.mouse.get_pos()
        hovered_idx = find_hovered(self.cell_rects, mouse_pos)

        for idx, rect in enumerate(self.cell_rects):
            self.screen.blit(self.cell_img, rect)

            slot = self._get_slot(idx)
            if slot is not None:
                item = self.catalog.get(slot["id"])
                icon = self._get_icon(slot["id"])
                if icon:
                    draw_icon = icon
                    if self.drag_active and idx == self.drag_src:
                        draw_icon = icon.copy()
                        draw_icon.set_alpha(80)
                    ix = rect.x + (self.cell_w - icon.get_width()) // 2
                    iy = rect.y + (self.cell_h - icon.get_height()) // 2
                    self.screen.blit(draw_icon, (ix, iy))

                if item and item.get("stackable") and slot.get("count", 1) > 1:
                    count_surf = self.stack_font.render(str(slot["count"]), True, (255, 255, 255))
                    cx = rect.right - count_surf.get_width() - 4
                    cy = rect.bottom - count_surf.get_height() - 2
                    self.screen.blit(count_surf, (cx, cy))

            if idx == hovered_idx or idx == self.selected_idx:
                draw_hover_border(self.screen, rect)

        if hovered_idx is not None:
            slot = self._get_slot(hovered_idx)
            if slot:
                item = self.catalog.get(slot["id"])
                if item:
                    self._draw_name(item["name"], mouse_pos)

        if self.drag_active and self.drag_src is not None:
            slot = self._get_slot(self.drag_src)
            if slot:
                icon = self._get_icon(slot["id"])
                if icon:
                    self.screen.blit(icon, (
                        mouse_pos[0] - icon.get_width() // 2,
                        mouse_pos[1] - icon.get_height() // 2,
                    ))

    def _draw_name(self, name, mouse_pos):
        label = self.name_font.render(name, True, (255, 240, 200))
        pad = int(CHEST_NAME_PAD * self.size)
        rect = pygame.Rect(
            mouse_pos[0] + pad,
            mouse_pos[1] - label.get_height() - pad,
            label.get_width() + pad * 2,
            label.get_height() + pad,
        )

        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((30, 28, 24, 230))
        self.screen.blit(bg, rect)
        pygame.draw.rect(self.screen, (120, 110, 100), rect, 1)
        self.screen.blit(label, (rect.x + pad, rect.y + pad // 2))

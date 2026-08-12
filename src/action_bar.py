import pygame
import os
from settings import BASE_DIR
from utils import FONT_PATH
from actions import Actions

class ActionBar:
    def __init__(self, screen, player, scale, inventory, cam_centerer = None):
        self.screen = screen
        self.player = player
        self.scale = scale
        
        self.sw, self.sh = screen.get_size()
        
        # Локальная инициализация шрифта
        self.font = pygame.font.Font(FONT_PATH, int(10 * scale))
        
        # 1. Загрузка текстур
        bar_path = os.path.join(BASE_DIR, "assets", "player_bar", "bar.png")
        hp_bar_path = os.path.join(BASE_DIR, "assets", "player_bar" ,"health_bar.png")
        xp_bar_path = os.path.join(BASE_DIR, "assets", "player_bar", "XP_bar.png")
        
        # Панель действий
        raw_bar = pygame.image.load(bar_path).convert_alpha()
        self.bar_w = int(raw_bar.get_width() * scale)
        self.bar_h = int(raw_bar.get_height() * scale)
        self.bar_img = pygame.transform.scale(raw_bar, (self.bar_w, self.bar_h))
        
                # Шкала здоровья
        raw_hp = pygame.image.load(hp_bar_path).convert_alpha()
        self.hp_w = int(raw_hp.get_width() * scale)
        self.hp_h = int(raw_hp.get_height() * scale)
        self.hp_img = pygame.transform.scale(raw_hp, (self.hp_w, self.hp_h))

        # Шкала опыта
        raw_xp = pygame.image.load(xp_bar_path).convert_alpha()
        self.xp_w = int(raw_xp.get_width() * scale)
        self.xp_h = int(raw_xp.get_height() * scale)
        self.xp_img = pygame.transform.scale(raw_xp, (self.xp_w, self.xp_h))
        
        # 2. Располагаем основную панель строго по центру внизу экрана
        self.x = (self.sw - self.bar_w) // 2
        self.y = self.sh - self.bar_h
        
        # Быстрые слоты (2x2 сетка, начиная с 547, 24 на оригинальном спрайте)
        self.quick_slot_rects = []
        qs_start_x = self.x + int(549 * scale)
        qs_start_y = self.y + int(26 * scale)
        qs_cell_size = int(44 * scale)

        for i in range(4):
            col = i % 2
            row = i // 2
            rect = pygame.Rect(
                qs_start_x + col * (qs_cell_size + 3 * self.scale),
                qs_start_y + row * (qs_cell_size + 3 * self.scale),
                qs_cell_size,
                qs_cell_size
            )
            # Привязываем каждый rect к индексам инвентаря 54, 55, 56, 57
            self.quick_slot_rects.append((rect, 54 + i))
        

        # Кнопки перезарядки (под слотами оружия)
        btn_y = self.y + int(82 * scale)
        btn_w = int(56 * scale)
        btn_h = int(15 * scale)
        
        self.btn_reload_left = pygame.Rect(self.x + int(115 * scale), btn_y, btn_w, btn_h)
        self.btn_reload_right = pygame.Rect(self.x + int(177 * scale), btn_y, btn_w, btn_h)
        
        # Позиция шкалы здоровья
        self.hp_x = self.x + int(114 * scale)
        self.hp_y = self.y + int(108 * scale)
        
        # Позиция шкалы опыта (под здоровьем)
        self.xp_x = self.x + int(114 * scale)
        self.xp_y = self.y + int(126 * scale)
        
        # Состояния наведения для кнопок
        self.hover_left = False
        self.hover_right = False

        # Портрет
        self.portrait_x = self.x + int(3 * scale)
        self.portrait_y = self.y + int(4 * scale)
        self.portrait_h = int(140 * scale)
        self.portrait_w = int(100 * scale)

        self.portrait_rect = pygame.Rect(self.portrait_x, self.portrait_y, self.portrait_w, self.portrait_h)
        self.last_click_time = 0
        self.double_click_threshold = 300  # Время в миллисекундах между кликами
        self.cam_centerer = cam_centerer

        # Инициализация менеджера действий и кэш иконок
        actions_db_path = os.path.join(BASE_DIR, "actions.json")
        # Передаем словарь игрока (или свойства)
        player_dict = {"flags": self.player.flags}
        self.actions_manager = Actions(actions_db_path, player_dict)
        self.icon_cache = {}

        self.inventory = inventory

        # Состояние выбора действия и прицеливания
        self.selected_action = None  # Хранит ID или индекс выбранного действия
        self.is_targeting = False    # Режим прицеливания линии к игроку

        # Слоты оружия
        slot_w = int(60 * scale)
        slot_h = int(50 * scale)

        self.left_weapon_rect = pygame.Rect(
            self.x + int(114 * scale),
            self.y + int(27 * scale),
            slot_w,
            slot_h,
        )

        self.right_weapon_rect = pygame.Rect(
            self.x + int(175 * scale),
            self.y + int(27 * scale),
            slot_w,
            slot_h,
        )

        self.hover_left_weapon = False
        self.hover_right_weapon = False

        self.weapon_select_mode = False
        self.selected_weapon_slot = None    
        
        self.rect = pygame.Rect(self.x, self.y, self.bar_w, self.bar_h)
        self.selected_action_cost = 0

    def get_action_rects(self):
        # Начало сетки по координатам 252, 26 на оригинальном спрайте
        start_grid_x = self.x + int(252 * self.scale)
        start_grid_y = self.y + int(26 * self.scale)
        cell_size = int(44 * self.scale)
        gap = int(3 * self.scale)

        # Получаем актуальный список доступных действий
        # Оружие пока берем по умолчанию "unarmed" или проверяем инвентарь игрока
        current_weapon = getattr(self.player, "equipped_weapon_category", "unarmed")
        actions_list = self.actions_manager.get_available_actions(current_weapon)

        rects = []
        # Отрисовка по столбцам, состоящим из двух квадратных ячеек
        for i, action in enumerate(actions_list):
            col = i // 2
            row = i % 2
            rx = start_grid_x + col * (cell_size + gap)
            ry = start_grid_y + row * (cell_size + gap)
            rect = pygame.Rect(rx, ry, cell_size, cell_size)
            rects.append((rect, action))
        return rects
    def get_selected_action_cost(self):
        if self.is_targeting:
            return self.selected_action_cost
        return 0
    
    def use_quick_slot(self, inv_idx):
        if inv_idx >= len(self.player.inventory):
            return
        
        slot = self.player.inventory[inv_idx]
        if slot is None:
            return

        item = self.inventory.catalog.get(slot["id"])
        if not item:
            return

        # Логика применения предмета
        if item.get("type") == "healing":
            self.player.heal(item.get("heal_points", 1))
            slot["count"] = slot.get("count", 1) - 1
            if slot["count"] <= 0:
                self.player.inventory[inv_idx] = None
        elif item.get("type") in ("pistol", "rifle", "shotgun", "melee"):
            # Экипируем оружие
            self.equip_weapon(slot["id"])
        # Здесь можно добавить логику для метательного оружия (переход в режим is_targeting)

    def handle_mousemotion(self, pos):
        self.hover_left = self.btn_reload_left.collidepoint(pos)
        self.hover_right = self.btn_reload_right.collidepoint(pos)

        self.hover_left_weapon = self.left_weapon_rect.collidepoint(pos)
        self.hover_right_weapon = self.right_weapon_rect.collidepoint(pos)

    def handle_mousedown(self, pos, camera_x=0, camera_y=0, player_world_pos=None):
        self.validate_equipment()
        # Получаем актуальный список оружия в инвентаре
        available_weapons = self.get_available_weapon_choices()

        # Обновленная проверка клика во всплывающем окне:
        if self.weapon_select_mode:
            for rect, inv_idx, weapon in self.get_weapon_rects():
                if rect.collidepoint(pos):
                    self.equip_weapon(inv_idx)
                    self.weapon_select_mode = False
                    return True
            self.weapon_select_mode = False

        # Клик по левому слоту
        if self.left_weapon_rect.collidepoint(pos):
            if self.weapon_select_mode and self.selected_weapon_slot == 58:
                self.weapon_select_mode = False
            # Открываем если есть доступное оружие или слот уже занят
            elif available_weapons or self.player.inventory[58] is not None or self.player.inventory[59] is not None:
                self.weapon_select_mode = True
                self.selected_weapon_slot = 58
            return True

        # Клик по правому слоту
        if self.right_weapon_rect.collidepoint(pos):
            if self.weapon_select_mode and self.selected_weapon_slot == 59:
                self.weapon_select_mode = False
            # Открываем если есть доступное оружие или слот уже занят
            elif available_weapons or self.player.inventory[59] is not None or self.player.inventory[58] is not None:
                self.weapon_select_mode = True
                self.selected_weapon_slot = 59
            return True

        # Проверка клика по быстрым слотам
        for rect, inv_idx in self.quick_slot_rects:
            if rect.collidepoint(pos):
                self.use_quick_slot(inv_idx)
                return True

        # 1. СНАЧАЛА проверяем клик по сетке действий (позволяет переключать действия)
        action_rects = self.get_action_rects()
        for rect, action in action_rects:
            if rect.collidepoint(pos):
                if self.is_targeting and self.selected_action == action["name"]:
                    self.selected_action = None
                    self.selected_action_cost = None
                    self.is_targeting = False
                    return True
                self.selected_action = action["name"] # Запоминаем по ключу "name"
                self.selected_action_cost = action["AP"]
                self.is_targeting = True 
                self.player.stop_movement()
                return "action_selected"

        # 2. ПОТОМ проверяем режим прицеливания
        if self.is_targeting:
            if player_world_pos and self._is_clicked_on_player(pos, player_world_pos, camera_x, camera_y):
                applied_action = self.selected_action
                cost = self.selected_action_cost
                self.selected_action = None
                self.is_targeting = False
                return {"action": applied_action, "cost": cost, "target": "player"}
            else:
                self.selected_action = None
                self.is_targeting = False
                return None

        
        if self.portrait_rect.collidepoint(pos):
            current_time = pygame.time.get_ticks()
            if current_time - self.last_click_time <= self.double_click_threshold:
                if self.cam_centerer:
                    self.cam_centerer()
                self.last_click_time = 0
                return True
            else:
                self.last_click_time = current_time
                return True

        if self.btn_reload_left.collidepoint(pos):
            self.reload_weapon(0)
            return True
        if self.btn_reload_right.collidepoint(pos):
            self.reload_weapon(1)
            return True
        if self.rect.collidepoint(pos):
            return True           

        return False
    
    def get_inventory_weapons(self):
        weapons = []
        for i, slot in enumerate(self.player.inventory):
            # Игнорируем уже экипированное в руки
            if i in (58, 59) or slot is None:
                continue
            item = self.inventory.catalog.get(slot["id"])
            if item and item.get("type") in ("pistol", "rifle", "shotgun", "melee"):
                weapons.append((i, slot)) # Возвращаем кортеж с индексом
        return weapons

    def get_available_weapon_choices(self):
        weapons = self.get_inventory_weapons()

        for equip_idx in (58, 59):
            if equip_idx >= len(self.player.inventory):
                continue
            if equip_idx == self.selected_weapon_slot:
                continue

            equipped = self.player.inventory[equip_idx]
            if equipped is not None:
                weapons.insert(0, (equip_idx, equipped))

        if self.selected_weapon_slot is not None and self.player.inventory[self.selected_weapon_slot] is not None:
            weapons.insert(0, (self.selected_weapon_slot, self.player.inventory[self.selected_weapon_slot]))

        return weapons

    def get_weapon_rects(self):
        if not self.weapon_select_mode:
            return []
        weapons = self.get_available_weapon_choices()

        if not weapons:
            self.weapon_select_mode = False
            return []

        cell_size = int(48 * self.scale)
        gap = int(3 * self.scale)
        slot_rect = self.left_weapon_rect if self.selected_weapon_slot == 58 else self.right_weapon_rect
        total_width = len(weapons) * cell_size + max(0, len(weapons) - 1) * gap
        start_x = slot_rect.centerx - total_width // 2
        start_y = slot_rect.y - cell_size - int(12 * self.scale)

        rects = []
        for i, (inv_idx, weapon) in enumerate(weapons):
            rect = pygame.Rect(start_x + i * (cell_size + gap), start_y, cell_size, cell_size)
            rects.append((rect, inv_idx, weapon))
        return rects

    def equip_weapon(self, inv_idx):
        target_slot = self.selected_weapon_slot
        
        if inv_idx == target_slot:
            # Снимаем оружие
            item = self.player.inventory[target_slot]
            for i in range(54):
                if i < len(self.player.inventory):
                    if self.player.inventory[i] is None:
                        self.player.inventory[i] = item
                        self.player.inventory[target_slot] = None
                        break
                else:
                    self.player.inventory.append(item)
                    self.player.inventory[target_slot] = None
                    break
        else:
            while len(self.player.inventory) <= max(target_slot, inv_idx):
                self.player.inventory.append(None)
            self.player.inventory[target_slot], self.player.inventory[inv_idx] = \
                self.player.inventory[inv_idx], self.player.inventory[target_slot]

        self.validate_equipment()

    def validate_equipment(self):
        # Гарантируем длину списка
        while len(self.player.inventory) <= 59:
            self.player.inventory.append(None)
            
        left_slot = self.player.inventory[58]
        right_slot = self.player.inventory[59]
        
        # Обновляем старые атрибуты для совместимости с другими системами, если они их читают
        self.player.left_arm_weapon = left_slot
        self.player.right_arm_weapon = right_slot
        
        # Обновляем категорию действий (рукопашная / стрельба и тд)
        if left_slot:
            item = self.inventory.catalog.get(left_slot["id"])
            self.player.equipped_weapon_category = item.get("type", "unarmed") if item else "unarmed"
        elif right_slot:
            item = self.inventory.catalog.get(right_slot["id"])
            self.player.equipped_weapon_category = item.get("type", "unarmed") if item else "unarmed"
        else:
            self.player.equipped_weapon_category = "unarmed"

    def _is_clicked_on_player(self, mouse_pos, player_world_pos, cam_x, cam_y):
        # Переводим мировые координаты игрока в экранные или используем player.rect с учетом камеры
        p_screen_rect = self.player.rect.move(-cam_x, -cam_y)
        return p_screen_rect.collidepoint(mouse_pos)

    def reload_weapon(self, slot_index):
        # Функция-заглушка для механики перезарядки
        print(f"Вызвана перезарядка для слота {slot_index}!")

    def draw(self, camera_x=0, camera_y=0):
        # 0. Проверяем, не выбросил ли игрок экипированное оружие
        self.validate_equipment()

        # 1. Отрисовка основной панели
        self.screen.blit(self.bar_img, (self.x, self.y))

        # Отрисовка левого оружия (с центрированием)
        if self.player.left_arm_weapon is not None:
            icon = self.inventory._get_icon(self.player.left_arm_weapon["id"])
            if icon:
                ix = self.left_weapon_rect.x + (self.left_weapon_rect.w - icon.get_width()) // 2
                iy = self.left_weapon_rect.y + (self.left_weapon_rect.h - icon.get_height()) // 2
                self.screen.blit(icon, (ix, iy))

        # Отрисовка правого оружия (с центрированием)
        if self.player.right_arm_weapon is not None:
            icon = self.inventory._get_icon(self.player.right_arm_weapon["id"])
            if icon:
                ix = self.right_weapon_rect.x + (self.right_weapon_rect.w - icon.get_width()) // 2
                iy = self.right_weapon_rect.y + (self.right_weapon_rect.h - icon.get_height()) // 2
                self.screen.blit(icon, (ix, iy))
        
        # 2. Отрисовка ячеек действий
        action_rects = self.get_action_rects()
        cell_size = int(44 * self.scale)

        current_weapon = getattr(self.player, "equipped_weapon_category", "unarmed")
        actions_list = self.actions_manager.get_available_actions(current_weapon)

        for i, (rect, action) in enumerate(action_rects):
            # Рисуем подложку ячейки (или иконку)
            full_path = os.path.join(BASE_DIR, action.get("icon_path", ""))
            if full_path not in self.icon_cache:
                try:
                    img = pygame.image.load(full_path).convert_alpha()
                    self.icon_cache[full_path] = pygame.transform.scale(img, (cell_size, cell_size))
                except FileNotFoundError:
                    self.icon_cache[full_path] = None
                
            cached_img = self.icon_cache.get(full_path)
            if cached_img:
                self.screen.blit(cached_img, rect.topleft)

            # НОВОЕ: Полупрозрачный серый квадрат при наведении мыши
            if rect.collidepoint(pygame.mouse.get_pos()):
                hover_surf = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
                hover_surf.fill((128, 128, 128, 128)) # Последнее число - прозрачность (0-255)
                self.screen.blit(hover_surf, rect.topleft)

            # ИСПРАВЛЕНО: Сравниваем с action["name"], так как именно его мы сохраняем
            if self.selected_action == action["name"]:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, width=2)

        # 4. Отрисовка кнопок Reload
        self._draw_button(self.btn_reload_left, "Reload", self.hover_left)
        self._draw_button(self.btn_reload_right, "Reload", self.hover_right)
        
        # 5. Шкала здоровья
        max_hp = self.player.get_max_health()
        current_hp = self.player.health_points
        hp_ratio = max(0.0, min(1.0, current_hp / max_hp)) if max_hp > 0 else 0.0
        render_w = int(self.hp_w * hp_ratio)
        if render_w > 0:
            self.screen.blit(self.hp_img, (self.hp_x, self.hp_y), (0, 0, render_w, self.hp_h))
            
        hp_text = f"{current_hp}/{max_hp}"
        self._draw_shadowed_text(hp_text, self.hp_x + self.hp_w // 2, self.hp_y + self.hp_h // 2, center=True)

        level_text = f"{self.player.level}"
        self._draw_shadowed_text(level_text, self.x + int(218 * self.scale), self.y + int(128 * self.scale), (215, 161, 37), center=True)
        
        # 6. Шкала опыта
        max_xp = self.player.xp_cap
        current_xp = self.player.xp_points
        xp_ratio = max(0.0, min(1.0, current_xp / max_xp)) if max_xp > 0 else 0.0
        xp_render_w = int(self.xp_w * xp_ratio)
        
        if xp_render_w > 0:
            self.screen.blit(self.xp_img, (self.xp_x, self.xp_y), (0, 0, xp_render_w, self.xp_h))

        if self.hover_left_weapon:
            pygame.draw.rect(self.screen, (255,255,255), self.left_weapon_rect, 2)

        if self.hover_right_weapon:
            pygame.draw.rect(self.screen, (255,255,255), self.right_weapon_rect, 2)

        if self.weapon_select_mode:
            mouse = pygame.mouse.get_pos()
            for rect, inv_idx, weapon in self.get_weapon_rects():
                # Рисуем png-фон ячейки из инвентаря вместо серой подложки
                # Подгоняем размер под текущий rect
                cell_bg = pygame.transform.scale(self.inventory.cell_img, (rect.w, rect.h))
                self.screen.blit(cell_bg, rect.topleft)

                # Отрисовка иконки оружия строго по центру ячейки
                icon = self.inventory._get_icon(weapon["id"])
                if icon:
                    ix = rect.x + (rect.w - icon.get_width()) // 2
                    iy = rect.y + (rect.h - icon.get_height()) // 2
                    self.screen.blit(icon, (ix, iy))

                # Оставляем белую обводку при наведении
                if rect.collidepoint(mouse):
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)

        # Отрисовка ячеек быстрого доступа
        mouse_pos = pygame.mouse.get_pos()
        for rect, inv_idx in self.quick_slot_rects:
            # Отрисовка иконки предмета, если он есть
            if inv_idx < len(self.player.inventory):
                slot = self.player.inventory[inv_idx]
                if slot:
                    icon = self.inventory._get_icon(slot["id"])
                    if icon:
                        ix = rect.x + (rect.w - icon.get_width()) // 2
                        iy = rect.y + (rect.h - icon.get_height()) // 2
                        self.screen.blit(icon, (ix, iy))
                        
                        # Опционально: отрисовка счетчика стака (если предметов больше 1)
                        item_data = self.inventory.catalog.get(slot["id"])
                        if item_data and item_data.get("stackable") and slot["count"] > 1:
                            count_surf = self.inventory.stack_font.render(str(slot["count"]), True, (255, 255, 255))
                            cx = rect.right - count_surf.get_width() - 4
                            cy = rect.bottom - count_surf.get_height() - 2
                            self.screen.blit(count_surf, (cx, cy))

            # Серый полупрозрачный квадрат при наведении (как у ячеек действий)
            if rect.collidepoint(mouse_pos):
                hover_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                hover_surf.fill((128, 128, 128, 128))
                self.screen.blit(hover_surf, rect.topleft)

    def _draw_button(self, rect, text, is_hovered):
        color = (255, 255, 255) if is_hovered else (215, 161, 37)
        self._draw_shadowed_text(text, rect.centerx, rect.centery, color, center=True)
        
    def _draw_shadowed_text(self, text, x, y, color=(255, 255, 255), center=False):
        label = self.font.render(text, True, color)
        shadow = self.font.render(text, True, (0, 0, 0))
        
        if center:
            rect = label.get_rect(center=(x, y))
            sx, sy = rect.x, rect.y
        else:
            sx, sy = x, y
            
        self.screen.blit(shadow, (sx + 2 * self.scale, sy + 1 * self.scale))
        self.screen.blit(label, (sx, sy))

import pygame
import os
from settings import BASE_DIR
from utils import FONT_PATH

class ActionBar:
    def __init__(self, screen, player, scale, cam_centerer = None):
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

    def handle_mousemotion(self, pos):
        self.hover_left = self.btn_reload_left.collidepoint(pos)
        self.hover_right = self.btn_reload_right.collidepoint(pos)

    def handle_mousedown(self, pos):
        if self.portrait_rect.collidepoint(pos):
            current_time = pygame.time.get_ticks()
            if current_time - self.last_click_time <= self.double_click_threshold:
                self.cam_centerer()
                self.last_click_time = 0  # Сбрасываем таймер
                return True
            else:
                self.last_click_time = current_time

        if self.btn_reload_left.collidepoint(pos):
            self.reload_weapon(0)
            return True
        if self.btn_reload_right.collidepoint(pos):
            self.reload_weapon(1)
            return True
        return False
        
    def reload_weapon(self, slot_index):
        # Функция-заглушка для механики перезарядки
        print(f"Вызвана перезарядка для слота {slot_index}!")

    def draw(self):
        # 1. Отрисовка основной панели
        self.screen.blit(self.bar_img, (self.x, self.y))
        
        # 2. Отрисовка кнопок Reload
        self._draw_button(self.btn_reload_left, "Reload", self.hover_left)
        self._draw_button(self.btn_reload_right, "Reload", self.hover_right)
        
        # 3. Шкала здоровья (частичный рендер)
        max_hp = self.player.get_max_health()
        current_hp = self.player.health_points
        hp_ratio = max(0.0, min(1.0, current_hp / max_hp)) if max_hp > 0 else 0.0
        
        render_w = int(self.hp_w * hp_ratio)
        if render_w > 0:
            self.screen.blit(self.hp_img, (self.hp_x, self.hp_y), (0, 0, render_w, self.hp_h))
            
        # Текст здоровья текущее/максимальное
        hp_text = f"{current_hp}/{max_hp}"
        self._draw_shadowed_text(hp_text, self.hp_x + self.hp_w // 2, self.hp_y + self.hp_h // 2, center=True)

        # Текст текущего уровня игрока
        level_text = f"{self.player.level}"
        self._draw_shadowed_text(level_text, self.x + int(218 * self.scale), self.y + int(128 * self.scale), (215, 161, 37),center=True)
        
        # 4. Шкала опыта (частичный рендер со спрайтом xp_bar.png)
        max_xp = self.player.xp_cap
        current_xp = self.player.xp_points
        xp_ratio = max(0.0, min(1.0, current_xp / max_xp)) if max_xp > 0 else 0.0
        
        xp_render_w = int(self.xp_w * xp_ratio)
        if xp_render_w > 0:
            self.screen.blit(self.xp_img, (self.xp_x, self.xp_y), (0, 0, xp_render_w, self.xp_h))

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
import pygame
import os
from settings import BASE_DIR

class CombatManager:
    def __init__(self, player, scale):
        self.player = player
        self.scale = scale
        self.is_turn_based = False
        self.current_ap = player.action_points
        
        # Загрузка и масштабирование графики
        bar_path = os.path.join(BASE_DIR, "assets", "player_bar", "action_points_bar.png")
        point_path = os.path.join(BASE_DIR, "assets", "player_bar", "action_point.png")
        used_path = os.path.join(BASE_DIR, "assets", "player_bar", "used_point.png") # <--- Новый спрайт
        
        self.bar_img = pygame.image.load(bar_path).convert_alpha()
        self.point_img = pygame.image.load(point_path).convert_alpha()
        self.used_point_img = pygame.image.load(used_path).convert_alpha() # <--- Загрузка
        
        self.bar_img = pygame.transform.scale(self.bar_img, (int(self.bar_img.get_width() * scale), int(self.bar_img.get_height() * scale)))
        self.point_img = pygame.transform.scale(self.point_img, (int(self.point_img.get_width() * scale), int(self.point_img.get_height() * scale)))
        self.used_point_img = pygame.transform.scale(self.used_point_img, (int(self.used_point_img.get_width() * scale), int(self.used_point_img.get_height() * scale))) # <--- Масштабирование

    def toggle_mode(self):
        self.is_turn_based = not self.is_turn_based
        if self.is_turn_based:
            # При входе в режим восполняем AP и останавливаем текущее движение
            self.current_ap = self.player.action_points
            self.player.stop_movement()
        else:
            # При выходе из режима можно также сбросить AP для надежности
            self.current_ap = self.player.action_points

    def can_move(self):
        if not self.is_turn_based:
            return True
        return self.current_ap > 0

    def consume_ap(self):
        if self.is_turn_based and self.current_ap > 0:
            self.current_ap -= 1

    def draw(self, screen, preview_cost=0):
        if not self.is_turn_based:
            return
            
        screen_w, screen_h = screen.get_size()
        
        # Центрируем шкалу по горизонтали
        bar_x = (screen_w - self.bar_img.get_width()) // 2
        # Размещаем над action_bar (высоту отступа 120 можно настроить под ваш интерфейс)
        bar_y = screen_h - int(163 * self.scale) 
        
        screen.blit(self.bar_img, (bar_x, bar_y))
        
        # Отрисовка делений внутри шкалы
        # Отступы 10 и 5 заданы для примера, их нужно подогнать под пиксели вашего спрайта action_points_bar.png
        start_x = bar_x + int(4 * self.scale)
        start_y = bar_y + int(3 * self.scale)
        
        for i in range(self.current_ap):
            point_x = start_x + i * (self.point_img.get_width())
            # Первые N (preview_cost) очков отображаем спрайтом used_point_img
           
            if i >= (self.current_ap - preview_cost):
                screen.blit(self.used_point_img, (point_x, start_y))
            else:
                screen.blit(self.point_img, (point_x, start_y))

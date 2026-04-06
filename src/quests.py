import pygame
import os
from settings import BASE_DIR
from utils import init_menu_base


class QuestsWindow:
    def __init__(self, screen, player):
        self.screen = screen
        self.player = player

        size, menu_w, menu_h, self.offset_x, self.offset_y, self.bg = \
            init_menu_base(screen, os.path.join(BASE_DIR, "assets", "quests", "menu.png"))
        self.size = size

    def handle_click(self, pos):
        return None

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.bg, (self.offset_x, self.offset_y))

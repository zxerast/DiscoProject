import sys
import os

# Базовое разрешение — все пиксельные координаты
# в проекте заданы для этого разрешения и автоматически масштабируются.
BASE_WIDTH = 1366
BASE_HEIGHT = 768

# Корневая папка проекта
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS 
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SAVE_DIR = os.path.join(BASE_DIR, "save")


def get_scale(screen):  #   Возвращает (scale_x, scale_y) — коэффициенты масштабирования.
    sw, sh = screen.get_size()
    return sw / BASE_WIDTH, sh / BASE_HEIGHT


def get_uniform_scale(screen):  #   Возвращает единый масштаб без растяжения пропорций.
    sx, sy = get_scale(screen)
    return min(sx, sy)

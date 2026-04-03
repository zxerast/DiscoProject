import sys
import os

# Базовое (дизайнерское) разрешение — все пиксельные координаты
# в проекте заданы для этого разрешения и автоматически масштабируются.
BASE_WIDTH = 1366
BASE_HEIGHT = 768

# Корневая папка проекта (работает и из исходников, и из .exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # PyInstaller распаковывает сюда
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def get_scale(screen):
    """Возвращает (scale_x, scale_y) — коэффициенты масштабирования."""
    sw, sh = screen.get_size()
    return sw / BASE_WIDTH, sh / BASE_HEIGHT

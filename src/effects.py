import pygame

class Effect:
    def __init__(self, duration_ms):
        self.duration_ms = duration_ms
        self.start_time = pygame.time.get_ticks()
        self.is_finished = False

    def update(self):
        # Проверяем, не истекло ли время (реал-тайм)
        if pygame.time.get_ticks() - self.start_time >= self.duration_ms:
            self.is_finished = True

class DashEffect(Effect):
    def __init__(self):
        super().__init__(10000) # 10 секунд (10000 мс)

    def apply_speed_multiplier(self):
        return 20.0 # Ускорение в 2 раза
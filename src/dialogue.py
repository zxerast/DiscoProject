import pygame
import os
import json
from settings import BASE_DIR, SAVE_DIR
from utils import wrap_text, FONT_PATH, Scrollbar

ASSETS_PATH = os.path.join(BASE_DIR, "assets", "dialogue_window")
DIALOGUES_PATH = os.path.join(BASE_DIR, "dialogues")
SAVE_DIALOGUES_PATH = os.path.join(SAVE_DIR, "dialogues")
SKILLS_PATH = os.path.join(BASE_DIR, "assets", "skills")
PORTRAIT_PATH = os.path.join(BASE_DIR, "assets", "portraits")

def load_dialogue(dialogue_id):
    save_path = os.path.join(SAVE_DIALOGUES_PATH, f"{dialogue_id}.json")
    path = save_path if os.path.exists(save_path) else os.path.join(DIALOGUES_PATH, f"{dialogue_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

COLOR_TEXT = (0, 0, 0)          # Цвета
COLOR_OPTION = (0, 255, 0)
COLOR_OPTION_HOVER = (255, 240, 200)
COLOR_OPTION_BG = (40, 35, 30, 0)
COLOR_OPTION_BG_HOVER = (60, 50, 40, 0)

COLOR_NPC_NAME = (150, 0, 0)     # Красный для NPC
COLOR_PLAYER_NAME = (100, 220, 100)  # Зеленый для игрока
COLOR_SKILL_NAME = (140, 75, 0)    # Золотой для навыков
COLOR_HISTORY_TEXT = (60, 60, 60) # Светло-серый для самого текста лога

ANSWER_FONT_SIZE = 14
QUESTION_FONT_SIZE = 14


class DialogueWindow:
    def __init__(self, screen, dialogue_data, player, scale, node_id=None):
        self.screen = screen
        sw, sh = screen.get_size()

        raw = pygame.image.load(os.path.join(ASSETS_PATH, "window.png")).convert_alpha()

        self.ui_scale = scale
        w = int(raw.get_width() * self.ui_scale)
        h = int(raw.get_height() * w / raw.get_width())

        self.image = pygame.transform.scale(raw, (w, h))

        self.rect = self.image.get_rect(midbottom=(sw // 2, sh))   # Расположение окна диалога

        # Загрузка текстуры полосы здоровья для диалога
        hp_bar_path = os.path.join(ASSETS_PATH, "health_bar_dialogue.png")
        raw_hp = pygame.image.load(hp_bar_path).convert_alpha()
        self.hp_w = int(raw_hp.get_width() * self.ui_scale)
        self.hp_h = int(raw_hp.get_height() * self.ui_scale)
        self.hp_img = pygame.transform.scale(raw_hp, (self.hp_w, self.hp_h))

        # Смещения полосы здоровья относительно верхнего левого угла окна диалога
        # (Эти значения нужно будет подогнать под твой дизайн)
        self.hp_offset_x = int(838 * self.ui_scale)
        self.hp_offset_y = int(179 * self.ui_scale)

        self.font = pygame.font.Font(FONT_PATH, int(ANSWER_FONT_SIZE * self.ui_scale))  # Текст ответа
        self.option_font = pygame.font.Font(FONT_PATH, int(QUESTION_FONT_SIZE * self.ui_scale))   # Текст вопросов
        self.hp_font = pygame.font.Font(FONT_PATH, int(8 * self.ui_scale))     # Уменьшенный шрифт специально для значений на полосе здоровья

        # Область текста NPC (координаты для спрайта window.png 960x192)
        self.text_offset_x = int(160 * self.ui_scale)
        self.text_offset_y = int(27 * self.ui_scale)
        self.text_width = int(316 * self.ui_scale)
        self.text_line_height = int(16 * self.ui_scale)
        self.scroll_speed = int(24 * self.ui_scale)    # Скорость прокрутки колёсиком
        self.text_height = int(156 * self.ui_scale) # Видимая высота области текста

        self.history_blocks = []  # Теперь храним список словарей {"lines": [...], "color": tuple}
        self.text_target_scroll = 0.0
        self.is_auto_scrolling = False  # Флаг автоматической прокрутки
        self.anchor_scroll = 0.0        # Якорь для последней реплики NPC/Навыка

        # Отступ сверху для новой реплики
        self.text_target_y = self.text_line_height * 2 
        self.last_speaker = None  # Отслеживаем, кто говорил последнимself.text_target_y = self.text_line_height * 1.5
        
        self.text_scrollbar = Scrollbar(
            pygame.Rect(
                self.rect.x + self.text_offset_x + self.text_width + int(10 * self.ui_scale),
                self.rect.y + self.text_offset_y,
                int(6 * self.ui_scale),
                self.text_height,
            ),
            self.scroll_speed,
            int(18 * self.ui_scale),
            track_color=(208, 160, 85),
            thumb_color=(168, 112, 40),
            thumb_drag_color=(255, 255, 255),
        )
        self.text_scrollbar.track_rect.x -= 1 

        # Область кнопок ответов
        self.options_offset_x = int(515 * self.ui_scale) #   Смещение от верхнего левого угла по x и y
        self.options_offset_y = int(30 * self.ui_scale)
        self.options_width = int(303 * self.ui_scale)    #   Ширина кнопок 
        self.option_line_height = int(14 * self.ui_scale)    #   Высота одной строки
        self.option_padding_y = int(5 * self.ui_scale)
        self.button_gap = int(5 * self.ui_scale)
        self.option_text_pad_x = int(8 * self.ui_scale)
        self.option_wrap_pad = int(20 * self.ui_scale)
        self.options_clip_y = int(25 * self.ui_scale)    # Верхняя граница clip-области (выше чем offset_y)
        self.options_height = int(158 * self.ui_scale)  # Видимая высота области ответов (от clip_y)

        self.total_options_h = 0    # Полная высота всех кнопок
        self.scrollbar = Scrollbar(
            pygame.Rect(
                self.rect.x + int(810 * self.ui_scale),
                self.rect.y + self.options_clip_y,
                int(6 * self.ui_scale),
                self.options_height,
            ),
            self.scroll_speed,
            int(18 * self.ui_scale),
        )
        self.scrollbar.track_rect.x += 6

        # Область портрета навыка (левая часть окна диалога)
        self.portrait_w = int(103 * self.ui_scale)
        self.portrait_h = int(144 * self.ui_scale)
        self.portrait_x = int(20 * self.ui_scale)
        self.portrait_y = int(22 * self.ui_scale)

        # Заглушка портрета NPC
        self.npc_portrait = self._build_npc_placeholder(dialogue_data.get("portrait", "???"))

        self.dialogue_data = dialogue_data  #   Дерево текущего диалога
        self.player = player
        self.active = True

        # Состояние пассивных проверок
        self.passive_state = None       # None | "continue" (ждём клик "Продолжить")
        self.passive_queue = []         # Очередь успешных проверок для показа
        self.current_portrait = None    # Загруженный портрет навыка (Surface или None)

        # Определяем стартовый узел через entry или напрямую
        if node_id is None:
            node_id = self._resolve_entry()
        self.set_node(node_id)      #   Устанавливаем первый узел (строит кнопки внутри)

    def _build_option_rects(self):  #   Строит прямоугольники для каждого варианта ответа.
        self.option_rects = []
        self.option_lines = []  # Завёрнутые строки для каждой кнопки
        start_x = self.rect.x + self.options_offset_x   #   Сдвиг относительно окна диалога
        base_y = self.rect.y + self.options_offset_y     #   Верх области ответов
        current_y = base_y

        for i in range(len(self.options)):  #   Добавляем все ответы на экран
            prefix = f"{i + 1}. "   #   Номер ответа
            lines = wrap_text(prefix + self.options[i], self.option_font, self.options_width - self.option_wrap_pad)
            self.option_lines.append(lines)

            btn_height = len(lines) * self.option_line_height + 2 * self.option_padding_y
            rect = pygame.Rect(start_x, current_y, self.options_width, btn_height)
            self.option_rects.append(rect)
            current_y += btn_height + self.button_gap

        # Полная высота контента и максимальная прокрутка
        # Видимое пространство для контента = options_height - (offset_y - clip_y)
        self.total_options_h = current_y - base_y
        visible_content_h = self.options_height - (self.options_offset_y - self.options_clip_y)
        self.scrollbar.set_content(
            self.total_options_h,
            visible_content_h,
            thumb_visible_height=self.options_height,
            reset=True,
        )

    def _add_text_to_history(self, text, color=COLOR_TEXT, speaker=None, speaker_color=COLOR_NPC_NAME):
        # 1. Мгновенно перекидываем экран к ЯКОРЮ (последней реплике NPC/Навыка).
        # Делаем это ТОЛЬКО если автопрокрутка не активна (т.е. это самое первое 
        # добавление после клика игрока).
        if not self.is_auto_scrolling and hasattr(self, 'anchor_scroll'):
            self.text_scrollbar.scroll_offset = self.anchor_scroll

        # 2. Добавление имени в историю (если спикер сменился)
        if speaker and speaker != self.last_speaker:
            self.history_blocks.append({
                "lines": [speaker], 
                "color": speaker_color, 
                "is_name": True
            })
            self.last_speaker = speaker
            
        # 3. Добавление самого текста
        lines = wrap_text(text, self.font, self.text_width)
        self.history_blocks.append({
            "lines": lines, 
            "color": color, 
            "is_name": False
        })
        
        # Считаем высоту контента
        total_lines = sum(len(block["lines"]) for block in self.history_blocks)
        total_h = total_lines * self.text_line_height
        
        start_line_idx = total_lines - len(lines)
        
        desired_scroll = (start_line_idx * self.text_line_height) - self.text_target_y
        desired_scroll = max(0, desired_scroll) 
        
        content_height = max(total_h, desired_scroll + self.text_height)
        
        self.text_scrollbar.set_content(
            content_height,
            self.text_height,
            thumb_visible_height=self.text_height
        )
        
        # 4. Задаем новую цель (в самом низу) и включаем линейную автопрокрутку
        self.text_target_scroll = desired_scroll
        self.is_auto_scrolling = True

        # 5. Обновляем якорь ТОЛЬКО если это реплика не от игрока.
        # Таким образом, якорь всегда будет указывать на последнюю фразу NPC или навыка.
        if speaker != "Игрок":
            self.anchor_scroll = desired_scroll

    def handle_scroll(self, dy):
        if not self.active:
            return
        mouse_pos = pygame.mouse.get_pos()
        # Если курсор находится в левой половине экрана — крутим историю диалога, иначе варианты ответов
        if mouse_pos[0] < self.rect.x + self.options_offset_x:
            self.text_scrollbar.handle_scroll(dy)
        else:
            self.scrollbar.handle_scroll(dy)

    def handle_mousedown(self, pos, button):
        if not self.active:
            return None
        if button == 1:
            if self.scrollbar.handle_mousedown(pos):
                return None
            if self.text_scrollbar.handle_mousedown(pos):
                return None
            return self.handle_click(pos)
        return None

    def handle_mouseup(self):
        self.scrollbar.handle_mouseup()
        self.text_scrollbar.handle_mouseup()

    def handle_mousemotion(self, pos):
        self.scrollbar.handle_mousemotion(pos)
        self.text_scrollbar.handle_mousemotion(pos)

    def handle_click(self, pos):
        if not self.active:
            return None

        # Проверяем попадание с учётом прокрутки
        clip_rect = pygame.Rect(
            self.rect.x + self.options_offset_x,
            self.rect.y + self.options_clip_y,
            self.options_width, self.options_height
        )
        if not clip_rect.collidepoint(pos):
            return None

        for i, rect in enumerate(self.option_rects):
            scrolled = rect.move(0, -self.scrollbar.scroll_offset)
            if scrolled.collidepoint(pos):

                # Клик при пассивной проверке
                if self.passive_state == "continue":

                    # Отложенный переход на ветку (текст уже был показан)
                    if self.passive_pending_node:
                        node_id = self.passive_pending_node
                        self.passive_pending_node = None
                        self.passive_state = None
                        self.passive_queue = []
                        self.set_node(node_id)
                        return "continue"

                    check = self.passive_queue.pop(0)

                    # Показываем текст и портрет проверки
                    skill_id = check.get("skill", "???")
                    dc = check.get("dc", 0)
                    
                    # Если в JSON есть поле "skill_name" ("Анализ [Успех]"), берем его. 
                    # Иначе генерируем из ID навыка и сложности (например: "Analysis [Сложность 2: Успех]")
                    skill_name = check.get("skill_name", f"{skill_id.capitalize()} [Сложность {dc}: Успех]")
                    
                    self._add_text_to_history(check["text"], color=COLOR_HISTORY_TEXT, speaker=skill_name, speaker_color=COLOR_SKILL_NAME)
                    self.current_portrait = self._load_portrait(check.get("portrait"))

                    # Кнопка после текст проверки — из option_text самой проверки
                    btn_text = check.get("option_text", ">_")

                    if check.get("success_node"):
                        # Следующий клик уведёт в ветку
                        self.passive_pending_node = check["success_node"]
                        self.option_data = [{"text": btn_text, "next": None}]
                        self.options = [btn_text]
                        self._build_option_rects()
                    elif self.passive_queue:
                        # Ещё есть проверки
                        self.option_data = [{"text": btn_text, "next": None}]
                        self.options = [btn_text]
                        self._build_option_rects()
                    else:
                        # Все проверки показаны — оригинальные ответы с фильтрацией по флагам
                        self.passive_state = None
                        node = self.dialogue_data[self.current_node_id]
                        visible = []
                        for opt in node["options"]:
                            required_flag = opt.get("flag")
                            if required_flag is None or self.player.get_flag(required_flag):
                                visible.append(opt)
                        self.option_data = visible
                        self.options = [opt["text"] for opt in visible]
                        self._build_option_rects()
                    return "continue"

                opt = self.option_data[i]
                if self.passive_state != "continue" and opt.get("text") and opt.get("text") != ">_":
                    self._add_text_to_history(f"— {opt['text']}", color=COLOR_HISTORY_TEXT, speaker="Игрок", speaker_color=COLOR_PLAYER_NAME)
                damage = opt.get("damage_on_failure", 0)
                if damage:
                    self.player.take_damage(damage)

                self._apply_option_effects(opt)

                if "change_to" in opt:
                    self.active = False
                    return {"action": "change_tile", "change_to": opt["change_to"]}

                #   Вариант с проверкой навыка
                if "check" in opt:
                    self.pending_check = opt["check"]
                    return "check"

                #   Обычный вариант
                next_node = opt.get("next")
                if next_node is None:
                    self.active = False
                    return "close"
                else:
                    self.set_node(next_node)
                    return "continue"

        return None

    def _resolve_entry(self):   #   Выбирает стартовый узел: проверяет entry-правила сверху вниз, возвращает первый подходящий.
        entry = self.dialogue_data.get("entry")
        if entry:
            for rule in entry:      #   Смотрим какое состояние сейчас у NPC
                flag = rule.get("flag")     
                if flag is None or self.player.get_flag(flag):  #   В зависимости от состояния запускаем стартовый диалог
                    return rule["node"]
        return "start"

    def _build_npc_placeholder(self, npc_portrait): #   Создаёт заглушку портрета NPC — серый прямоугольник с именем."""
        if not npc_portrait:
            return None
        path = os.path.join(PORTRAIT_PATH, f"{npc_portrait}.png")
        if not os.path.exists(path):
            return None
        raw = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(raw, (self.portrait_w, self.portrait_h))

    def _load_portrait(self, skill_name):   #   Загружает и масштабирует портрет навыка из assets/skills/.
        if not skill_name:
            return None
        path = os.path.join(SKILLS_PATH, f"{skill_name}.png")
        if not os.path.exists(path):
            return None
        raw = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(raw, (self.portrait_w, self.portrait_h))

    def _set_flags(self, flags):
        if not flags:
            return
        if isinstance(flags, str):
            self.player.set_flag(flags)
            return
        if isinstance(flags, list):
            for flag in flags:
                if isinstance(flag, str):
                    self.player.set_flag(flag)

    def _remove_flags(self, flags):
        if not flags:
            return
        if isinstance(flags, str):
            self.player.flags.pop(flags, None)
            return
        if isinstance(flags, list):
            for flag in flags:
                if isinstance(flag, str):
                    self.player.flags.pop(flag, None)

    def _remove_item(self, item_data):
        if isinstance(item_data, str):
            item_id = item_data
            count = 1
        elif isinstance(item_data, dict):
            item_id = item_data.get("id")
            count = item_data.get("count", 1)
        else:
            return

        if not item_id:
            return

        remaining = max(1, int(count))
        for idx, slot in enumerate(self.player.inventory):
            if remaining <= 0:
                break
            if not slot or slot.get("id") != item_id:
                continue

            slot_count = slot.get("count", 1)
            if slot_count > remaining:
                slot["count"] = slot_count - remaining
                remaining = 0
            else:
                remaining -= slot_count
                self.player.inventory[idx] = None

    def _remove_items(self, items):
        if not items:
            return
        if isinstance(items, (str, dict)):
            self._remove_item(items)
            return
        if isinstance(items, list):
            for item in items:
                self._remove_item(item)

    def _apply_option_effects(self, opt):
        self._remove_flags(opt.get("remove_flag"))
        self._remove_items(opt.get("remove_item"))

    def set_node(self, node_id):
        node = self.dialogue_data[node_id]
        self.current_node_id = node_id

        # Ставим флаг, если узел его задаёт
        self._set_flags(node.get("set_flag"))

        # Определяем, кто сейчас говорит (навык или NPC)
        speaker_name = node.get("speaker_name")
        if not speaker_name:
            if node.get("portrait"):
                speaker_name = node["portrait"].capitalize() # Имя навыка, если это нода навыка
                speaker_color = COLOR_SKILL_NAME
            else:
                speaker_name = self.dialogue_data.get("npc_name", "???")
                speaker_color = COLOR_NPC_NAME
        else:
            speaker_color = COLOR_NPC_NAME

        self._add_text_to_history(node["text"], color=COLOR_HISTORY_TEXT, speaker=speaker_name, speaker_color=speaker_color)

        # Портрет навыка из поля "portrait" узла (для узлов-реплик навыка)
        portrait_name = node.get("portrait")
        self.current_portrait = self._load_portrait(portrait_name) if portrait_name else None

        # Пассивные проверки навыков
        self.passive_state = None
        self.passive_queue = []
        self.passive_pending_node = None

        checks = node.get("passive_checks") or []

        for check in checks:
            skill_val = self.player.get_skill(check["skill"])
            if skill_val >= check["dc"]:
                self.passive_queue.append(check)
                # Ставим флаг при успешной проверке
                self._set_flags(check.get("set_flag"))

        # Вставки идут первыми, переходы на ветку — последними
        self.passive_queue.sort(key=lambda c: 1 if c.get("success_node") else 0)

        if self.passive_queue:
            self.passive_state = "continue"
            self.option_data = [{"text": ">_", "next": None}]
            self.options = [">_"]
            self._build_option_rects()
            return

        # Фильтруем опции по флагам — скрываем те, чей флаг не установлен
        visible = []
        for opt in node["options"]:
            required_flag = opt.get("flag")
            if required_flag is None or self.player.get_flag(required_flag):
                visible.append(opt)

        self.option_data = visible
        self.options = [opt["text"] for opt in visible]
        self._build_option_rects()

    def draw(self):
        if not self.active:
            return
        
        # --- ЛИНЕЙНАЯ АВТОПРОКРУТКА ---
        if self.is_auto_scrolling:
            diff = self.text_target_scroll - self.text_scrollbar.scroll_offset
            scroll_speed = 14  # Скорость движения (можешь поменять: больше - быстрее)
            
            if abs(diff) <= scroll_speed:
                # Если расстояние до цели меньше скорости шага, примагничиваемся к финишу
                self.text_scrollbar.scroll_offset = self.text_target_scroll
                self.is_auto_scrolling = False # Достигли цели - отключаем
            else:
                # Линейно шагаем вниз или вверх
                self.text_scrollbar.scroll_offset += scroll_speed if diff > 0 else -scroll_speed

        self.screen.blit(self.image, self.rect)

        # --- Отрисовка полосы здоровья игрока ---
        if hasattr(self, 'hp_img') and self.hp_img:
            # Получаем актуальные данные о здоровье игрока
            max_hp = self.player.get_max_health()
            current_hp = self.player.health_points
            
            # Рассчитываем соотношение
            hp_ratio = max(0.0, min(1.0, current_hp / max_hp)) if max_hp > 0 else 0.0
            render_w = int(self.hp_w * hp_ratio)
            
            # Отрисовываем только заполненную часть (через clip-прямоугольник в tuple)
            if render_w > 0:
                hp_draw_x = self.rect.x + self.hp_offset_x
                hp_draw_y = self.rect.y + self.hp_offset_y
                self.screen.blit(self.hp_img, (hp_draw_x, hp_draw_y), (0, 0, render_w, self.hp_h))

        # --- Текст здоровья (текущее/максимальное) по центру ---
        hp_text = f"{current_hp}/{max_hp}"
            
            # Рендерим сам текст и черную тень для читаемости
        label = self.hp_font.render(hp_text, True, (255, 255, 255))
        shadow = self.hp_font.render(hp_text, True, (0, 0, 0))
            
        # Вычисляем координаты центра полосы здоровья
        center_x = hp_draw_x + self.hp_w // 2
        center_y = hp_draw_y + self.hp_h // 2
            
         # Получаем прямоугольник текста для центрирования
        label_rect = label.get_rect(center=(center_x, center_y))
            
        # Вычисляем смещение тени с учетом масштабирования интерфейса (как в ActionBar)
        shadow_x = label_rect.x + (2 * self.ui_scale)
        shadow_y = label_rect.y + (1 * self.ui_scale)
            
        # Отрисовываем сначала тень, затем основной текст сверху
        self.screen.blit(shadow, (shadow_x, shadow_y))
        self.screen.blit(label, label_rect)

        # Портрет (навык или заглушка NPC) 
        px = self.rect.x + self.portrait_x
        py = self.rect.y + self.portrait_y
        if self.current_portrait:
            self.screen.blit(self.current_portrait, (px, py))
        elif self.npc_portrait:
            self.screen.blit(self.npc_portrait, (px, py))

        mouse_pos = pygame.mouse.get_pos()

        # --- 1. ЛЕВАЯ ЧАСТЬ: ИСТОРИЯ ДИАЛОГОВ ---
        text_x = self.rect.x + self.text_offset_x
        text_y = self.rect.y + self.text_offset_y
        
        text_clip_rect = pygame.Rect(
            text_x, text_y, 
            self.text_width + int(20 * self.ui_scale), self.text_height
        )
        self.screen.set_clip(text_clip_rect)
        
        current_line_idx = 0
        
        for block_i, block in enumerate(self.history_blocks):
            is_last_block = (block_i == len(self.history_blocks) - 1)
            
            # Определяем цвет: 
            # - Имена всегда сохраняют свой уникальный цвет
            # - Обычный текст становится черным, если это последний блок, иначе серым
            if block.get("is_name", False):
                current_color = block["color"]
            else:
                current_color = COLOR_TEXT if is_last_block else COLOR_HISTORY_TEXT

            for line in block["lines"]:
                draw_y = text_y + current_line_idx * self.text_line_height - self.text_scrollbar.scroll_offset
                
                # Рендерим только видимые строки
                if text_y - self.text_line_height <= draw_y <= text_y + self.text_height:
                    surf = self.font.render(line, False, current_color)
                    self.screen.blit(surf, (text_x, draw_y))
                
                current_line_idx += 1
                
        self.screen.set_clip(None)
        self.text_scrollbar.draw(self.screen)

        # --- 2. ПРАВАЯ ЧАСТЬ: ВАРИАНТЫ ОТВЕТОВ ИГРОКА ---
        options_clip_rect = pygame.Rect(
            self.rect.x + self.options_offset_x,
            self.rect.y + self.options_clip_y,
            self.options_width + 16, self.options_height
        )
        self.screen.set_clip(options_clip_rect)

        for i in range(len(self.option_rects)):
            rect = self.option_rects[i]
            draw_y = rect.y - self.scrollbar.scroll_offset
            hovered = pygame.Rect(rect.x, draw_y, rect.w, rect.h).collidepoint(mouse_pos)

            # Фон кнопки
            bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg.fill(COLOR_OPTION_BG_HOVER if hovered else COLOR_OPTION_BG)
            self.screen.blit(bg, (rect.x, draw_y))

            # Текст варианта
            color = COLOR_OPTION_HOVER if hovered else COLOR_OPTION
            lines = self.option_lines[i]
            for j in range(len(lines)):
                text_surf = self.option_font.render(lines[j], True, color)
                self.screen.blit(text_surf, (
                    rect.x + self.option_text_pad_x,
                    draw_y + self.option_padding_y + j * self.option_line_height
                ))

        self.scrollbar.draw(self.screen)
        self.screen.set_clip(None)
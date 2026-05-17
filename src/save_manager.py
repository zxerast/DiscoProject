import json
import os
import shutil

from settings import BASE_DIR, SAVE_DIR


SAVE_PLAYER_PATH = os.path.join(SAVE_DIR, "player.json")
SAVE_ROOMS_PATH = os.path.join(SAVE_DIR, "rooms.json")


def json_file(path, data=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if data is None:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)    #   Дампим питоновский код в джэсон


def rooms_to_state(rooms):
    return {
        location_id: room.to_state()    #   map -> метод который особым образом дампит параметры комнаты в JSON
        for location_id, room in rooms.items()
    }


def ensure_initial_save(rooms):
    os.makedirs(SAVE_DIR, exist_ok=True)    #   Создаём директория под сейвы

    for filename in ["player.json", "items.json", "quests.json"]:   #   Закидываем туда готовые json стартового состояния мира
        src = os.path.join(BASE_DIR, filename)
        dst = os.path.join(SAVE_DIR, filename)

        if not os.path.exists(dst) and os.path.exists(src): #   Но только если там пусто иначе прогресс затрём
            shutil.copy2(src, dst)

    if not os.path.exists(SAVE_ROOMS_PATH):
        json_file(SAVE_ROOMS_PATH, rooms_to_state(rooms))   #   Записываем данные о комнатах в виде JSON получая его из .py файлов

    src_dialogues = os.path.join(BASE_DIR, "dialogues")
    dst_dialogues = os.path.join(SAVE_DIR, "dialogues")

    if os.path.isdir(src_dialogues) and not os.path.exists(dst_dialogues):  #   Ну и диалоги тоже кидаем
        shutil.copytree(src_dialogues, dst_dialogues)


def load_rooms_state(rooms):
    if not os.path.exists(SAVE_ROOMS_PATH):
        return

    state = json_file(SAVE_ROOMS_PATH)

    for location_id, room_state in state.items():   #   Загружаем состояние комнат по сохранённым JSON
        if location_id in rooms:
            rooms[location_id].load_state(room_state)   #   map -> методы для преобразования из JSON в py


def get_saved_location(default="test"):         #   Берём послднюю сохранённую локацию перса
    if not os.path.exists(SAVE_PLAYER_PATH):
        return default

    return json_file(SAVE_PLAYER_PATH).get("location", default)


def save_game(player, rooms):
    os.makedirs(SAVE_DIR, exist_ok=True)
    player.save()                                       #   player -> сохраняем игрока
    json_file(SAVE_ROOMS_PATH, rooms_to_state(rooms))

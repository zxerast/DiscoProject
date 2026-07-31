import json

class Actions:
    def __init__(self, path: str, player_data: dict):
        self.player_data = player_data
        
        with open(path, 'r', encoding='utf-8') as file:
            self.actions_db = json.load(file)
        
        # Разделяем базу для удобного доступа
        self._all_player_actions = self.actions_db.get("player_actions", {})
        self._all_weapon_actions = self.actions_db.get("weapon_actions", {})

    def _check_flags(self, required_flags: list) -> bool:
        if not required_flags:
            return True # Если флагов не требуется, действие доступно
        
        player_flags = self.player_data.get("flags", {})
      
        # Проверяем, что все нужные флаги присутствуют в словаре флагов игрока и равны True
        return all(player_flags.get(flag, False) for flag in required_flags)

    def get_available_actions(self, equipped_weapon_category: str = "unarmed") -> list:
        available = []
        # 1. Действия игрока по флагам
        for action_id, data in self._all_player_actions.items():
            if self._check_flags(data.get("required_flags", [])):
                item = data.copy()
                item["id"] = action_id
                available.append(item)
                
        # 2. Действия оружием
        weapon_group = self._all_weapon_actions.get(equipped_weapon_category, self._all_weapon_actions.get("unarmed", {}))
        for action_id, data in weapon_group.items():
            item = data.copy()
            item["id"] = action_id
            available.append(item)
            
        return available

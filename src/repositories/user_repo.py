from typing import Dict, List, Optional
from src.repositories.json_repository import JsonRepository

class UserRepository(JsonRepository):
    def __init__(self, filepath: str = "data/users.json"):
        super().__init__(filepath)

    def get_all(self) -> List[Dict]:
        return self.read_json()

    def get_by_email(self, email: str) -> Optional[Dict]:
        for raw in self.get_all():
            if raw.get("email", "").lower() == email.lower():
                return raw
        return None

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        for raw in self.get_all():
            if raw.get("id") == user_id:
                return raw
        return None

    def save_all(self, users: List[Dict]) -> bool:
        return self.write_json(users)

    def add_user(self, user_data: Dict) -> bool:
        users = self.get_all()
        users.append(user_data)
        return self.save_all(users)

    def update_user(self, user_data: Dict) -> bool:
        users = self.get_all()
        updated = False
        for idx, raw in enumerate(users):
            if raw.get("id") == user_data.get("id"):
                users[idx] = user_data
                updated = True
                break
        if not updated:
            users.append(user_data)
        return self.save_all(users)

    def next_sequence(self, role: str) -> str:
        raw_users = self.get_all()
        prefix = role.upper()
        existing = [u for u in raw_users if u.get("role") == role]
        if not existing:
            return "001"

        max_number = 0
        for user in existing:
            identifier = user.get("id", "")
            if identifier.startswith(f"{prefix}-"):
                try:
                    number = int(identifier.split("-")[-1])
                    max_number = max(max_number, number)
                except ValueError:
                    continue
        return str(max_number + 1).zfill(3)

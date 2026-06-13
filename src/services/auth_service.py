import hashlib
import logging
import uuid
from typing import Dict, Optional
from src.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
_user_repo = UserRepository()
_token_store: Dict[str, Dict] = {}


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def _generate_token() -> str:
    return uuid.uuid4().hex


def register_user(name: str, email: str, password: str, role: str) -> Dict:
    if not name or not email or not password or role not in {"SME", "EXPERT"}:
        raise ValueError("Dữ liệu đăng ký không hợp lệ.")

    existing = _user_repo.get_by_email(email)
    if existing:
        raise ValueError("Email này đã được đăng ký.")

    next_id = f"{role}-{_user_repo.next_sequence(role)}"
    user = {
        "id": next_id,
        "email": email,
        "name": name,
        "role": role,
        "auth_provider": "local",
        "password_hash": _hash_password(password),
        "created_at": "2026-06-11T00:00:00Z",
    }

    saved = _user_repo.add_user(user)
    if not saved:
        raise IOError("Không thể lưu thông tin tài khoản.")

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "auth_provider": user["auth_provider"],
    }


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    user = _user_repo.get_by_email(email)
    if not user:
        return None

    if user.get("password_hash") != _hash_password(password):
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "auth_provider": user["auth_provider"],
    }


def create_access_token(user_info: Dict) -> str:
    token = _generate_token()
    _token_store[token] = user_info
    return token


def validate_token(token: str) -> Optional[Dict]:
    return _token_store.get(token)

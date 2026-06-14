"""
Module  : src/services/auth_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý nghiệp vụ xác thực và quản lý Profile người dùng.

Luồng Register:
    payload → verify Firebase token → check duplicate email
    → build profile dict → insert MongoDB → trả về profile

Luồng Login:
    payload → verify Firebase token → lấy email từ token
    → find_by_email → trả về profile (Frontend tự quản lý session bằng Firebase token)

Thiết kế ID người dùng:
    SME    : id = "SME-" + firebase_uid  (vd: "SME-abc123xyz")
    Expert : id = "EXP-" + firebase_uid  (vd: "EXP-abc123xyz")
    → ID ổn định, không thay đổi, liên kết trực tiếp với Firebase UID.

Exception convention:
    ValueError   → 400 Bad Request  (email đã tồn tại, role không hợp lệ, payload thiếu)
    LookupError  → 404 Not Found    (tài khoản chưa tạo hồ sơ)
    PermissionError → 401           (token Firebase không hợp lệ)
    IOError      → 500 Server Error (ghi MongoDB thất bại)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from firebase_admin import auth
from firebase_admin.auth import (
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
)
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.repositories.auth_repo import AuthRepository

logger = logging.getLogger(__name__)

# Tập hợp role hợp lệ — dễ mở rộng thêm sau
_VALID_ROLES = frozenset({"SME", "EXPERT"})

# Module-level singleton repository
_auth_repo = AuthRepository()


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _verify_firebase_token(token: str) -> dict:
    """
    Xác minh Firebase ID Token và trả về decoded payload.

    Args:
        token: Firebase ID Token từ Frontend.

    Returns:
        dict decoded token chứa uid, email, và các claims khác.

    Raises:
        PermissionError: Nếu token hết hạn, bị thu hồi, hoặc không hợp lệ.
    """
    try:
        decoded = auth.verify_id_token(token)
        logger.debug(
            "[AuthService._verify_firebase_token] Token hợp lệ — uid='%s'.",
            decoded.get("uid"),
        )
        return decoded

    except ExpiredIdTokenError:
        raise PermissionError("Token Firebase đã hết hạn. Vui lòng đăng nhập lại.")
    except RevokedIdTokenError:
        raise PermissionError("Token Firebase đã bị thu hồi. Vui lòng đăng nhập lại.")
    except InvalidIdTokenError:
        raise PermissionError("Token Firebase không hợp lệ.")
    except Exception as exc:
        logger.error(
            "[AuthService._verify_firebase_token] Lỗi không xác định: %s", str(exc)
        )
        raise PermissionError(f"Xác thực thất bại: {exc}") from exc


def _now_iso() -> str:
    """Trả về timestamp UTC hiện tại dạng ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _build_sme_dict(uid: str, name: str, email: str) -> dict:
    """
    Tạo dict SME mặc định để insert MongoDB.
    Các trường "Chưa cập nhật" sẽ được hoàn thiện qua Profile Update sau.
    """
    return {
        "id": f"SME-{uid}",
        "firebase_uid": uid,
        "company_name": name,
        "email": email.lower().strip(),
        "industry": "Chưa cập nhật",
        "contact_email": email.lower().strip(),
        "founded_year": None,
        "employee_count": None,
        "pain_points": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _build_expert_dict(uid: str, name: str, email: str) -> dict:
    """
    Tạo dict Expert mặc định để insert MongoDB.
    Các trường "Chưa cập nhật" sẽ được hoàn thiện qua Profile Update sau.
    """
    return {
        "id": f"EXP-{uid}",
        "firebase_uid": uid,
        "expert_name": name,
        "email": email.lower().strip(),
        "institution": "Chưa cập nhật",
        "department": "Chưa cập nhật",
        "specialties": [],
        "available_technologies": [],
        "research_areas": "Chưa cập nhật",
        "active_projects_count": 0,
        "is_available": True,
        "rating": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


# ------------------------------------------------------------------
# Public service functions
# ------------------------------------------------------------------

def register_user(payload: dict) -> dict:
    """
    Đăng ký tài khoản mới — tạo Profile trong MongoDB sau khi xác minh Firebase token.

    Luồng xử lý:
        1. Validate payload đầu vào (token, name, role, email).
        2. Xác minh Firebase token → lấy uid thực tế.
        3. Kiểm tra email đã tồn tại chưa (tránh duplicate profile).
        4. Build dict profile theo role (SME / EXPERT).
        5. Lưu vào collection tương ứng.
        6. Trả về profile dict kèm trường "role" cho Controller.

    Args:
        payload: dict từ request body gồm:
            - token (str)  : Firebase ID Token — bắt buộc.
            - name  (str)  : Tên người dùng / công ty — bắt buộc.
            - role  (str)  : "SME" hoặc "EXPERT" — bắt buộc.
            - email (str)  : Địa chỉ email — bắt buộc.

    Returns:
        dict Profile vừa tạo kèm trường "role".

    Raises:
        ValueError     : Thiếu field, role không hợp lệ, email đã tồn tại.
        PermissionError: Firebase token không hợp lệ / hết hạn.
        IOError        : Ghi MongoDB thất bại.
    """
    # ── Validate payload ───────────────────────────────────────────────
    token = (payload.get("token") or "").strip()
    name = (payload.get("name") or "").strip()
    role = (payload.get("role") or "").strip().upper()
    email = (payload.get("email") or "").strip().lower()

    if not token:
        raise ValueError("Trường 'token' là bắt buộc.")
    if not name:
        raise ValueError("Trường 'name' (tên người dùng / công ty) là bắt buộc.")
    if not email:
        raise ValueError("Trường 'email' là bắt buộc.")
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Trường 'role' không hợp lệ: '{role}'. "
            f"Chỉ chấp nhận: {', '.join(_VALID_ROLES)}."
        )

    # ── Xác minh Firebase token → lấy uid ─────────────────────────────
    decoded_token = _verify_firebase_token(token)
    uid = decoded_token["uid"]
    firebase_email = decoded_token.get("email", email)

    # Ưu tiên email từ Firebase token (đã được xác thực) hơn payload
    verified_email = firebase_email.lower().strip() if firebase_email else email

    # ── Kiểm tra email đã tồn tại chưa ────────────────────────────────
    existing = _auth_repo.find_by_email(verified_email)
    if existing is not None:
        raise ValueError(
            f"Email '{verified_email}' đã được đăng ký với vai trò "
            f"'{existing.get('role')}'. Vui lòng đăng nhập."
        )

    # ── Build profile dict theo role ───────────────────────────────────
    if role == "SME":
        profile_dict = _build_sme_dict(uid=uid, name=name, email=verified_email)
        try:
            _auth_repo.create_sme(profile_dict)
        except DuplicateKeyError:
            raise ValueError(
                f"Email '{verified_email}' hoặc Firebase UID đã tồn tại trong hệ thống."
            )
        except PyMongoError as exc:
            raise IOError(f"Lỗi hệ thống: Không thể tạo hồ sơ SME. Chi tiết: {exc}") from exc

    else:  # EXPERT
        profile_dict = _build_expert_dict(uid=uid, name=name, email=verified_email)
        try:
            _auth_repo.create_expert(profile_dict)
        except DuplicateKeyError:
            raise ValueError(
                f"Email '{verified_email}' hoặc Firebase UID đã tồn tại trong hệ thống."
            )
        except PyMongoError as exc:
            raise IOError(
                f"Lỗi hệ thống: Không thể tạo hồ sơ Expert. Chi tiết: {exc}"
            ) from exc

    # ── Inject role vào kết quả trả về ────────────────────────────────
    profile_dict["role"] = role

    # Loại bỏ firebase_uid khỏi response (thông tin nội bộ)
    profile_dict.pop("firebase_uid", None)
    profile_dict.pop("_id", None)
    logger.info(
        "[AuthService.register_user] Tạo tài khoản thành công — "
        "id='%s', role='%s', email='%s'.",
        profile_dict.get("id"), role, verified_email,
    )
    return profile_dict


def login_user(payload: dict) -> dict:
    """
    Đăng nhập — xác minh Firebase token và trả về Profile từ MongoDB.

    Backend không phát hành JWT riêng. Frontend tự quản lý session
    bằng Firebase ID Token và refresh token.
    Backend chỉ xác minh token và trả về Profile đầy đủ để Frontend render UI.

    Luồng xử lý:
        1. Lấy và validate token từ payload.
        2. Xác minh Firebase token → lấy email.
        3. Tìm Profile theo email trong MongoDB.
        4. Nếu chưa có Profile → raise LookupError (chưa đăng ký).
        5. Trả về Profile dict kèm trường "role".

    Args:
        payload: dict từ request body gồm:
            - token (str): Firebase ID Token — bắt buộc.

    Returns:
        dict Profile đầy đủ kèm trường "role".

    Raises:
        ValueError     : Thiếu token trong payload.
        PermissionError: Firebase token không hợp lệ / hết hạn.
        LookupError    : Tài khoản Firebase hợp lệ nhưng chưa tạo hồ sơ.
    """
    # ── Validate payload ───────────────────────────────────────────────
    token = (payload.get("token") or "").strip()
    if not token:
        raise ValueError("Trường 'token' là bắt buộc.")

    # ── Xác minh Firebase token → lấy email ───────────────────────────
    decoded_token = _verify_firebase_token(token)
    email = decoded_token.get("email", "").lower().strip()

    if not email:
        # Một số Firebase provider (phone auth) không có email
        # Fallback: tìm theo UID
        uid = decoded_token["uid"]
        logger.warning(
            "[AuthService.login_user] Token không chứa email — "
            "fallback tìm theo uid='%s'.", uid,
        )
        profile = _auth_repo.find_by_uid(uid)
    else:
        profile = _auth_repo.find_by_email(email)

    # ── Kiểm tra hồ sơ tồn tại ────────────────────────────────────────
    if profile is None:
        raise LookupError(
            "Tài khoản Firebase hợp lệ nhưng chưa có hồ sơ trong hệ thống. "
            "Vui lòng đăng ký trước."
        )

    # Loại bỏ thông tin nội bộ khỏi response
    profile.pop("firebase_uid", None)

    logger.info(
        "[AuthService.login_user] Đăng nhập thành công — "
        "id='%s', role='%s', email='%s'.",
        profile.get("id"), profile.get("role"), email,
    )
    return profile
"""
Module  : src/controllers/auth_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa API endpoints cho Firebase Auth & Profile Management.

Nguyên tắc tuyệt đối:
    - Controller KHÔNG chứa bất kỳ business logic hay Firebase logic nào.
    - Chỉ: nhận request → validate sơ bộ → gọi service → trả response.
    - Mọi Exception từ Service đều bị bắt và map sang HTTP status code chuẩn.

Exception → HTTP mapping:
    ValueError      → 400 Bad Request      (input không hợp lệ, email duplicate)
    PermissionError → 401 Unauthorized     (Firebase token lỗi / hết hạn)
    LookupError     → 404 Not Found        (chưa có hồ sơ)
    IOError         → 500 Internal Error   (ghi MongoDB thất bại)
    Exception       → 500 Internal Error   (lỗi không xác định)

Endpoints:
    POST /api/auth/register  — Đăng ký tài khoản mới
    POST /api/auth/login     — Đăng nhập và lấy Profile
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.auth_service import register_user, login_user

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ------------------------------------------------------------------
# Response helpers
# ------------------------------------------------------------------

def _ok(data, message: str = "", status_code: int = 200):
    """Trả về HTTP response thành công theo chuẩn dự án."""
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
    }), status_code


def _err(message: str, status_code: int = 400):
    """Trả về HTTP response lỗi theo chuẩn dự án."""
    return jsonify({
        "success": False,
        "message": message,
        "data": None,
    }), status_code


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /api/auth/register
    Đăng ký tài khoản mới — tạo Profile SME hoặc Expert trong MongoDB.

    Request body (JSON):
    {
        "token" : "eyJhbGciOiJSUzI1NiIs...",  ← Firebase ID Token (bắt buộc)
        "name"  : "Công ty CP Xanh Việt",      ← Tên hiển thị / công ty (bắt buộc)
        "role"  : "SME",                        ← "SME" hoặc "EXPERT" (bắt buộc)
        "email" : "contact@xanhviet.com.vn"     ← Email (bắt buộc)
    }

    Response 201 (thành công):
    {
        "success": true,
        "message": "Đăng ký thành công. Chào mừng Công ty CP Xanh Việt!",
        "data": {
            "id"           : "SME-firebase_uid_here",
            "company_name" : "Công ty CP Xanh Việt",
            "email"        : "contact@xanhviet.com.vn",
            "role"         : "SME",
            "industry"     : "Chưa cập nhật",
            "pain_points"  : [],
            "created_at"   : "2025-01-10T08:30:00",
            ...
        }
    }

    Response 400: Thiếu field, role không hợp lệ, email đã tồn tại.
    Response 401: Firebase token hết hạn hoặc không hợp lệ.
    Response 500: Lỗi ghi MongoDB.
    """
    body = request.get_json(silent=True) or {}

    # ── Kiểm tra sơ bộ tại Controller (trước khi vào Service) ─────────
    if not body.get("token"):
        return _err("Trường 'token' là bắt buộc trong request body.", 400)

    try:
        user_profile = register_user(payload=body)

        # Lấy tên hiển thị để cá nhân hóa message
        display_name = (
            user_profile.get("company_name")
            or user_profile.get("expert_name")
            or "bạn"
        )

        return _ok(
            # Gói dữ liệu lại cho khớp với kỳ vọng của Frontend
            data={
                "access_token": body.get("token"), 
                        "user": user_profile
            },
            message=f"Đăng ký thành công. Chào mừng {body.get('name')}!",
            status_code=201,
        )

    except ValueError as exc:
        logger.warning("[AuthController.register] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except PermissionError as exc:
        logger.warning("[AuthController.register] PermissionError: %s", str(exc))
        return _err(str(exc), 401)

    except IOError as exc:
        logger.error("[AuthController.register] IOError: %s", str(exc))
        return _err(str(exc), 500)

    except Exception as exc:
        logger.error(
            "[AuthController.register] Unexpected error: %s", str(exc), exc_info=True
        )
        return _err("Lỗi hệ thống không xác định. Vui lòng thử lại sau.", 500)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Đăng nhập — xác minh Firebase token và trả về Profile đầy đủ.

    Backend không phát hành JWT riêng. Frontend tiếp tục dùng Firebase
    token để xác thực các request sau (thông qua @require_auth middleware).

    Request body (JSON):
    {
        "token": "eyJhbGciOiJSUzI1NiIs..."  ← Firebase ID Token (bắt buộc)
    }

    Response 200 (thành công):
    {
        "success": true,
        "message": "Đăng nhập thành công.",
        "data": {
            "id"           : "SME-firebase_uid_here",
            "company_name" : "Công ty CP Xanh Việt",
            "email"        : "contact@xanhviet.com.vn",
            "role"         : "SME",
            "industry"     : "Chế biến thực phẩm",
            ...
        }
    }

    Response 400: Thiếu token trong body.
    Response 401: Firebase token hết hạn hoặc không hợp lệ.
    Response 404: Tài khoản Firebase hợp lệ nhưng chưa tạo hồ sơ.
    Response 500: Lỗi hệ thống.
    """
    body = request.get_json(silent=True) or {}

    if not body.get("token"):
        return _err("Trường 'token' là bắt buộc trong request body.", 400)

    try:
        user_profile = login_user(payload=body)

        return _ok(
            # Gói dữ liệu lại cho khớp với kỳ vọng của Frontend
            data={
                "access_token": body.get("token"),
                "user": user_profile
            },
            message="Đăng nhập thành công.",
            status_code=200,
        )

    except ValueError as exc:
        logger.warning("[AuthController.login] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except PermissionError as exc:
        logger.warning("[AuthController.login] PermissionError: %s", str(exc))
        return _err(str(exc), 401)

    except LookupError as exc:
        logger.warning("[AuthController.login] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except Exception as exc:
        logger.error(
            "[AuthController.login] Unexpected error: %s", str(exc), exc_info=True
        )
        return _err("Lỗi hệ thống không xác định. Vui lòng thử lại sau.", 500)
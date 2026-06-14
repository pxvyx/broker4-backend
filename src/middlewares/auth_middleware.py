"""
Module  : src/middlewares/auth_middleware.py
Layer   : Middlewares
Purpose : Decorator @require_auth — xác thực Firebase ID Token trên mọi route cần bảo vệ.

Luồng xác thực:
    1. Đọc header: Authorization: Bearer <firebase_id_token>
    2. Gọi firebase_admin.auth.verify_id_token(token) để giải mã.
    3. Nếu hợp lệ → gán request.user = {"uid": ..., "email": ...} → tiếp tục.
    4. Nếu lỗi   → trả HTTP 401 ngay, không gọi handler tiếp theo.

Cách dùng trong Controller:
    from src.middlewares.auth_middleware import require_auth

    @profile_bp.route("/me", methods=["GET"])
    @require_auth
    def get_my_profile():
        uid = request.user["uid"]
        ...

Lưu ý:
    - @require_auth phải đặt SAU @bp.route() (Python decorator stack từ dưới lên).
    - request.user chỉ tồn tại trong vòng đời của một request — thread-safe.
"""

import logging
from functools import wraps
from typing import Callable

from firebase_admin import auth
from firebase_admin.auth import (
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    CertificateFetchError,
)
from flask import request, jsonify

logger = logging.getLogger(__name__)


def _unauthorized(message: str):
    """Trả về HTTP 401 Unauthorized theo chuẩn response của dự án."""
    return jsonify({
        "success": False,
        "message": message,
        "data": None,
    }), 401


def require_auth(func: Callable) -> Callable:
    """
    Decorator bảo vệ route — yêu cầu Firebase ID Token hợp lệ.

    Sau khi xác thực thành công, inject thông tin user vào request:
        request.user = {
            "uid"  : "firebase_uid_string",
            "email": "user@example.com"
        }

    Args:
        func: Hàm view handler Flask cần được bảo vệ.

    Returns:
        Wrapper function — trả 401 nếu token lỗi, gọi func nếu hợp lệ.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # ── Đọc Authorization header ───────────────────────────────────
        auth_header = request.headers.get("Authorization", "").strip()

        if not auth_header:
            logger.warning(
                "[AuthMiddleware] Request thiếu Authorization header. "
                "Path: %s", request.path,
            )
            return _unauthorized(
                "Yêu cầu xác thực. Vui lòng đăng nhập và gửi token."
            )

        # ── Parse "Bearer <token>" ─────────────────────────────────────
        parts = auth_header.split(" ", maxsplit=1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(
                "[AuthMiddleware] Authorization header sai định dạng: '%s'.",
                auth_header[:30],
            )
            return _unauthorized(
                "Định dạng token không hợp lệ. "
                "Yêu cầu: 'Authorization: Bearer <token>'."
            )

        token = parts[1].strip()
        if not token:
            return _unauthorized("Token không được để trống.")

        # ── Xác thực token với Firebase ───────────────────────────────
        try:
            decoded_token = auth.verify_id_token(token)

            # Inject user info vào request — sẵn sàng dùng trong handler
            request.user = {
                "uid": decoded_token["uid"],
                "email": decoded_token.get("email", ""),
            }
            logger.debug(
                "[AuthMiddleware] Token hợp lệ — uid='%s', path='%s'.",
                request.user["uid"], request.path,
            )
            return func(*args, **kwargs)

        except ExpiredIdTokenError:
            logger.info(
                "[AuthMiddleware] Token đã hết hạn. Path: %s", request.path
            )
            return _unauthorized(
                "Token đã hết hạn. Vui lòng đăng nhập lại để lấy token mới."
            )

        except RevokedIdTokenError:
            logger.warning(
                "[AuthMiddleware] Token đã bị thu hồi. Path: %s", request.path
            )
            return _unauthorized(
                "Token đã bị thu hồi. Vui lòng đăng nhập lại."
            )

        except InvalidIdTokenError as exc:
            logger.warning(
                "[AuthMiddleware] Token không hợp lệ: %s. Path: %s",
                str(exc), request.path,
            )
            return _unauthorized("Token không hợp lệ hoặc đã bị giả mạo.")

        except CertificateFetchError as exc:
            # Lỗi kết nối đến Firebase để lấy public key xác thực
            logger.error(
                "[AuthMiddleware] Không thể xác thực token — "
                "lỗi kết nối Firebase: %s", str(exc),
            )
            return _unauthorized(
                "Dịch vụ xác thực tạm thời không khả dụng. "
                "Vui lòng thử lại sau."
            )

        except Exception as exc:
            logger.error(
                "[AuthMiddleware] Lỗi xác thực không xác định: %s", str(exc)
            )
            return _unauthorized("Xác thực thất bại. Vui lòng thử lại.")

    return wrapper
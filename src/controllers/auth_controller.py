import logging
from flask import Blueprint, request, jsonify
from src.services.auth_service import authenticate_user, create_access_token, register_user, validate_token

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _ok(data, message="", status_code=200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message, status_code=400):
    return jsonify({"success": False, "message": message, "data": None}), status_code


@auth_bp.route("/register", methods=["POST"])
def register_endpoint():
    body = request.get_json(silent=True) or {}
    try:
        user = register_user(
            name=body.get("name", ""),
            email=body.get("email", ""),
            password=body.get("password", ""),
            role=body.get("role", "SME"),
        )
        access_token = create_access_token(user)
        return _ok(
            data={"access_token": access_token, "user": user},
            message="Tạo tài khoản thành công.",
            status_code=201,
        )
    except ValueError as exc:
        logger.warning("[AuthController.register] %s", str(exc))
        return _err(str(exc), 400)
    except Exception as exc:
        logger.error("[AuthController.register] %s", str(exc))
        return _err("Đã xảy ra lỗi hệ thống khi đăng ký.", 500)


@auth_bp.route("/login", methods=["POST"])
def login_endpoint():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")

    user = authenticate_user(email, password)
    if not user:
        return _err("Email hoặc mật khẩu không đúng.", 401)

    access_token = create_access_token(user)
    return _ok(
        data={"access_token": access_token, "user": user},
        message="Đăng nhập thành công.",
    )


@auth_bp.route("/me", methods=["GET"])
def me_endpoint():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return _err("Không tìm thấy token.", 401)

    token = auth_header.split(" ", 1)[1]
    user = validate_token(token)
    if not user:
        return _err("Token không hợp lệ hoặc đã hết hạn.", 401)

    return _ok(
        data=user,
        message="Thông tin user.",
    )

"""
Module  : src/controllers/project_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa các API endpoint liên quan đến Project.

Nguyên tắc tuyệt đối:
    - Controller KHÔNG chứa bất kỳ business logic nào.
    - Chỉ: nhận request → gọi service → trả response.
    - Mọi lỗi nghiệp vụ từ Service đều bị bắt tại đây và map sang HTTP code.

Endpoints:
    POST /api/projects          — Tạo Project mới (Bước 1)
    GET  /api/projects/<id>     — Lấy chi tiết một Project
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.project_service import create_project, get_project

logger = logging.getLogger(__name__)

project_bp = Blueprint("project", __name__, url_prefix="/api/projects")


# ── Helper nội bộ ──────────────────────────────────────────────────────────────

def _ok(data, message: str = "", status_code: int = 200):
    """Trả về response thành công theo chuẩn nhất quán."""
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message: str, status_code: int = 400):
    """Trả về response lỗi theo chuẩn nhất quán."""
    return jsonify({"success": False, "message": message, "data": None}), status_code


# ── Endpoints ──────────────────────────────────────────────────────────────────

@project_bp.route("", methods=["POST"])
def create_project_endpoint():
    """
    POST /api/projects
    Tạo một Project mới — Bước 1: SME đăng nhu cầu R&D.

    Request body (JSON):
    {
        "sme_id"               : "SME-001",           (bắt buộc)
        "title"                : "Tên dự án",         (bắt buộc)
        "budget"               : 150000000,            (tuỳ chọn)
        "deadline"             : "2025-12-31",         (tuỳ chọn)
        "description"          : "Mô tả chi tiết",    (tuỳ chọn)
        "required_specialties" : ["Machine Learning"] (tuỳ chọn)
    }

    Response 201: Project vừa tạo.
    Response 400: Thiếu field bắt buộc hoặc dữ liệu không hợp lệ.
    Response 500: Lỗi hệ thống khi ghi file.
    """
    body = request.get_json(silent=True) or {}

    try:
        project = create_project(
            sme_id=body.get("sme_id", ""),
            title=body.get("title", ""),
            budget=body.get("budget"),
            deadline=body.get("deadline"),
            description=body.get("description"),
            required_specialties=body.get("required_specialties", []),
        )
        return _ok(
            data=project.to_dict(),
            message=f"Project '{project.title}' đã được tạo thành công.",
            status_code=201,
        )

    except ValueError as exc:
        logger.warning("[ProjectController.create] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except IOError as exc:
        logger.error("[ProjectController.create] IOError: %s", str(exc))
        return _err(str(exc), 500)


@project_bp.route("/<project_id>", methods=["GET"])
def get_project_endpoint(project_id: str):
    """
    GET /api/projects/<project_id>
    Lấy chi tiết một Project theo ID.

    Response 200: Project object.
    Response 404: Không tìm thấy Project.
    """
    try:
        project = get_project(project_id)
        return _ok(data=project.to_dict())

    except LookupError as exc:
        logger.warning("[ProjectController.get] LookupError: %s", str(exc))
        return _err(str(exc), 404)
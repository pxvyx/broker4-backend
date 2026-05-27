"""
Module  : src/controllers/matching_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa API endpoint cho chức năng Matching.

Endpoints:
    GET /api/matches/<project_id> — Tìm danh sách chuyên gia phù hợp (Bước 2)
"""

import logging
from flask import Blueprint, jsonify

from src.services.matching_service import find_matches

logger = logging.getLogger(__name__)

matching_bp = Blueprint("matching", __name__, url_prefix="/api/matches")


def _ok(data, message: str = "", status_code: int = 200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message: str, status_code: int = 400):
    return jsonify({"success": False, "message": message, "data": None}), status_code


@matching_bp.route("/<project_id>", methods=["GET"])
def find_matches_endpoint(project_id: str):
    """
    GET /api/matches/<project_id>
    Tìm danh sách chuyên gia phù hợp cho một Project — Bước 2: Matching.

    Response 200: Danh sách Expert kèm score, sắp xếp giảm dần.
    [
        {
            "expert"       : { ...expert fields... },
            "score"        : 87,
            "score_label"  : "87%",
            "match_reasons": ["Machine Learning", "Tối ưu hóa thuật toán"]
        },
        ...
    ]
    Response 400: Project không ở trạng thái hợp lệ để matching.
    Response 404: Không tìm thấy Project.
    Response 500: Lỗi hệ thống.
    """
    try:
        matches = find_matches(project_id)

        message = (
            f"Tìm được {len(matches)} chuyên gia phù hợp."
            if matches
            else "Không tìm thấy chuyên gia phù hợp hoặc không có Expert available."
        )
        return _ok(data=matches, message=message)

    except LookupError as exc:
        logger.warning("[MatchingController] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except ValueError as exc:
        logger.warning("[MatchingController] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except Exception as exc:
        logger.error("[MatchingController] Unexpected error: %s", str(exc))
        return _err("Lỗi hệ thống. Vui lòng thử lại sau.", 500)
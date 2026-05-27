"""
Module  : src/controllers/review_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa API endpoint cho chức năng Đánh giá.

Endpoints:
    POST /api/reviews — Gửi đánh giá sau khi dự án hoàn thành (Bước 6)
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.review_service import submit_review

logger = logging.getLogger(__name__)

review_bp = Blueprint("review", __name__, url_prefix="/api/reviews")


def _ok(data, message: str = "", status_code: int = 200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message: str, status_code: int = 400):
    return jsonify({"success": False, "message": message, "data": None}), status_code


@review_bp.route("", methods=["POST"])
def submit_review_endpoint():
    """
    POST /api/reviews
    SME gửi đánh giá sau khi dự án hoàn thành — Bước 6.

    Đồng thời:
        - Tạo Review mới.
        - Chuyển Project → Completed.
        - Cập nhật lại rating trung bình của Expert.

    Request body (JSON):
    {
        "project_id"           : "PRJ-XXXXXXXX",       (bắt buộc)
        "reviewer_sme_id"      : "SME-001",             (bắt buộc)
        "reviewed_expert_id"   : "EXP-001",             (bắt buộc)
        "rating"               : 5,                     (bắt buộc, 1-5)
        "feedback"             : "Nhận xét chi tiết",   (bắt buộc)
        "tags"                 : ["đúng tiến độ"]       (tuỳ chọn)
    }

    Response 201: Review vừa tạo.
    Response 400: Thiếu input hoặc rating không hợp lệ.
    Response 404: Không tìm thấy Project.
    Response 500: Lỗi hệ thống.
    """
    body = request.get_json(silent=True) or {}

    # ── Kiểm tra field bắt buộc ngay tại Controller ───────────────────
    required_fields = [
        "project_id", "reviewer_sme_id", "reviewed_expert_id", "rating", "feedback"
    ]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        return _err(
            f"Thiếu các trường bắt buộc: {', '.join(missing)}.", 400
        )

    try:
        review = submit_review(
            project_id=body["project_id"],
            reviewer_sme_id=body["reviewer_sme_id"],
            reviewed_expert_id=body["reviewed_expert_id"],
            rating=body["rating"],
            feedback=body["feedback"],
            tags=body.get("tags", []),
        )
        return _ok(
            data=review.to_dict(),
            message=(
                f"Đánh giá đã được ghi nhận. "
                f"Cảm ơn bạn đã đóng góp cho cộng đồng Broker 4.0!"
            ),
            status_code=201,
        )

    except LookupError as exc:
        logger.warning("[ReviewController] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except ValueError as exc:
        logger.warning("[ReviewController] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except IOError as exc:
        logger.error("[ReviewController] IOError: %s", str(exc))
        return _err(str(exc), 500)
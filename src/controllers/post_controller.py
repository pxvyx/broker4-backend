"""
Module  : src/controllers/post_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : Định nghĩa các API endpoints cho Innovation Feed.

Nguyên tắc tuyệt đối:
    - Controller KHÔNG chứa bất kỳ business logic nào.
    - Chỉ: nhận request → gọi service → trả response.
    - Mọi Exception từ Service đều bị bắt và map sang HTTP status code.

Response format chuẩn (dùng _ok / _err):
    Thành công : {"success": true,  "message": "...", "data": {...}}
    Thất bại   : {"success": false, "message": "...", "data": null}

Endpoints:
    GET  /api/posts                         — Lấy Innovation Feed
    POST /api/posts                         — Tạo bài viết mới
    POST /api/posts/<post_id>/like          — Toggle like
    POST /api/posts/<post_id>/comments      — Thêm bình luận
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.post_service import (
    create_post,
    get_all_posts,
    toggle_post_like,
    add_post_comment,
)

logger = logging.getLogger(__name__)

post_bp = Blueprint("post", __name__, url_prefix="/api/posts")


# ------------------------------------------------------------------
# Response helpers — dùng nhất quán trong toàn controller
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

@post_bp.route("", methods=["GET"])
def get_feed():
    """
    GET /api/posts
    Lấy danh sách bài viết trên Innovation Feed, mới nhất trước.

    Query params (tuỳ chọn):
        limit (int): Số bài tối đa cần lấy. Mặc định 50, tối đa 200.

    Response 200:
    {
        "success": true,
        "message": "Lấy được 12 bài viết.",
        "data": [
            {
                "id": "POST-1A2B3C4D",
                "author_id": "SME-001",
                "author_name": "Nguyễn Văn A",
                "author_role": "SME",
                "content": "Chúng tôi đang gặp khó khăn...",
                "created_at": "2025-01-10T08:30:00",
                "likes": ["EXP-001"],
                "comments": [...]
            },
            ...
        ]
    }
    Response 500: Lỗi kết nối MongoDB.
    """
    try:
        # Đọc và validate query param limit
        raw_limit = request.args.get("limit", 50)
        try:
            limit = max(1, min(int(raw_limit), 200))  # Clamp [1, 200]
        except (ValueError, TypeError):
            limit = 50

        posts = get_all_posts(limit=limit)
        posts_data = [p.to_dict() for p in posts]

        return _ok(
            data=posts_data,
            message=f"Lấy được {len(posts_data)} bài viết.",
        )

    except Exception as exc:
        logger.error("[PostController.get_feed] Unexpected error: %s", str(exc))
        return _err("Lỗi hệ thống khi tải feed. Vui lòng thử lại.", 500)


@post_bp.route("", methods=["POST"])
def create_post_endpoint():
    """
    POST /api/posts
    Tạo một bài viết mới trên Innovation Feed.

    Request body (JSON) — tất cả bắt buộc:
    {
        "author_id"   : "SME-001",
        "author_name" : "Nguyễn Văn A",
        "author_role" : "SME",
        "content"     : "Chúng tôi đang gặp khó khăn với quy trình kiểm soát..."
    }

    Response 201: Post vừa tạo.
    Response 400: Thiếu field bắt buộc hoặc content rỗng.
    Response 500: Lỗi ghi MongoDB.
    """
    body = request.get_json(silent=True) or {}

    # ── Kiểm tra field bắt buộc tại Controller ────────────────────────
    required = ["author_id", "author_name", "author_role", "content"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _err(
            f"Thiếu các trường bắt buộc: {', '.join(missing)}.", 400
        )

    try:
        post = create_post(
            author_id=body["author_id"],
            author_name=body["author_name"],
            author_role=body["author_role"],
            content=body["content"],
        )
        return _ok(
            data=post.to_dict(),
            message="Bài viết đã được đăng thành công.",
            status_code=201,
        )

    except ValueError as exc:
        logger.warning("[PostController.create_post] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except IOError as exc:
        logger.error("[PostController.create_post] IOError: %s", str(exc))
        return _err(str(exc), 500)

    except Exception as exc:
        logger.error("[PostController.create_post] Unexpected: %s", str(exc))
        return _err("Lỗi hệ thống. Vui lòng thử lại sau.", 500)


@post_bp.route("/<post_id>/like", methods=["POST"])
def toggle_like_endpoint(post_id: str):
    """
    POST /api/posts/<post_id>/like
    Toggle like / unlike cho một bài viết.

    Gọi liên tiếp 2 lần → like rồi unlike (hoạt động như nút toggle).

    Request body (JSON):
    {
        "user_id": "EXP-001"
    }

    Response 200:
    {
        "success": true,
        "message": "Đã thích bài viết.",
        "data": {
            "post_id" : "POST-1A2B3C4D",
            "user_id" : "EXP-001",
            "action"  : "liked"          ← "liked" hoặc "unliked"
        }
    }
    Response 400: Thiếu user_id.
    Response 404: Không tìm thấy bài viết.
    Response 500: Lỗi hệ thống.
    """
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()

    if not user_id:
        return _err("user_id là trường bắt buộc.", 400)

    try:
        result = toggle_post_like(post_id=post_id, user_id=user_id)

        action_msg = "Đã thích bài viết." if result["action"] == "liked" \
            else "Đã bỏ thích bài viết."

        return _ok(data=result, message=action_msg)

    except ValueError as exc:
        logger.warning("[PostController.toggle_like] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except LookupError as exc:
        logger.warning("[PostController.toggle_like] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except Exception as exc:
        logger.error("[PostController.toggle_like] Unexpected: %s", str(exc))
        return _err("Lỗi hệ thống. Vui lòng thử lại sau.", 500)


@post_bp.route("/<post_id>/comments", methods=["POST"])
def add_comment_endpoint(post_id: str):
    """
    POST /api/posts/<post_id>/comments
    Thêm một bình luận mới vào bài viết.

    Request body (JSON):
    {
        "user_id"   : "EXP-001",
        "user_name" : "TS. Trần Thị Lan Anh",
        "user_role" : "Expert",
        "content"   : "Vấn đề này rất thú vị, chúng tôi có thể hỗ trợ..."
    }

    Response 201:
    {
        "success": true,
        "message": "Bình luận đã được thêm thành công.",
        "data": {
            "comment_id" : "CMT-A1B2C3D4",
            "user_id"    : "EXP-001",
            "user_name"  : "TS. Trần Thị Lan Anh",
            "user_role"  : "Expert",
            "content"    : "Vấn đề này rất thú vị...",
            "created_at" : "2025-01-10T09:00:00"
        }
    }
    Response 400: Thiếu field bắt buộc hoặc content rỗng.
    Response 404: Không tìm thấy bài viết.
    Response 500: Lỗi hệ thống.
    """
    body = request.get_json(silent=True) or {}

    # ── Kiểm tra field bắt buộc ───────────────────────────────────────
    required = ["user_id", "user_name", "content"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _err(
            f"Thiếu các trường bắt buộc: {', '.join(missing)}.", 400
        )

    try:
        comment = add_post_comment(
            post_id=post_id,
            user_id=body["user_id"],
            user_name=body["user_name"],
            user_role=body.get("user_role", ""),
            content=body["content"],
        )
        return _ok(
            data=comment,
            message="Bình luận đã được thêm thành công.",
            status_code=201,
        )

    except ValueError as exc:
        logger.warning("[PostController.add_comment] ValueError: %s", str(exc))
        return _err(str(exc), 400)

    except LookupError as exc:
        logger.warning("[PostController.add_comment] LookupError: %s", str(exc))
        return _err(str(exc), 404)

    except Exception as exc:
        logger.error("[PostController.add_comment] Unexpected: %s", str(exc))
        return _err("Lỗi hệ thống. Vui lòng thử lại sau.", 500)
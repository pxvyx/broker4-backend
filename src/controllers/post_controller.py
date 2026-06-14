"""
Module  : src/controllers/post_controller.py
Layer   : Controllers (Routing & HTTP Response)
Purpose : API endpoints cho Community Posts (CRUD + Like).
"""

import logging
from flask import Blueprint, request, jsonify
from src.services.post_service import add_comment_to_post, create_post, get_all_posts, toggle_like_post, delete_post

logger = logging.getLogger(__name__)

post_bp = Blueprint("post", __name__, url_prefix="/api/posts")


def _ok(data, message="", status_code=200):
    return jsonify({"success": True, "message": message, "data": data}), status_code


def _err(message, status_code=400):
    return jsonify({"success": False, "message": message, "data": None}), status_code


@post_bp.route("", methods=["GET"])
def get_posts_endpoint():
    """GET /api/posts — Lấy tất cả posts."""
    try:
        posts = get_all_posts()
        data = [p.to_dict() for p in posts]
        return _ok(data=data, message="Lấy danh sách bài viết thành công.")
    except Exception as exc:
        logger.error(f"[PostController.get_posts] {str(exc)}")
        return _err("Lỗi khi lấy danh sách bài viết.", 500)


@post_bp.route("", methods=["POST"])
def create_post_endpoint():
    """POST /api/posts — Tạo bài viết mới."""
    body = request.get_json(silent=True) or {}
    
    try:
        post = create_post(
            author_id=body.get("author_id", ""),
            author_name=body.get("author_name", ""),
            author_role=body.get("author_role", ""),
            content=body.get("content", ""),
        )
        return _ok(
            data=post.to_dict(),
            message="Bài viết đã được tạo thành công.",
            status_code=201,
        )
    except ValueError as exc:
        logger.warning(f"[PostController.create] {str(exc)}")
        return _err(str(exc), 400)
    except Exception as exc:
        logger.error(f"[PostController.create] {str(exc)}")
        return _err("Lỗi hệ thống khi tạo bài viết.", 500)


@post_bp.route("/<post_id>/like", methods=["POST"])
def toggle_like_endpoint(post_id: str):
    """POST /api/posts/<post_id>/like — Toggle like (thêm/xóa user từ danh sách like)."""
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id", "")

    if not user_id:
        return _err("user_id là bắt buộc.", 400)

    try:
        post = toggle_like_post(post_id, user_id)
        return _ok(
            data=post.to_dict(),
            message="Thích/Bỏ thích bài viết thành công.",
        )
    except LookupError as exc:
        logger.warning(f"[PostController.like] {str(exc)}")
        return _err(str(exc), 404)
    except Exception as exc:
        logger.error(f"[PostController.like] {str(exc)}")
        return _err("Lỗi hệ thống khi cập nhật like.", 500)


@post_bp.route("/<post_id>", methods=["DELETE"])
def delete_post_endpoint(post_id: str):
    """DELETE /api/posts/<post_id> — Xóa bài viết."""
    try:
        delete_post(post_id)
        return _ok(
            data=None,
            message="Xóa bài viết thành công.",
        )
    except LookupError as exc:
        logger.warning(f"[PostController.delete] {str(exc)}")
        return _err(str(exc), 404)
    except Exception as exc:
        logger.error(f"[PostController.delete] {str(exc)}")
        return _err("Lỗi hệ thống khi xóa bài viết.", 500)


@post_bp.route("/<post_id>/comments", methods=["POST"])
def add_comment_endpoint(post_id: str):
    """POST /api/posts/<post_id>/comments — Thêm bình luận vào bài viết."""
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id", "")
    user_name = body.get("user_name", "")
    text = body.get("text", "")

    if not user_id or not user_name or not text:
        return _err("user_id, user_name và text là bắt buộc.", 400)

    try:
        post = add_comment_to_post(post_id, user_id, user_name, text)
        return _ok(
            data=post.to_dict(),
            message="Bình luận đã được thêm thành công.",
        )
    except LookupError as exc:
        logger.warning(f"[PostController.comment] {str(exc)}")
        return _err(str(exc), 404)
    except ValueError as exc:
        logger.warning(f"[PostController.comment] {str(exc)}")
        return _err(str(exc), 400)
    except Exception as exc:
        logger.error(f"[PostController.comment] {str(exc)}")
        return _err("Lỗi hệ thống khi thêm bình luận.", 500)

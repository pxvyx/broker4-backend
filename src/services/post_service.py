"""
Module  : src/services/post_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý toàn bộ nghiệp vụ Innovation Feed.

Luồng nghiệp vụ:
    create_post()        → Validate → Sinh ID/timestamp → Lưu qua Repo
    get_all_posts()      → Lấy feed → Parse về List[Post] → Trả về
    toggle_post_like()   → Validate → Gọi repo.toggle_like()
    add_post_comment()   → Validate → Sinh comment_id/timestamp → Gọi repo.add_comment()

Convention ID sinh tự động:
    Post    : "POST-" + uuid.hex[:8].upper()  → "POST-1A2B3C4D"
    Comment : "CMT-"  + uuid.hex[:8].upper()  → "CMT-A1B2C3D4"

Exception convention (để Controller map sang HTTP status):
    ValueError   → 400 Bad Request  (input không hợp lệ)
    LookupError  → 404 Not Found    (không tìm thấy resource)
    IOError      → 500 Server Error (thao tác ghi thất bại)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List

from src.models.post import Post
from src.repositories.post_repo import PostRepository

logger = logging.getLogger(__name__)

# Module-level singleton — tái dùng connection pool
_post_repo = PostRepository()


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _generate_post_id() -> str:
    """Sinh Post ID dạng 'POST-1A2B3C4D'."""
    return f"POST-{uuid.uuid4().hex[:8].upper()}"


def _generate_comment_id() -> str:
    """Sinh Comment ID dạng 'CMT-A1B2C3D4'."""
    return f"CMT-{uuid.uuid4().hex[:8].upper()}"


def _now_iso() -> str:
    """Trả về timestamp hiện tại theo ISO 8601 UTC: '2025-01-10T08:30:00'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ------------------------------------------------------------------
# Public service functions
# ------------------------------------------------------------------

def create_post(
    author_id: str,
    author_name: str,
    author_role: str,
    content: str,
) -> Post:
    """
    Tạo một bài viết mới trên Innovation Feed.

    Validate:
        - content không được rỗng hoặc chỉ chứa khoảng trắng.
        - author_id, author_name, author_role không được rỗng.

    Tự động sinh:
        - id          : "POST-XXXXXXXX"
        - created_at  : timestamp ISO 8601 UTC hiện tại
        - likes       : [] (mảng rỗng)
        - comments    : [] (mảng rỗng)

    Args:
        author_id   : ID của tác giả (SME-xxx hoặc EXP-xxx).
        author_name : Tên hiển thị của tác giả.
        author_role : Vai trò (SME | Expert | Admin).
        content     : Nội dung bài viết.

    Returns:
        Post object vừa được tạo và lưu thành công.

    Raises:
        ValueError : Nếu content rỗng hoặc thiếu thông tin tác giả.
        IOError    : Nếu ghi MongoDB thất bại.
    """
    # ── Validate ──────────────────────────────────────────────────────
    if not author_id or not author_id.strip():
        raise ValueError("author_id không được để trống.")
    if not author_name or not author_name.strip():
        raise ValueError("author_name không được để trống.")
    if not author_role or not author_role.strip():
        raise ValueError("author_role không được để trống.")
    if not content or not content.strip():
        raise ValueError("Nội dung bài viết (content) không được để trống.")

    # ── Khởi tạo Post mới ────────────────────────────────────────────
    post = Post(
        id=_generate_post_id(),
        author_id=author_id.strip(),
        author_name=author_name.strip(),
        author_role=author_role.strip(),
        content=content.strip(),
        created_at=_now_iso(),
        likes=[],
        comments=[],
    )

    # ── Lưu vào MongoDB ──────────────────────────────────────────────
    try:
        _post_repo.save(post.to_dict())
    except Exception as exc:
        logger.error(
            "[PostService.create_post] Ghi MongoDB thất bại: %s", str(exc)
        )
        raise IOError(f"Lỗi hệ thống: Không thể lưu bài viết. Chi tiết: {exc}") from exc

    logger.info(
        "[PostService.create_post] Tạo Post id='%s' — author='%s' (%s).",
        post.id, author_name, author_role,
    )
    return post


def get_all_posts(limit: int = 50) -> List[Post]:
    """
    Lấy danh sách bài viết mới nhất cho Innovation Feed.

    Bài viết được sắp xếp từ mới nhất đến cũ nhất (order by created_at DESC).
    Mỗi dict từ Repository được parse thành Post object để tầng Controller
    luôn nhận về Model objects nhất quán.

    Args:
        limit: Số lượng bài viết tối đa (mặc định 50).

    Returns:
        List[Post] — [] nếu feed rỗng hoặc lỗi kết nối.
    """
    raw_posts = _post_repo.get_recent_posts(limit=limit)
    result: List[Post] = []

    for raw in raw_posts:
        try:
            result.append(Post.from_dict(raw))
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[PostService.get_all_posts] Bỏ qua post lỗi cấu trúc "
                "(id='%s'): %s", raw.get("id", "UNKNOWN"), str(exc),
            )

    logger.debug(
        "[PostService.get_all_posts] Trả về %d post(s).", len(result)
    )
    return result


def toggle_post_like(post_id: str, user_id: str) -> dict:
    """
    Toggle like/unlike cho một bài viết.

    Logic atomic tại Repository (dùng $pull / $addToSet) — không cần
    đọc document trước, đảm bảo thread-safe.

    Args:
        post_id : ID của bài viết cần toggle like.
        user_id : ID của user thực hiện hành động.

    Returns:
        dict: {"post_id": ..., "user_id": ..., "action": "liked" | "unliked"}

    Raises:
        ValueError  : Nếu post_id hoặc user_id rỗng.
        LookupError : Nếu không tìm thấy bài viết.
    """
    # ── Validate ──────────────────────────────────────────────────────
    if not post_id or not post_id.strip():
        raise ValueError("post_id không được để trống.")
    if not user_id or not user_id.strip():
        raise ValueError("user_id không được để trống.")

    # ── Kiểm tra post tồn tại ────────────────────────────────────────
    existing = _post_repo.get_by_id(post_id)
    if existing is None:
        raise LookupError(f"Không tìm thấy bài viết với id='{post_id}'.")

    # ── Xác định trạng thái like trước khi toggle ────────────────────
    already_liked = user_id in existing.get("likes", [])

    # ── Thực hiện toggle ──────────────────────────────────────────────
    success = _post_repo.toggle_like(post_id, user_id)
    if not success:
        raise LookupError(f"Không thể toggle like cho bài viết id='{post_id}'.")

    action = "unliked" if already_liked else "liked"
    logger.info(
        "[PostService.toggle_post_like] user='%s' %s post='%s'.",
        user_id, action, post_id,
    )

    return {
        "post_id": post_id,
        "user_id": user_id,
        "action": action,
    }


def add_post_comment(
    post_id: str,
    user_id: str,
    user_name: str,
    user_role: str,
    content: str,
) -> dict:
    """
    Thêm một bình luận mới vào bài viết.

    Tự động sinh:
        - comment_id : "CMT-XXXXXXXX"
        - created_at : timestamp ISO 8601 UTC hiện tại

    Args:
        post_id   : ID của bài viết cần bình luận.
        user_id   : ID của người bình luận.
        user_name : Tên hiển thị của người bình luận.
        user_role : Vai trò (SME | Expert | Admin).
        content   : Nội dung bình luận.

    Returns:
        dict: comment object vừa được tạo (có comment_id, created_at).

    Raises:
        ValueError  : Nếu content rỗng hoặc thiếu thông tin người dùng.
        LookupError : Nếu không tìm thấy bài viết.
    """
    # ── Validate ──────────────────────────────────────────────────────
    if not post_id or not post_id.strip():
        raise ValueError("post_id không được để trống.")
    if not user_id or not user_id.strip():
        raise ValueError("user_id không được để trống.")
    if not user_name or not user_name.strip():
        raise ValueError("user_name không được để trống.")
    if not content or not content.strip():
        raise ValueError("Nội dung bình luận (content) không được để trống.")

    # ── Kiểm tra post tồn tại ────────────────────────────────────────
    existing = _post_repo.get_by_id(post_id)
    if existing is None:
        raise LookupError(f"Không tìm thấy bài viết với id='{post_id}'.")

    # ── Tạo comment object ────────────────────────────────────────────
    comment = {
        "comment_id": _generate_comment_id(),
        "user_id": user_id.strip(),
        "user_name": user_name.strip(),
        "user_role": user_role.strip() if user_role else "",
        "content": content.strip(),
        "created_at": _now_iso(),
    }

    # ── Đẩy vào MongoDB bằng $push ────────────────────────────────────
    success = _post_repo.add_comment(post_id, comment)
    if not success:
        raise LookupError(
            f"Không thể thêm bình luận vào bài viết id='{post_id}'."
        )

    logger.info(
        "[PostService.add_post_comment] comment='%s' → post='%s' — user='%s'.",
        comment["comment_id"], post_id, user_id,
    )
    return comment
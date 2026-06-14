"""
Module  : src/services/post_service.py
Layer   : Services (Business Logic)
Purpose : PostService — logic xử lý Posts (CRUD, Like toggle).
"""

import logging
import uuid
from datetime import datetime
from typing import List
from src.models.post import Post
from src.repositories.post_repo import PostRepository

logger = logging.getLogger(__name__)
_post_repo = PostRepository()


def get_all_posts() -> List[Post]:
    """Lấy tất cả posts, sắp xếp mới nhất trước."""
    return _post_repo.get_all()


def create_post(author_id: str, author_name: str, author_role: str, content: str) -> Post:
    """Tạo post mới."""
    if not content or not content.strip():
        raise ValueError("Nội dung bài viết không được trống.")
    
    if not author_id or not author_name:
        raise ValueError("Thông tin tác giả không hợp lệ.")

    post_id = _post_repo.next_id()
    post = Post(
        id=post_id,
        author_id=author_id,
        author_name=author_name,
        author_role=author_role,
        content=content.strip(),
        created_at=datetime.utcnow().isoformat() + "Z",
        likes=[],
        comments=[],
    )

    saved = _post_repo.add_post(post)
    if not saved:
        raise IOError("Không thể lưu bài viết.")

    logger.info(f"[PostService] Tạo post mới: {post_id}")
    return post


def add_comment_to_post(post_id: str, user_id: str, user_name: str, text: str) -> Post:
    """Thêm bình luận vào bài viết."""
    if not text or not text.strip():
        raise ValueError("Nội dung bình luận không được để trống.")

    post = _post_repo.get_by_id(post_id)
    if not post:
        raise LookupError(f"Không tìm thấy post {post_id}.")

    comment = {
        "comment_id": f"CMT-{uuid.uuid4().hex[:8].upper()}",
        "user_id": user_id,
        "user_name": user_name,
        "text": text.strip(),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    post.comments.append(comment)

    updated = _post_repo.update_post(post)
    if not updated:
        raise IOError("Không thể lưu bình luận.")

    logger.info(f"[PostService] Thêm bình luận cho post {post_id} bởi {user_id}")
    return post


def toggle_like_post(post_id: str, user_id: str) -> Post:
    """Thêm hoặc xóa user từ danh sách like của post."""
    post = _post_repo.get_by_id(post_id)
    if not post:
        raise LookupError(f"Không tìm thấy post {post_id}.")

    if user_id in post.likes:
        post.likes.remove(user_id)
        logger.info(f"[PostService] Unlike post {post_id} bởi {user_id}")
    else:
        post.likes.append(user_id)
        logger.info(f"[PostService] Like post {post_id} bởi {user_id}")

    updated = _post_repo.update_post(post)
    if not updated:
        raise IOError("Không thể cập nhật like.")

    return post


def delete_post(post_id: str) -> bool:
    """Xóa post theo ID."""
    post = _post_repo.get_by_id(post_id)
    if not post:
        raise LookupError(f"Không tìm thấy post {post_id}.")

    deleted = _post_repo.delete_post(post_id)
    if not deleted:
        raise IOError("Không thể xóa bài viết.")

    logger.info(f"[PostService] Xóa post {post_id}")
    return True

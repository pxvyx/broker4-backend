"""
Module  : src/repositories/post_repo.py
Layer   : Repositories (Data Access)
Purpose : PostRepository — quản lý đọc/ghi Posts từ JSON.
"""

import logging
from typing import List, Optional
from src.models.post import Post
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

_POST_DATA_FILE = "data/posts.json"


class PostRepository(JsonRepository):
    def __init__(self, filepath: str = _POST_DATA_FILE):
        super().__init__(filepath)

    def get_all(self) -> List[Post]:
        """Lấy toàn bộ danh sách posts, sắp xếp mới nhất trước."""
        raw_data = self.read_json()
        posts = []
        for raw in raw_data:
            try:
                posts.append(Post.from_dict(raw))
            except Exception as exc:
                logger.warning(f"[PostRepository] Bỏ qua record lỗi: {exc}")
                continue
        
        # Sắp xếp theo created_at mới nhất trước
        posts.sort(key=lambda p: p.created_at, reverse=True)
        return posts

    def get_by_id(self, post_id: str) -> Optional[Post]:
        """Tìm post theo ID."""
        for raw in self.read_json():
            if raw.get("id") == post_id:
                try:
                    return Post.from_dict(raw)
                except Exception as exc:
                    logger.error(f"[PostRepository] Lỗi parse post {post_id}: {exc}")
                    return None
        return None

    def save_all(self, posts: List[Post]) -> bool:
        """Lưu tất cả posts."""
        data = [p.to_dict() for p in posts]
        return self.write_json(data)

    def add_post(self, post: Post) -> bool:
        """Thêm post mới."""
        posts = self.get_all()
        posts.append(post)
        return self.save_all(posts)

    def update_post(self, post: Post) -> bool:
        """Cập nhật post."""
        posts = self.get_all()
        for idx, p in enumerate(posts):
            if p.id == post.id:
                posts[idx] = post
                return self.save_all(posts)
        return False

    def delete_post(self, post_id: str) -> bool:
        """Xóa post theo ID."""
        posts = self.get_all()
        for idx, p in enumerate(posts):
            if p.id == post_id:
                posts.pop(idx)
                return self.save_all(posts)
        return False

    def next_id(self) -> str:
        """Sinh ID tiếp theo cho post mới."""
        posts = self.get_all()
        if not posts:
            return "POST-001"
        
        max_num = 0
        for p in posts:
            try:
                num = int(p.id.split("-")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        
        return f"POST-{str(max_num + 1).zfill(3)}"

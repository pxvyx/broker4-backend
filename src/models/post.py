"""
Module  : src/models/post.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Post (Bài viết / Nỗi đau).

Thiết kế Embedded Pattern:
    Post document nhúng trực tiếp 2 mảng con:
        likes    : List[str]  — danh sách user_id đã like.
        comments : List[dict] — danh sách bình luận kèm metadata.

    Ưu điểm: Đọc toàn bộ post + likes + comments trong 1 query duy nhất.
    Phù hợp cho Innovation Feed — số lượng comment/like vừa phải mỗi bài.

Schema MongoDB document (broker4_db.posts):
{
    "id"          : "POST-1A2B3C4D",   ← string ID tự sinh, dùng giao tiếp ngoài
    "author_id"   : "SME-001",
    "author_name" : "Nguyễn Văn A",
    "author_role" : "SME",             ← SME | Expert | Admin
    "content"     : "Nội dung bài viết...",
    "created_at"  : "2025-01-10T08:30:00",
    "likes"       : ["SME-002", "EXP-001"],
    "comments"    : [
        {
            "comment_id"  : "CMT-A1B2C3D4",
            "user_id"     : "EXP-001",
            "user_name"   : "TS. Trần Lan Anh",
            "user_role"   : "Expert",
            "content"     : "Nội dung bình luận...",
            "created_at"  : "2025-01-10T09:00:00"
        }
    ]
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Post:
    """
    Entity: Bài viết / Nỗi đau trên Innovation Feed của Broker 4.0.

    Embedded Pattern:
        `likes`    nhúng trực tiếp → tránh collection riêng cho 1 thao tác toggle.
        `comments` nhúng trực tiếp → đọc bài viết kèm comment trong 1 round-trip.
    """

    id: str
    author_id: str                              # Khóa ngoại → SME.id hoặc Expert.id
    author_name: str
    author_role: str                            # SME | Expert | Admin
    content: str
    created_at: str                             # ISO 8601: YYYY-MM-DDTHH:MM:SS
    likes: List[str] = field(default_factory=list)      # List user_id đã like
    comments: List[dict] = field(default_factory=list)  # List comment objects

    # ------------------------------------------------------------------
    # Serialization / Deserialization
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> Post:
        """
        Khởi tạo Post từ Python dict (parse từ MongoDB document).

        Args:
            data: dict đã loại bỏ _id từ MongoDB.

        Returns:
            Post instance đầy đủ.

        Raises:
            KeyError: Nếu thiếu field bắt buộc (id, author_id, author_name,
                      author_role, content, created_at).
        """
        return cls(
            id=data["id"],
            author_id=data["author_id"],
            author_name=data["author_name"],
            author_role=data["author_role"],
            content=data["content"],
            created_at=data["created_at"],
            likes=data.get("likes", []),
            comments=data.get("comments", []),
        )

    def to_dict(self) -> dict:
        """
        Chuyển Post về Python dict để insert/update MongoDB hoặc trả về API.

        Returns:
            dict hoàn chỉnh, KHÔNG chứa _id (MongoDB tự quản lý nội bộ).
        """
        return {
            "id": self.id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_role": self.author_role,
            "content": self.content,
            "created_at": self.created_at,
            "likes": self.likes,
            "comments": self.comments,
        }
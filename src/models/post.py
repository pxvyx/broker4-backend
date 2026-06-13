"""
Module  : src/models/post.py
Layer   : Models (Data Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho Community Post.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Post:
    id: str
    author_id: str
    author_name: str
    author_role: str
    content: str
    created_at: str
    likes: List[str] = field(default_factory=list)
    comments: List[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        return cls(
            id=data.get("id", ""),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", ""),
            author_role=data.get("author_role", ""),
            content=data.get("content", ""),
            created_at=data.get("created_at", ""),
            likes=data.get("likes", []),
            comments=data.get("comments", []),
        )

    def to_dict(self) -> dict:
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

"""
Module  : src/models/review.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Review (Đánh giá sau dự án).

Vị trí trong luồng 7 bước:
    Bước 6 — Đánh giá → SME tạo Review sau khi Project hoàn thành.
    Bước 7 — Dữ liệu Review là đầu vào để xây dựng Knowledge Graph (future).

Quan hệ Pseudo-Relational:
    Project (1) ──< Review (N)  :  Review.project_id       → Project.id
    SME     (1) ──< Review (N)  :  Review.reviewer_sme_id  → SME.id
    Expert  (1) ──< Review (N)  :  Review.reviewed_expert_id → Expert.id
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Review:
    """
    Entity: Đánh giá chất lượng hợp tác sau khi Project kết thúc.

    rating: Thang điểm 1–5 (1=Rất kém, 5=Xuất sắc).
    tags:   Nhãn tự do giúp phân loại tri thức cho Knowledge Graph sau này.
    """

    id: str
    project_id: str                          # Khóa ngoại → Project.id
    reviewer_sme_id: str                     # Khóa ngoại → SME.id
    reviewed_expert_id: str                  # Khóa ngoại → Expert.id
    rating: int                              # 1 | 2 | 3 | 4 | 5
    feedback: str
    created_at: Optional[str] = None         # YYYY-MM-DD
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Review:
        """
        Khởi tạo Review từ Python dict được parse từ JSON.

        Raises:
            KeyError: Nếu thiếu field bắt buộc (id, project_id,
                      reviewer_sme_id, reviewed_expert_id, rating, feedback).
        """
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            reviewer_sme_id=data["reviewer_sme_id"],
            reviewed_expert_id=data["reviewed_expert_id"],
            rating=int(data["rating"]),
            feedback=data["feedback"],
            created_at=data.get("created_at"),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """Chuyển Review về Python dict để ghi lại JSON."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "reviewer_sme_id": self.reviewer_sme_id,
            "reviewed_expert_id": self.reviewed_expert_id,
            "rating": self.rating,
            "feedback": self.feedback,
            "created_at": self.created_at,
            "tags": self.tags,
        }
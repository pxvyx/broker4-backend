"""
Module  : src/models/project.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Project (Dự án / Nhu cầu R&D).

Vị trí trong luồng 7 bước:
    Bước 1 — SME Đăng nhu cầu  → tạo Project với status='Pending'
    Bước 2 — Matching           → Broker tìm Expert phù hợp
    Bước 3 — Đàm phán           → status='Negotiating'
    Bước 4 — Ký hợp đồng        → tạo Contract, status='In Progress'
    Bước 5 — Thực hiện          → cập nhật tiến độ
    Bước 6 — Đánh giá           → tạo Review, status='Completed'
    Bước 7 — Knowledge Graph    → lưu tri thức (future)

Quan hệ Pseudo-Relational:
    SME     (1) ──< Project (N)  :  Project.sme_id là khóa ngoại → SME.id
    Project (1) ──< Contract (N) :  Contract.project_id → Project.id
    Project (1) ──< Review (N)   :  Review.project_id   → Project.id
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Tập hợp giá trị hợp lệ cho trường status — dùng để validate ở tầng Service
PROJECT_STATUSES = frozenset({"Pending", "Negotiating", "In Progress", "Completed"})


@dataclass
class Project:
    """
    Entity: Dự án / Nhu cầu R&D do SME đăng lên marketplace.

    Đây là entity trung tâm liên kết SME, Expert, Contract và Review
    trong kiến trúc Pseudo-Relational của Broker 4.0.
    """

    id: str
    sme_id: str                              # Khóa ngoại → SME.id
    title: str
    status: str                              # Pending | Negotiating | In Progress | Completed
    description: Optional[str] = None
    required_specialties: List[str] = field(default_factory=list)
    budget: Optional[float] = None           # Đơn vị: VND
    deadline: Optional[str] = None          # Định dạng ISO 8601: YYYY-MM-DD

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        """
        Khởi tạo Project từ Python dict được parse từ JSON.

        Raises:
            KeyError: Nếu thiếu field bắt buộc (id, sme_id, title, status).
        """
        return cls(
            id=data["id"],
            sme_id=data["sme_id"],
            title=data["title"],
            status=data.get("status", "Pending"),
            description=data.get("description"),
            required_specialties=data.get("required_specialties", []),
            budget=data.get("budget"),
            deadline=data.get("deadline"),
        )

    def to_dict(self) -> dict:
        """Chuyển Project về Python dict để ghi lại JSON."""
        return {
            "id": self.id,
            "sme_id": self.sme_id,
            "title": self.title,
            "description": self.description,
            "required_specialties": self.required_specialties,
            "budget": self.budget,
            "deadline": self.deadline,
            "status": self.status,
        }
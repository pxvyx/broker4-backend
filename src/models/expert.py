"""
Module  : src/models/expert.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Expert.

THAY ĐỔI: Đã cập nhật Schema để khớp với bộ dữ liệu Seed mới 
(tags, expertise, title, projects, available).

Quan hệ Pseudo-Relational:
    Expert (1) ──< Contract (N)  :  truy vấn qua ContractRepository.get_by_expert_id()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Expert:
    """
    Entity: Chuyên gia / Tổ chức nghiên cứu hàn lâm — Bên Cung trong marketplace.
    """

    id: str
    expert_name: str
    institution: str
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    expertise: List[str] = field(default_factory=list)
    department: Optional[str] = None
    email: Optional[str] = None
    research_areas: Optional[str] = None
    projects: int = 0
    available: bool = True
    rating: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> Expert:
        return cls(
            id=data["id"],
            expert_name=data["expert_name"],
            institution=data["institution"],
            title=data.get("title"),
            tags=data.get("tags", []),
            expertise=data.get("expertise", []),
            department=data.get("department"),
            email=data.get("email"),
            research_areas=data.get("research_areas"),
            projects=data.get("projects", 0),
            available=data.get("available", True),
            rating=data.get("rating"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expert_name": self.expert_name,
            "institution": self.institution,
            "title": self.title,
            "department": self.department,
            "email": self.email,
            "tags": self.tags,
            "expertise": self.expertise,
            "research_areas": self.research_areas,
            "projects": self.projects,
            "available": self.available,
            "rating": self.rating,
        }
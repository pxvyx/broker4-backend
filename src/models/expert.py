"""
Module  : src/models/expert.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Expert.

THAY ĐỔI: Không có — giữ nguyên từ Bước 2 ban đầu.

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
    specialties: List[str] = field(default_factory=list)
    available_technologies: List[str] = field(default_factory=list)
    department: Optional[str] = None
    email: Optional[str] = None
    research_areas: Optional[str] = None
    active_projects_count: int = 0
    is_available: bool = True
    rating: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> Expert:
        return cls(
            id=data["id"],
            expert_name=data["expert_name"],
            institution=data["institution"],
            specialties=data.get("specialties", []),
            available_technologies=data.get("available_technologies", []),
            department=data.get("department"),
            email=data.get("email"),
            research_areas=data.get("research_areas"),
            active_projects_count=data.get("active_projects_count", 0),
            is_available=data.get("is_available", True),
            rating=data.get("rating"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expert_name": self.expert_name,
            "institution": self.institution,
            "department": self.department,
            "email": self.email,
            "specialties": self.specialties,
            "available_technologies": self.available_technologies,
            "research_areas": self.research_areas,
            "active_projects_count": self.active_projects_count,
            "is_available": self.is_available,
            "rating": self.rating,
        }
"""
Module  : src/models/sme.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể SME.

THAY ĐỔI (Refactor Pseudo-Relational):
  - XÓA class ServiceUsed (đã tách sang Project / Contract).
  - XÓA trường services_used khỏi SME.
  - Quan hệ SME → Projects được thể hiện qua Project.sme_id (khóa ngoại).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SME:
    """
    Entity: Doanh nghiệp vừa và nhỏ (SME) — Bên Cầu trong marketplace Broker 4.0.

    Quan hệ Pseudo-Relational:
        SME (1) ──< Project (N)  :  truy vấn qua ProjectRepository.get_by_sme_id()
    """

    id: str
    company_name: str
    industry: str
    contact_email: str
    pain_points: List[str] = field(default_factory=list)
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> SME:
        """
        Khởi tạo SME từ Python dict được parse từ JSON.

        Raises:
            KeyError: Nếu thiếu field bắt buộc (id, company_name, industry).
        """
        return cls(
            id=data["id"],
            company_name=data["company_name"],
            industry=data["industry"],
            contact_email=data.get("contact_email", ""),
            pain_points=data.get("pain_points", []),
            founded_year=data.get("founded_year"),
            employee_count=data.get("employee_count"),
        )

    def to_dict(self) -> dict:
        """Chuyển SME về Python dict để ghi lại JSON."""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "industry": self.industry,
            "contact_email": self.contact_email,
            "founded_year": self.founded_year,
            "employee_count": self.employee_count,
            "pain_points": self.pain_points,
        }
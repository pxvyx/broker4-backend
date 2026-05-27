"""
Module  : src/models/contract.py
Layer   : Models (Entities)
Purpose : Định nghĩa cấu trúc dữ liệu cho thực thể Contract (Hợp đồng).

Vị trí trong luồng 7 bước:
    Bước 3 — Đàm phán  → tạo Contract với status='Draft'
    Bước 4 — Ký kết    → status='Active'
    Bước 6 — Kết thúc  → status='Closed'

Quan hệ Pseudo-Relational:
    Project (1) ──< Contract (N) :  Contract.project_id là khóa ngoại → Project.id
    Expert  (1) ──< Contract (N) :  Contract.expert_id  là khóa ngoại → Expert.id
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Tập hợp giá trị hợp lệ — dùng để validate ở tầng Service
CONTRACT_TYPES = frozenset({"MOU", "NDA", "R&D"})
CONTRACT_STATUSES = frozenset({"Draft", "Active", "Closed", "Terminated"})


@dataclass
class Contract:
    """
    Entity: Hợp đồng ràng buộc pháp lý giữa SME và Expert cho một Project.

    contract_type:
        MOU  — Biên bản ghi nhớ hợp tác (Memorandum of Understanding)
        NDA  — Thỏa thuận bảo mật (Non-Disclosure Agreement)
        R&D  — Hợp đồng nghiên cứu & phát triển chính thức
    """

    id: str
    project_id: str                          # Khóa ngoại → Project.id
    expert_id: str                           # Khóa ngoại → Expert.id
    contract_type: str                       # MOU | NDA | R&D
    status: str                              # Draft | Active | Closed | Terminated
    signed_date: Optional[str] = None       # YYYY-MM-DD
    start_date: Optional[str] = None        # YYYY-MM-DD
    end_date: Optional[str] = None          # YYYY-MM-DD
    value: Optional[float] = None           # Giá trị hợp đồng (VND)
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> Contract:
        """
        Khởi tạo Contract từ Python dict được parse từ JSON.

        Raises:
            KeyError: Nếu thiếu field bắt buộc (id, project_id, expert_id,
                      contract_type, status).
        """
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            expert_id=data["expert_id"],
            contract_type=data["contract_type"],
            status=data.get("status", "Draft"),
            signed_date=data.get("signed_date"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            value=data.get("value"),
            notes=data.get("notes"),
        )

    def to_dict(self) -> dict:
        """Chuyển Contract về Python dict để ghi lại JSON."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "expert_id": self.expert_id,
            "contract_type": self.contract_type,
            "signed_date": self.signed_date,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "value": self.value,
            "status": self.status,
            "notes": self.notes,
        }
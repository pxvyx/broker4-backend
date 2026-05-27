"""
Module  : src/services/project_service.py
Layer   : Services (Business Logic)
Purpose : Xử lý nghiệp vụ liên quan đến Project.

Luồng 7 bước — phụ trách:
    Bước 1 — SME Đăng nhu cầu : create_project() → Project(status="Pending")
"""

import logging
import uuid
from typing import Optional

from src.models.project import Project, PROJECT_STATUSES
from src.repositories.project_repo import ProjectRepository

logger = logging.getLogger(__name__)

# Module-level repository instance (shared trong toàn service)
_project_repo = ProjectRepository()


def create_project(
    sme_id: str,
    title: str,
    budget: Optional[float] = None,
    deadline: Optional[str] = None,
    description: Optional[str] = None,
    required_specialties: Optional[list] = None,
) -> Project:
    """
    Bước 1 — SME đăng nhu cầu R&D lên marketplace.

    Khởi tạo Project mới với status='Pending' và lưu vào data layer.

    Args:
        sme_id              : ID của SME đăng nhu cầu.
        title               : Tiêu đề mô tả nhu cầu / dự án.
        budget              : Ngân sách dự kiến (VND). Có thể None.
        deadline            : Hạn chót mong muốn (YYYY-MM-DD). Có thể None.
        description         : Mô tả chi tiết bài toán cần giải quyết.
        required_specialties: Danh sách chuyên môn cần thiết — dùng cho matching.

    Returns:
        Project object vừa được tạo và lưu thành công.

    Raises:
        ValueError : Nếu sme_id hoặc title bị thiếu / rỗng.
        IOError    : Nếu không thể ghi xuống data layer.
    """
    # ── Validate đầu vào ──────────────────────────────────────────────
    if not sme_id or not sme_id.strip():
        raise ValueError("sme_id không được để trống.")
    if not title or not title.strip():
        raise ValueError("title không được để trống.")
    if budget is not None and float(budget) < 0:
        raise ValueError("budget không được là số âm.")

    # ── Tạo Project mới với status mặc định = Pending ─────────────────
    project = Project(
        id=f"PRJ-{uuid.uuid4().hex[:8].upper()}",
        sme_id=sme_id.strip(),
        title=title.strip(),
        status="Pending",
        description=description,
        required_specialties=required_specialties or [],
        budget=float(budget) if budget is not None else None,
        deadline=deadline,
    )

    if not _project_repo.save(project):
        raise IOError("Lỗi hệ thống: Không thể lưu Project vào database.")

    logger.info(
        "[ProjectService] Tạo Project id='%s' — SME='%s' — status=Pending.",
        project.id, sme_id,
    )
    return project


def get_project(project_id: str) -> Project:
    """
    Lấy chi tiết một Project theo ID.

    Args:
        project_id: ID của Project cần truy vấn.

    Returns:
        Project object nếu tìm thấy.

    Raises:
        LookupError: Nếu không tìm thấy Project với ID đã cho.
    """
    project = _project_repo.get_by_id(project_id)
    if not project:
        raise LookupError(f"Không tìm thấy Project với id='{project_id}'.")
    return project


def get_projects_by_sme(sme_id: str) -> list:
    """
    Lấy toàn bộ Project của một SME.

    Args:
        sme_id: ID của SME cần truy vấn.

    Returns:
        List[Project] — có thể là [].
    """
    return _project_repo.get_by_sme_id(sme_id)
"""
Module  : src/repositories/project_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ProjectRepository — toàn bộ thao tác đọc/ghi dữ liệu Project.

Đây là repository trung tâm nhất trong kiến trúc Pseudo-Relational,
vì Project là entity liên kết SME, Expert, Contract và Review.
"""

import logging
from typing import List, Optional

from src.models.project import Project
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

_PROJECT_DATA_FILE = "data/projects.json"


class ProjectRepository(JsonRepository):
    """Repository chuyên biệt cho entity Project."""

    def __init__(self, filepath: str = _PROJECT_DATA_FILE):
        super().__init__(filepath)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_all_raw(self) -> List[dict]:
        return self.read_json()

    def _save_all_raw(self, raw_list: List[dict]) -> bool:
        return self.write_json(raw_list)

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Project]:
        """Lấy toàn bộ danh sách Project. Trả [] nếu file lỗi."""
        raw_list = self._load_all_raw()
        result: List[Project] = []
        for raw in raw_list:
            try:
                result.append(Project.from_dict(raw))
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "[ProjectRepository.get_all] Bỏ qua record lỗi (id='%s'): %s",
                    raw.get("id", "UNKNOWN"), str(exc),
                )
        return result

    def get_by_id(self, project_id: str) -> Optional[Project]:
        """
        Tìm Project theo ID.

        Returns:
            Project object nếu tìm thấy, None nếu không có.
        """
        for raw in self._load_all_raw():
            if raw.get("id") == project_id:
                try:
                    return Project.from_dict(raw)
                except (KeyError, TypeError) as exc:
                    logger.error(
                        "[ProjectRepository.get_by_id] Parse lỗi id='%s': %s",
                        project_id, str(exc),
                    )
                    return None
        logger.debug(
            "[ProjectRepository.get_by_id] Không tìm thấy id='%s'.", project_id
        )
        return None

    def get_by_sme_id(self, sme_id: str) -> List[Project]:
        """
        Lấy toàn bộ Project thuộc về một SME.
        Đây là phép JOIN tương đương: SELECT * FROM projects WHERE sme_id = ?

        Args:
            sme_id: ID của SME cần truy vấn project.

        Returns:
            List[Project] của SME đó, có thể là [].
        """
        return [p for p in self.get_all() if p.sme_id == sme_id]

    def get_by_status(self, status: str) -> List[Project]:
        """
        Lọc Project theo trạng thái.

        Args:
            status: Một trong Pending | Negotiating | In Progress | Completed.

        Returns:
            List[Project] khớp status.
        """
        return [p for p in self.get_all() if p.status == status]

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, project: Project) -> bool:
        """
        Upsert một Project object:
            id đã tồn tại → replace toàn bộ record.
            id chưa có    → append vào cuối file.

        Args:
            project: Project object đã được validate ở tầng Service.

        Returns:
            True nếu ghi thành công, False nếu thất bại.
        """
        raw_list = self._load_all_raw()
        project_dict = project.to_dict()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == project.id),
            None,
        )

        if target_index is not None:
            raw_list[target_index] = project_dict
            logger.info(
                "[ProjectRepository.save] Cập nhật Project id='%s'.", project.id
            )
        else:
            raw_list.append(project_dict)
            logger.info(
                "[ProjectRepository.save] Thêm mới Project id='%s'.", project.id
            )

        return self._save_all_raw(raw_list)
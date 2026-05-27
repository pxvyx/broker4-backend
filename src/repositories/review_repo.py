"""
Module  : src/repositories/review_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ReviewRepository — toàn bộ thao tác đọc/ghi dữ liệu Review.
"""

import logging
from typing import List, Optional

from src.models.review import Review
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

_REVIEW_DATA_FILE = "data/reviews.json"


class ReviewRepository(JsonRepository):
    """Repository chuyên biệt cho entity Review."""

    def __init__(self, filepath: str = _REVIEW_DATA_FILE):
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

    def get_all(self) -> List[Review]:
        """Lấy toàn bộ danh sách Review. Trả [] nếu file lỗi."""
        raw_list = self._load_all_raw()
        result: List[Review] = []
        for raw in raw_list:
            try:
                result.append(Review.from_dict(raw))
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "[ReviewRepository.get_all] Bỏ qua record lỗi (id='%s'): %s",
                    raw.get("id", "UNKNOWN"), str(exc),
                )
        return result

    def get_by_id(self, review_id: str) -> Optional[Review]:
        """Tìm Review theo ID. Trả None nếu không tìm thấy."""
        for raw in self._load_all_raw():
            if raw.get("id") == review_id:
                try:
                    return Review.from_dict(raw)
                except (KeyError, TypeError) as exc:
                    logger.error(
                        "[ReviewRepository.get_by_id] Parse lỗi id='%s': %s",
                        review_id, str(exc),
                    )
                    return None
        logger.debug(
            "[ReviewRepository.get_by_id] Không tìm thấy id='%s'.", review_id
        )
        return None

    def get_by_project_id(self, project_id: str) -> List[Review]:
        """
        Lấy toàn bộ Review của một Project.
        Tương đương: SELECT * FROM reviews WHERE project_id = ?

        Args:
            project_id: ID của Project cần truy vấn review.

        Returns:
            List[Review] của Project đó.
        """
        return [r for r in self.get_all() if r.project_id == project_id]

    def get_by_expert_id(self, expert_id: str) -> List[Review]:
        """
        Lấy toàn bộ Review mà một Expert nhận được.
        Dùng để tính rating trung bình cho Expert ở tầng Service.

        Args:
            expert_id: ID của Expert cần truy vấn.

        Returns:
            List[Review] có reviewed_expert_id khớp.
        """
        return [r for r in self.get_all() if r.reviewed_expert_id == expert_id]

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, review: Review) -> bool:
        """
        Upsert một Review object:
            id đã tồn tại → replace. Chưa có → append.

        Args:
            review: Review object đã được validate ở tầng Service.

        Returns:
            True nếu ghi thành công, False nếu thất bại.
        """
        raw_list = self._load_all_raw()
        review_dict = review.to_dict()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == review.id),
            None,
        )

        if target_index is not None:
            raw_list[target_index] = review_dict
            logger.info(
                "[ReviewRepository.save] Cập nhật Review id='%s'.", review.id
            )
        else:
            raw_list.append(review_dict)
            logger.info(
                "[ReviewRepository.save] Thêm mới Review id='%s'.", review.id
            )

        return self._save_all_raw(raw_list)
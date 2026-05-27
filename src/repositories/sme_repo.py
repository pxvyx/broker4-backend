"""
Module  : src/repositories/sme_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : SMERepository — thao tác đọc/ghi dữ liệu SME.

THAY ĐỔI (Refactor Pseudo-Relational):
  - XÓA hàm update_services_used() — logic này đã được tách ra
    thành ProjectRepository và ContractRepository riêng biệt.
  - Giữ lại: get_all(), get_by_id(), get_by_industry(), save().
"""

import logging
from typing import List, Optional

from src.models.sme import SME
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

_SME_DATA_FILE = "data/smes.json"


class SMERepository(JsonRepository):
    """Repository chuyên biệt cho entity SME."""

    def __init__(self, filepath: str = _SME_DATA_FILE):
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

    def get_all(self) -> List[SME]:
        """Lấy toàn bộ danh sách SME. Trả [] nếu file lỗi."""
        raw_list = self._load_all_raw()
        result: List[SME] = []
        for raw in raw_list:
            try:
                result.append(SME.from_dict(raw))
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "[SMERepository.get_all] Bỏ qua record lỗi (id='%s'): %s",
                    raw.get("id", "UNKNOWN"), str(exc),
                )
        return result

    def get_by_id(self, sme_id: str) -> Optional[SME]:
        """Tìm SME theo ID. Trả None nếu không tìm thấy."""
        for raw in self._load_all_raw():
            if raw.get("id") == sme_id:
                try:
                    return SME.from_dict(raw)
                except (KeyError, TypeError) as exc:
                    logger.error(
                        "[SMERepository.get_by_id] Parse lỗi id='%s': %s",
                        sme_id, str(exc),
                    )
                    return None
        logger.debug("[SMERepository.get_by_id] Không tìm thấy id='%s'.", sme_id)
        return None

    def get_by_industry(self, industry_keyword: str) -> List[SME]:
        """Lọc SME theo từ khóa ngành. Substring match, không phân biệt hoa/thường."""
        keyword = industry_keyword.lower().strip()
        return [sme for sme in self.get_all() if keyword in sme.industry.lower()]

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, sme: SME) -> bool:
        """
        Upsert một SME object:
            id đã tồn tại → replace. Chưa có → append.
        """
        raw_list = self._load_all_raw()
        sme_dict = sme.to_dict()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == sme.id), None
        )

        if target_index is not None:
            raw_list[target_index] = sme_dict
            logger.info("[SMERepository.save] Cập nhật SME id='%s'.", sme.id)
        else:
            raw_list.append(sme_dict)
            logger.info("[SMERepository.save] Thêm mới SME id='%s'.", sme.id)

        return self._save_all_raw(raw_list)
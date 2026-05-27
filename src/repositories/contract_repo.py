"""
Module  : src/repositories/contract_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ContractRepository — toàn bộ thao tác đọc/ghi dữ liệu Contract.
"""

import logging
from typing import List, Optional

from src.models.contract import Contract
from src.repositories.json_repository import JsonRepository

logger = logging.getLogger(__name__)

_CONTRACT_DATA_FILE = "data/contracts.json"


class ContractRepository(JsonRepository):
    """Repository chuyên biệt cho entity Contract."""

    def __init__(self, filepath: str = _CONTRACT_DATA_FILE):
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

    def get_all(self) -> List[Contract]:
        """Lấy toàn bộ danh sách Contract. Trả [] nếu file lỗi."""
        raw_list = self._load_all_raw()
        result: List[Contract] = []
        for raw in raw_list:
            try:
                result.append(Contract.from_dict(raw))
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "[ContractRepository.get_all] Bỏ qua record lỗi (id='%s'): %s",
                    raw.get("id", "UNKNOWN"), str(exc),
                )
        return result

    def get_by_id(self, contract_id: str) -> Optional[Contract]:
        """Tìm Contract theo ID. Trả None nếu không tìm thấy."""
        for raw in self._load_all_raw():
            if raw.get("id") == contract_id:
                try:
                    return Contract.from_dict(raw)
                except (KeyError, TypeError) as exc:
                    logger.error(
                        "[ContractRepository.get_by_id] Parse lỗi id='%s': %s",
                        contract_id, str(exc),
                    )
                    return None
        logger.debug(
            "[ContractRepository.get_by_id] Không tìm thấy id='%s'.", contract_id
        )
        return None

    def get_by_project_id(self, project_id: str) -> List[Contract]:
        """
        Lấy toàn bộ Contract thuộc về một Project.
        Tương đương: SELECT * FROM contracts WHERE project_id = ?

        Args:
            project_id: ID của Project cần truy vấn contract.

        Returns:
            List[Contract] của Project đó. Thông thường chỉ có 1,
            nhưng thiết kế hỗ trợ nhiều (MOU → NDA → R&D theo tiến trình).
        """
        return [c for c in self.get_all() if c.project_id == project_id]

    def get_by_expert_id(self, expert_id: str) -> List[Contract]:
        """
        Lấy toàn bộ Contract mà một Expert tham gia.
        Tương đương: SELECT * FROM contracts WHERE expert_id = ?

        Args:
            expert_id: ID của Expert cần truy vấn.

        Returns:
            List[Contract] có expert_id khớp.
        """
        return [c for c in self.get_all() if c.expert_id == expert_id]

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, contract: Contract) -> bool:
        """
        Upsert một Contract object:
            id đã tồn tại → replace. Chưa có → append.

        Args:
            contract: Contract object đã được validate ở tầng Service.

        Returns:
            True nếu ghi thành công, False nếu thất bại.
        """
        raw_list = self._load_all_raw()
        contract_dict = contract.to_dict()

        target_index: Optional[int] = next(
            (i for i, r in enumerate(raw_list) if r.get("id") == contract.id),
            None,
        )

        if target_index is not None:
            raw_list[target_index] = contract_dict
            logger.info(
                "[ContractRepository.save] Cập nhật Contract id='%s'.", contract.id
            )
        else:
            raw_list.append(contract_dict)
            logger.info(
                "[ContractRepository.save] Thêm mới Contract id='%s'.", contract.id
            )

        return self._save_all_raw(raw_list)
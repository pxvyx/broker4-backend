"""
Module  : src/repositories/contract_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ContractRepository — toàn bộ thao tác đọc/ghi Contract trên MongoDB.

THAY ĐỔI SO VỚI PHIÊN BẢN JSON:
    ① Bỏ kế thừa JsonRepository.
    ② get_by_project_id() → query {"project_id": project_id}.
    ③ get_by_expert_id()  → query {"expert_id": expert_id}.
    ④ save()              → update_one upsert=True.

Collection: broker4_db.contracts
Index nên tạo:
    db.contracts.createIndex({ "id": 1 },          { unique: true })
    db.contracts.createIndex({ "project_id": 1 })
    db.contracts.createIndex({ "expert_id": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.contract import Contract

logger = logging.getLogger(__name__)

_NO_ID: dict = {"_id": 0}


class ContractRepository:
    """Repository chuyên biệt cho entity Contract trên MongoDB Atlas."""

    def __init__(self) -> None:
        self.collection: Collection = get_db()["contracts"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_contract(self, doc: dict) -> Optional[Contract]:
        doc.pop("_id", None)
        try:
            return Contract.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[ContractRepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Contract]:
        """
        Lấy toàn bộ danh sách Contract.

        MongoDB: db.contracts.find({}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                contract
                for doc in cursor
                if (contract := self._doc_to_contract(doc)) is not None
            ]
            logger.debug(
                "[ContractRepository.get_all] Lấy được %d contract(s).", len(result)
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ContractRepository.get_all] Lỗi MongoDB: %s. Trả về [].", str(exc)
            )
            return []

    def get_by_id(self, contract_id: str) -> Optional[Contract]:
        """
        Tìm Contract theo string ID.

        MongoDB: db.contracts.find_one({"id": contract_id}, {"_id": 0})
        """
        try:
            doc = self.collection.find_one({"id": contract_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[ContractRepository.get_by_id] Không tìm thấy id='%s'.",
                    contract_id,
                )
                return None
            return self._doc_to_contract(doc)

        except PyMongoError as exc:
            logger.error(
                "[ContractRepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                contract_id, str(exc),
            )
            return None

    def get_by_project_id(self, project_id: str) -> List[Contract]:
        """
        Lấy toàn bộ Contract thuộc về một Project.

        MongoDB: db.contracts.find({"project_id": project_id}, {"_id": 0})
        Tương đương SQL: SELECT * FROM contracts WHERE project_id = ?

        Args:
            project_id: ID của Project cần truy vấn.

        Returns:
            List[Contract] — thường 1 record, nhưng hỗ trợ nhiều
            (MOU → NDA → R&D theo tiến trình đàm phán).
        """
        try:
            cursor = self.collection.find({"project_id": project_id}, _NO_ID)
            result = [
                contract
                for doc in cursor
                if (contract := self._doc_to_contract(doc)) is not None
            ]
            logger.debug(
                "[ContractRepository.get_by_project_id] "
                "project_id='%s' → %d contract(s).",
                project_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ContractRepository.get_by_project_id] "
                "Lỗi MongoDB (project_id='%s'): %s.", project_id, str(exc),
            )
            return []

    def get_by_expert_id(self, expert_id: str) -> List[Contract]:
        """
        Lấy toàn bộ Contract mà một Expert tham gia.

        MongoDB: db.contracts.find({"expert_id": expert_id}, {"_id": 0})
        Tương đương SQL: SELECT * FROM contracts WHERE expert_id = ?

        Args:
            expert_id: ID của Expert cần truy vấn.
        """
        try:
            cursor = self.collection.find({"expert_id": expert_id}, _NO_ID)
            result = [
                contract
                for doc in cursor
                if (contract := self._doc_to_contract(doc)) is not None
            ]
            logger.debug(
                "[ContractRepository.get_by_expert_id] "
                "expert_id='%s' → %d contract(s).",
                expert_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ContractRepository.get_by_expert_id] "
                "Lỗi MongoDB (expert_id='%s'): %s.", expert_id, str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, contract: Contract) -> bool:
        """
        Upsert Contract: tìm theo "id" → cập nhật hoặc tạo mới.

        MongoDB:
            db.contracts.update_one(
                {"id": contract.id},
                {"$set": contract.to_dict()},
                upsert=True
            )
        """
        try:
            result = self.collection.update_one(
                {"id": contract.id},
                {"$set": contract.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[ContractRepository.save] INSERT mới — Contract id='%s'.",
                    contract.id,
                )
            else:
                logger.info(
                    "[ContractRepository.save] UPDATE — Contract id='%s'.",
                    contract.id,
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[ContractRepository.save] Lỗi MongoDB (id='%s'): %s.",
                contract.id, str(exc),
            )
            return False
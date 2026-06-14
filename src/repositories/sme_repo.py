"""
Module  : src/repositories/sme_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : SMERepository — toàn bộ thao tác đọc/ghi SME trên MongoDB.

THAY ĐỔI SO VỚI PHIÊN BẢN JSON:
    ① Bỏ kế thừa JsonRepository.
    ② get_by_industry() → $regex + $options:"i" thay cho Python lower() + in.
    ③ save()            → update_one upsert=True.

Collection: broker4_db.smes
Index nên tạo:
    db.smes.createIndex({ "id": 1 },       { unique: true })
    db.smes.createIndex({ "industry": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.sme import SME

logger = logging.getLogger(__name__)

_NO_ID: dict = {"_id": 0}


class SMERepository:
    """Repository chuyên biệt cho entity SME trên MongoDB Atlas."""

    def __init__(self) -> None:
        self.collection: Collection = get_db()["smes"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_sme(self, doc: dict) -> Optional[SME]:
        doc.pop("_id", None)
        try:
            return SME.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[SMERepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[SME]:
        """
        Lấy toàn bộ danh sách SME.

        MongoDB: db.smes.find({}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                sme
                for doc in cursor
                if (sme := self._doc_to_sme(doc)) is not None
            ]
            logger.debug(
                "[SMERepository.get_all] Lấy được %d SME(s).", len(result)
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[SMERepository.get_all] Lỗi MongoDB: %s. Trả về [].", str(exc)
            )
            return []

    def get_by_id(self, sme_id: str) -> Optional[SME]:
        """
        Tìm SME theo string ID.

        MongoDB: db.smes.find_one({"id": sme_id}, {"_id": 0})
        """
        try:
            doc = self.collection.find_one({"id": sme_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[SMERepository.get_by_id] Không tìm thấy id='%s'.", sme_id
                )
                return None
            return self._doc_to_sme(doc)

        except PyMongoError as exc:
            logger.error(
                "[SMERepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                sme_id, str(exc),
            )
            return None

    def get_by_industry(self, industry_keyword: str) -> List[SME]:
        """
        Tìm SME theo từ khóa ngành — substring match, không phân biệt hoa/thường.

        MongoDB:
            db.smes.find({
                "industry": { "$regex": keyword, "$options": "i" }
            }, {"_id": 0})

        $options "i" = case-insensitive, thay thế hoàn toàn cho
        Python's keyword.lower() + "in" logic ở phiên bản JSON cũ.

        Args:
            industry_keyword: Từ khóa tìm kiếm (vd: "dệt may", "nông nghiệp").
        """
        try:
            query = {
                "industry": {
                    "$regex": industry_keyword.strip(),
                    "$options": "i",
                }
            }
            cursor = self.collection.find(query, _NO_ID)
            result = [
                sme
                for doc in cursor
                if (sme := self._doc_to_sme(doc)) is not None
            ]
            logger.debug(
                "[SMERepository.get_by_industry] keyword='%s' → %d SME(s).",
                industry_keyword, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[SMERepository.get_by_industry] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, sme: SME) -> bool:
        """
        Upsert SME: tìm theo "id" → cập nhật hoặc tạo mới.

        MongoDB:
            db.smes.update_one(
                {"id": sme.id},
                {"$set": sme.to_dict()},
                upsert=True
            )
        """
        try:
            result = self.collection.update_one(
                {"id": sme.id},
                {"$set": sme.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[SMERepository.save] INSERT mới — SME id='%s'.", sme.id
                )
            else:
                logger.info(
                    "[SMERepository.save] UPDATE — SME id='%s'.", sme.id
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[SMERepository.save] Lỗi MongoDB (id='%s'): %s.",
                sme.id, str(exc),
            )
            return False
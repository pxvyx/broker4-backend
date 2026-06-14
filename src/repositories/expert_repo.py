"""
Module  : src/repositories/expert_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ExpertRepository — toàn bộ thao tác đọc/ghi Expert trên MongoDB.

THAY ĐỔI SO VỚI PHIÊN BẢN JSON:
    ① Bỏ kế thừa JsonRepository — kết nối thẳng MongoDB.
    ② get_by_specialty()     → $regex trên mảng specialties.
    ③ get_by_technology()    → $regex trên mảng expertise.
    ④ get_available()        → query {"available": True}.
    ⑤ update_availability()  → update_one + $set (không đọc lại toàn bộ collection).
    ⑥ save()                 → update_one upsert=True.

Collection: broker4_db.experts
Index nên tạo:
    db.experts.createIndex({ "id": 1 },           { unique: true })
    db.experts.createIndex({ "available": 1 })
    db.experts.createIndex({ "specialties": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.expert import Expert

logger = logging.getLogger(__name__)

_NO_ID: dict = {"_id": 0}


class ExpertRepository:
    """Repository chuyên biệt cho entity Expert trên MongoDB Atlas."""

    def __init__(self) -> None:
        self.collection: Collection = get_db()["experts"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_expert(self, doc: dict) -> Optional[Expert]:
        """
        Chuyển MongoDB document thành Expert object.
        Loại bỏ _id trước khi parse để tránh lỗi Model.
        """
        doc.pop("_id", None)
        try:
            return Expert.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[ExpertRepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Expert]:
        """
        Lấy toàn bộ danh sách Expert.

        MongoDB: db.experts.find({}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                expert
                for doc in cursor
                if (expert := self._doc_to_expert(doc)) is not None
            ]
            logger.debug(
                "[ExpertRepository.get_all] Lấy được %d expert(s).", len(result)
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.get_all] Lỗi MongoDB: %s. Trả về [].", str(exc)
            )
            return []

    def get_by_id(self, expert_id: str) -> Optional[Expert]:
        """
        Tìm Expert theo string ID.

        MongoDB: db.experts.find_one({"id": expert_id}, {"_id": 0})
        """
        try:
            doc = self.collection.find_one({"id": expert_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[ExpertRepository.get_by_id] Không tìm thấy id='%s'.", expert_id
                )
                return None
            return self._doc_to_expert(doc)

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                expert_id, str(exc),
            )
            return None

    def get_by_specialty(self, specialty: str) -> List[Expert]:
        """
        Tìm Expert có chuyên môn khớp với từ khóa.
        Dùng $regex trên mảng specialties — MongoDB tự duyệt từng phần tử.

        MongoDB:
            db.experts.find({
                "specialties": { "$regex": keyword, "$options": "i" }
            }, {"_id": 0})

        Args:
            specialty: Từ khóa chuyên môn (vd: "Machine Learning", "AI").
        """
        try:
            query = {
                "specialties": {
                    "$regex": specialty.strip(),
                    "$options": "i",   # case-insensitive
                }
            }
            cursor = self.collection.find(query, _NO_ID)
            result = [
                expert
                for doc in cursor
                if (expert := self._doc_to_expert(doc)) is not None
            ]
            logger.debug(
                "[ExpertRepository.get_by_specialty] keyword='%s' → %d kết quả.",
                specialty, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.get_by_specialty] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    def get_available(self) -> List[Expert]:
        """
        Lấy danh sách Expert đang sẵn sàng nhận dự án.

        MongoDB: db.experts.find({"available": true}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({"available": True}, _NO_ID)
            result = [
                expert
                for doc in cursor
                if (expert := self._doc_to_expert(doc)) is not None
            ]
            logger.debug(
                "[ExpertRepository.get_available] %d expert(s) đang available.",
                len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.get_available] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    def get_by_technology(self, technology: str) -> List[Expert]:
        """
        Tìm Expert theo công nghệ trong mảng `expertise`.
        Dùng $regex — MongoDB duyệt từng phần tử trong mảng.

        MongoDB:
            db.experts.find({
                "expertise": { "$regex": keyword, "$options": "i" }
            }, {"_id": 0})

        Args:
            technology: Tên công nghệ (vd: "PyTorch", "Blockchain", "ERP").
        """
        try:
            query = {
                "expertise": {
                    "$regex": technology.strip(),
                    "$options": "i",
                }
            }
            cursor = self.collection.find(query, _NO_ID)
            result = [
                expert
                for doc in cursor
                if (expert := self._doc_to_expert(doc)) is not None
            ]
            logger.debug(
                "[ExpertRepository.get_by_technology] keyword='%s' → %d kết quả.",
                technology, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.get_by_technology] Lỗi MongoDB: %s. Trả về [].",
                str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def update_availability(self, expert_id: str, available: bool) -> bool:
        """
        Cập nhật trạng thái nhận dự án của Expert — chỉ sửa đúng 1 field.

        MongoDB:
            db.experts.update_one(
                {"id": expert_id},
                {"$set": {"available": available}}
            )

        Không upsert: nếu Expert không tồn tại → log warning, trả False.
        """
        try:
            result = self.collection.update_one(
                {"id": expert_id},
                {"$set": {"available": available}},
            )

            if result.matched_count == 0:
                logger.warning(
                    "[ExpertRepository.update_availability] "
                    "Không tìm thấy Expert id='%s'. Bỏ qua cập nhật.",
                    expert_id,
                )
                return False

            logger.info(
                "[ExpertRepository.update_availability] "
                "Expert id='%s' → available=%s.", expert_id, available,
            )
            return True

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.update_availability] Lỗi MongoDB (id='%s'): %s.",
                expert_id, str(exc),
            )
            return False

    def save(self, expert: Expert) -> bool:
        """
        Upsert Expert: tìm theo "id" → cập nhật hoặc tạo mới.

        MongoDB:
            db.experts.update_one(
                {"id": expert.id},
                {"$set": expert.to_dict()},
                upsert=True
            )
        """
        try:
            result = self.collection.update_one(
                {"id": expert.id},
                {"$set": expert.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[ExpertRepository.save] INSERT mới — Expert id='%s'.", expert.id
                )
            else:
                logger.info(
                    "[ExpertRepository.save] UPDATE — Expert id='%s'.", expert.id
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[ExpertRepository.save] Lỗi MongoDB (id='%s'): %s.",
                expert.id, str(exc),
            )
            return False
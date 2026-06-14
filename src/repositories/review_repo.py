"""
Module  : src/repositories/review_repo.py
Layer   : Repositories (Data Access Layer)
Purpose : ReviewRepository — toàn bộ thao tác đọc/ghi Review trên MongoDB.

THAY ĐỔI SO VỚI PHIÊN BẢN JSON:
    ① Bỏ kế thừa JsonRepository.
    ② get_by_project_id()  → query {"project_id": project_id}.
    ③ get_by_expert_id()   → query {"reviewed_expert_id": expert_id}.
    ④ save()               → update_one upsert=True.

Collection: broker4_db.reviews
Index nên tạo:
    db.reviews.createIndex({ "id": 1 },                   { unique: true })
    db.reviews.createIndex({ "project_id": 1 })
    db.reviews.createIndex({ "reviewed_expert_id": 1 })
    db.reviews.createIndex({ "reviewer_sme_id": 1 })
"""

import logging
from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.config.db import get_db
from src.models.review import Review

logger = logging.getLogger(__name__)

_NO_ID: dict = {"_id": 0}


class ReviewRepository:
    """Repository chuyên biệt cho entity Review trên MongoDB Atlas."""

    def __init__(self) -> None:
        self.collection: Collection = get_db()["reviews"]

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _doc_to_review(self, doc: dict) -> Optional[Review]:
        doc.pop("_id", None)
        try:
            return Review.from_dict(doc)
        except (KeyError, TypeError) as exc:
            logger.warning(
                "[ReviewRepository] Bỏ qua document lỗi cấu trúc (id='%s'): %s",
                doc.get("id", "UNKNOWN"), str(exc),
            )
            return None

    # ------------------------------------------------------------------
    # Public Read methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[Review]:
        """
        Lấy toàn bộ danh sách Review.

        MongoDB: db.reviews.find({}, {"_id": 0})
        """
        try:
            cursor = self.collection.find({}, _NO_ID)
            result = [
                review
                for doc in cursor
                if (review := self._doc_to_review(doc)) is not None
            ]
            logger.debug(
                "[ReviewRepository.get_all] Lấy được %d review(s).", len(result)
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ReviewRepository.get_all] Lỗi MongoDB: %s. Trả về [].", str(exc)
            )
            return []

    def get_by_id(self, review_id: str) -> Optional[Review]:
        """
        Tìm Review theo string ID.

        MongoDB: db.reviews.find_one({"id": review_id}, {"_id": 0})
        """
        try:
            doc = self.collection.find_one({"id": review_id}, _NO_ID)
            if doc is None:
                logger.debug(
                    "[ReviewRepository.get_by_id] Không tìm thấy id='%s'.", review_id
                )
                return None
            return self._doc_to_review(doc)

        except PyMongoError as exc:
            logger.error(
                "[ReviewRepository.get_by_id] Lỗi MongoDB (id='%s'): %s.",
                review_id, str(exc),
            )
            return None

    def get_by_project_id(self, project_id: str) -> List[Review]:
        """
        Lấy toàn bộ Review của một Project.

        MongoDB: db.reviews.find({"project_id": project_id}, {"_id": 0})
        Tương đương SQL: SELECT * FROM reviews WHERE project_id = ?

        Args:
            project_id: ID của Project cần truy vấn.
        """
        try:
            cursor = self.collection.find({"project_id": project_id}, _NO_ID)
            result = [
                review
                for doc in cursor
                if (review := self._doc_to_review(doc)) is not None
            ]
            logger.debug(
                "[ReviewRepository.get_by_project_id] "
                "project_id='%s' → %d review(s).",
                project_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ReviewRepository.get_by_project_id] "
                "Lỗi MongoDB (project_id='%s'): %s.", project_id, str(exc),
            )
            return []

    def get_by_expert_id(self, expert_id: str) -> List[Review]:
        """
        Lấy toàn bộ Review mà một Expert nhận được.
        Dùng để tính rating trung bình cho Expert ở tầng Service.

        MongoDB:
            db.reviews.find({"reviewed_expert_id": expert_id}, {"_id": 0})
        Tương đương SQL: SELECT * FROM reviews WHERE reviewed_expert_id = ?

        Args:
            expert_id: ID của Expert cần truy vấn.
        """
        try:
            cursor = self.collection.find(
                {"reviewed_expert_id": expert_id}, _NO_ID
            )
            result = [
                review
                for doc in cursor
                if (review := self._doc_to_review(doc)) is not None
            ]
            logger.debug(
                "[ReviewRepository.get_by_expert_id] "
                "expert_id='%s' → %d review(s).",
                expert_id, len(result),
            )
            return result

        except PyMongoError as exc:
            logger.error(
                "[ReviewRepository.get_by_expert_id] "
                "Lỗi MongoDB (expert_id='%s'): %s.", expert_id, str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Public Write methods
    # ------------------------------------------------------------------

    def save(self, review: Review) -> bool:
        """
        Upsert Review: tìm theo "id" → cập nhật hoặc tạo mới.

        MongoDB:
            db.reviews.update_one(
                {"id": review.id},
                {"$set": review.to_dict()},
                upsert=True
            )
        """
        try:
            result = self.collection.update_one(
                {"id": review.id},
                {"$set": review.to_dict()},
                upsert=True,
            )

            if result.upserted_id is not None:
                logger.info(
                    "[ReviewRepository.save] INSERT mới — Review id='%s'.", review.id
                )
            else:
                logger.info(
                    "[ReviewRepository.save] UPDATE — Review id='%s'.", review.id
                )
            return True

        except PyMongoError as exc:
            logger.error(
                "[ReviewRepository.save] Lỗi MongoDB (id='%s'): %s.",
                review.id, str(exc),
            )
            return False